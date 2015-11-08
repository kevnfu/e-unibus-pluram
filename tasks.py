import webapp2
from database import database

class TaskHandler(webapp2.RequestHandler):
    def sync(self):
        database.sync_with_tmdb()


app = webapp2.WSGIApplication([
    webapp2.Route('/tasks/sync', handler=TaskHandler, handler_method="sync")
], debug=True)