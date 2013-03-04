'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

import re

import ujson
from urlparse import *
from gevent.pywsgi import WSGIServer

FUNC_MATCH = re.compile('^(?P<func>[a-z]+)\((?P<stat>[^\)]+)\)$')

class Web(WSGIServer):
  '''
  Web server to mine data out of kairos.
  '''

  def __init__(self, **kwargs):
    '''
    Initialize with the given configuration and start the server.
    '''
    host = kwargs.get('host', '')
    port = kwargs.get('port', 8080)
    self._configuration = kwargs.get('configuration')
    super(Web,self).__init__( (host,int(port)), self.handle_request, log=None )

  def handle_request(self, env, start_response):
    cmd = env['PATH_INFO'][1:]
    if cmd.endswith('/'):
      cmd = cmd[:-1]
    params = parse_qs( env['QUERY_STRING'] )
   
    try:
      if cmd=='data':
        return ujson.dumps( self._data(params, start_response), double_precision=4 )
    except Exception as e:
      import traceback
      traceback.print_exc()
      start_response( '500 Internal Server Error', 
        [('content-type','application/json')] )
      return []

    start_response( '404 Not Found', [('content-type','application/json')] )
    return []

  def _data(self, params, start_response):
    '''
    Handle the data URL.
    '''
    rval = []

    format = params.setdefault('format',['graphite'])[0]

    # Force condensed data for graphite
    if format=='graphite':
      params['condensed'] = True
    params['condensed'] = bool(params.get('condensed',False))

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
      
      # find the schema that matches 
      schemas = self._configuration.schemas(stat)

      if not schemas:
        rval.append( {
          'stat' : stat,
          'function' : func,
          'target' : stat,  # graphite compatible key
          'datapoints' : []
        } )
      
      # TODO: what to do with multiple schema matches?
      schema = schemas[-1]
      intervals = schema.config['intervals'].keys()
      data = schema.timeseries.series(stat, intervals[-1], 
        condensed=params['condensed'], transform=func)
      rval.append( {
        'stat' : stat,
        'function' : func,
        'target' : stat,  # graphite compatible key
        'schema' : schema.name,
        'interval' : intervals[-1],
        'datapoints' : data,
      } )

    start_response('200 OK', [('content-type','application/json')] )
    return rval
