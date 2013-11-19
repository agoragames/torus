'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

import re
import time

import ujson
from urlparse import *
from gevent.pywsgi import WSGIServer

from .util import parse_time
from .exceptions import *

FUNC_MATCH = re.compile('^(?P<func>[a-zA-Z0-9_]+)\((?P<stat>[^\)]+)\)$')

def extract(dct, transform):
  '''
  Recursively extract the transformed data from a given dictionary.
  '''
  # If we're at the point where we've found the transformed data, return it
  if transform in dct:
    return dct[transform]

  rval = type(dct)()
  for k,v in dct.iteritems():
    rval[k] = extract(v, transform)
  return rval

class Web(WSGIServer):
  '''
  Web server to mine data out of kairos.
  '''

  def __init__(self, **kwargs):
    '''
    Initialize with the given configuration and start the server.
    '''
    self.host = kwargs.get('host', '')
    self.port = kwargs.get('port', 8080)
    self._configuration = kwargs.get('configuration')
    super(Web,self).__init__( (self.host,int(self.port)), self.handle_request, log=None )

  def handle_request(self, env, start_response):
    cmd = env['PATH_INFO'][1:]
    if cmd.endswith('/'):
      cmd = cmd[:-1]
    params = parse_qs( env['QUERY_STRING'] )
   
    try:
      if cmd == 'series':
        result = self._series(params)

      elif cmd == 'list':
        result = self._list(params)

      elif cmd == 'properties':
        result = self._properties(params)

      else:
        raise HttpNotFound()

      start_response('200 OK', [('content-type','application/json')] )
      return [ ujson.dumps(result, double_precision=4) ]

    except HttpError as e:
      start_response( '%s %s'%(e.code, e.msg), 
        [('content-type','application/json')] )
      return []
      
    except Exception as e:
      import traceback
      traceback.print_exc()
      start_response( '500 Internal Server Error', 
        [('content-type','application/json')] )
      return []

    start_response( '404 Not Found', [('content-type','application/json')] )
    return []

  def _list(self, params):
    '''
    Return a list of all stored stat names.
    '''
    # Future versions may add an "extended" view that includes properties.
    schema_name = params.get('schema',[None])[0]
    rval = set()

    if schema_name:
      schema = self._configuration.schema(schema_name)
      if not schema:
        raise HttpNotFound()
      rval.update( schema.list() )
    else:
      for schema in self._configuration.schemas():
        rval.update( schema.list() )
    return sorted(rval)

  def _properties(self, params):
    '''
    Fetch the properties of a stat.
    '''
    rval = {}

    for stat in params['stat']:
      rval.setdefault( stat, {} )
      for schema in self._configuration.schemas(stat):
        rval[stat][schema.name] == schema.properties(stat)

    return rval

  def _series(self, params):
    '''
    Handle the data URL.
    '''
    rval = []

    format = params.setdefault('format',['graphite'])[0]
    condense = False
    fetch = None
    process_row = None
    join_rows = None

    # Force condensed data for graphite return
    if format=='graphite':
      condense = True
    else:
      condense = bool(params.get('condense',[False])[0])

    collapse = bool(params.get('collapse',[False])[0])

    # If start or end times are defined, process them
    start = params.get('start', [''])[0]
    end = params.get('end', [''])[0]
    if start:
      start = parse_time(start)
    if end:
      end = parse_time(end)

    steps = int(params.get('steps',[0])[0])
    schema_name = params.get('schema',[None])[0]
    interval = params.get('interval',[None])[0]

    # First assemble the unique stats and the functions.
    stat_queries = {}
    for stat_spec in params['stat']:
      func_match = FUNC_MATCH.match(stat_spec)
      if func_match:
        func_name = func_match.groupdict()['func']
        stat = func_match.groupdict()['stat']
      else:
        if format=='graphite':
          func_name = 'mean'
        else:
          func_name = None
        stat = stat_spec

      stat = tuple(stat.split(','))
      stat_queries.setdefault( stat, {} )
      
      # First process as a macro
      if func_name:
        macro = self._configuration.macro(func_name)
        if macro:
          format = macro.get( 'format', format )
          fetch = macro.get( 'fetch' )
          process_row = macro.get( 'process_row' )
          join_rows = macro.get( 'join_rows' )
          condense = macro.get( 'condense', condense )
          collapse = macro.get( 'collapse', collapse )
          start = macro.get( 'start', start )
          end = macro.get( 'end', end )
          steps = macro.get( 'steps', steps )
          func_name = macro.get( 'transform' )
          schema_name = macro.get( 'schema', schema_name )
          interval = macro.get( 'interval', interval )
          if start:
            start = parse_time(start)
          if end:
            end = parse_time(end)

      # If not a macro, or the macro has defined its own transform
      if func_name:
        func = self._configuration.transform(func_name) or func_name
        stat_queries[stat][stat_spec] = (func_name, func)
      else:
        # essentially a "null" transform, we'll get our data back
        stat_queries[stat][stat_spec] = (None, None)

    # For each unique stat, walk trough all the schemas until we find one that
    # matches the stat and has a matching interval if one is specified. If there
    # isn't one specified, then pick the first match and the first interval.
    for stat,specs in stat_queries.iteritems():
      schema = self._configuration.schema(schema_name)

      # If user-requested schema (or none) not found, try to find one.
      if not schema and not schema_name:
        schemas = self._configuration.schemas(stat)
        for schema in schemas:
          if interval in schema.config['intervals'].keys():
            break
        else:
          # No matching interval found, so if there were any schemas and the
          # user didn't define an interval, try to find one.
          if schema and not interval:
            interval = schema.config['intervals'].keys()[0]

      # If user-requested schema found, resolve interval if necessary
      elif not interval:
        interval = schema.config['intervals'].keys()[0]

      # No schema found, return an empty data set for each query
      # on that stat
      if not schema:
        for spec,transform in specs.items():
          rval.append( {
            'stat' : spec,
            'stat_name' : stat,
            'function' : transform[0],
            'target' : stat,  # graphite compatible key
            'datapoints' : []
          } )
        continue

      # Filter out the unique transforms 
      transforms = specs.values()
      if transforms==[(None,None)]:
        transforms = None
      else:
        transforms = [ t[1] for t in transforms ]

      start = start or None
      end = end or None

      data = schema.timeseries.series(stat, interval,
        condense=condense, transform=transforms,
        fetch=fetch, process_row=process_row, join_rows=join_rows,
        start=start, end=end, steps=steps, collapse=collapse)

      # If there were any transforms, then that means there's a list to append
      # for each matching stat, else there's just a single value.
      if transforms:
        for spec,transform in specs.iteritems(): 
          # This transposition of the way in which kairos returns the
          # transforms and how torus presents it is most unfortunate.
          # In both cases I prefer the format for its given role.
          rval.append( {
            'stat' : spec,
            'stat_name' : stat,
            'function' : transform[0],
            'target' : stat,  # graphite compatible key
            'schema' : schema.name,
            'interval' : interval,
            'datapoints' : extract(data, transform[1]),
          } )
      else:
        rval.append( {
          'stat' : specs.keys()[0],
          'stat_name' : stat,
          'target' : stat,  # graphite compatible key
          'schema' : schema.name,
          'interval' : interval,
          'datapoints' : data,
        } )

    return rval
