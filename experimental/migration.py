"""Migration script to run web.py 0.23 programs using 0.3.

Import this module at the beginning of your program.
"""
import web
import sys

def setup_database():
    if web.config.get('db_parameters'):
        db = web.database(**web.config.db_parameters)
        web.insert = db.insert
        web.select = db.select
        web.update = db.update
        web.delete = db.delete
        web.query = db.query

        def transact():
            t = db.transaction()
            web.ctx.setdefault('transaction_stack', []).append(t)

        def rollback():
            stack = web.ctx.get('transaction_stack')
            t = stack and stack.pop()
            t and t.rollback()

        def commit():
            stack = web.ctx.get('transaction_stack')
            t = stack and stack.pop()
            t and t.commit()

        web.transact = transact
        web.rollback = rollback
        web.commit = commit
        
web.loadhooks = web.webapi.loadhooks = {}
web._loadhooks = web.webapi._loadhooks = {}
web.unloadhooks = web.webapi.unloadhooks = {}

def load():
    setup_database()

web.load = load

def run(urls, fvars, *middleware):
    setup_database()

    def stdout_processor(handler):
        handler()
        return web.ctx.get('output', '')

    def hook_processor(handler):
        for h in web.loadhooks.values() + web._loadhooks.values(): h()
        output = handler()
        for h in web.unloadhooks.values(): h()
        return output

    app = web.application(urls, fvars)
    app.add_processor(stdout_processor)
    app.add_processor(hook_processor)
    app.run(*middleware)

class _outputter:
    """Wraps `sys.stdout` so that print statements go into the response."""
    def __init__(self, file): self.file = file
    def write(self, string_):
        if hasattr(web.ctx, 'output'):
            return output(string_)
        else:
            self.file.write(string_)
    def __getattr__(self, attr): return getattr(self.file, attr)
    def __getitem__(self, item): return self.file[item]

def output(string_):
    """Appends `string_` to the response."""
    string_ = web.safestr(string_)
    if web.ctx.get('flush'):
        web.ctx._write(string_)
    else:
        web.ctx.output += str(string_)

def _capturedstdout():
    sysstd = sys.stdout
    while hasattr(sysstd, 'file'):
        if isinstance(sys.stdout, _outputter): return True
        sysstd = sysstd.file
    if isinstance(sys.stdout, _outputter): return True
    return False

if not _capturedstdout():
    sys.stdout = _outputter(sys.stdout)

web.run = run

class Stowage(web.storage):
    def __str__(self):
        return self._str

web.template.Stowage = web.template.stowage = Stowage

