import webapp2
from database import database, Series, AppStat
from tmdb import TMDB
from google.appengine.api import taskqueue

class TaskHandler(webapp2.RequestHandler):
    def sync(self):
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
                # enqueue update series
                self.add_update_series(changed_id)
                updated_count.value += 1

        updated_count.put()
        return

    def load_series(self):
        series_id = self.request.get('series_id')
        database.load_series(series_id)

    def update_series(self):
        series_id = self.request.get('series_id')
        database.update_series(series_id)

    @staticmethod
    def add_load_series(series_id):
        taskqueue.add(url="/tasks/load_series", 
            queue_name="tmdb-queue",
            params={'series_id':series_id},
            retry_options=taskqueue.TaskRetryOptions(task_retry_limit=5))    

    @staticmethod
    def add_update_series(series_id):
        taskqueue.add(url="/tasks/update_series",
            queue_name="tmdb-queue",
            params={'series_id':series_id},
            retry_options=taskqueue.TaskRetryOptions(task_retry_limit=5))

app = webapp2.WSGIApplication([
    webapp2.Route('/tasks/load_series', 
        handler=TaskHandler, handler_method="load_series", methods=['POST']),
    webapp2.Route('/tasks/update_series', 
        handler=TaskHandler, handler_method="update_series", methods=['POST']),
    webapp2.Route('/tasks/sync', handler=TaskHandler, handler_method="sync")
], debug=True)