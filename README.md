# remote_driver_shell

* http://github.com/tagomoris/remote_driver

This library works with Google App Engine SDK Python 1.4.0.

## DESCRIPTION

'remote_driver' is extension library works as remote_api_shell of Google App Engine. On remote_driver_shell's shell, specified function runs on appspot directly, and you can get result in more-more shorter time than remote_api_shell.

'readline' module supports remote_driver, but on Windows, you can run remote_driver without readline. Thanks for great patch from @najeira.

## SYNOPSIS

    bin/remote_driver_shell.py APPENGINE_SDK_DIR_PATH APP_ID

## Overview
### Setup
To use remote_driver, you must do setup settings below.

Add remote_driver handler to your application

    cp remote_driver_handler.py YOUR_APPLICATION_DIRECTORY

Edit app.yaml to enable remote_api, and remote_driver handler

    builtins:
    - remote_api: on
    
    handlers:
    - url: /_ex_ah/remote_driver/.*
      script: remote_driver_handler.py

Add queue.yaml to your application by copying, or add below lines to your queue.yaml

    queue:
    - name: RemoteDriverJob
      rate: 1/s
      retry_parameters:
        task_retry_limit: 2

Deploy your application

    appcfg.py update YOUR_APPLICATION

### Run
run bin/remote_driver_shell.py with path of AppEngine SDK, and your application id.

    $ bin/remote_driver_shell.py ~/google_appengine youraplication
    Email: youraccount@gmail.com
    Password: [PASSWORD]
    App Engine remote_api shell with remote_driver_shell
    Python 2.5.4 (r254:67916, Jun 24 2010, 21:47:25) 
    [GCC 4.2.1 (Apple Inc. build 5646)]
    The db, users, urlfetch, and memcache modules are imported.
    yourapplication/driver> 

## Demonstrations
### Creating data
You can use remote_driver_shell same as remote_api_shell.

    yourapplication/driver> class TestData(db.Model):
    ...   name = db.StringProperty()
    ...   valid = db.BooleanProperty()
    ...   content = db.TextProperty()
    ... 
    yourapplication/driver> entity1 = TestData(name="tagomoris",valid=True,content="text, you want...")
    yourapplication/driver> entity1.put()
    datastore_types.Key.from_path(u'TestData', 2101227038L, _app=u'yourapplication')
    yourapplication/driver> 

You write codes above, shell puts 'entity1' to Datastore Service on appspot, with remote_api.

You can also use functions for data creation with remote_api.

    yourapplication/driver> def create_testdata(num):
    ...   for i in range(0,num):
    ...     TestData(name="tagomoris"+str(num), valid=True, content="hoge hogehoge hogehoge ....").put()
    ... 
    yourapplication/driver> create_testdata(10)
    yourapplication/driver> 

But datastore accesses over remote_api is very slow, and then, you can use 'remote' builtin directive of remote_driver.

    yourapplication/driver> print datetime.datetime.now(); create_testdata(500); print datetime.datetime.now()
    2010-12-26 06:01:58.362485
    2010-12-26 06:04:59.821365
    yourapplication/driver> remote create_testdata(500)
    job id: 2101176047 in 9.513875 sec
    yourapplication/driver> 

First 'create_testdata(500)' runs on local python interpriter, and putted over remote_api, and second 'remote create_testdata(500)' runs on appspot environment.

You can use 'remote' directive without care for class-definitions and function-definitions. These definitions are restored on appspot environment in 'remote' procedure. (But re-assigned functions/classes doesn't works now...)

And you can use variables defined on local shell in function runned in 'remote'. See below.

    yourapplication/driver> content_string = "0123456789 " + str(datetime.datetime.now())
    yourapplication/driver> content_string
    '01234567892011-01-02 15:40:55.316633'
    yourapplication/driver> def create2_testdata(num):
    ...   for i in range(0,num):
    ...     TestData(name="moris"+str(i), valid=True, content=content_string).put()
    ... 
    yourapplication/driver> remote create2_testdata(100)
    job id: 2101268052 in 1.488545 sec
    yourapplication/driver> ary = TestData.all().filter("name =", "moris5").fetch(10)
    yourapplication/driver> len(ary)
    1
    yourapplication/driver> ary[0].name
    u'moris5'
    yourapplication/driver> ary[0].content
    u'01234567892011-01-02 15:40:55.316633'
    yourapplication/driver> 

### Async Remote Jobs
You can do each jobs asynchronously by using 'remote_async' directive. 'remote_async' directive doesn't wait executions in appspot, and returns immediately. To wait jobs and see results, you can use 'remote_async_wait' directive.

    yourapplication/driver> def create3_testdata(num):
    ...   for i in range(0,num):
    ...     TestData(name="tago"+str(i), valid=True, content=content_string).put()
    ... 
    yourapplication/driver> content_string
    '01234567892011-01-02 15:40:55.316633'
    yourapplication/driver> remote_async create3_testdata(500)
    job id: 2101207050
    yourapplication/driver> content_string = "0123456789" + str(datetime.datetime.now())
    yourapplication/driver> remote_async create3_testdata(100)
    job id: 2101222050
    yourapplication/driver> content_string = "0123456789" + str(datetime.datetime.now())
    yourapplication/driver> remote_async create3_testdata(200)
    job id: 2101281037
    yourapplication/driver> remote_async_wait
    job id: 2101207050 in 7.478004 sec
    job id: 2101222050 in 1.486641 sec
    job id: 2101281037 in 2.949463 sec
    [None, None, None]
    yourapplication/driver> 

### Functional call and getting return values
You can get return value by functional calling.

    yourapplication/driver> c = remote_sync(TestData.all().count())
    job id: 2101224053 in 0.194382 sec
    yourapplication/driver> c
    700L
    yourapplication/driver> 

With asynchronous call, you can use 'remote_async_results()' instead of 'remote_async_wait'.

    yourapplication/driver> remote_async Hoge.all().count()
    job id: 2101267068
    yourapplication/driver> remote_async TestData.all().count()
    job id: 2101197052
    yourapplication/driver> remote_async Pos.all().count()
    job id: 2101241070
    yourapplication/driver> results = remote_async_results()
    job id: 2101267068 failed, check logs on Admin Console...   # ok, 'Hoge' model is not defined.
    job id: 2101197052 in 0.106693 sec
    job id: 2101241070 failed, check logs on Admin Console...   # ok, 'Pos' model is not defined.
    yourapplication/driver> results
    [None, 0L, None]
    yourapplication/driver> 

With job ids, you can get each jobs' return values by 'remote_job_results()'.

    yourapplication/driver> results = remote_job_results(2101197051, 2101249063, 2101267068, 2101197052)
    job id: 2101197051 in 0.073766 sec
    job id: 2101249063 in 0.075781 sec
    job id: 2101267068 failed, check logs on Admin Console...
    job id: 2101197052 in 0.106693 sec
    yourapplication/driver> results
    [502L, 0L, None, 0L]
    yourapplication/driver> 

## Cautions and Limitations
Now, you must take care limitations below.

### Directives' limitation
'remote' and 'remote_async' directives accept only one formula (not statement). If you want to run loops and/or condition controls, you must wrap codes as function, or write as below.

    yourapplication/driver> remote [TestData(name=s).put() for s in ["hogemoris","posmoris"]]

### Importing modules
Importing any modules of AppEngine SDK is allowed. But you can import your own modules that has same package name between local and appspot.

    from google.appengine.api import taskqueue  # OK, you can use taskqueue module in 'remote'.
    
    import your_data_models # Only when your_data_models.py is deployed in appspot, you can use it in 'remote'.

### Re-assigned functions/classes
Re-assigned functions/classes are out of accessable members in 'remote' procedure.

    yourapplication/driver> def hoge_func1(num):
    ...   return num * 10
    ... 
    yourapplication/driver> hoge_func2 = hoge_func1
    yourapplication/driver> hoge_func1(10)
    100
    yourapplication/driver> hoge_func2(10)
    100
    yourapplication/driver> remote hoge_func1(10)
    0.013490 sec
    100
    yourapplication/driver> remote hoge_func2(10) # Doesn't work this code !!!

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
