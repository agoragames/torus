'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''
from collections import OrderedDict

from chai import Chai

from torus.web import extract

class ExtractTest(Chai):

  def test_extract(self):
    dct = OrderedDict((
      (1234, {'min':3, 'max':5}),
      (5678, {'min':5, 'max':7})
    ))
    val = extract(dct, 'min')

    assert_equals( OrderedDict( ((1234,3), (5678,5)) ), val )

    dct = OrderedDict((
      (1234, OrderedDict((
        (12340, {'min':3, 'max':5}),
        (12341, {'min':4, 'max':6}),
      )) ),
      (5678, OrderedDict((
        (56780, {'min':5, 'max':7}),
        (56781, {'min':6, 'max':8}),
      )) ),
    ))
    val = extract(dct, 'min')

    assert_equals( OrderedDict(( (1234,OrderedDict(((12340,3),(12341,4)))), (5678,OrderedDict(((56780,5),(56781,6)))) )), val )
