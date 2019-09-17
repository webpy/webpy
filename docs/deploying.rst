Deploying web.py applications
=============================

FastCGI
-------

web.py uses `flup`_ library for supporting fastcgi. Make sure it is installed.

.. _flup: http://trac.saddi.com/flup

You just need to make sure you application file is executable. Make it so by adding the following line to tell the system to execute it using python::

    #! /usr/bin/env python

and setting the exeutable flag on the file::

    chmod +x /path/to/yourapp.py

Configuring lighttpd    
^^^^^^^^^^^^^^^^^^^^

Here is a sample lighttpd configuration file to expose a web.py app using fastcgi. ::

    # Enable mod_fastcgi and mod_rewrite modules
    server.modules   += ( "mod_fastcgi" )
    server.modules   += ( "mod_rewrite" )

    # configure the application
    fastcgi.server = ( "/yourapp.py" =>
        (( 
            # path to the socket file
            "socket" => "/tmp/yourapp-fastcgi.socket", 

            # path to the application
            "bin-path" => "/path/to/yourapp.py",

            # number of fastcgi processes to start
            "max-procs" => 1,

            "bin-environment" => (
                "REAL_SCRIPT_NAME" => ""
            ),
            "check-local" => "disable"
        ))
    )

     url.rewrite-once = (
        # favicon is usually placed in static/
        "^/favicon.ico$" => "/static/favicon.ico",

        # Let lighttpd serve resources from /static/. 
        # The web.py dev server automatically servers /static/, but this is 
        # required when deploying in production.
        "^/static/(.*)$" => "/static/$1",

        # everything else should go to the application, which is already configured above.
        "^/(.*)$" => "/yourapp.py/$1",
     )

With this configuration lighttpd takes care of starting the application. The webserver talks to your application using fastcgi via a unix domain socket. This means both the webserver and the application will run on the same machine.

nginx + Gunicorn
----------------

Gunicorn 'Green Unicorn' is a Python WSGI HTTP Server for UNIX. It's a pre-fork worker model ported from Ruby's Unicorn project.

To make a web.py application work with gunicorn, you'll need to get the wsgi app from web.py application object. ::

    import web
    ...
    app = web.application(urls, globals())

    # get the wsgi app from web.py application object
    wsgiapp = app.wsgifunc()

Once that change is made, gunicorn server be started using::

    gunicorn -w 4 -b 127.0.0.1:4000 yourapp:wsgiapp

This starts gunicorn with 4 workers and listens at port 4000 on localhost.

It is best to use Gunicorn behind HTTP proxy server. The gunicorn team strongly advises to use nginx.
Here is a sample nginx configuration which proxies to application running on `127.0.0.1:4000`. ::

  server {
    listen 80;
    server_name example.org;
    access_log  /var/log/nginx/example.log;

    location / {
        proxy_pass http://127.0.0.1:4000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
  }
