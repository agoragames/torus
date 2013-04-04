'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

from urlparse import *
import re

from redis import Redis
from kairos import Timeseries

def long_or_float(v):
  try:
    return long(v)
  except ValueError:
    return float(v)

class Schema(object):
  '''
  Implements the schema and associated data processing for data points.
  '''

  def __init__(self, name, config):
    self._name = name
    self._host = config.pop('host', 'redis://localhost:6379/0')

    config.setdefault('type', 'count')
    config.setdefault('write_func', long_or_float)
    config.setdefault('read_func', long_or_float)
    self._transform = config.get('transform')

    # parse the patterns and bind the Schema.match function
    # TODO: optimize this binding even further to reduce lookups at runtime
    self._patterns = config.pop('match', [])
    if isinstance(self._patterns, (tuple,list)):
      if len(self._patterns) != 1:
        self._patterns = [ re.compile(x) for x in self._patterns ]
        self.match = self._match_list
      else:
        self._patterns = re.compile(self._patterns[0])
        self.match = self._match_single
    else:
      self._patterns = re.compile(self._patterns)
      self.match = self._match_single

    self._client = self._init_client()

    # TODO: Remove the need for this and add accessors to Schema or Kairos
    self.config = config
    self.timeseries = Timeseries(self._client, **config)

  @property
  def name(self):
    return self._name

  @property
  def host(self):
    return self._host

  def store(self, stat, val, timestamp=None):
    '''
    Store a value in this schema.
    '''
    if self.match(stat):
      if self._transform:
        stat,val = self._transform(stat,val)
        if stat is None:
          return False
      self.timeseries.insert(stat, val, timestamp)
      return True
    return False

  def _match_single(self, stat):
    '''
    Used for when schema implements a single regular expression, returns
    True if the stat matches this schema, False otherwise.
    '''
    return self._patterns.search(stat) is not None

  def _match_list(self, stat):
    '''
    Used for when schema implements several regular expressions, returns
    True if the stat matches this schema, False otherwise.
    '''
    for pattern in self._patterns:
      if pattern.search(stat):
        return True
    return False

  def _init_client(self):
    '''
    Parse the host URL and initialize a client connection.
    '''
    if not isinstance(self._host, (str,unicode)):
      return self._host


    # To force scheme and netloc behavior. Easily a bug here but let it 
    # go for now
    if '//' not in self._host:
      self._host = '//'+self._host
    location = urlparse(self._host)

    if location.scheme in ('','redis'):
      if ':' in location.netloc:
        host,port = location.netloc.split(':')
      else:
        host,port = location.netloc,6379

      # TODO: better matching here
      if location.path in ('', '/'):
        db = 0
      else:
        db = location.path[1:]

      return Redis(host=host, port=int(port), db=int(db))
      

    raise ValueError("unsupported scheme", location.scheme)      
