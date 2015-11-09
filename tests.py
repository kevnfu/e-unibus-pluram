from main import *


class TestHandler(BaseHandler):
    def get(self):
        series_ids = [1408, 56570]

        changes_ids = TMDB.tv_changes_ids()
        series_list = list()
        for changes_id in changes_ids[0:]:
            series = Series.from_json(TMDB.series(changes_id))
            series_list.append(series)

        series_names = map(lambda x: x.name(), series_list)

        self.render_json(series_names)

    def sync(self):
        database.sync_with_tmdb()

    def delete(self):
        database.delete_all_entries()

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
    webapp2.Route('/special/delete', handler=TestHandler,handler_method="delete"),
    webapp2.Route('/test/sync', handler=TestHandler, handler_method="sync"),
    (decorator.callback_path, decorator.callback_handler())
], debug=True)