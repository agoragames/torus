'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

import time

import ujson
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
config._transforms['unique'] = lambda dct: len(dct)

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

  def _request(self, request):
    '''
    Helper to make a request and confirm that it can be encoded. Needed
    until this test actually starts a webserver and queries it.
    '''
    start_response = mock()
    expect(start_response)
    result = web._series(request, start_response)
    ujson.dumps( result, double_precision=4 )
    return result

  def test_series(self):
    request = {
      'stat' : ['count(foo)', 'count(foo.bar)', 'count(foo.bor)',
        'count(foo.bar.dog)', 'count(foo.bor.cat)', 'min(foo)', 'max(foo)'],
    }
    result = self._request(request)

    counts = {}
    for row in result:
      counts[ row['stat'] ] = row['datapoints'].values()[-1]

    dog = counts['count(foo.bar.dog)']
    assert_not_equals( 0, dog )
    assert_equals( dog, counts['count(foo.bor.cat)'] )
    assert_equals( dog, counts['count(foo.bor)'] )
    assert_equals( 2*dog, counts['count(foo.bar)'] )
    assert_equals( 3*dog, counts['count(foo)'] )
    assert_not_equals( counts['count(foo)'], counts['max(foo)'] )
    assert_not_equals( counts['max(foo)'], counts['min(foo)'] )


    request = {
      'stat' : ['foo'],
      'interval' : ['second']
    }
    result = self._request(request)
    assert_equals( 'redis-minutely', result[0]['schema'] )
    
    # Simply test that this works, come back to asserting the results
    # another time
    request = {
      'stat' : ['foo'],
      'start' : ['yesterday']
    }
    result = self._request(request)
    
    request = {
      'stat' : ['foo'],
      'start' : ['8675309']
    }
    result = self._request(request)

  def test_series_with_stat_lists(self):
    # check the graphite version wherein there's always a "function" (mean)
    # so the raw data and collapse function isn't exercised.
    request = {
      'stat' : ['count(foo.bar.cat,foo.bar.dog)', 'count(foo.bar.cat)', 'count(foo.bar.dog)'],
    }
    result = self._request(request)

    counts = {}
    for row in result:
      counts[ row['stat'] ] = row['datapoints'].values()[-1]

    assert_not_equals( 0, counts['count(foo.bar.cat,foo.bar.dog)'] )
    assert_equals( counts['count(foo.bar.cat,foo.bar.dog)'],
       counts['count(foo.bar.cat)'] + counts['count(foo.bar.dog)'] )

    # check the graphite version wherein there's always a "function" (mean)
    # so the raw data and collapse function isn't exercised.
    request = {
      'stat' : [
        'foo.bar.cat,foo.bar.dog', 'foo.bar.cat', 'foo.bar.dog',
        'unique(foo.bar.cat,foo.bar.dog)', 'unique(foo.bar.cat)', 'unique(foo.bar.dog)'
      ],
      'format' : 'json',
      'collapse' : 'true',
    }
    result = self._request(request)

    counts = {}
    for row in result:
      counts[ row['stat'] ] = row['datapoints'].values()[-1]

    # assert that collapse and the uniqueness function worked
    uniques = filter( lambda row: row['function']=='unique', result )
    assert_equals( 3, len(uniques) )
    assert_equals( 1, len(uniques[0]['datapoints']) )
    assert_equals( 1, len(uniques[1]['datapoints']) )
    assert_equals( 1, len(uniques[2]['datapoints']) )

    assert_not_equals( 0, counts['foo.bar.cat,foo.bar.dog'][0] )
    assert_equals( counts['foo.bar.cat,foo.bar.dog'][0],
       counts['foo.bar.cat'][0] + counts['foo.bar.dog'][0] )
    assert_equals( counts['unique(foo.bar.cat,foo.bar.dog)'], 240 )
    assert_equals( counts['unique(foo.bar.cat,foo.bar.dog)'],
       counts['unique(foo.bar.cat)'] )
    assert_equals( counts['unique(foo.bar.cat,foo.bar.dog)'],
       counts['unique(foo.bar.dog)'] )
