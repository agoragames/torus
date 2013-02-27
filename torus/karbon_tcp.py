'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

import socket

import gevent
from gevent.server import StreamServer

class KarbonTcp(StreamServer):
  '''
  A TCP server implementing the Carbon protocol.
  '''

  def __init__(self, **config):
    '''
    Initialize with the given configuration and start the server.
    '''
    host = config.get('host', '')
    port = config.get('port', 2003)

    self._schemas = config.get('schemas')
    self._aggregates = config.get('aggregates')

    super(KarbonTcp,self).__init__( (host,int(port)), self.handle )

  def handle(self, sock, address):
    '''
    Handle a new client on a fresh greenlet.
    '''
    # We could in the future make these configurable
    sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
    recv_size = sock.getsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF)

    while True:
      try:
        lines = sock.recv( recv_size )
        if not len(lines):
          sock.close()
          return
      except EnvironmentError:
        sock.close()
        return

      # spawn the line processing into another greenlet so that overhead of
      # communicating with store does not prevent reading more data points
      # from this client.
      gevent.spawn( self._process_lines, lines )
      

  def _process_lines(self, lines):
    '''
    Process all the datapoints that we read.
    '''
    for line in lines.split('\n'):
      if not len(line.strip()): continue

      stat,val,timestamp = line.split()
      timestamp = long(timestamp)
      aggregates = self._aggregates.match( stat )

      for schema in self._schemas:
        schema.store(stat,val,timestamp)
        for ag in aggregates:
          schema.store(ag,val,timestamp)
