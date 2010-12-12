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
  flex_remote_api_shell.py [-s HOSTNAME] APPENGINE_SDK_PATH APPID [PATH]
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

from google.appengine.ext.remote_api import remote_api_stub

from google.appengine.api import datastore
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import search


HISTORY_PATH = os.path.expanduser('~/.remote_api_shell_history')
DEFAULT_PATH = '/remote_api'
BANNER = """App Engine remote_api shell with flex_remote_api_shell
Python %s
The db, users, urlfetch, and memcache modules are imported.""" % sys.version


def auth_func():
    return (raw_input('Email: '), getpass.getpass('Password: '))


__readline_history_session_start = 0
__flex_remote_api_server = None

def xx(func, *args, **keywords):
    return func(*args, **keywords)


def magic_input(prompt=''):
    line = raw_input(prompt)
    if not line.strip().startswith('xx '):
        return line
    bareline = line.strip()[len('xx '):]
    match_result = re.compile('([a-zA-Z0-9_]+)\((.*)\)$').match(bareline)
    if not match_result:
        return bareline
    return 'xx(' + match_result.group(1) + ', ' + match_result.group(2) + ')'


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

    remote_api_stub.ConfigureRemoteApi(appid, path, auth_func,
                                       servername=options.server,
                                       save_cookies=True, secure=options.secure)
    remote_api_stub.MaybeInvokeAuthentication()

    os.environ['SERVER_SOFTWARE'] = 'Development (flex_remote_api_shell)/1.0'

    sys.ps1 = '%s/xx> ' % appid #TODO rewrite from xx to 'flex'
    readline.parse_and_bind('tab: complete')
    atexit.register(lambda: readline.write_history_file(HISTORY_PATH))
    if os.path.exists(HISTORY_PATH):
        readline.read_history_file(HISTORY_PATH)
        #TODO check get_current_history_length() and set start-point of loading

    code.interact(banner=BANNER, readfunc=magic_input, local=globals())


if __name__ == '__main__':
  main(sys.argv)
