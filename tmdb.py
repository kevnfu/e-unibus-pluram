import os
import json
import cgi
import logging
import time
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
        """
        Contacts the TMDb server. 
        Handles rate-limiting conditions
        """
        r = urlfetch.fetch(url=url, headers={'Accept':'application/json'})
        logging.info("urlfetch: %s" % url)

        # too many requests from this ip. cool off.
        if r.status_code == 429:
            retry_after = int(r.headers.get('retry-after'))
            time.sleep(retry_after + 1)
            r = urlfetch.fetch(url=url, headers={'Accept':'application/json'})

        if r.status_code != 200:
            logging.error(
                "urlfetch error 200 in TMDd: %s \nHeaders: %s, \nContent: %s" % 
                (url, str(r.headers), r.content))
            return None
        data = json.loads(r.content)
        return data

    @classmethod
    def search_tv(cls, title):
        # TODO: deal w/ multiple pages
        title = cgi_space_escape(title)
        url = BASE_URL + "/search/tv?api_key={key}&query={title}" 
        url = url.format(title=title, key=API_KEY)
        resp_json = cls.fetch_json(url)
        return resp_json.get('results')
        
    @classmethod
    def series(cls, series_id):
        url = (BASE_URL + 
            '/tv/{series_id}?api_key={key}'
            '&append_to_response=external_ids')
        url = url.format(series_id=str(series_id), key=API_KEY)
        return cls.fetch_json(url)

    @classmethod
    def season(cls, series_id, season_number):
        url = BASE_URL + '/tv/{series_id}/season/{num}?api_key={key}'
        url = url.format(series_id=str(series_id), num=str(season_number), key=API_KEY)
        return cls.fetch_json(url)

    @classmethod
    def episode(cls, series_id, season_number, episode_number):
        url = (BASE_URL +
            '/tv/{series_id}/season/{season_number}'
            '/episode/{episode_number}?api_key={key}')
        url = url.format(series_id=str(series_id), season_number=str(season_number), 
            episode_number=str(episode_number), key=API_KEY)
        return cls.fetch_json(url)

    @classmethod
    def configuration(cls):
        url = (BASE_URL + "/configuration?api_key={key}")
        url = url.format(key=API_KEY)
        return cls.fetch_json(url)

    @classmethod
    def tv_changes(cls, page):
        url = (BASE_URL + '/tv/changes?api_key={key}&page={page}')
        url = url.format(key=API_KEY, page=str(page))
        return cls.fetch_json(url)

    @classmethod
    def tv_changes_ids(cls, start_date=None):
        """
        Gives a list containing the ids of series that have changed
        in the last 24hrs
        """
        # TODO implement start_date
        data = cls.tv_changes(1)
        results = data.get('results')
        total_pages = data.get('total_pages')
        for page in range(2, total_pages+1):
            results.extend(cls.tv_changes(page).get('results'))

        ids = list()
        for item in results:
            ids.append(str(item.get('id')))
        return ids

    @classmethod
    def series_changes(cls, series_id, start_date=None):
        """By default, gives last 24 hours"""
        if start_date is None:
            url = (BASE_URL + "/tv/{id}/changes?api_key={key}")
            url = url.format(id=series_id, key=API_KEY)
        else:
            url = (BASE_URL + 
                "/tv/{id}/changes?api_key={key}&start_date={start_date}")
            url = url.format(id=series_id, start_date=start_date, key=API_KEY)

        return cls.fetch_json(url)

    @classmethod
    def season_changes(cls, season_id, start_date=None):
        if start_date is None:
            url = (BASE_URL + "/tv/season/{id}/changes?api_key={key}")
            url = url.format(id=season_id, key=API_KEY)
        else:
            url = (BASE_URL + 
                "/tv/season/{id}/changes?api_key={key}&start_date={start_date}")
            url = url.format(id=season_id, start_date=start_date, key=API_KEY)

        return cls.fetch_json(url)

    @classmethod
    def episode_changes(cls, episode_id, start_date=None):
        if start_date is None:
            url = (BASE_URL + "/tv/episode/{id}/changes?api_key={key}")
            url = url.format(id=episode_id, key=API_KEY)
        else:
            url = (BASE_URL + 
                "/tv/episode/{id}/changes?api_key={key}&start_date={start_date}")
            url = url.format(id=episode_id, start_date=start_date, key=API_KEY)

        return cls.fetch_json(url)