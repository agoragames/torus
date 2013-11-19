'''
Copyright (c) 2013, Agora Games, LLC All rights reserved.

https://github.com/agoragames/torus/blob/master/LICENSE.txt
'''

class HttpError(Exception):
  msg = "Internal Server Error"
  code = 500

class HttpNotFound(Exception):
  msg = "Not Found"
  code = 404
