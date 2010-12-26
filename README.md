# flex_remote_api

* http://github.com/tagomoris/flex_remote_api

## DESCRIPTION

'flex_remote_api' is extension library works as remote_api_shell of Google App Engine. On flex_remote_api_shell's shell, specified function runs on appspot directly, and you can get result in more-more shorter time than remote_api_shell.

## SYNOPSIS

    bin/flex_remote_api_shell.py APPENGINE_SDK_DIR_PATH APP_ID

## Overview
### Setup
To use flex_remote_api, you must do setup settings below.

Add flex_remote_api handler to your application

    cp flex_remote_api.py YOUR_APPLICATION_DIRECTORY

Edit app.yaml to enable remote_api, and flex_remote_api handler

    builtins:
    - remote_api: on
    
    handlers:
    - url: /_ex_ah/flex_remote_api/.*
      script: flex_remote_api.py

Deploy your application

    appcfg.py update YOUR_APPLICATION

### Demonstration


* * * * *

## License

Copyright 2010 TAGOMORI Satoshi (tagomoris)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

