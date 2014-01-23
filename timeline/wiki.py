# wikipedia information api


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










class Wiki(object):
  def __init__(self):
    self.session = requests.session()
    # self.db = dataset.connect(DB)
  
  def get_page(self, title):
    params = dict(
      format='json',
      action='query',
      prop='revisions',
      rvprop='content',
      titles=title
    )
    try:
      request = self.session.get(URL, params=params)
      page = json.loads(request.content)['query']['pages']
      revid = page.keys()[0]
      return page[revid]['revisions'][0]['*']
    except Exception as e:
      print 'Failed to get the page: {}'.format(title)
      raise e
  
  def parse_date(wikiDate):
    ''' Parse a mediawiki date template -- assumes years, month, day
    Input:
      a mwparser object containing just the date to be parsed
    Returns:
      datetime.date object of the date
    '''
    template = mwparserfromhell.parse(str(wikiDate.value))
    return '-'.join(map(template.filter_templates()[0].get, [3,2,1]))
    # d = map(template.filter_templates()[0].get, [1,2,3])
    # d = [int(str(x.value)) for x in d]
    # return datetime.date(*d)
 
 
  def parse_infobox(page):
    '''Parse out the nice mediawiki markdown to get birth and death
    Input:
      mediawiki unicode page string
    Returns:
      a dictionary with name(string), birth_date:DateTime, death_date:DateTime
    '''
    # try:
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
            item = parse_date(template.get(date))
          except ValueError as e:
            item = None
          output[date] = item

        # ok we are done here
        return output
      
    raise ValueError('Missing InfoBox')
 
    # except Exception as e:
    #   print "Failed to parse find infobox or something else"
    #   raise e
  
  
  
  def debug_page(self, title):
    page = self.get_page(title)
    pprint(page)
    raise ValueError()
  
  def get_person(self, name, group):
    '''Append the name, birth date, and death date to
    the starting kwargs dictionary'''
    table = self.db['people']
    
    out = table.find_one(name=name)
    
    if out is None:
      out = parse_infobox(self.get_page(name))
      out['group'] = group
      table.insert(out)
    
    return out
  
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
  
  
  api = Wiki()
  
  # Get the page and parse it
  # page = api.get_page('Albert Einstein')
  # print parse_infobox(page)
  
  # load the data into the db
  # pprint(api.get_person('Albert Einstein', 'Scientist'))
  
  
  # get a list of american
  # api.debug_page('List_of_American_scientists')
  # api.get_list('List_of_Nobel_laureates_in_Physics', 'Scientist')
  api.debug_page('List_of_Nobel_laureates_in_Physics')
  
  