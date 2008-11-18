"""
Interface to various templating engines.
"""
import os.path

__all__ = [
    "render_cheetah", "render_genshi", "render_mako",
    "cache", 
]

class render_cheetah:
    """Rendering interface to Cheetah Templates.

    Example:

        render = render_cheetah('templates')
        render.hello(name="cheetah")
    """
    def __init__(self, path):
        # give error if Chetah is not installed
        from Cheetah.Template import Template
        self.path = path

    def __getattr__(self, name):
        from Cheetah.Template import Template
        path = os.path.join(self.path, name + ".html")
        
        def template(**kw):
            t = Template(file=path, searchList=[kw])
            return t.respond()

        return template
    
class render_genshi:
    """Rendering interface genshi templates.
    Example:

    for xml/html templates.

        render = render_genshi(['templates/'])
        render.hello(name='genshi')

    For text templates:

        render = render_genshi(['templates/'], type='text')
        render.hello(name='genshi')
    """

    def __init__(self, *a, **kwargs):
        from genshi.template import TemplateLoader

        self._type = kwargs.pop('type', None)
        self._loader = TemplateLoader(*a, **kwargs)

    def __getattr__(self, name):
        # Assuming all templates are html
        path = name + ".html"

        if self._type == "text":
            from genshi.template import TextTemplate
            cls = TextTemplate
            type = "text"
        else:
            cls = None
            type = None

        t = self._loader.load(path, cls=cls)
        def template(**kw):
            stream = t.generate(**kw)
            if type:
                return stream.render(type)
            else:
                return stream.render()
        return template

class render_jinja:
    """Rendering interface to Jinja2 Templates
    
    Example:

        render= render_jinja('templates')
        render.hello(name='jinja2')
    """
    def __init__(self, *a, **kwargs):
        from jinja2 import Environment,FileSystemLoader
        self._lookup = Environment(loader=FileSystemLoader(*a, **kwargs))
        
    def __getattr__(self, name):
        # Assuming all templates end with .html
        path = name + '.html'
        t = self._lookup.get_template(path)
        return t.render
        
class render_mako:
    """Rendering interface to Mako Templates.

    Example:

        render = render_mako(directories=['templates'])
        render.hello(name="mako")
    """
    def __init__(self, *a, **kwargs):
        from mako.lookup import TemplateLookup
        self._lookup = TemplateLookup(*a, **kwargs)

    def __getattr__(self, name):
        # Assuming all templates are html
        path = name + ".html"
        t = self._lookup.get_template(path)
        return t.render

class cache:
    """Cache for any rendering interface.
    
    Example:

        render = cache(render_cheetah("templates/"))
        render.hello(name='cache')
    """
    def __init__(self, render):
        self._render = render
        self._cache = {}

    def __getattr__(self, name):
        if name not in self._cache:
            self._cache[name] = getattr(self._render, name)
        return self._cache[name]
