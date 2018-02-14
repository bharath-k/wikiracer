'''
Settings for the project.
'''
import os
import re

LISTEN_PORT = os.environ.get('LISTEN_PORT', 8080)
REDIS_HOST = 'localhost'
REDIS_PORT = os.environ.get('REDIS_PORT', 6439)

# wiki settings
WIKI_PREFIX = 'https://en.wikipedia.org/wiki/'
WIKI_IGNORE_EXP = re.compile('^(Category:|Special:|Wikipedia:|File:|Template_talk:|Talk:|Template:|Portal:|Help:|Main_Page|PubMed_Identifier|Digital_object_identifier|Internation↪al_Standard_Book_Number)')
