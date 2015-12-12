import webapp2
from database import database, Series
from google.appengine.api import taskqueue

class TaskHandler(webapp2.RequestHandler):
    def sync(self):
        database.sync_with_tmdb()

    def load_series(self):
        series_id = self.request.get('series_id')

        database.load_series(series_id)


    @staticmethod
    def add_load_series(series_id):
        taskqueue.add(url="/tasks/load_series", 
            params={'series_id':series_id},
            retry_options=taskqueue.TaskRetryOptions(task_retry_limit=5))    


app = webapp2.WSGIApplication([
    webapp2.Route('/tasks/load_series', 
        handler=TaskHandler, handler_method="load_series", methods=['POST']),
    webapp2.Route('/tasks/sync', handler=TaskHandler, handler_method="sync")
], debug=True)