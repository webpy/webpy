#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module is basado in internationalitation of web2py and Django.
"""

import re, os
import webapi as web
from ast import Dict,parse,Str,Expression

#pattern to find _('Hello Word') expressions
PY_STRING_LITERAL_RE = r'(?<=[^\w]_\()(?P<name>'\
     + r"[uU]?[rR]?(?:'''(?:[^']|'{1,2}(?!'))*''')|"\
     + r"(?:'(?:[^'\\]|\\.)*')|" + r'(?:"""(?:[^"]|"{1,2}(?!"))*""")|'\
     + r'(?:"(?:[^"\\]|\\.)*"))'

regex_translate = re.compile(PY_STRING_LITERAL_RE, re.DOTALL)

# pattern for a valid accept_language
accept_language_re = re.compile('''
    ^[a-zA-Z]{2}        # "es", "es-es", "en-au","it-it"
    (\-[a-zA-Z]{2})?$
    ''',re.VERBOSE)


def literal_eval(node_or_string):
    """
    Of AST.literal_eval but only consist Python literal
    structures: strings and dicts.

    Safely evaluate an expression node or a string containing a Python
    expression.  The string or node provided may only consist of the following
    Python literal structures: strings and dicts.
    """
    _safe_names = {'None': None, 'True': True, 'False': False}
    if isinstance(node_or_string, basestring):
        node_or_string = parse(node_or_string, mode='eval')
    if isinstance(node_or_string, Expression):
        node_or_string = node_or_string.body
    def _convert(node):
        if isinstance(node, Str):
            return node.s
        elif isinstance(node, Dict):
            return dict((_convert(k), _convert(v)) for k, v
                        in zip(node.keys, node.values))
        raise ValueError('malformed string')
    return _convert(node_or_string)


def read_file(filename, mode='r'):
    """
    Returns content from filename, making sure to close the file
    explicitly on exit.
    """
    f = open(filename, mode)
    try:
        return f.read()
    finally:
        f.close()

def read_dict_aux(filename):
    """
    Safely evaluate an expression dicts
    """
    lang_text = read_file(filename)
    try:
        return literal_eval(lang_text)
    except:
        return {}

def get_lng_c(key, filename, filter):
    """
    Caches the *filtered* file 'filename' with 'key' until the file is
    modified.
    """
    t = os.stat(filename)[8] #Indices for stat ST_MTIME returned by os.stat()
    item = web.ctx.get(key, None)
    if item and item[0] == t:
        return item[1]
    else:
        data = filter()
    web.ctx[key] = (t, data)
    return data

def read_dict(filename):
    return get_lng_c('%s'%filename,filename,
                  lambda filename=filename:read_dict_aux(filename))


class WebPyTranslation(object):
    __slots__=['__language','__t','__folder']

    def __init__(self, folder='languages'):
        self.__folder=folder #folder of languages
        self.__language=self.force_language('en-us')#en-us, by default

    def __call__(self, message, symbols={}):
            return self.__do_translate(message, symbols)

    def set_folder(self, folder):
        self.__folder = folder

    def set_language(self, language):
        self.__language = language

    def get_language(self):
        return self.__language

    def get_possible_languages(self):
        possible_languages = [self.__language]
        file_ending = re.compile("\.py$")
        for langfile in os.listdir(self.__folder):
            if file_ending.search(langfile):
                possible_languages.append(file_ending.sub('',langfile))
        return possible_languages

    def force_language(self, language):
        if not language:
            language = []
        if language:
            if isinstance(language, (str, unicode)):
                if accept_language_re.match(language.strip()):
                    language = language.strip().lower()

                path = os.path.join(self.__folder, language+'.py')
                if os.path.isfile(path):
                    self.__language=language
                    self.__t = read_dict(path)
                    return language
        self.__t = {}  # ## no language by default
        return language

    def __do_translate(self, message, symbols=None):
        """
        T(' hello world ') -> ' hola mundo '
        """
        current_translation = self.__t.get(message, None)
        if current_translation == None:
            self.__t[message] = current_translation = message
        if symbols != None:
            return current_translation % symbols
        return current_translation


if __name__ == '__main__':
    T=WebPyTranslation()
    
    print T.get_possible_languages()
    T.force_language('es-es')
    print T("About")

    #-------------------------------------

    #Template file: proj/templates/hello.html.
    data='''
        $_("Hello %s") % Kmilo
        '''
    #find all _('...') expressions
    to_translate = regex_translate.findall(data)
    print T(literal_eval(to_translate[0]),'Kmilo')


    #language = 'ES-ES'
    #print accept_language_re.match(language.strip()).group()


