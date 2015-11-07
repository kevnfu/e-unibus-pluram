import os
import json
import cgi
import logging
from datetime import datetime, timedelta

from urllib import urlencode
from google.appengine.api import urlfetch
from google.appengine.api import memcache

from utilities import load_secret

BASE_URL = 'http://api.themoviedb.org/3'
API_KEY = load_secret('tmdb-key.txt')
api_param = {'api_key':API_KEY}
headers = {
  'Accept': 'application/json'
}

def cgi_space_escape(text):
    """cgi escape w/ additional escape for spaces"""
    return cgi.escape(text, quote=True).replace(' ', '%20')

class TMDB:
    @classmethod
    def fetch_json(cls, url):
        r = urlfetch.fetch(url=url, headers={'Accept':'application/json'})
        if r.status_code != 200:
            logging.error("urlfetch error in TMDB")
            return None

        return json.loads(r.content)

    @classmethod
    def search_tv(cls, title):
        # TODO deal w/ multiple pages
        title = cgi_space_escape(title)
        url = BASE_URL + "/search/tv?api_key={key}&query={title}" 
        url = url.format(title=title, key=API_KEY)
        resp_json = cls.fetch_json(url)
        return resp_json.get('results')
        

    @classmethod
    def series(cls, tvid):
        url = (BASE_URL + 
            '/tv/{tvid}?api_key={key}'
            '&append_to_response=external_ids')
        url = url.format(tvid=str(tvid), key=API_KEY)
        return cls.fetch_json(url)

    @classmethod
    def season(cls, tvid, season_number):
        url = BASE_URL + '/tv/{tvid}/season/{num}?api_key={key}'
        url = url.format(tvid=str(tvid), num=str(season_number), key=API_KEY)
        return cls.fetch_json(url)

    @classmethod
    def episode(cls, tvid, season_number, episode_number):
        url = (BASE_URL +
            '/tv/{tvid}/season/{season_number}'
            '/episode/{episode_number}?api_key={key}')
        url = url.format(tvid=str(tvid), season_number=str(season_number), 
            episode_number=str(episode_number), key=API_KEY)
        return cls.fetch_json(url)

    @classmethod
    def configuration(cls):
        url = (BASE_URL + "/configuration?api_key={key}")
        url = url.format(key=API_KEY)
        return cls.fetch_json(url)

    @classmethod
    def changes(cls, series_id, start_date=None):
        """By default, gives last 24 hours"""
        if start_date is None:
            url = (BASE_URL + "/tv/{id}/changes?api_key={key}")
            url = url.format(id=series_id, key=API_KEY)
        else:
            url = (BASE_URL + 
                "/tv/{id}/changes?api_key={key}&start_date={start_date}")
            url = url.format(id=series_id, start_date=start_date, key=API_KEY)

        return cls.fetch_json(url)
