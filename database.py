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

        air_date_str = json.get('first_air_date') or None;
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

    def to_json(self):
        seasons_json = {k:v.to_json() for k,v in self.seasons.items()}
        json = {k:self.json[k] for k in 
            ('id', 'name', 'poster_path', 'first_air_date', 'number_of_seasons')}
        json.update({'seasons':seasons_json})
        return json

    def seasons_json(self):
        seasons_json = {k:v.to_json() for k,v in self.seasons.items()}
        json = {'seasons' : seasons_json}
        return json

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
    
    def to_json(self):
        episode_json = {k:v.to_json() for k,v in self.episodes.items()}
        json = {k:self.json[k] for k in ['id', 'air_date']}
        json.update({'episodes':episode_json})
        return json


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

    def to_json(self):
        json = {k:self.json[k] for k in 
            ('name', 'air_date')}
        return json

    def get_id(self):
        return self.json.get('id')

    def number(self):
        return self.json.get('episode_number')

    def name(self):
        return self.json.get('name')

    def air_date(self):
        return self.json.get('air_date')

    def aired(self, within=7):
        air_str = self.json.get('air_date')
        if air_str is None:
            return False
        air_date = datetime.strptime(air_str, "%Y-%m-%d")
        return air_date <= (datetime.now() + timedelta(within))

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

# class BaseRating(object):
#     """
#     ID field should match ID of the user this rating is for
#     """
#     def __init__(self, rating_id, value, date=None):
#         self.id = int(rating_id)
#         self.value = int(value)
#         self.date = date or datetime.now()

#     def watchlisted(self):
#         return self.value == RatingCode.WATCHLIST

#     def watched(self):
#         return self.value == RatingCode.WATCHED

#     def set(self, value):
#         self.value = value
#         self.date = datetime.now()

class BaseRating(object):
    def __init__(self):
        self.rating = 0
        self.rated = datetime.now()
        self.added = datetime.now()

    def to_json(self):
        return {'rating':self.rating}

    def rate(self, value):
        if value is None:
            return
        self.rated = datetime.now()
        self.rating = value


class SeriesRating(BaseRating):
    def __init__(self, series_id, series_name, tracking=True):
        super(SeriesRating, self).__init__()
        self.id = int(series_id)
        self.name = series_name
        self.tracking = tracking
        self.seasons = dict()

    def to_json(self):
        ret = super(SeriesRating, self).to_json()
        ret.update({'id':self.id, 'name':self.name, 'tracking':self.tracking})
        ret.update({'seasons':{k:v.to_json() for k,v in self.seasons.items()}})
        return ret

    def set_tracking(self, value):
        if value is None:
            return
        self.tracking = value

    def get_season(self, season_number):
        return self.seasons.setdefault(season_number, SeasonRating())

    def changes(self, c):
        self.rate(c.get('rating'))
        self.set_tracking(c.get('tracking'))

        for season_number, season_changes in c['seasons'].items():
            self.get_season(season_number).changes(season_changes)

    def rate_season(self, season_number, value):
        self.get_season(season_number).rate(value)

    def rate_episode(self, season_number, episode_number, value):
        self.get_season(season_number).get_episode(episode_number).rate(value)


class SeasonRating(BaseRating):
    def __init__(self):
        super(SeasonRating, self).__init__()
        self.episodes = dict()

    def to_json(self):
        ret = super(SeasonRating, self).to_json()
        ret.update(
            {'episodes':{k:v.to_json() for k,v in self.episodes.items()}})
        return ret

    def get_episode(self, episode_number):
        return self.episodes.setdefault(episode_number, EpisodeRating())

    def changes(self, c):
        self.rate(c.get('rating'))
        for episode_number, episode_changes in c['episodes'].items():
            self.get_episode(episode_number).changes(episode_changes)

    def watched(self):
        for episode in self.episodes.values():
            if not episode.watched:
                return False

        return True

class EpisodeRating(BaseRating):
    def __init__(self, watched=False):
        super(EpisodeRating, self).__init__()
        self.watched = watched

    def to_json(self):
        ret = super(EpisodeRating, self).to_json()
        ret.update({'watched':self.watched})
        return ret

    def set_watched(self, value):
        if value is None:
            return
        self.watched = value

    def changes(self, c):
        self.rate(c.get('rating'))
        self.set_watched(c.get('watched'))

class UserRating(ndb.Model):
    """
    All ratings for a user.
    Uses the same integer_id as User.
    """
    # this will be a dict mapping series_id to SeriesRating
    series_ratings = ndb.PickleProperty()
    movie_ratings = ndb.PickleProperty()

    @classmethod
    def new(cls, user):
        return cls(id=user.get_id(), 
            series_ratings=dict(),
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

    def get_id(self):
        return self.key.string_id()

    # def add_movie_rating(self, movie_rating):
    #     self.movie_ratings[movie_rating.id] = movie_rating

    def set_series(self, series_id, series_name):
        series_id = int(series_id)
        series = SeriesRating(series_id, series_name)
        self.series_ratings[series_id] = series
        return series

    def get_series(self, series_id):
        series_id = int(series_id)
        return self.series_ratings.get(series_id)

    def get_all_series_json(self):
        return {k:v.to_json() for k,v in self.series_ratings.items()}

    def update_all_series(self, changes):
        """
        Changes is a json object
        """
        for series_id, series_changes in changes.items():
            series = self.get_series(series_id)
            if series is None:
                series = self.set_series(series_id, series_changes.get("name"))

            series.changes(series_changes)

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
        #check if already in database
        series = Series.get_by_id(series_id)
        if series is not None:
            logging.info("Tried to re-add series %d" % series_id)
            return False

        # fetch from TMDB
        series_json = TMDB.series(series_id)
        if not series_json:
            return False;

        series = Series.from_json(series_json)

        for i in range(1, series.number_of_seasons() + 1):
            season_json = TMDB.season(series_id, season_number=i)
            if not season_json:
                continue
            season = Season.from_json(season_json)
            series.set_season(season)

        series.put()
        return True

    
    @staticmethod
    def watchlist_series(series_id, series_name, user):
        """
        Returns True if successful
        Returns False if already added
        """
        user_rating = UserRating.for_user(user)
        # check if already on watchlist
        if user_rating.get_series(series_id):
            return False

        user_rating.set_series(series_id, series_name)
        user_rating.put()
        return True

    @classmethod
    def update_series(cls, series_id):
        """
        Refetches series, and refetches its seasons IF it has changes
        """
        series_id = int(series_id)
        series = Series.get_by_id(series_id)
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
        
        new_series.put()
        logging.info("Updated series: %s %s" % (series_id, series.name))
        
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










        
