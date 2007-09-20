import os
import web

class Parser:
    def __init__(self):
        self.mode = 'normal'
        self.text = ''
        
    def go(self, pyfile):
        for line in file(pyfile):
            if self.mode == 'in def':
                self.text += ' ' + line.strip()
                if line.strip().endswith(':'):
                    if self.definition(self.text):
                        self.text = ''
                        self.mode = 'in func'
                    else:
                        self.text = ''
                        self.mode = 'normal'

            elif self.mode == 'in func':
                if '"""' in line:
                    self.text += line.strip().strip('"')
                    self.mode = 'in doc'
                    if line.count('"""') == 2:
                        self.mode = 'normal'
                        self.docstring(self.text)
                        self.text = ''
                else:
                    self.mode = 'normal'

            elif self.mode == 'in doc':
                self.text += ' ' + line
                if '"""' in line:
                    self.mode = 'normal'
                    self.docstring(self.text.strip().strip('"'))
                    self.text = ''
            
            elif line.startswith('## '):
                self.header(line.strip().strip('#'))
            
            elif line.startswith('def ') or line.startswith('class '):
                self.text += line.strip().strip(':')
                if line.strip().endswith(':'):
                    if self.definition(self.text):
                        self.text = ''
                        self.mode = 'in func'
                    else:
                        self.text = ''
                        self.mode = 'normal'
                else:
                    self.mode = 'in def'
    
    def clean(self, text):
        text = text.strip()
        text = text.replace('*', r'\*')
        return text
    
    def definition(self, text):
        text = web.lstrips(text, 'def ')
        if text.startswith('_') or text.startswith('class _'):
            return False
        print '`'+text.strip()+'`'
        return True
    
    def docstring(self, text):
        print '   :', text.strip()
        print
    
    def header(self, text):
        print '##', text.strip()
        print
        
for pyfile in os.listdir('trunk/web'):
    if pyfile[-2:] == 'py':
        print
        print '## ' + pyfile
        print
        Parser().go('trunk/web/' + pyfile)
print '`ctx`\n   :',
print '\n'.join('    '+x for x in web.ctx.__doc__.strip().split('\n'))
