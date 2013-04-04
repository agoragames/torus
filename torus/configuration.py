'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

import imp
import hashlib

from torus.schema import Schema, long_or_float
from torus.aggregates import Aggregates

class Configuration(object):
  '''
  Manages the loading and reloading of configuration files.
  '''

  def __init__(self):
    self._files = []
    self._schemas = []
    self._aggregates = Aggregates()

  def load(self, fname):
    '''
    Load a file and cache the rename for future reloading.
    '''
    self._files.append( fname )
    self._load_source( fname )

  def reload(self):
    '''
    Reload all of the configurations.
    '''
    self._schemas = []
    self._aggregates = Aggregates()
    
    for fname in self._files:
      self._load_source( fname )

  def schemas(self, stat):
    '''
    Get the matching schemas for a stat, or an empty list if there aren't any.
    '''
    return [s for s in self._schemas if s.match(stat)]

  def process(self, stat, val, timestamp=None, seen=None):
    '''
    Process a stat through this configuration.
    '''
    if not seen:
      seen = set([stat])
    elif stat in seen:
      return

    aggregates = self._aggregates.match(stat)
    for schema in self._schemas:
      schema.store(stat, val, timestamp)
    
    # Infinite loop is prevented by match() implementation
    #seen = set([stat])
    #seen.update( aggregates )
    for ag in aggregates:
      self.process(ag, val, timestamp, seen=seen)

  def _load_source(self, fname):
    '''
    Load the file source.
    '''
    mod_name = hashlib.sha1(fname).hexdigest()
    with open(fname, 'r') as source:
      mod = imp.load_module( mod_name, source, fname, ('py','r',imp.PY_SOURCE) )
      mod.__dict__['long_or_float'] = long_or_float

      schemas = getattr(mod,'SCHEMAS',{})
      aggregates = getattr(mod,'AGGREGATES',[])

      for name,schema in schemas.iteritems():
        self._schemas.append( Schema(name, schema) )

      self._aggregates.add( aggregates )
