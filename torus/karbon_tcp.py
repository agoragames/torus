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

  def __init__(self, **kwargs):
    '''
    Initialize with the given configuration and start the server.
    '''
    host = kwargs.get('host', '')
    port = kwargs.get('port', 2003)
    self._configuration = kwargs.get('configuration')
    super(KarbonTcp,self).__init__( (host,int(port)), self.handle )

  def handle(self, sock, address):
    '''
    Handle a new client on a fresh greenlet.
    '''
    # We could in the future make these configurable
    sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)

    while True:
      try:
        recv_size = sock.getsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF)
        lines = sock.recv( recv_size )
        if not len(lines):
          sock.close()
          return
      except EnvironmentError as e:
        import traceback
        traceback.print_exc()
        sock.close()
        return

      # spawn the line processing into another greenlet so that overhead of
      # communicating with store does not prevent reading more data points
      # from this client.
      # TODO: handle when there's a partial last line and how to integrate
      # that with the next batch of data read from the socket.
      gevent.spawn( self._process_lines, lines )
      
  def _process_lines(self, lines):
    '''
    Process all the datapoints that we read.
    '''
    try:
      import time
      num = len(lines.split('\n'))
      t0 = time.time()
      for line in lines.split('\n'):
        if not len(line.strip()): continue

        if self._configuration.debug>1:
          print 'RECV', line
        try:
          stat,val,timestamp = line.split()
        except ValueError:
          # TODO: Store like stasd failed lines
          continue
        timestamp = long(timestamp)

        self._configuration.process(stat,val,timestamp)
      t1 = time.time()
      if self._configuration.debug:
        print 'DONE', num, t1-t0, float(num)/float(t1-t0)
    except Exception as e:
      import traceback
      traceback.print_exc()
