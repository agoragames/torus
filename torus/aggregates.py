'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

import re

STAR = '[a-zA-Z0-9_-]+'

class Aggregates(object):
  '''
  Implements the aggregating of stats through pattern matches.
  '''

  def __init__(self, rules=[]):
    '''
    Initialize with a list of aggregate rules.
    '''
    self._rules = []
    self.add( rules )

  def add(self, rules):
    '''
    Add a set of aggregate rules.
    '''
    for target,source in rules:
      self._rules.append( Aggregate(source,target) )

  def match(self, stat):
    '''
    Return the name of any aggregates which should be generated from the stat
    '''
    return filter(None, (r.match(stat) for r in self._rules))

class Aggregate(object):
  '''
  A single aggregate.
  '''

  def __init__(self, source, target):
    self._source = source
    self._target = target
    source = source.split('.')
    target = target.split('.')

    source_pattern = []
    for src_comp in source:
      if src_comp.startswith('<') and src_comp.endswith('>'):
        source_pattern.append( '(?P%s%s)'%(src_comp, STAR) )
      elif src_comp=='*':
        source_pattern.append( STAR )
      else:
        source_pattern.append( src_comp )
    source_pattern = "\.".join( source_pattern )
    self._pattern = re.compile('^%s$'%(source_pattern))

    target_format = []
    for target_comp in target:
      if target_comp.startswith('<') and target_comp.endswith('>'):
        name = target_comp[1:-1]
        target_format.append( '%%(%s)s'%( name ) )
      else:
        target_format.append( target_comp )
    self._target_format = '.'.join( target_format )

  def __repr__(self):
    return self._source

  def match(self, stat):
    '''
    If the stat matches, return the name of the aggregate, else return None
    '''
    res = self._pattern.match(stat)
    if res:
      return self._target_format%res.groupdict()
    return None
