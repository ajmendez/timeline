# wikipedia information api

import os
import json
import codecs 
import datetime
from pprint import pprint
from collections import OrderedDict

# import urllib
import dataset
import requests
import wikipedia
import mwparserfromhell
from bs4 import BeautifulSoup




DB = 'sqlite:///wiki.db'
URL = 'http://en.wikipedia.org/w/api.php'
DATA_DIR = os.path.abspath('../data/')
CACHE_FILE = DATA_DIR + '/cache.json'
PEOPLE_FILE = DATA_DIR + '/people.txt'
SIMPLE_FILE = DATA_DIR + '/version1.json'
WAR_FILE = DATA_DIR + '/wars1.json'


class InfoError(Exception):
  pass


class Wiki(object):
  def __init__(self):
    self.session = requests.session()
    # self.db = dataset.connect(DB)
  
  def __enter__(self):
    '''simple cache '''
    try:
      self.cache = json.load(open(CACHE_FILE, 'r'))
      # pprint([l for l in self.cache.keys() if 'list' in l.lower()])
    except ValueError as e:
      self.cache = {}
    return self
  
  def __exit__(self, type, value, traceback):
    '''Shutdown any open files'''
    json.dump(self.cache, open(CACHE_FILE, 'w'), indent=2)
  
  
  def get_page(self, title, cache=True, beautiful=False, **kwargs):
    '''Get the wikitext code of a wikipedia page with a title.
    cache [True] -- Cache the page so that we are not abusing wikipedia
    beautiful [False] -- Return the BeautifulSoup html code -- for tables
    **kwargs -- updates the requests params
    
    Example URL:
    http://en.wikipedia.org/w/api.php?
    action=parse&prop=wikitext&page=List_of_Nobel_laureates_in_Physics&
    format=json&section=1
    
    '''
    # Load from the cache
    if title in self.cache and cache:
      if beautiful:
        return BeautifulSoup(self.cache[title])
      else:
        return self.cache[title]
        
    # If using BeautifulSoup get the html rather than the wikitext
    if beautiful:
      kwargs['prop'] = 'text'
    
    # url parameters for the wikipedia api
    params = dict(
      action='parse',
      prop='wikitext',
      page=title.encode('utf-8'),
      format='json',
    )
    params.update(kwargs)
    
    request = self.session.get(URL, params=params)
    print 'Loaded: {}'.format(request.url)
    page = json.loads(request.content)['parse'][params['prop']]['*']
    
    # handle redirects nicely
    if '#REDIRECT' in page:
      if beautiful:
        code = BeautifulSoup(page)
        newtitle = code.find('span',{'class','redirectText'}).find('a').get('title')
      else:
        code = mwparserfromhell.parse(page)
        newtitle = u'{}'.format(code.filter_wikilinks()[0].title)
      kwargs.update(dict(cache=cache, beautiful=beautiful))
      return self.get_page(newtitle, **kwargs)
  
    # Save to the cache for the future
    if cache:
      self.cache[title] = page
  
    # Output the wikitext string or make it beautiful
    if beautiful:
      return BeautifulSoup(page)
    else:
      return page
  
  def debug_page(self, title):
    '''Sometimes it is nice to debug'''
    page = self.get_page(title)
    code = mwparserfromhell.parse(page)
    html = BeautifulSoup(self.get_page(title, beautiful=True))
    raise ValueError()
  
  
  def get_section(self, title, sectionname, **kwargs):
    '''Get a section of a page.  Basically a wrapper around get_page() 
    that figures out which section index to pull down.'''
    
    if sectionname is None:
      return self.get_page(title, **kwargs)
    
    # Figure out what is the index for the section parameter
    params = dict(
      action='parse',
      prop='sections',
      page=title,
      format='json',
    )
    request = self.session.get(URL, params=params)
    sections = json.loads(request.content)['parse']['sections']
    for section in sections:
      if sectionname.lower() in section['line'].lower():
        kwargs.update(dict(section=section['index']))
        return self.get_page(title, **kwargs)
    
    tmp = ', '.join([s['line'] for s in sections])
    raise ValueError('Could not find section: {}.  Page Sections: {}'
                      .format(sectionname, tmp))
  
  
  
  def parse_date(self, wikiDate):
    ''' Parse a mediawiki date template -- assumes years, month, day
    Input:
      a mwparser object containing just the date to be parsed
    Returns:
      a 'YYYY-MM-DD' string 
    '''
    template = mwparserfromhell.parse(str(wikiDate.value))


    # make a few passes at parsing the date format
    
    try:
      tmp = map(template.filter_templates()[0].get, [1,2,3])
      return '-'.join([str(t).strip() for t in tmp])
    except Exception as e:
      # print 'failed 1', e
      pass
    
    template = str(template).split('(')[0].strip()
    
    try:
      tmp = datetime.datetime.strptime(template.strip(),'%B %d, %Y')
      # return tmp.strftime('%Y-%m-%d')
      return tmp.isoformat().split('T')[0]
    except Exception as e:
      # print 'failed 2', e
      pass
    
    try:
      tmp = datetime.datetime.strptime(template.strip(),'%d %B %Y')
      return tmp.isoformat().split('T')[0]
    except Exception as e:
      # print 'failed 3', e
      pass
    
    raise ValueError('Could not parse date: {}'.format(wikiDate))
    
 
  def parse_infobox(self, title, page):
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
        output = dict(title=title)
        
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
    raise InfoError()
  
  
  
  
  
  def get_person(self, name, group=None):
    '''Get the dictionary for a person'''
    out = self.parse_infobox(name, self.get_page(name))
    out['group'] = group
    return out

  
  def parse_nobel(self, row, col, j):
    if ( ((len(row) == 11) and (j == 2)) or
         ((len(row) <  11) and (len(row) > 5) and (j == 1)) or 
         ((len(row) ==  5) and (j == 0)) or
         ((len(row) == 15) and (j == 2)) ):
      if 'Not awarded' in str(row):
        return
      
      # tmp = col.find('a').get('href').replace('/wiki/','')
      tmp = col.find('a').get('title').replace('/wiki/','')
      return tmp
  
  def parse_war(self, row, col, j):
    if ((len(row) == 11) and (j == 0)):
      tmp = row.findAll('td')
      try:
        name = tmp[2].find('a').text
        title = tmp[2].find('a').get('title')
      except:
        name = tmp[2].text
        title = tmp[2].text
      out = dict(
        start = tmp[0].text.split('(')[0],
        end   = tmp[1].text.split('(')[0],
        name  = name,
        title = title,
      )
      return out
      # raise ValueError()
      # print len(row), row
      # for c in row.findAll('td'):
      #   out[]
      
      
    
  
  def get_list(self, title, section, parse_fcn):
    out = []
    tmp =  self.get_section(title, section, beautiful=True)
    for i, row in enumerate(tmp.findAll('tr')):
      for j,col in enumerate(row.findAll('td')):
        
        tmp = parse_fcn(row, col, j)
        if tmp is not None:
          out.append(tmp)
        
        # try:
        #   tmp = parse_fcn(row, col, j)
        #   if tmp is not None:
        #     out.append(tmp)
        # except:
        #   print u'Failed to parse row: {} {}'.format(len(row), row.prettify())
        
        # if i > 10: return out
        
    return out
    
    
    
    


def parse_list():
  items = [
    ['physics','List_of_Nobel_laureates_in_Physics'],
    ['chemistry','List_of_Nobel_laureates_in_Chemistry'],
    ['peace','List_of_Nobel_Peace_Prize_laureates'],
    ['medicine','List_of_Nobel_laureates_in_Physiology_or_Medicine'],
    ['literature','List_of_Nobel_laureates_in_Literature'],
  ]
  with Wiki() as api:
    out = OrderedDict()
    for group, title in items:
      out[group] = api.get_list(title, 'Laureates', api.parse_nobel)
      print group, title, len(out[group])
      
    with codecs.open(PEOPLE_FILE, 'w', 'utf-8') as f:
      for group, people in out.items():
        for person in people:
          f.write(u'{}, {}\n'.format(group, person))
    
    # for person in people:
    #   print person

def parse_war():
  items = [
   # u'List of wars 1000\u20131499',
   # u'List of wars 1500\u20131799',
    'List_of_wars_1000-1499',
    'List_of_wars_1500-1799',
    'List_of_wars_1800-1899',
    'List_of_wars_1900-1944',
    'List_of_wars_1945-1989',
    'List_of_wars_1990-2002',
    'List_of_wars_2003-2010',
    'List_of_wars_2011-present',
  ]
  # out = OrderedDict()
  out = []
  with Wiki() as api:
    for title in items:
      # out[title] = api.get_list(title, None, api.parse_war)
      out.extend(api.get_list(title, None, api.parse_war))
      print title, len(out)
  # pprint(out)
  json.dump(out, open(WAR_FILE, 'w'), indent=2)
    


def parse_simple():
  '''Get the people from the list and turn it into a json'''
  with Wiki() as api:
    out = []
    with codecs.open(PEOPLE_FILE, 'r', 'utf-8') as f:
      for tmp in f.readlines():
        group = tmp.split(',')[0].strip()
        person = ','.join(tmp.split(',')[1:]).strip()
        
        try:
          out.append(api.get_person(person, group))
        except InfoError as e:
          print person, group, e
        
  json.dump(out, open(SIMPLE_FILE, 'w'), indent=2)
  


def parse_nice():
  
  out = json.load(open(SIMPLE_FILE, 'r'))
  m = dict(birth_date='start',
           death_date='end',
           title='id')
  for o in out:
    tmp = {v:o[k] for k,v in m.items()}
    tmp['start'] == tmp['start'].split('-')[0]
    tmp['end'] == tmp['end'].split('-')[0]
    tmp['lane'] = 1
    print '{},'.format(tmp)


if __name__ == '__main__':
  from pysurvey import util
  util.setup_stop()
  
  
  # parse_list()
  # parse_simple()
  # parse_nice()
  
  parse_war()
  
  # with Wiki() as api:
  #   print api.get_person('J. J. Thomson', None)
  
  