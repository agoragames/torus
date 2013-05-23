'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

import time

from chai import Chai

from torus.web import Web
from torus.configuration import Configuration

SCHEMAS = {
  'redis-minutely' : {
    'type'  : 'histogram',
    'host'  : 'redis://localhost',
    'match' : '.*',
    'intervals' : {
      'second' : {
        'step' : 1,
        'steps' : 60
      },
      'minute' : {
        'step' : 60,
        'steps' : 5,
      }
    }
  },

  'mongo-hourly': {
    'type'  : 'histogram',
    'host'  : 'mongodb://localhost',
    'match' : '.*',
    'intervals' : {
      'minute' : {
        'step' : 60,
        'steps' : 5,
      },
      'hour' : {
        'step' : '1h',
        'steps' : 24,
      },
    }
  }
}

AGGREGATES = (
  ('foo', 'foo.*'),
  ('foo', 'foo.*.*'),
  ('foo.<bar>', 'foo.<bar>.*')
)

config = Configuration()
for name,spec in SCHEMAS.iteritems():
  config.load_schema( name, spec )
config.load_aggregate( AGGREGATES )

# insert some test data, 2 hours in 30 second intervals
for schema in config._schemas:
  schema.timeseries.delete( 'foo' )
  schema.timeseries.delete( 'foo.bar' )
  schema.timeseries.delete( 'foo.bor' )
  schema.timeseries.delete( 'foo.bar.cat' )
  schema.timeseries.delete( 'foo.bor.cat' )
  schema.timeseries.delete( 'foo.bar.dog' )

t = time.time() - 7200
for x in xrange(0,7200,30):
  config.process( 'foo.bar.cat', x/15, t+x )
  config.process( 'foo.bor.cat', x/15, t+x )
  config.process( 'foo.bar.dog', x/15, t+x )

web = Web(configuration=config)

# It would be nice to spin up the web server here and make requests against it

class WebTest(Chai):

  def setUp(self):
    super(WebTest,self).setUp()

  def test_series(self):
    start_response = mock()
    expect( start_response )

    request = {
      'stat' : ['count(foo)', 'count(foo.bar)', 'count(foo.bor)',
        'count(foo.bar.dog)', 'count(foo.bor.cat)'],
    }
    result = web._series(request, start_response)

    counts = {}
    for row in result:
      counts[ row['stat'] ] = row['datapoints'].values()[0]

    dog = counts['foo.bar.dog']
    assert_equals( dog, counts['foo.bor.cat'] )
    assert_equals( dog, counts['foo.bor'] )
    assert_equals( 2*dog, counts['foo.bar'] )
    assert_equals( 3*dog, counts['foo'] )

    request = {
      'stat' : ['foo'],
      'interval' : ['second']
    }
    result = web._series(request, start_response)
    assert_equals( 'redis-minutely', result[0]['schema'] )
