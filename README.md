# flex_remote_api

* http://github.com/tagomoris/flex_remote_api

This library works with Google App Engine SDK Python 1.4.0.

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

Add queue.yaml to your application by copying, or add below lines to your queue.yaml

    queue:
    - name: FlexRemoteApiJob
      rate: 1/s
      retry_parameters:
        task_retry_limit: 2

Deploy your application

    appcfg.py update YOUR_APPLICATION

### Run
run bin/flex_remote_api_shell.py with path of AppEngine SDK, and your application id.

    $ bin/flex_remote_api_shell.py ~/google_appengine youraplication
    Email: youraccount@gmail.com
    Password: [PASSWORD]
    App Engine remote_api shell with flex_remote_api_shell
    Python 2.5.4 (r254:67916, Jun 24 2010, 21:47:25) 
    [GCC 4.2.1 (Apple Inc. build 5646)]
    The db, users, urlfetch, and memcache modules are imported.
    yourapplication/flex> 

## Demonstrations
### Creating data
You can use flex_remote_api_shell same as remote_api_shell.

    yourapplication/flex> class TestData(db.Model):
    ...   name = db.StringProperty()
    ...   valid = db.BooleanProperty()
    ...   content = db.TextProperty()
    ... 
    yourapplication/flex> entity1 = TestData(name="tagomoris",valid=True,content="text, you want...")
    yourapplication/flex> entity1.put()
    datastore_types.Key.from_path(u'TestData', 2101227038L, _app=u'yourapplication')
    yourapplication/flex> 

You write codes above, shell puts 'entity1' to Datastore Service on appspot, with remote_api.

You can also use functions for data creation with remote_api.

    yourapplication/flex> def create_testdata(num):
    ...   for i in range(0,num):
    ...     TestData(name="tagomoris"+str(num), valid=True, content="hoge hogehoge hogehoge ....").put()
    ... 
    yourapplication/flex> create_testdata(10)
    yourapplication/flex> 

But datastore accesses over remote_api is very slow, and then, you can use 'remote' builtin directive of flex_remote_api.

    yourapplication/flex> print datetime.datetime.now(); create_testdata(500); print datetime.datetime.now()
    2010-12-26 06:01:58.362485
    2010-12-26 06:04:59.821365
    yourapplication/flex> remote create_testdata(500)
    job id: 2101176047 in 9.513875 sec
    yourapplication/flex> 

First 'create_testdata(500)' runs on local python interpriter, and putted over remote_api, and second 'remote create_testdata(500)' runs on appspot environment.

You can use 'remote' directive without care for class-definitions and function-definitions. These definitions are restored on appspot environment in 'remote' procedure. (But re-assigned functions/classes doesn't works now...)

And you can use variables defined on local shell in function runned in 'remote'. See below.

    yourapplication/flex> content_string = "0123456789 " + str(datetime.datetime.now())
    yourapplication/flex> content_string
    '01234567892011-01-02 15:40:55.316633'
    yourapplication/flex> def create2_testdata(num):
    ...   for i in range(0,num):
    ...     TestData(name="moris"+str(i), valid=True, content=content_string).put()
    ... 
    yourapplication/flex> remote create2_testdata(100)
    job id: 2101268052 in 1.488545 sec
    yourapplication/flex> ary = TestData.all().filter("name =", "moris5").fetch(10)
    yourapplication/flex> len(ary)
    1
    yourapplication/flex> ary[0].name
    u'moris5'
    yourapplication/flex> ary[0].content
    u'01234567892011-01-02 15:40:55.316633'
    yourapplication/flex> 

### Async Remote Jobs
You can do each jobs asynchronously by using 'remote_async' directive. 'remote_async' directive doesn't wait executions in appspot, and returns immediately. To wait jobs and see results, you can use 'remote_async_wait' directive.

    yourapplication/flex> def create3_testdata(num):
    ...   for i in range(0,num):
    ...     TestData(name="tago"+str(i), valid=True, content=content_string).put()
    ... 
    yourapplication/flex> content_string
    '01234567892011-01-02 15:40:55.316633'
    yourapplication/flex> remote_async create3_testdata(500)
    job id: 2101207050
    yourapplication/flex> content_string = "0123456789" + str(datetime.datetime.now())
    yourapplication/flex> remote_async create3_testdata(100)
    job id: 2101222050
    yourapplication/flex> content_string = "0123456789" + str(datetime.datetime.now())
    yourapplication/flex> remote_async create3_testdata(200)
    job id: 2101281037
    yourapplication/flex> remote_async_wait
    job id: 2101207050 in 7.478004 sec
    job id: 2101222050 in 1.486641 sec
    job id: 2101281037 in 2.949463 sec
    [None, None, None]
    yourapplication/flex> 

### Functional call and getting return values
You can get return value by functional calling.

    yourapplication/flex> c = remote_sync(TestData.all().count())
    job id: 2101224053 in 0.194382 sec
    yourapplication/flex> c
    700L
    yourapplication/flex> 

With asynchronous call, you can use 'remote_async_results()' instead of 'remote_async_wait'.

    yourapplication/flex> remote_async Hoge.all().count()
    job id: 2101267068
    yourapplication/flex> remote_async TestData.all().count()
    job id: 2101197052
    yourapplication/flex> remote_async Pos.all().count()
    job id: 2101241070
    yourapplication/flex> results = remote_async_results()
    job id: 2101267068 failed, check logs on Admin Console...   # ok, 'Hoge' model is not defined.
    job id: 2101197052 in 0.106693 sec
    job id: 2101241070 failed, check logs on Admin Console...   # ok, 'Pos' model is not defined.
    yourapplication/flex> results
    [None, 0L, None]
    yourapplication/flex> 

With job ids, you can get each jobs' return values by 'remote_job_results()'.

    yourapplication/flex> results = remote_job_results(2101197051, 2101249063, 2101267068, 2101197052)
    job id: 2101197051 in 0.073766 sec
    job id: 2101249063 in 0.075781 sec
    job id: 2101267068 failed, check logs on Admin Console...
    job id: 2101197052 in 0.106693 sec
    yourapplication/flex> results
    [502L, 0L, None, 0L]
    yourapplication/flex> 

## Cautions and Limitations
Now, you must take care limitations below.

### Requirements
'readline' module required. Then, on Windows environment, you cannot use flex_remote_api_shell.... You should Cygwin on Windows.

### Directives' limitation
'remote' and 'remote_async' directives accept only one formula (not statement). If you want to run loops and/or condition controls, you must wrap codes as function, or write as below.

    yourapplication/flex> remote [TestData(name=s).put() for s in ["hogemoris","posmoris"]]

### Importing modules
Importing any modules of AppEngine SDK is allowed. But you can import your own modules that has same package name between local and appspot.

    from google.appengine.api import taskqueue  # OK, you can use taskqueue module in 'remote'.
    
    import your_data_models # Only when your_data_models.py is deployed in appspot, you can use it in 'remote'.

### Re-assigned functions/classes
Re-assigned functions/classes are out of accessable members in 'remote' procedure.

    yourapplication/flex> def hoge_func1(num):
    ...   return num * 10
    ... 
    yourapplication/flex> hoge_func2 = hoge_func1
    yourapplication/flex> hoge_func1(10)
    100
    yourapplication/flex> hoge_func2(10)
    100
    yourapplication/flex> remote hoge_func1(10)
    0.013490 sec
    100
    yourapplication/flex> remote hoge_func2(10) # Doesn't work this code !!!

### API call quota
You should take care about Datastore(and other api) calls quota per min. Tasks to put entities over 1000 will fail with logs below.

    12-19 12:31AM 38.262 /_ex_ah/flex_remote_api/execute 500 31376ms 41440cpu_ms 33646api_cpu_ms 1kb AppEngine-Google; (+http://code.google.com/appengine)
    E 12-19 12:32AM 09.599 The API call datastore_v3.Put() required more quota than is available. Traceback (most recent call last): File "/base/python_runtime/python_lib/vers

* * * * *

## License

Copyright 2011 TAGOMORI Satoshi (tagomoris)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
