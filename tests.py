from main import *

class TestHandler(BaseHandler):
    def get(self):
        series_ids = [1408, 56570]
        nathan = 58957
        series = Series.get_by_id(nathan)
        self.render_json(series.seasons)
        season1 = Season.from_json(TMDB.season(nathan, 1))
        self.render_json(season1.get_episode(1).json)

    def spacer(self):
        self.write('\n\n')

    def changes(self):
        nathan = 58957
        self.write('Total changes:\n')
        self.render_json(len(TMDB.tv_changed_ids()))
        self.spacer()

        self.write('Seasons changed in nathan:\n')
        self.render_json(TMDB.seasons_changed_in_series(nathan))
        self.spacer()
        self.write('Episodes in season 3\n')
        season3 = Season.from_json(TMDB.season(nathan, 3))
        self.render_json([episode.json for episode in season3.iter_episodes()])
        self.spacer()
        self.write('Changes in season 3\n')
        self.render_json(TMDB.season_changes(season3.get_id()))

    def sync(self):
        database.sync_with_tmdb()

    def images(self):
        q = self.request.get('q')
        if not q:
            self.render('images-example.html')
            return

        url_list = list()
        series = Series.query().filter(Series.name==q).get()
        if not series:
            self.render('images-example.html', error_msg="Not found.")
            return

        for i in range(7):
            desc = "Series poster. Size %d" % i
            url = TmdbConfig.poster_path(i) + series.image
            url_list.append((desc, url))

        for i in range(4):
            desc = "Series backdrop. Size %d" % i
            url = TmdbConfig.backdrop_path(i) + series.backdrop
            url_list.append((desc, url))

        season = Season.query(ancestor=series.key).get()
        if season.image:
            for i in range(7):
                desc = "Season %d poster. size %d" % (season.number, i)
                url = TmdbConfig.poster_path(i) + season.image
                url_list.append((desc, url))

        episode = Episode.query(ancestor=series.key).get()
        if episode.image:
            for i in range(4):
                desc = "Episode %s poster. size %d" % (episode.name, i)
                url = TmdbConfig.poster_path(i) + episode.image
                url_list.append((desc, url))

        self.render('images-example.html', url_list=url_list)

    def populate(self):
        pass

app = webapp2.WSGIApplication([
    ('/test/?', TestHandler),
    webapp2.Route('/test/images', handler=TestHandler, handler_method="images"),
    webapp2.Route('/test/populate', handler=TestHandler, handler_method="populate"),
    webapp2.Route('/test/changes', handler=TestHandler,handler_method="changes"),
    webapp2.Route('/test/sync', handler=TestHandler, handler_method="sync")
], debug=True)