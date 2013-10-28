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
    self._debug = 0
    self._schemas = []
    self._aggregates = Aggregates()
    self._transforms = {}
    self._macros = {}

  @property
  def debug(self):
    return self._debug

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
    self._transforms = {}
    self._macros = {}
    
    for fname in self._files:
      self._load_source( fname )

  def transform(self, name):
    '''
    Get a named transform from the configurations, or None if not found.
    '''
    return self._transforms.get(name)

  def macro(self, name):
    '''
    Get a named macro from the configurations, or None if not found.
    '''
    return self._macros.get(name)

  def schema(self, name):
    '''Get a schema by name, or None if not found.'''
    for s in self._schemas:
      if s.name == name:
        return s
    return None

  def schemas(self, stat=None):
    '''
    Get the matching schemas for a stat, or an empty list if there aren't any.
    If no stat name provided, will return a list of all schemas.
    '''
    if stat is None:
      return self._schemas[:]
    return [s for s in self._schemas if s.match(stat)]

  def process(self, stat, val, timestamp=None, seen=None):
    '''
    Process a stat through this configuration.
    '''
    if not seen:
      seen = set()
    elif stat in seen:
      return False
    seen.add(stat)

    aggregates = self._aggregates.match(stat)
    for schema in self._schemas:
      stored = schema.store(stat, val, timestamp)
      if self._debug:
        if stored:
          print 'STOR', stat, val, timestamp
        elif self._debug > 1:
          print 'SKIP', stat, val, timestamp
    
    # Infinite loop is prevented by match() implementation
    for ag in aggregates:
      processed = self.process(ag, val, timestamp, seen=seen)
      if self._debug and processed:
        print 'AGRT', ag, 'FROM', stat, val, timestamp

    return True

  def load_schema(self, name, spec):
    self._schemas.append( Schema(name,spec) )

  def load_aggregate(self, spec):
    self._aggregates.add( spec )

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
      transforms = getattr(mod,'TRANSFORMS',{})
      macros = getattr(mod,'MACROS',{})

      for name,schema in schemas.items():
        self.load_schema(name, schema)
      self.load_aggregate( aggregates )

      for name,func in transforms.items():
        self._transforms[name] = func

      for name,macro in macros.items():
        self._macros[name] = macro
      
      self._debug = getattr(mod, 'DEBUG', self._debug)
