Accessing User Input
====================

While building web applications, one basic and important thing is to respond to the user input that is sent to the server.

Web.py makes it easy to access that whether it is parameters in the url (`GET` request) or the form data (`POST` or `PUT` request). The `web.input()` method returns a dictionary-like object (more specifically a `web.storage` object) that contains the user input, whatever the request method is.


To access the URL parameters (?key=value) from the `web.input` object, just use `web.input().key`.

GET
---

For a URL which looks like `/page?id=1&action=edit`, you do

::

    class Page(object):
        def GET(self):
            data = web.input()
            id = int(data.id)   # all the inputs are now strings. Cast it to int, to get integer.
            action = data.action
            ...

`KeyError` exception is thrown if `key` is not there in the URL parameters.
Web.py makes it easier to handle that with default values to web.input().

::

    class Page(object):
        def GET(self):
            data = web.input(id=1, action='read')
            id, action = int(data.id), data.action
            ...

POST
----

It works exactly the same way with POST method. If you have a form with `name` and `password` elements, you would do

::

    class Login(object):
        def POST(self):
            data = web.input()
            name, password = data.name, data.password
            ...


Multiple inputs with same name
------------------------------

What if you have a URL which looks like `/page?id=1&id=2&id=3` or you have a form with multiple selects? What would `web.input().id` give us? It simply swallows all but one value. But to let web.input() know that we're expecting more values with the same name is simple. Just pass `[]` as the default argument for that name.

::

    class Page(object):
        def GET(self):
            data = web.input(id=[])
            ids = data.id         # now, `ids` is a list with all the `id`s.
            ...


File uploads
------------

Uploading files is easy with web.py. `web.input()` takes care of that too. Just make sure that the upload form has an attribute enctype="multipart/form-data". The `input()` gives you `filename` and `value`, which are the uploaded file name and the contents of it, respectively.
To make things simpler, it also gives you `file`, a file-like object if you pass `myfile={}` where `myfile` is the name of the input element in your form.
::

    class Upload(object):
        def GET(self):
            return render.upload()

        def POST(self):
             data = web.input(myfile={})
             fp = data.myfile
             save(fp)   # fp.filename, fp.read() gives name and contents of the file
             ...

or

::

    class Upload(object):
        ...

        def POST(self):
             data = web.input() # notice that `myfile={}` is missing here.
             fp = data.myfile
             save(fp.filename, fp.value)
             ...
