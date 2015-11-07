from google.appengine.ext import ndb
from oauth2client.appengine import CredentialsProperty
from tmdb import TMDB
from datetime import datetime, timedelta

class User(ndb.Model):
    """id is google id"""
    name = ndb.StringProperty(required=True)

class Series(ndb.Model):
    """id is from external db"""
    name = ndb.StringProperty(required=True)
    last_modified = ndb.DateTimeProperty(auto_now=True)
    air_date = ndb.StringProperty()
    imdb_id = ndb.StringProperty()
    image = ndb.StringProperty()
    backdrop = ndb.StringProperty()
    overview = ndb.StringProperty()
    status = ndb.StringProperty()

    @classmethod
    def from_json(cls, data):
        if data.get('external_ids'):
            imdb_id = data.get('external_ids').get('imdb_id')
        else:
            imdb_id = ""

        series = cls(
            id=str(data.get('id')),
            name=data.get('name'),
            air_date=data.get('first_air_date'),
            imdb_id=imdb_id,
            image=data.get('poster_path'),
            backdrop=data.get('backdrop_path'),
            overview=data.get('overview'),
            status=data.get('status'))
        return series

    def get_seasons(self):
        """Returns list of seasons"""
        return Season.query(ancestor=self.key).order(Season.number).fetch()

class Season(ndb.Model):
    """Has parent Series"""
    number = ndb.IntegerProperty(required=True)
    last_modified = ndb.DateTimeProperty(auto_now=True)
    air_date = ndb.StringProperty()
    image = ndb.StringProperty()

    @classmethod
    def from_json(cls, data, parent):
        season = cls(
            id=str(data.get('id')),
            number=data.get('season_number'),
            air_date=data.get('air_date'),
            image=data.get('poster_path'),
            parent=parent.key)
        return season

    def get_episodes(self):
        """Retuns list of episodes"""
        return Episode.query(ancestor=self.key).order(Episode.number).fetch()

class Episode(ndb.Model):
    """Has parent Season"""
    # tmdb_id = ndb.IntegerProperty(required=True)
    number = ndb.IntegerProperty(required=True)
    name = ndb.StringProperty(required=True)
    last_modified = ndb.DateTimeProperty(auto_now=True)
    air_date = ndb.StringProperty()
    overview = ndb.StringProperty()
    image = ndb.StringProperty()

    @classmethod
    def from_json(cls, data, parent):
        episode = cls(
            id=str(data.get('id')),
            number=data.get('episode_number'),
            name=data.get('name'),
            air_date=data.get('air_date'),
            overview=data.get('overview'),
            image=data.get('still_path'),
            parent=parent.key)
        return episode

class Rating(ndb.Model):
    """
    A rating for a series or movie.
    Rating includes the seasons, episodes of a series,
    under the field children.
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
        """Checks if config current. If not, refetch"""

        config = cls.get_by_id(cls.STRING_ID)

        if not config:
            return cls.refetch()

        if ((config.last_modified - datetime.now()) > 
            timedelta(cls.REFRESH_LATENCY)):
            return cls.refetch()

        return config

    @classmethod
    def poster_path(cls, size):
        images = cls.get_config().json.get('images')
        return (images.get('base_url') + 
            images.get('poster_sizes')[size])


class database:
    """consolidated of method that interact w/ database"""
    @staticmethod
    @ndb.transactional
    def load_series(series_id):
        """
        Loads series, season, episode into db.
        Returns series.
        """
        # TODO handle None errors.

        #check if already in database
        series = Series.get_by_id(str(series_id))
        if series:
            return series

        series_json = TMDB.series(series_id)
        series = Series.from_json(series_json)
        series.put()
        for i in range(1, series_json.get('number_of_seasons') + 1):
            season_json = TMDB.season(series_id, season_number=i)
            season = Season.from_json(season_json, parent=series)
            season.put()

            for episode_json in season_json.get('episodes'):
                episode = Episode.from_json(episode_json, parent=season)
                episode.put()

        return series
    
    @staticmethod
    def watchlist_series(series, user):
        # check if already on watchlist
        if Rating.get_by_id(series.key.string_id(), parent=user.key):
            return

        series_rating = Rating(
            parent=user.key,
            id=series.key.string_id(),
            rating_type=Rating.SERIES_TYPE,
            value=Rating.WATCHLIST,
            children=dict()).put()

        # seasons_key_iter = (
        #     Season.query(ancestor=series.key).iter(keys_only=True))
        # for season_key in seasons_key_iter:
        #     series_rating.children.set(
        #         season_key.string_id, )
            
        #     epiosode_key_iter = (
        #         Episode.query(ancestor=season_key).iter(keys_only=True))
        #     for episode_key in epiosode_key_iter:
        #         Rating(
        #             parent=season_rating.key,
        #             id=episode_key.string_id(),
        #             rating_type=Rating.EPISODE_TYPE,
        #             value=Rating.WATCHLIST).put()
    
    @classmethod
    def update_series(cls):
        for series_key in Series.query().fetch(keys_only=True):
            pass

    @classmethod
    def delete_all_entries(cls):
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

        all_rating_keys = list()
        for user_key in User.query().fetch(keys_only=True):
            all_rating_keys.extend(
                Rating.query(ancestor=user_key).fetch(keys_only=True))

        ndb.delete_multi(all_rating_keys)









        
