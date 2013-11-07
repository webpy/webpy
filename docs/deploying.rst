Deploying web.py applications
=============================

FastCGI
-------

web.py uses `flup`_ library for supporting fastcgi. Make sure it is installed.

.. _flup: http://trac.saddi.com/flup

You just need to make sure you applicaiton file is executable. Make it so by adding the following line to tell the system to execute it using python::

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

With this configuration lighttpd takes care of starting the application. The webserver tasks to your application using fastcgi via a unix domain socket. This means both the webserver and the application will run on the same machine.
