#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import logging
import os
import pprint

from oauth2client.appengine import OAuth2DecoratorFromClientSecrets
from apiclient.discovery import build
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from database import *
from utilities import *
from tasks import TaskHandler

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True,
                               line_statement_prefix='#')

SCOPE = (
    'https://www.googleapis.com/auth/plus.login '
    'https://www.googleapis.com/auth/userinfo.email')

decorator = OAuth2DecoratorFromClientSecrets(
    os.path.join(os.path.dirname(__file__), 'secrets', 'client_secret.json'), 
    scope=SCOPE,
    approval_prompt='force')

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class BaseHandler(webapp2.RequestHandler):
    # cookie names
    param_id = 'user-id'

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def render_json(self, d):
        self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
        self.write(pprint.pformat(d))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, uid):
        self.set_secure_cookie(self.param_id, str(uid))

    def logout(self):
        self.response.headers.add_header(
            'Set-Cookie', '%s=; Path=/' % self.param_id)

    def initialize(self, *a, **kw):
        super(BaseHandler, self).initialize(*a, **kw)
        # provides every BaseHandler subclass with a reference to the 
        # current User
        uid = str(self.read_secure_cookie(self.param_id))
        
        if not uid:
            self.user = None
            return

        # TODO: is explicitly caching neccessary after switching to ndb?
        self.user = memcache.get(uid)
        if not self.user:
            self.user = User.get_by_id(uid)
            memcache.set(uid, self.user)

class LoginHandler(BaseHandler):
    @decorator.oauth_required
    def get(self):
        """
        Sort of login and register.
        First time user logs in they will be added to the db.
        """
        if not decorator.has_credentials():
            # direct to oauth
            url = decorator.authorize_url()
            self.render('login.html', url=url)
            return

        # check if still valid
        credentials = decorator.get_credentials()
        if credentials.access_token_expired:
            logging.info("access token expired")
            credentials.refresh(decorator.http())

        # get user info w/ oauth2
        service = build('plus', 'v1', http=decorator.http())
        people_doc = service.people().get(userId='me').execute()
        uid = str(people_doc.get('id'))
        name = str(people_doc.get('displayName'))
        
        # login user w/ cookie
        self.login(uid)

        # add new user to database
        if User.get_by_id(uid) is None:
            user = User(
                id=uid, 
                name=name,
                credentials=credentials)
            user.put()

        self.redirect('/')

class LogoutHandler(BaseHandler):
    @decorator.oauth_required
    def get(self):
        self.logout() # clear cookie
        credentials = decorator.get_credentials()
        credentials.revoke(decorator.http())
        self.redirect('/')
        
class MainHandler(BaseHandler):
    def get(self):
        # render search results
        q = self.request.get('q', None)
        if q is None:
            self.render('front.html', user=self.user)
            return

        data = TMDB.search_tv(q)
        if not data:
            self.render('front.html', 
                user=self.user, 
                q=q,
                message="No Results.")
            return

        series_list = list()
        for series_json in data:
            series_list.append(Series.from_json(series_json))

        self.render('front.html',
            poster_base=TmdbConfig.poster_path(2),
            user=self.user, 
            series_list=series_list)
            

    def post(self):
        # user clicked add to watchlist
        series_id = int(self.request.get('series_id'))
        if series_id:
            TaskHandler.add_load_series(series_id)
            added_to_watchlist = database.watchlist_series(series_id, self.user)

        if added_to_watchlist:
            self.redirect('/')
        else:
            self.render('front.html', 
                user=self.user, 
                message="Already in watchlist")
            
class AccountHandler(BaseHandler):
    def get(self):
        self.redirect('/account/watchlist')


class WatchlistHandler(BaseHandler):
    def get(self):
        # TODO: implement paging
        if self.user is None:
            self.redirect('/')

        user_rating = UserRating.for_user(self.user)
        series_rated = ([Series.get_by_id(series_id) 
            for series_id in user_rating.get_all_series_id()])
        # TODO: implement sorting options here
        
        if not series_rated:
            self.write("Nothing on watchlist<br>")
            self.write("<a href='/'>Home</a>")
            return

        self.render('watchlist.html', 
            series_rated=series_rated, 
            ur=user_rating)

    def post(self):
        if not self.user:
            self.redirect('/account/watchlist')

        user_rating = UserRating.for_user(self.user)
        watched_id = int(self.request.get('watched_id'))
        series_div = self.request.get('series_div')
        id_type = self.request.get('id_type')

        rating = BaseRating(watched_id, RatingCode.WATCHED)
        if id_type == 'season':
            user_rating.set_season(rating)
        elif id_type == 'episode':
            user_rating.set_episode(rating)

        user_rating.put()

        self.redirect('/account/watchlist#' + series_div)

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/login/?', LoginHandler),
    ('/logout/?', LogoutHandler),
    ('/account/?', AccountHandler),
    ('/account/watchlist/?', WatchlistHandler),
    (decorator.callback_path, decorator.callback_handler())
], debug=True)
