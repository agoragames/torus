'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

from chai import Chai

from torus import schema
from torus.schema import Schema, long_or_float

class SchemaTest(Chai):

  def test_init_simple_options(self):
    config = {
      'host' : '',
      'match' : 'astat',
      'intervals' : {
        'minute' : {
          'step': 60
        }
      } 
    }

    expect( schema.Timeseries ).args( var('client'), type='count',
      read_func=is_arg(long_or_float), write_func=is_arg(long_or_float), intervals = {
        'minute':{'step':60}
      } )

    s = Schema('name', config)
    assert_equals( 'name', s._name )
    assert_equals( s.match, s._match_single )

  def test_init_more_options(self):
    config = {
      'host' : 'redis://localhost:6379/4',
      'match' : ['^astat', '^bstat\.'],
      'read_func' : float,
      'write_func' : lambda v: '%0.3f'%(v),
      'intervals' : {
        'minute' : {
          'step': 60
        }
      } 
    }

    expect( schema.Timeseries ).args( var('client'), type='count',
      read_func=var('rfunc'), write_func=var('wfunc'), intervals = {
        'minute':{'step':60}
      } )

    s = Schema('name', config)
    assert_equals( 'name', s._name )
    assert_equals( s.match, s._match_list )
    assert_equals( 0.2, var('rfunc').value('0.2') )
    assert_equals( '0.333', var('wfunc').value(0.3333333333) )
