'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

import time
import parsedatetime as pdt
cal = pdt.Calendar()

def parse_time(t):
  '''
  Parse a time value from a string, return a float in Unix epoch format.
  If no time can be parsed from the string, return None.
  '''
  try:
    return float(t)
  except ValueError:
    match = cal.parse(t)
    if match and match[1]:
      return time.mktime( match[0] )
  return None
