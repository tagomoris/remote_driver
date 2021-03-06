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
"""An interactive python shell that uses remote_api, with remote_driver calls.

Usage:
  remote_driver_shell.py APPENGINE_SDK_PATH APPID [PATH]
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
    os.path.join(SDK_PATH, 'lib', 'django_0_96'),
    os.path.join(SDK_PATH, 'lib', 'fancy_urllib'),
    os.path.join(SDK_PATH, 'lib', 'ipaddr'),

    os.path.join(SDK_PATH, 'lib', 'webob'),
    os.path.join(SDK_PATH, 'lib', 'yaml', 'lib'),
    os.path.join(SDK_PATH, 'lib', 'simplejson'),
    os.path.join(SDK_PATH, 'lib', 'graphy'),
]

sys.path = EXTRA_PATHS + sys.path

from google.appengine.tools import os_compat

import atexit
import code
import getpass
import optparse

# readline is needed
try:
    import readline
except ImportError:
    readline = None
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
BANNER = """App Engine remote_api shell with remote_driver_shell
Python %s
The db, users, urlfetch, and memcache modules are imported.""" % sys.version


class RemoteDriverJob(db.Model):
    created_at = db.DateTimeProperty(auto_now_add=True)
    started_at = db.DateTimeProperty()
    finished_at = db.DateTimeProperty()
    definitions = db.TextProperty()
    context = db.TextProperty()
    eval_line = db.TextProperty()
    result = db.TextProperty()
    retries = db.IntegerProperty()


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
    except StandardError:
        return False


def __check_executable_definition(lines):
    env = globals().copy()
    definitions = "\n".join(lines) + "\n"
    try:
        exec definitions in env
        return True
    except StandardError:
        return False


__readline_history_session_start = 0
__readline_history_lines = []


def __gather_definitions():
    definition_lines = []
    block = []
    block_force_continuous = False
    if readline:
        def __get_line():
            for index in range(__readline_history_session_start, readline.get_current_history_length()):
                yield readline.get_history_item(index)
    else:
        def __get_line():
            for line in __readline_history_lines:
                yield line
    for line in __get_line():
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
            elif r is False:
                block = []
                block_force_continuous = False
                continue

        if len(block) > 0:
            if __check_executable_definition(block):
                definition_lines += block
            block,block_for_definition,block_force_continuous = [],False,False

        if re.match('def |class |import |from ', line):
            r = __try_compile([line])
            if r is True:
                if __check_executable_definition([line]):
                    definition_lines.append(line)
            elif r is None:
                block.append(line)
                block_force_continuous = True
    if len(block) > 0:
        if __check_executable_definition(block):
            definition_lines += block
    return "\n".join(definition_lines) + "\n"


def __select_globals_to_send(context_dict):
    DESELECT_KEYS = ['BANNER', 'CURRENT_DIR_PATH', 'DEFAULT_PATH', 'EXTRA_PATHS', 'HISTORY_PATH', 'SDK_PATH',
                     '__builtins__', '__doc__', '__file__', '__name__',
                     '__remote_driver_server', '__readline_history_session_start', '__remote_api_auth_pair', '__running_job_id_list',
                     '__readline_history_lines',
                     'version_tuple',
                     'main',
                     'remote_sync', 'remote_async_results', 'remote_job_results',
                     '__auth_func', '__cached_auth_func', '__try_compile', '__gather_definitions', '__select_globals_to_send',
                     '__break_parenthesis', '__check_executable_definition',
                     '__run_in_remote', '__run_in_remote_sync', '__run_in_remote_async',
                     '__wait_remote_jobs', '__wait_async_remote_jobs',
                     '__magic_input'
                     ]
    selected = {}
    for k,v in context_dict.items():
        if type(v).__name__ == 'module' or type(v).__name__ == 'classobj' or type(v).__name__ == 'type':
            continue
        if k in DESELECT_KEYS:
            continue
        selected[k] = v
    return selected

__remote_driver_server = None

def __run_in_remote(b64_eval_line):
    job = RemoteDriverJob(
        definitions = base64.b64encode(__gather_definitions()),
        context = base64.b64encode(pickle.dumps(__select_globals_to_send(globals()))),
        eval_line = b64_eval_line,
        retries = 0
    )
    job.put()
    job_id = job.key().id()
    taskqueue.add(queue_name='RemoteDriverJob',
                  url='/_ex_ah/remote_driver/execute',
                  params={'id':str(job_id)})
    return job


def __wait_remote_jobs(waiting_jobs):
    running = True
    while running:
        time.sleep(0.5)
        jobs = RemoteDriverJob.get_by_id(waiting_jobs)
        if reduce(lambda x,y: x and (y.finished_at or y.retries > 0), jobs, True):
            running = False
    results = []
    for job in RemoteDriverJob.get_by_id(waiting_jobs):
        if job.finished_at:
            delta = job.finished_at - job.started_at
            print "job id: %d in %f sec" % (job.key().id(), (delta.seconds * 1.0 + delta.microseconds / 1000000.0))
            results.append(pickle.loads(base64.b64decode(job.result)))
        else:
            print "job id: %d failed, check logs on Admin Console..." % job.key().id()
            results.append(None)
    return results


def __run_in_remote_sync(b64_eval_line):
    job = __run_in_remote(b64_eval_line)
    job_id = job.key().id()
    return __wait_remote_jobs([job_id])[0]


__running_job_id_list = []

def __run_in_remote_async(b64_eval_line):
    job = __run_in_remote(b64_eval_line)
    global __running_job_id_list
    __running_job_id_list.append(job.key().id())
    print "job id: %d" % int(job.key().id())


def __wait_async_remote_jobs(*job_ids):
    if len(job_ids) < 1:
        global __running_job_id_list
        job_ids = __running_job_id_list
        results = __wait_remote_jobs(__running_job_id_list)
        __running_job_id_list = []
        return results
    return __wait_remote_jobs(job_ids)

remote_async_results = __wait_async_remote_jobs
remote_job_results = remote_async_results


def __break_parenthesis(funcname, line):
    keypart = funcname + '('
    front_position = line.find(keypart)
    start_index = front_position + len(keypart)
    end_index = -1
    parenthesis_count = 0
    for i in range(start_index,len(line)):
        char = line[i]
        if char == '(':
            parenthesis_count += 1
        elif char == ')':
            if parenthesis_count == 0:
                end_index = i
                break
            else:
                parenthesis_count -= 1
    return (front_position, start_index, end_index)


def __magic_input(prompt=''):
    line = raw_input(prompt)
    if not readline:
        global __readline_history_lines
        __readline_history_lines.append(line)
    if line == 'remote_async_wait':
        return '__wait_async_remote_jobs()'
    elif reduce(lambda x,y: x or line.startswith(y + ' '), ['remote', 'remote_sync', 'remote_async'], False):
        space_position = line.index(' ')
        directive = line[:space_position]
        bareline = line[space_position+1:]
        if directive == 'remote' or directive == 'remote_sync':
            return "__run_in_remote_sync('" + base64.b64encode(bareline) + "')"
        if directive == 'remote_async':
            return "__run_in_remote_async('" + base64.b64encode(bareline) + "')"
    elif line.find('remote_async_results()') >= 0:
        return line
    elif line.find('remote_job_results') >= 0:
        front_position, start_index, end_index = __break_parenthesis('remote_job_results', line)
        if end_index > -1:
            return line[:front_position] + "remote_job_results(" + line[start_index:end_index] + ")" + line[end_index+1:]
    elif line.find('remote_sync(') >= 0:
        front_position, start_index, end_index = __break_parenthesis('remote_sync', line)
        if end_index > -1:
            eval_b64_line = base64.b64encode(line[start_index:end_index])
            return line[:front_position] + "__run_in_remote_sync('" + eval_b64_line + "')" + line[end_index+1:]

    return line


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
                                             remote_api_stub.GetUserAgent() + ' remote_driver_shell/1.0',
                                             remote_api_stub.GetSourceName(),
                                             save_cookies=True,
                                             debug_data=False,
                                             secure=options.secure)
    global __remote_driver_server
    __remote_driver_server = rpc_server

    os.environ['SERVER_SOFTWARE'] = 'Development (remote_driver_shell/1.0)'

    sys.ps1 = '%s/driver> ' % appid
    if readline:
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
