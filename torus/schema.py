'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

from urlparse import *
import re

from redis import Redis
from pymongo import MongoClient
from kairos import Timeseries
from sqlalchemy import create_engine
import cql
import time

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
    self._count = 0
    self._name = name
    self._host = config.pop('host', 'sqlite:///:memory:')
    self._rolling = config.pop('rolling', 0)
    self._generator = config.pop('generator',None)

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

    self.config = config
    self.timeseries = Timeseries(self._host, **config)

    # Bind some of the timeseries methods to this for convenience
    self.list = self.timeseries.list
    self.properties = self.timeseries.properties
    self.iterate = self.timeseries.iterate

  @property
  def name(self):
    return self._name

  @property
  def host(self):
    return self._host

  @property
  def count(self):
    return self._count

  def generate(self):
    if self._generator:
      stat,value = self._generator()
      return stat,value,time.time()
    return None

  def store(self, stat, val, timestamp=None):
    '''
    Store a value in this schema.
    '''
    if self.match(stat):
      if self._transform:
        stat,val = self._transform(stat,val)
        if stat is None:
          return False
      self._count += 1
      self.timeseries.insert(stat, val, timestamp, intervals=self._rolling)
      return True
    return False

  def _match_single(self, stat):
    '''
    Used for when schema implements a single regular expression, returns
    True if the stat matches this schema, False otherwise.
    '''
    if isinstance(stat,(list,tuple)):
      matches = filter(None, [self._patterns.search(s) for s in stat] )
      return len(matches)==len(stat)
    return self._patterns.search(stat) is not None

  def _match_list(self, stat):
    '''
    Used for when schema implements several regular expressions, returns
    True if the stat matches this schema, False otherwise.
    '''
    matches = set()
    for pattern in self._patterns:
      if isinstance(stat,(list,tuple)):
        for s in stat:
          if pattern.search(s):
            matches.add(s)
        if len(matches)==len(stat):
          return True
      elif pattern.search(stat):
        return True
    return False
