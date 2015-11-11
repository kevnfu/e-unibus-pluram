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

    def get_id(self):
        return self.key.string_id()

class Series(ndb.Model):
    """
    Contains information about a TV series, its seasons and episodes.
    Use integer id from TMDB.
    All TMDB ids are unique within a collection,
    e.g. Movies, Series, Seasons, Episodes.
    """
    json = ndb.JsonProperty(required=True)
    seasons = ndb.PickleProperty()
    name = ndb.StringProperty()
    air_date = ndb.DateProperty()
    imdb_id = ndb.StringProperty()
    status = ndb.StringProperty()

    @classmethod
    def from_json(cls, json):
        # don't store season info here
        json.pop('seasons', None)

        air_date_str = json.get('first_air_date')
        air_date = (air_date_str and datetime.strptime(air_date_str, "%Y-%m-%d"))
        external_ids = json.get('external_ids')
        imdb_id = (external_ids and external_ids.get('imdb_id'))
        
        return cls(id=json.get('id'), 
            json=json, 
            seasons=dict(),
            name=json.get('name'),
            air_date=air_date,
            imdb_id=imdb_id,
            status=json.get('status'))

    def get_id(self):
        return self.key.integer_id() # == self.json.get('id')

    def number_of_seasons(self):
        return self.json.get('number_of_seasons')

    def number_of_episodes(self):
        return self.json.get('number_of_episodes')

    def poster(self):
        return self.json.get('poster_path')

    def backdrop(self):
        return self.json.get('backdrop_path')

    def overview(self):
        return self.json.get('overview')

    def get_season(self, season_number):
        return self.seasons.get(season_number)

    def set_season(self, season):
        self.seasons[season.number()] = season

    def iter_seasons(self):
        for i in sorted(self.seasons.keys()):
            yield self.get_season(i)

    def get_episode(self, season_number, episode_number):
        return self.get_season(season_number).get_episode(episode_number)

    def set_episode(self, season_number, episode):
        self.get_season(season_number).set_episode(episode)


class Season(object):
    def __init__(self, json, episodes=dict()):
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

        episodes = dict()
        for episode_json in episodes_json:
            episode = Episode.from_json(episode_json)
            episodes[episode.number()] = episode

        return cls(json=json, episodes=episodes)
    
    def get_id(self):
        return self.json.get('id')

    def name(self):
        return self.json.get('name')

    def number(self):
        return self.json.get('season_number')

    def number_of_episodes(self):
        """
        Need to add episodes before this is called
        """
        return len(self.episodes)

    def air_date(self):
        return self.json.get('air_date')

    def poster(self):
        return self.json.get('poster_path')

    def get_episode(self, episode_number):
        return self.episodes.get(episode_number)

    def set_episode(self, episode):
        self.episodes[episode.number()] = episode

    def iter_episodes(self):
        for i in sorted(self.episodes.keys()):
            yield self.get_episode(i)

class Episode(object):
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

    def aired(self):
        air_date = datetime.strptime(self.json.get('air_date'), "%Y-%m-%d")
        return air_date <= datetime.now()

    def overview(self):
        return self.json.get('overview')

    def still(self):
        return self.json.get('still_path')

    def season_number(self):
        return self.json.get('season_number')

class RatingCode:
    """
    Pseudoenum for different rating values.
    Not using enum because it's not pickleable
    """
    WATCHLIST = 200
    WATCHED = 201

class BaseRating(object):
    """
    ID field should match ID of the user this rating is for
    """
    def __init__(self, rating_id, value, date=None):
        self.id = int(rating_id)
        self.value = int(value)
        self.date = date or datetime.now()

    def watchlisted(self):
        return self.value == RatingCode.WATCHLIST

    def watched(self):
        return self.value == RatingCode.WATCHED

    def set(self, value):
        self.value = value
        self.date = datetime.now()


class UserRating(ndb.Model):
    """
    All ratings for a user.
    Uses the same integer_id as User.
    """
    # this will be a dict mapping series_id to SeriesRating
    series_ratings = ndb.PickleProperty()
    season_ratings = ndb.PickleProperty()
    episode_ratings = ndb.PickleProperty()
    movie_ratings = ndb.PickleProperty()

    @classmethod
    def new(cls, user):
        return cls(id=user.get_id(), 
            series_ratings=dict(),
            season_ratings=dict(),
            episode_ratings=dict(), 
            movie_ratings=dict())

    @classmethod
    def for_user(cls, user):
        """
        Returns the UserRating object for a user.
        Creates a new one if user hasn't rated before.
        """
        user_rating = cls.get_by_id(user.get_id())
        if user_rating is None:
            user_rating = cls.new(user)
        return user_rating

    # def add_movie_rating(self, movie_rating):
    #     self.movie_ratings[movie_rating.id] = movie_rating

    def get_all_series_id(self):
        return iter(self.series_ratings)

    def get_all_series(self):
        return self.series_ratings.iteritems()

    def set_series(self, rating):
        self.series_ratings[rating.id] = rating

    def get_series(self, series_id):
        return self.series_ratings.get(series_id)

    def set_season(self, rating):
        self.season_ratings[rating.id] = rating

    def get_season(self, season_id):
        return self.season_ratings.get(season_id)

    def set_episode(self, rating):
        self.episode_ratings[rating.id] = rating

    def get_episode(self, episode_id):
        return self.episode_ratings.get(episode_id)



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

class database:
    """
    consolidated methods to interact w/ database
    """
    @staticmethod
    def load_series(series_id):
        """
        Loads series, season, episode into db.
        """
        # TODO: handle None errors.

        # fetch from TMDB
        series_json = TMDB.series(series_id)
        series = Series.from_json(series_json)

        for i in range(1, series.number_of_seasons() + 1):
            season_json = TMDB.season(series_id, season_number=i)
            season = Season.from_json(season_json)
            series.set_season(season)

        # store
        series.put()
        return True

    
    @staticmethod
    def watchlist_series(series_id, user):
        """
        Returns True if successful
        Returns False if already added
        """
        user_rating = UserRating.for_user(user)
        # check if already on watchlist
        if user_rating.get_series(series_id):
            return False

        rating = BaseRating(series_id, RatingCode.WATCHLIST)
        user_rating.set_series(rating)
        user_rating.put()
        return True
    
    @classmethod
    def sync_with_tmdb(cls):
        """
        Reloads shows to db that were changed in the last 24 hours
        """
        # Get changed ids from tmdb
        changed_ids = TMDB.tv_changed_ids()

        # track # of changes
        updated_count = AppStat.get_by_id("daily_sync_count")
        if not updated_count:
            updated_count = AppStat(id="daily_sync_count", 
                description="Number of seasons updated last night")
        updated_count.value = 0

        # if a show in db changed, update
        new_series_list = list()
        for changed_id in changed_ids:
            series = Series.get_by_id(changed_id)
            if series:
                new_series = cls.update_series(series)
                new_series_list.append(new_series)
                logging.info("Updated series: %s" % changed_id)

        updated_count.value = len(new_series_list)
        updated_count.put()

        ndb.put_multi(new_series_list)
        return

    @classmethod
    def update_series(cls, series):
        """
        Refetches series, and refetches its seasons IF it has changes
        """
        series_id = series.get_id()
        seasons_changed = TMDB.seasons_changed_in_series(series_id)
        for season_number in seasons_changed:
            # refetch seasons that have changed
            new_season = Season.from_json(
                TMDB.season(series_id, season_number))

            # store the season
            series.set_season(new_season)

        # refetch series
        new_series = Series.from_json(TMDB.series(series_id))
        
        # store seasons
        new_series.seasons = series.seasons
        
        return new_series

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










        
