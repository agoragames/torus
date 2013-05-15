'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

import re

import ujson
from urlparse import *
from gevent.pywsgi import WSGIServer
import parsedatetime as pdt

FUNC_MATCH = re.compile('^(?P<func>[a-z]+)\((?P<stat>[^\)]+)\)$')
cal = pdt.Calendar()

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
      # changing name to 'series', still supporting 'data' for now
      if cmd in ('data', 'series'):
        return ujson.dumps( self._series(params, start_response), double_precision=4 )
    except Exception as e:
      import traceback
      traceback.print_exc()
      start_response( '500 Internal Server Error', 
        [('content-type','application/json')] )
      return []

    start_response( '404 Not Found', [('content-type','application/json')] )
    return []

  def _series(self, params, start_response):
    '''
    Handle the data URL.
    '''
    rval = []

    format = params.setdefault('format',['graphite'])[0]

    # Force condensed data for graphite return
    if format=='graphite':
      params['condensed'] = True
    params['condensed'] = bool(params.get('condensed',False))

    # If start or end times are defined, process them
    start = params.get('start', [''])[0]
    end = params.get('end', [''])[0]
    if start:
      try:
        start = float(start)
      except ValueError:
        match = cal.parse(start)
        if match and match[1]:
          start = time.mktime( match[0] )
        else:
          start = None
    if end:
      try:
        end = float(end)
      except ValueError:
        match = cal.parse(end)
        if match and match[1]:
          end = time.mktime( match[0] )
        else:
          end = None

    steps = int(params.get('steps',[0])[0])

    # First assemble the unique stats and the functions.
    stat_queries = {}
    for stat_spec in params['stat']:
      func_match = FUNC_MATCH.match(stat_spec)
      if func_match:
        func = func_match.groupdict()['func']
        stat = func_match.groupdict()['stat']
      else:
        if format=='graphite':
          func = 'mean'
        else:
          func = None
        stat = stat_spec
      stat_queries.setdefault( stat, {} )
      if func:
        stat_queries[stat][func] = func
      else:
        stat_queries[stat]['data'] = None

    # For each unique stat, walk trough all the schemas until we find one that
    # matches the stat and has a matching interval if one is specified. If there
    # isn't one specified, then pick the first match and the first interval.
    for stat,transforms in stat_queries.iteritems():

      schemas = self._configuration.schemas(stat)
      if not schemas:
        # No schema found
        rval.append( {
          'stat' : stat,
          'function' : func,
          'target' : stat,  # graphite compatible key
          'datapoints' : []
        } )
        continue

      interval = params.get('interval')

      for schema in schemas:
        if interval in schema.config['intervals'].keys():
          break
      else:
        # No interval found, pick the first interval of the chosen schema
        # TODO: pick the finest or largest interval?
        interval = schema.config['intervals'].keys()[0]


      # Handle if no actual transforms were defined
      if transforms=={'data':None}:
        transforms = None

      data = schema.timeseries.series(stat, interval,
        condensed=params['condensed'], transform=transforms,
        start=start, end=end, steps=steps)

      # If there were any transforms, then that means there's a list to append
      # for each matching stat, else there's just a single value.
      if transforms:
        for transform in transforms.iterkeys():
          # This transposition of the way in which kairos returns the
          # transforms and how torus presents it is most unfortunate.
          # In both cases I prefer the format for its given role.
          # TODO: Extract the data
          rval.append( {
            'stat' : stat,
            'function' : transform,
            'target' : stat,  # graphite compatible key
            'schema' : schema.name,
            'interval' : interval,
            'datapoints' : extract(data, transform),
          } )
      else:
        rval.append( {
          'stat' : stat,
          'target' : stat,  # graphite compatible key
          'schema' : schema.name,
          'interval' : interval,
          'datapoints' : data,
        } )

    start_response('200 OK', [('content-type','application/json')] )
    return rval
