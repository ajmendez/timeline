# wikipedia information api

import os
import json
import codecs 
import datetime
from pprint import pprint


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
  
  def get_section(self, title, sectionname, **kwargs):
    params = dict(
      action='parse',
      prop='sections',
      page=title,
      format='json'
    )
    request = self.session.get(URL, params=params)
    sections = json.loads(request.content)['parse']['sections']
    for section in sections:
      if sectionname in section['line']:
        return self.get_page(title, section=section['index'], cache=False, **kwargs)
    raise ValueError('Could not find section: {}.  Page Sections: {}'
                      .format(sectionname, 
                              ', '.join([s['line'] for s in sections]) ))
    # print request.content
  
  def get_page(self, title, cache=True, beautiful=False, **kwargs):
    '''Get a page
    http://en.wikipedia.org/w/api.php?
    action=parse&prop=wikitext&page=List_of_Nobel_laureates_in_Physics&
    format=json&section=1
    
    '''
    if title in self.cache and cache:
      return self.cache[title]
    if beautiful:
      kwargs['prop'] = 'text'
    
    
    params = dict(
      action='parse',
      prop='wikitext',
      page=title.encode('utf-8'),
      format='json',
    )
    params.update(kwargs)
    
    # try:
    request = self.session.get(URL, params=params)
    print request.url
    
    
    page = json.loads(request.content)['parse'][params['prop']]['*']
    
    # handle redirects
    if '#REDIRECT' in page:
      newtitle = u'{}'.format(mwparserfromhell.parse(page)
                                              .filter_wikilinks()[0].title)
      return self.get_page(newtitle, 
                           cache=cache, beautiful=beautiful, 
                           **kwargs)
      # raise ValueError()
    
    
    if cache:
      self.cache[title] = page
    
    if beautiful:
      return BeautifulSoup(page)
    else:
      return page

    # except Exception as e:
    #   print u'Failed to get the page: {}'.format(title)
    #   print request.content
    #   raise e
  
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
    raise ValueError('Missing InfoBox')
  
  def debug_page(self, title):
    page = self.get_page(title)
    code = mwparserfromhell.parse(page)
    # pprint(page)
    raise ValueError()
  
  def get_person(self, name, group):
    '''get a dictionary for a person.'''
    out = self.parse_infobox(name, self.get_page(name))
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
  
  def get_list(self, title, section):
    out = []
    tmp =  self.get_section(title, section, beautiful=True)
    for i, row in enumerate(tmp.findAll('tr')):
      for j,col in enumerate(row.findAll('td')):
        if ( ((len(row) == 11) and (j == 2)) or
             ((len(row) <  11) and (len(row) > 5) and (j == 1)) or 
             ((len(row) ==  5) and( j == 0)) ):
          if 'Not awarded' in str(row):
            continue
          
          try:
            # tmp = col.find('a').get('href').replace('/wiki/','')
            tmp = col.find('a').get('title').replace('/wiki/','')
            out.append(tmp)
          except:
            print u'Failed to parse row: {} {}'.format(len(row), row.prettify())
    return out
    
    
    
    



def parse_simple():
  '''Get the people from the list and turn it into a json'''
  with Wiki() as api:
    out = []
    # tmp = codecs.open(PEOPLE_FILE, 'r', 'utf-8').readlines()
    with codecs.open(PEOPLE_FILE, 'r', 'utf-8') as f:
      for person in f.readlines():
        out.append(api.get_person(person.strip(), None))
    # for person in open(PEOPLE_FILE,'r').readlines():
    #   out.append(api.get_person(person.strip(), None))
    #   print out
    json.dump(out, open(SIMPLE_FILE, 'w'), indent=2)
  
def parse_list():
  with Wiki() as api:
    people = api.get_list('List_of_Nobel_laureates_in_Physics','Laureates')
    with codecs.open(PEOPLE_FILE, 'w', 'utf-8') as f:
      # f.write(u'\ufeff')
      for person in people:
        f.write(u'{}\n'.format(person))
    
    # for person in people:
    #   print person
  


if __name__ == '__main__':
  from pysurvey import util
  util.setup_stop()
  
  
  # parse_list()
  parse_simple()
  
  # with Wiki() as api:
  #   # api.debug_page('List_of_Nobel_laureates_in_Physics')
  #   tmp =  api.get_section('List_of_Nobel_laureates_in_Physics','Laureates', beautiful=True)
  #   for i, row in enumerate(tmp.findAll('tr')):
  #     # if i > 10:
  #     #   break
  #     for j,col in enumerate(row.findAll('td')):
  #       if ( ((len(row) == 11) and (j == 2)) or
  #            ((len(row) <  11) and (len(row) > 5) and (j == 1)) or 
  #            ((len(row) ==  5) and( j == 0)) ):
  #         # print col.find('td').find('a').get('href')
  #         if 'Not awarded' in str(row):
  #           continue
  #         
  #         print col.find('a').get('href').replace('/wiki/','')
  #         try:
  #           pass
  #         except:
  #           print len(row), row.prettify()
          
    # print tmp.prettify()
    # print mwparserfromhell.parse(tmp).html()
  # Get the page and parse it
    # page = api.get_page('Albert Einstein')
    # print parse_infobox(page)
  
    # load the data into the db
    # pprint(api.get_person('Albert Einstein', 'Scientist'))
  
  
    # get a list of american
    # api.debug_page('List_of_American_scientists')
    # api.get_list('List_of_Nobel_laureates_in_Physics', 'Scientist')
    # api.debug_page('api')
  
  