'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

from chai import Chai

from torus import aggregates
from torus.aggregates import *

class AggregatesTest(Chai):

  def test_features(self):
    a = Aggregates( [('foo', 'foo.bar'), ('fum', 'foo.*'), ('fi', 'fii.*')] )
    assert_equals( ['foo', 'fum'], a.match('foo.bar') )


class AggregateTest(Chai):

  def test_features(self):
    a = Aggregate( 'foo.bar', 'foo' )
    assert_equals( 'foo', a.match('foo.bar') )
    assert_equals( None, a.match('foo.bur') )
    assert_equals( None, a.match('foo.bar.bow') )
    
    a = Aggregate( 'foo.bar.*', 'foo' )
    assert_equals( None, a.match('foo.bar') )
    assert_equals( None, a.match('foo.bur') )
    assert_equals( 'foo', a.match('foo.bar.bow') )
    
    a = Aggregate( 'foo.bar.<type>', 'foo.<type>' )
    assert_equals( None, a.match('foo.bar') )
    assert_equals( None, a.match('foo.bur') )
    assert_equals( 'foo.bow', a.match('foo.bar.bow') )

    a = Aggregate( 'foo.*.<env>.tee.<code>', 'foo.<env>.tee.<code>' )
    assert_equals( 'foo.production.tee.404', a.match('foo.bar.production.tee.404') )
