#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""An interactive python shell that uses remote_api, with flex_remote_api calls.

Usage:
  flex_remote_api_shell.py APPENGINE_SDK_PATH APPID [PATH]
"""

import os
import sys

if not hasattr(sys, 'version_info'):
    sys.stderr.write('Very old versions of Python are not supported. Please '
                     'use version 2.5 or greater.\n')
    sys.exit(1) 
version_tuple = tuple(sys.version_info[:2])
if version_tuple < (2, 4):
    sys.stderr.write('Error: Python %d.%d is not supported. Please use '
                     'version 2.5 or greater.\n' % version_tuple)
    sys.exit(1)
if version_tuple == (2, 4):
    sys.stderr.write('Warning: Python 2.4 is not supported; this program may '
                     'break. Please use version 2.5 or greater.\n')

if len(sys.argv) < 3:
    print __doc__
    sys.exit(0)
    
SDK_PATH = os.path.abspath(os.path.realpath(sys.argv[1]))
if sys.argv[1] is None or not os.path.join(SDK_PATH, 'google'):
    sys.stderr.write("Error: Invalid Google AppEngine SDK path: '%s'\n" % sys.argv[1])
    sys.exit(1)

CURRENT_DIR_PATH = os.path.abspath('.')
EXTRA_PATHS = [
    CURRENT_DIR_PATH,
    SDK_PATH,
    os.path.join(SDK_PATH, 'lib', 'antlr3'),
    os.path.join(SDK_PATH, 'lib', 'django'),
    os.path.join(SDK_PATH, 'lib', 'fancy_urllib'),
    os.path.join(SDK_PATH, 'lib', 'ipaddr'),
    os.path.join(SDK_PATH, 'lib', 'webob'),
    os.path.join(SDK_PATH, 'lib', 'yaml', 'lib'),
]

sys.path = EXTRA_PATHS + sys.path

from google.appengine.tools import os_compat

import atexit
import code
import getpass
import optparse

# readline is needed
import readline
import re
import codeop
import pickle
import base64
import time

from google.appengine.api import datastore
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.api import taskqueue
from google.appengine.ext import db
from google.appengine.ext import search

from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.tools import appengine_rpc

HISTORY_PATH = os.path.expanduser('~/.remote_api_shell_history')
DEFAULT_PATH = '/_ah/remote_api'
BANNER = """App Engine remote_api shell with flex_remote_api_shell
Python %s
The db, users, urlfetch, and memcache modules are imported.""" % sys.version


class FlexRemoteApiJob(db.Model):
    created_at = db.DateTimeProperty(auto_now_add=True)
    started_at = db.DateTimeProperty()
    finished_at = db.DateTimeProperty()
    definitions = db.TextProperty()
    context = db.TextProperty()
    eval_line = db.TextProperty()
    result = db.TextProperty()


__remote_api_auth_pair = ()

def __auth_func():
    global __remote_api_auth_pair
    __remote_api_auth_pair = (raw_input('Email: '), getpass.getpass('Password: '))
    return __remote_api_auth_pair

def __cached_auth_func():
    if __remote_api_auth_pair:
        return __remote_api_auth_pair
    return __auth_func()


def __try_compile(lines):
    try:
        if codeop.compile_command("\n".join(lines) + "\n"):
            return True
        else:
            return None
    except (SyntaxError, OverflowError, ValueError):
        return False


__readline_history_session_start = 0

def __gather_definitions():
    definition_lines = []
    block = []
    block_force_continuous = False
    for index in range(__readline_history_session_start, readline.get_current_history_length()):
        line = readline.get_history_item(index)
        if len(block) > 0 and (block_force_continuous or line.startswith(' ')):
            r = __try_compile(block + [line])
            if r is True:
                block.append(line)
                block_force_continuous = False
                continue
            elif r is None:
                block.append(line)
                block_force_continuous = True
                continue
        if len(block) > 0:
            definition_lines += block
            block,block_for_definition,block_force_continuous = [],False,False

        if re.match('def |class |import |from ', line):
            r = __try_compile([line])
            if r is True:
                definition_lines.append(line)
            elif r is None:
                block.append(line)
                block_force_continuous = True
    if len(block) > 0:
        definition_lines += block
    return "\n".join(definition_lines) + "\n"


def __select_globals_to_send(context_dict):
    DESELECT_KEYS = ['BANNER', 'CURRENT_DIR_PATH', 'DEFAULT_PATH', 'EXTRA_PATHS', 'HISTORY_PATH', 'SDK_PATH',
                     '__builtins__', '__doc__', '__file__', '__name__',
                     '__flex_remote_api_server', '__readline_history_session_start', '__remote_api_auth_pair', 'version_tuple',
                     'main',
                     '__auth_func', '__cached_auth_func', '__try_compile', '__gather_definitions', '__select_globals_to_send',
                     '__run_in_remote', '__magic_input'
                     ]
    selected = {}
    for k,v in context_dict.items():
        if type(v).__name__ == 'module' or type(v).__name__ == 'classobj' or type(v).__name__ == 'type':
            continue
        if k in DESELECT_KEYS:
            continue
        selected[k] = v
    return selected

__flex_remote_api_server = None

def __run_in_remote(b64_eval_line):
    job = FlexRemoteApiJob(
        definitions = base64.b64encode(__gather_definitions()),
        context = base64.b64encode(pickle.dumps(__select_globals_to_send(globals()))),
        eval_line = b64_eval_line,
    )
    job.put()
    job_id = job.key().id()
    taskqueue.add(queue_name='FlexRemoteApiJob',
                  url='/_ex_ah/flex_remote_api/execute',
                  params={'id':str(job_id)})
    running = True
    while running:
        time.sleep(0.5)
        if FlexRemoteApiJob.get_by_id(job_id).finished_at:
            running = False
    job = FlexRemoteApiJob.get_by_id(job_id)
    delta = job.finished_at - job.started_at
    print "%f sec" % (delta.seconds * 1.0 + delta.microseconds / 1000000.0)
    return pickle.loads(base64.b64decode(job.result))


def __magic_input(prompt=''):
    line = raw_input(prompt)
    if not line.strip().startswith('remote '):
        return line
    bareline = line.strip()[len('remote '):]
    match_result = re.compile('([a-zA-Z0-9_]+)\((.*)\)$').match(bareline)
    if not match_result:
        return bareline
    return "__run_in_remote('" + base64.b64encode(match_result.group(1) + '(' + match_result.group(2) + ')') + "')"


def main(argv):
    parser = optparse.OptionParser()
    parser.add_option('-s', '--server',
                      dest='server',
                      help='The hostname your app is deployed on. '
                      'Defaults to <app_id>.appspot.com.')
    parser.add_option('--secure',
                      dest='secure',
                      action="store_true",
                      default=False,
                      help='Use HTTPS when communicating '
                      'with the server.')
    (options, args) = parser.parse_args() 

    if not args or len(args) > 3:
        print >> sys.stderr, __doc__
        if len(args) > 3:
            print >> sys.stderr, 'Unexpected arguments: %s' % args[2:]
        sys.exit(1)

    appid = args[1]
    if len(args) == 3:
        path = args[2]
    else:
        path = DEFAULT_PATH

    remote_api_stub.ConfigureRemoteApi(appid, path, __auth_func,
                                       servername=options.server,
                                       save_cookies=True, secure=options.secure)
    remote_api_stub.MaybeInvokeAuthentication()

    servername = options.server
    if not servername:
        servername = '%s.appspot.com' % (appid,)
    rpc_server = appengine_rpc.HttpRpcServer(servername,
                                             __cached_auth_func,
                                             remote_api_stub.GetUserAgent() + ' flex_remote_api_shell/0.0',
                                             remote_api_stub.GetSourceName(),
                                             save_cookies=True,
                                             debug_data=False,
                                             secure=options.secure)
    global __flex_remote_api_server
    __flex_remote_api_server = rpc_server

    os.environ['SERVER_SOFTWARE'] = 'Development (flex_remote_api_shell)/0.0'

    sys.ps1 = '%s/flex> ' % appid
    readline.parse_and_bind('tab: complete')
    atexit.register(lambda: readline.write_history_file(HISTORY_PATH))
    if os.path.exists(HISTORY_PATH):
        readline.read_history_file(HISTORY_PATH)
        readline.add_history('')
        global __readline_history_session_start
        __readline_history_session_start = readline.get_current_history_length()

    code.interact(banner=BANNER, readfunc=__magic_input, local=globals())


if __name__ == '__main__':
  main(sys.argv)
