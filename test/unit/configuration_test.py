'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

from chai import Chai

from torus.configuration import Configuration
from torus.schema import Schema
from torus.aggregates import Aggregates

class ConfiguratonTest(Chai):

  def test_process_prevents_infinite_loops(self):
    c = Configuration()
    c._aggregates = mock()
    c._schemas = [ mock() ]

    expect( c._aggregates.match ).args('stat_1').returns(['stat_2']).times(1)
    expect( c._aggregates.match ).args('stat_2').returns(['stat_1']).times(1)
    expect( c._schemas[0].store ).times(2)

    c.process('stat_1', 'value', 'now')
