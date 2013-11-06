Templates
=========

Writing HTML from inside Python can get cumbersome; it's much more fun to write Python from inside HTML. Luckily, web.py makes that pretty easy.

Let's make a new directory for our templates (we'll call it templates). Inside, make a new file whose name ends with HTML (we'll call it index.html). Now, inside, you can just write normal HTML:

<em>Hello</em>, world!
Or you can use web.py's templating language to add code to your HTML:

::

    $def with (name)

    $if name:
        I just wanted to say <em>hello</em> to $name.
    $else:
        <em>Hello</em>, world!

As you can see, the templates look a lot like Python files except for the def with statement at the top (saying what the template gets called with) and the $s placed in front of any code. Currently, the templetor requires the $def statement to be the first line of the file. 


Now go back to code.py. Under the first line, add:

::

    render = web.template.render('templates/')

This tells web.py to look for templates in your templates directory. Then change index.GET to:

::

    name = 'Bob'    
    return render.index(name)

('index' is the name of the template and 'name' is the argument passed to it)

Visit your site and it should say hello to Bob.

But let's say we want to let people enter their own name in. Replace the two lines we added above with:

::

    i = web.input(name=None)
    return render.index(i.name)

Visit / and it should say hello to the world. Visit /?name=Joe and it should say hello to Joe.

Of course, having that ? in the URL is kind of ugly. Instead, change your URL line at the top to:

'/(.*)', 'index'
and change the definition of index.GET to:

::

    def GET(self, name):
        return render.index(name)

and delete the line setting name. Now visit /Joe and it should say hello to Joe.

Escaping
````````
web.py automatically escapes any variables used in templates, so that if for some reason name is set to a value containing some HTML, it will get properly escaped and appear as plain text. If you want to turn this off, write $:name instead of $name.

