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
    retries = db.IntergerProperty()
    # start-stop-position, and so on...


class FlexRemoteApiExecuteCallHandler(webapp.RequestHandler):
    def post(self):
        ___job = FlexRemoteApiJob.get_by_id(int(self.request.get('id')))
        if not ___job:
            self.response.set_status(404)
            return
        if ___job.started_at:
            if ___job.retries > 0:
                self.response.set_status(403)
            elif self.request.headers['X-AppEngine-TaskRetryCount'] \
                   and int(self.request.headers['X-AppEngine-TaskRetryCount']) > 0:
                ___job.retries = int(self.request.headers['X-AppEngine-TaskRetryCount'])
                ___job.put()
                self.response.set_status(403)
            else:
                self.response.set_status(304)
            return

        exec(base64.b64decode(___job.definitions), globals())
        globals().update(pickle.loads(base64.b64decode(___job.context)))

        ___job.started_at = datetime.datetime.now()
        ___job.put()

        ___result = eval(base64.b64decode(___job.eval_line), globals())
        ___job.result = base64.b64encode(pickle.dumps(___result))
        ___job.finished_at = datetime.datetime.now()
        ___job.put()
        self.response.set_status(200)
        

application = webapp.WSGIApplication([
    ('/_ex_ah/flex_remote_api/execute', FlexRemoteApiExecuteCallHandler),
    ],
    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()

    
    
