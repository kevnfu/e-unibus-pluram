import logging
import pickle
from enum import Enum
from google.appengine.ext import ndb
from oauth2client.appengine import CredentialsNDBProperty

from tmdb import TMDB
from datetime import datetime, timedelta

class AppStat(ndb.Model):
    """Table for getting data about server"""
    description = ndb.StringProperty(required=True)
    value = ndb.IntegerProperty()
    text = ndb.StringProperty()

class User(ndb.Model):
    """id is str(google id)"""
    name = ndb.StringProperty(required=True)
    joined = ndb.DateTimeProperty(auto_now_add=True)
    credentials = CredentialsNDBProperty()

class Series(ndb.Model):
    """
    Use integer id from TMDB.
    """
    json = ndb.JsonProperty(required=True)
    seasons = ndb.PickleProperty()

    @classmethod
    def from_json(cls, json, seasons=list()):
        # don't store season info here
        json.pop('seasons', None)
        return cls(id=json.get('id'), json=json, seasons=seasons)

    def get_id(self):
        return self.key.integer_id()

    def name(self):
        return self.json.get('name')

    def number_of_seasons(self):
        return self.json.get('number_of_seasons')

    def air_date(self):
        return self.json.get('first_air_date')

    def imdb_id(self):
        external_ids = self.json.get('external_ids')
        return external_ids and external_ids.get('imdb_id')

    def poster(self):
        return self.json.get('poster_path')

    def backdrop(self):
        return self.json.get('backdrop_path')

    def overview(self):
        return self.json.get('overview')

    def status(self):
        return self.json.get('status')

    def append_season(self, season):
        self.seasons.append(season)


class Season:
    def __init__(self, json, episodes=list()):
        self.json = json
        self.episodes = episodes

    @classmethod
    def from_json(cls, json):
        """
        TMDB includes episodes in their response for a season,
        so this method will also populate the episodes of a season.
        """
        episodes_json = json.pop('episodes', None)
        if episodes_json is None:
            return cls(json=json)

        episodes = list()
        for episode_json in episodes_json:
            episodes.append(Episode.from_json(episode_json))
        return cls(json=json, episodes=episodes)
    
    def get_id(self):
        return self.json.get('id')

    def name(self):
        return self.json.get('name')

    def number(self):
        return self.json.get('season_number')

    def number_of_episodes(self):
        return len(self.json.get('episodes'))

    def air_date(self):
        return self.json.get('air_date')

    def poster(self):
        return self.json.get('poster_path')

    def append_episode(self, episode):
        self.episodes.append(episode)

class Episode:
    def __init__(self, json):
        self.json = json

    @classmethod
    def from_json(cls, json):
        return cls(json=json)

    def get_id(self):
        return self.json.get('id')

    def number(self):
        return self.json.get('episode_number')

    def name(self):
        return self.json.get('name')

    def air_date(self):
        return self.json.get('air_date')

    def overview(self):
        return self.json.get('overview')

    def still(self):
        return self.json.get('still_path')


class SeriesRating:
    def __init__(self, series_id, value, seasons=None):
        self.id = series_id
        self.value = 0
        self.seasons = seasons

class Rating(ndb.Model):
    """
    All ratings for a user.
    Uses the same integer_id as User.
    """
    rating_type = ndb.IntegerProperty(required=True)
    value = ndb.IntegerProperty(required=True)
    children = ndb.JsonProperty()
    # static fields
    SERIES_TYPE = 0
    SEASON_TYPE = 1
    EPISODE_TYPE = 2

    WATCHLIST = 20
    WATCHED = 21

    @classmethod
    def new(cls, user):
        pass

    @classmethod
    def get_ratings_for_user(cls, user):
        return (cls
            .query(ancestor=user.key)
            .filter(cls.rating_type==cls.SERIES_TYPE)
            .fetch())

    def mark_watched(self, string_id):
        """Needs a put to store."""
        self.children[string_id] = self.WATCHED
        return self

    def watched(self, string_id):
        """Returns true if user watched this rating's seasons/episodes"""
        return self.children.get(string_id, 0) == self.WATCHED

class TmdbConfig(ndb.Model):
    """Storage place for config"""
    json = ndb.JsonProperty(required=True)
    last_modified = ndb.DateTimeProperty(auto_now=True)

    STRING_ID = 'singleton'
    REFRESH_LATENCY = 30 # days

    @classmethod
    def refetch(cls):
        data = TMDB.configuration()
        config = cls(id=cls.STRING_ID, json=data)
        config.put()
        return config

    @classmethod
    def get_config(cls):
        """Checks if config is fresh. If not, refetch"""
        config = cls.get_by_id(cls.STRING_ID)

        if not config:
            return cls.refetch()

        if ((config.last_modified - datetime.now()) > 
            timedelta(cls.REFRESH_LATENCY)):
            return cls.refetch()

        return config

    @classmethod
    def poster_path(cls, size):
        # size between 0-6
        images = cls.get_config().json.get('images')
        return (images.get('base_url') + 
            images.get('poster_sizes')[size])

    @classmethod
    def backdrop_path(cls, size):
        # size between 0-3
        images = cls.get_config().json.get('images')
        return (images.get('base_url') + 
            images.get('backdrop_sizes')[size]) 

    @classmethod
    def still_path(cls, size):
        # size between 0-3
        images = cls.get_config().json.get('images')
        return (images.get('base_url') + 
            images.get('still_sizes')[size])


class UnhandledChanges(Exception):
    """
    Raised when don't know what to do about response from
    TMDB.series_changes
    """
    pass


class database:
    """consolidated methods to interact w/ database"""
    @staticmethod
    def load_series(series_id):
        """
        Loads series, season, episode into db.
        Returns series.
        """
        # TODO handle None errors.
        series_id = int(series_id)

        #check if already in database
        series = Series.get_by_id(int(series_id))
        if series:
            return series

        # fetch from TMDB
        series_json = TMDB.series(series_id)
        series = Series.from_json(series_json)

        for i in range(1, series.number_of_seasons() + 1):
            season_json = TMDB.season(series_id, season_number=i)
            season = Season.from_json(season_json)
            series.append_season(season)

        # store series
        series.put()

        return series
    
    @staticmethod
    def watchlist_series(series, user):
        # check if already on watchlist
        if Rating.get_by_id(series.key.integer_id(), parent=user.key):
            return

        series_rating = Rating(
            parent=user.key,
            id=series.key.integer_id(),
            rating_type=Rating.SERIES_TYPE,
            value=Rating.WATCHLIST,
            children=dict()).put()
    
    @classmethod
    def sync_with_tmdb(cls):
        """
        Reloads shows to db that were changed in the last 24 hours
        """
        # Create set of all series id in database
        series_keys = Series.query().fetch(keys_only=True)
        series_ids = set(map(lambda x: x.string_id(), series_keys))

        # Get changed ids from tmdb
        changes_ids = TMDB.tv_changes_ids()

        updated_count = AppStat.get_by_id("daily_sync_count")
        if not updated_count:
            updated_count = AppStat(id="daily_sync_count", 
                description="Number of seasons updated last night")
        updated_count.value = 0


        # if a show in db changed, reload
        for changes_id in changes_ids:
            if changes_id in series_ids:
                cls.load_series(changes_id)
                logging.info("Reloaded series: %s" % changes_id)
                updated_count.value += 1

        updated_count.put()
        return

    @staticmethod
    @ndb.transactional(propagation=ndb.TransactionOptions.ALLOWED)
    def update_season(season_id, season_number, series):
        """only called by update_series"""
        # Refetch season
        season = Season.from_json(
            TMDB.season(series.key.string_id(), season_number), parent=series)
        season.put()

        # Find and update changed episodes
        changes = TMDB.season_changes(season_id).get('changes')
        for change in changes:
            if change.get('key') == 'episode':
                for action in change.get('items'):
                    # episode_id = str(action.get('value').get('episode_id'))
                    episode_num = str(action.get('value').get('episode_number'))
                    data = TMDB.episode(
                            tvid=series.key.string_id(),
                            season_number=season_number,
                            episode_number=episode_num)
                    episode = Episode.from_json(data, parent=season)
                    episode.put()

    @classmethod
    @ndb.transactional
    def update_series(cls, series_id):
        """
        Updates series and its seasons/episodes
        with TMDB.series_changes()
        """
        # Refetch series
        series = Series.from_json(TMDB.series(series_id))
        series.put()

        # Find and update changed seasons
        changed_season_nums = list()
        changes = TMDB.series_changes(series.key.string_id()).get('changes')
        for change in changes:
            if change.get('key') == 'season':
                for action in change.get('items'):
                    season_id = str(action.get('value').get('season_id'))
                    season_number = str(action.get('value').get('season_number'))
                    cls.update_season(season_id, season_number, series)


    @staticmethod
    def delete_all_entries():
        all_series_keys = Series.query().fetch(keys_only=True)
        all_season_keys = list()
        all_episode_keys = list()
        for series_key in all_series_keys:
            all_season_keys.extend(
                Season.query(ancestor=series_key).fetch(keys_only=True))
            all_episode_keys.extend(
                Episode.query(ancestor=series_key).fetch(keys_only=True))

        ndb.delete_multi(all_series_keys)
        ndb.delete_multi(all_season_keys)
        ndb.delete_multi(all_episode_keys)

        all_user_keys = User.query().fetch(keys_only=True)
        all_rating_keys = list()
        for user_key in all_user_keys:
            all_rating_keys.extend(
                Rating.query(ancestor=user_key).fetch(keys_only=True))

        ndb.delete_multi(all_rating_keys)
        ndb.delete_multi(all_user_keys)










        
