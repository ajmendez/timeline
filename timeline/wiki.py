# wikipedia information api

import os

import wikipedia
# import urllib
import datetime
import requests
import json
from pprint import pprint
import mwparserfromhell
import dataset


DB = 'sqlite:///wiki.db'
URL = 'http://en.wikipedia.org/w/api.php'
DATA_DIR = os.path.abspath('../data/')
CACHE_FILE = DATA_DIR + '/cache.json'
PEOPLE_FILE = DATA_DIR + '/people.txt'
SIMPLE_FILE = DATA_DIR + '/version1.json'








class Wiki(object):
  def __init__(self):
    self.session = requests.session()
    # self.db = dataset.connect(DB)
  
  def __enter__(self):
    '''simple cache '''
    try:
      self.cache = json.load(open(CACHE_FILE, 'r'))
    except ValueError as e:
      self.cache = {}
    return self
  
  def __exit__(self, type, value, traceback):
    '''Shutdown any open files'''
    json.dump(self.cache, open(CACHE_FILE, 'w'), indent=2)
  
  def get_section_num(self, title, section):
    pass
  
  def get_page(self, title):
    '''Get a page
    http://en.wikipedia.org/w/api.php?
    action=parse&prop=wikitext&page=List_of_Nobel_laureates_in_Physics&
    format=json&section=1
    
    '''
    if title in self.cache:
      return self.cache[title]
      pass
    params = dict(
      action='parse',
      prop='wikitext',
      page=title,
      format='json',
    )
    try:
      request = self.session.get(URL, params=params)
      print request.url
      page = json.loads(request.content)['parse']['wikitext']['*']
      self.cache[title] = page
      return page 
    except Exception as e:
      print 'Failed to get the page: {}'.format(title)
      raise e
  
  def get_html(self, title, section):
    self
  
  
  def parse_date(self, wikiDate):
    ''' Parse a mediawiki date template -- assumes years, month, day
    Input:
      a mwparser object containing just the date to be parsed
    Returns:
      a 'YYYY-MM-DD' string 
    '''
    template = mwparserfromhell.parse(str(wikiDate.value))
    # return '-'.join(map(str,map(template.filter_templates()[0].get, [3,2,1])))
    try:
      return '-'.join(map(str,map(template.filter_templates()[0].get, [1,2,3])))
    except:
      # sometimes they include the age -- remove
      template = str(template)
      if '(' in template:
        template = template.split('(')[0]
      
      tmp = datetime.datetime.strptime(template.strip(),'%B %d, %Y')
      return tmp.strftime('%Y-%m-%d')
 
 
  def parse_infobox(self, page):
    '''Parse out the nice mediawiki markdown to get birth and death
    Input:
      mediawiki unicode page string
    Returns:
      a dictionary with name(string), birth_date:DateTime, death_date:DateTime
    '''
    code = mwparserfromhell.parse(page)
    for template in code.filter_templates():
      if 'Infobox' in template.name:
        # Found the right template -- attempting to extract data
        output = {}
        for key in ['name', 'birth_name']:
          if template.has(key):
            output['name'] = template.get(key).value.strip()
        
        for date in ['birth_date', 'death_date']:
          try:
            item = self.parse_date(template.get(date))
          except ValueError as e:
            item = None
          output[date] = item

        # ok we are done here
        return output
    raise ValueError('Missing InfoBox')
  
  def debug_page(self, title):
    page = self.get_page(title)
    code = mwparserfromhell.parse(page)
    # pprint(page)
    raise ValueError()
  
  def get_person(self, name, group):
    '''get a dictionary for a person.'''
    out = self.parse_infobox(self.get_page(name))
    out['group'] = group
    return out
  
  # def get_person(self, name, group):
  #   '''Append the name, birth date, and death date to
  #   the starting kwargs dictionary'''
  #   table = self.db['people']
  #   
  #   out = table.find_one(name=name)
  #   
  #   if out is None:
  #     out = parse_infobox(self.get_page(name))
  #     out['group'] = group
  #     table.insert(out)
  #   
  #   return out
  
  def get_list(self, title, section, group):
    page = api.get_page(title)
    code = mwparserfromhell.parse(page)
    code
    out = []
    for item in page.links:
      print item
      print parse_infobox(self.get_page(item))
      # try:
      #   out.append(self.get_person(item, group))
      # except Exception as e:
      #   print u'Failed: {}, {}, {}'.format(item, group, title)
      #   # raise e
    
    
    
    




if __name__ == '__main__':
  from pysurvey import util
  util.setup_stop()
  
  with Wiki() as api:
    out = []
    for person in open(PEOPLE_FILE,'r').readlines():
      out.append(api.get_person(person.strip(), None))
      print out
    json.dump(out, open(SIMPLE_FILE, 'w'), indent=2)
    # Get the page and parse it
    # page = api.get_page('Albert Einstein')
    # print parse_infobox(page)
  
    # load the data into the db
    # pprint(api.get_person('Albert Einstein', 'Scientist'))
  
  
    # get a list of american
    # api.debug_page('List_of_American_scientists')
    # api.get_list('List_of_Nobel_laureates_in_Physics', 'Scientist')
    # api.debug_page('api')
  
  