'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''
import logging
from collections import OrderedDict

from chai import Chai

from torus.karbon_tcp import KarbonTcp

class KarbonTcpTest(Chai):
  
  def setUp(self):
    super(KarbonTcpTest,self).setUp()
    self.karbon = KarbonTcp.__new__( KarbonTcp )
    self.karbon._configuration = mock()
    self.karbon._configuration.debug = 0

  def test_process_lines(self):
    expect( self.karbon._configuration.process ).args( 'stat', 'foo', 1234 )
    expect( self.karbon._configuration.process ).args( 'stat', 'foo.bar', 1234 )
    expect( self.karbon._configuration.process ).args( 'stat', 'foo bar', 1234 )
    expect( self.karbon._configuration.process ).args( 'stats.statsd.bad_lines_seen', '0', 1391710252 )

    self.karbon._process_lines( '''
      stat\tfoo\t1234
      stat    foo.bar 1234
      stat  foo bar        1234.5678
      stats.statsd.bad_lines_seen 0 1391710252
    ''')

  def test_process_lines_when_bad_match(self):
    stub( self.karbon._configuration.process )
    stub( logging.exception )
    
    self.karbon._configuration.debug = 1

    self.karbon._process_lines('')
    self.karbon._process_lines('''
      stat\tfoo\tbar''')
