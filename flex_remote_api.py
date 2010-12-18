# -*- coding: utf-8 -*-

from google.appengine.ext import db
from google.appengine.api import taskqueue

from google.appengine.api import datastore
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import search

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import datetime
import pickle
import base64

class FlexRemoteApiJob(db.Model):
    created_at = db.DateTimeProperty(auto_now_add=True)
    started_at = db.DateTimeProperty()
    finished_at = db.DateTimeProperty()
    definitions = db.TextProperty()
    context = db.TextProperty()
    eval_line = db.TextProperty()
    result = db.TextProperty()
    # start-stop-position, and so on...


class FlexRemoteApiExecuteCallHandler(webapp.RequestHandler):
    def post(self):
        ___job = FlexRemoteApiJob.get_by_id(int(self.request.get('id')))
        if not ___job:
            self.response.set_status(404)
            return
        if ___job.started_at:
            self.response.set_status(304)
            return
        exec(base64.b64decode(___job.definitions), globals())
        # ep_func = pickle.loads(base64.b64decode(job.entrypoint_function))
        # ep_args = pickle.loads(base64.b64decode(job.entrypoint_arguments))
        # ep_keys = pickle.loads(base64.b64decode(job.entrypoint_keywords))
        # ep_func.func_globals.update(pickle.loads(base64.b64decode(job.context)))
        globals().update(pickle.loads(base64.b64decode(___job.context)))

        ___job.started_at = datetime.datetime.now()
        ___job.put()

        # job.result = base64.b64encode(pickle.dumps(ep_func(*ep_args, **ep_keys)))
        ___result = eval(base64.b64decode(___job.eval_line), globals())
        ___job.result = base64.b64encode(pickle.dumps(___result))
        ___job.finished_at = datetime.datetime.now()
        ___job.put()
        self.response.set_status(200)


class FlexRemoteApiCreateCallHandler(webapp.RequestHandler):
    def post(self):
        params = pickle.loads(self.request.body)
        job = FlexRemoteApiJob(
            definitions = db.Text(params['definitions']),
            context = db.Text(params['context']),
            eval_line = db.Text(params['eval_line'])
            # entrypoint_function = db.Text(params['entrypoint_function']),
            # entrypoint_arguments = db.Text(params['entrypoint_arguments']),
            # entrypoint_keywords = db.Text(params['entrypoint_keywords'])
        )
        # if not job.entrypoint_function:
        #     self.response.set_status(406)
        #     return
        job.put()
        taskqueue.add(url='/_ex_ah/flex_remote_api/execute',
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

    
    
