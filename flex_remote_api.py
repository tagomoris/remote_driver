# -*- coding: utf-8 -*-

from google.appengine.ext import db
from google.appengine.api import taskqueue

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import datetime
import pickle

class FlexRemoteApiJob(db.Model):
    created_at = db.DateTimeProperty(auto_now_add=True)
    started_at = db.DateTimeProperty()
    finished_at = db.DateTimeProperty()
    definitions = db.TextProperty()
    context = db.TextProperty()
    entrypoint_function = db.StringProperty()
    entrypoint_arguments = db.TextProperty()
    result = db.TextProperty()
    # start-stop-position, and so on...


class FlexRemoteApiExecuteCallHandler(webapp.RequestHandler):
    def post(self):
        job = FlexRemoteApiJob.get_by_id(int(self.request.get('id')))
        if not job:
            self.response.set_status(404)
            return
        if job.started_at:
            self.response.set_status(304)
            return
        exec definitions
        ep_func = pickle.loads(job.entrypoint_function)
        ep_args = pickle.loads(job.entrypoint_arguments)
        # post.func_globals.update(pickle.loads(job.context))
        # _global_context = pickle.loads(job.context)
        ep_func.func_globals.update(pickle.loads(job.context))

        job.started_at = datetime.datetime.now()
        job.put()

        job.result = pickle.dumps(ep_func(ep_args))
        job.finished_at = datetime.datetime.now()
        self.response.set_status(200)


class FlexRemoteApiCreateCallHandler(webapp.RequestHandler):
    def post(self):
        req = self.request
        job = FlexRemoteApiJob(
            definitions = req.get('definitions'),
            context = req.get('context'),
            entrypoint_function = req.get('entrypoint_function'),
            entrypoint_arguments = req.get('entrypoint_arguments'))
        if not job.entrypoint_function:
            self.response.set_status(406)
            return
        job.put()
        taskqueue.add(name='exec_flex_remote_api_job',
                      url='/_ex_ah/flex_remote_api/execute',
                      params={'id':str(job.key().id())})
        self.response.out.write(str(job.key().id()))


class FlexRemoteApiStatusCallHandler(webapp.RequestHandler):
    def get(self):
        job = FlexRemoteApiJob.get_by_id(self.request.get('id'))
        if not job:
            self.response.set_status(404)
        elif not job.finished_at:
            self.response.set_status(304)
        else:
            self.response.set_status(200)
            self.response.out.write(job.result)
        

application = webapp.WSGIApplication([
    ('/_ex_ah/flex_remote_api/create', FlexRemoteApiCreateCallHandler),
    ('/_ex_ah/flex_remote_api/status', FlexRemoteApiStatusCallHandler),
    ('/_ex_ah/flex_remote_api/execute', FlexRemoteApiExecuteCallHandler),
    ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()

    
    
