'''
An example configuration for quick integration with statsd. Uses SQLite for
data storage.

Assumes the following statsd configuration:

  "deleteIdleStats": true,
  "deleteGauges": true,
  "deleteTimers": true,
  "deleteSets": true,
  "deleteCounters": true,
  "graphite": {
    "legacyNamespace": true,
    "globalPrefix": "stats",
    "prefixCounter": "counters",
    "prefixTimer": "timers",
    "prefixGauge": "gauges",
    "prefixSet": "sets"
  }

'''

# Change this for your own installation. Check on globals in case this is a
# temp dir and we reload the configuration
STORAGE_DIR = globals().get('STORAGE_DIR',None)

if not STORAGE_DIR:
  import tempfile, os
  d = "%s%storus.%s"%(tempfile.gettempdir(),os.sep,os.getlogin())
  try: os.makedirs( d )
  except OSError: pass
  STORAGE_DIR = d

def timer_hash(f):
  '''
  Histogram hashing function for timers
  '''
  # anything less than 0 is an error
  f = float(f)
  if f < 0:
    f = 0
  # millisecond resolution below a second
  elif f < 1:
    f = '%0.3f'%(f)
  # hundredth resolution below 5 seconds
  elif f < 5:
    f = '%0.2f'%(f)
  else:
    f = '%0.1f'%(f)
  return f

# Standard intervals for all schemas
INTERVALS = {
  # 2 days of hourly data at 15 minute resolution
  'hourly': {
    'step' : '1h',
    'steps' : 48,
    'resolution' : 60*15,
  },

  # 2 weeks of daily data at hourly resolution
  'daily' : {
    'step' : 'daily',
    'steps' : 48,
    'resolution' : '1h',
  },

  # lifetime of monthly data at daily resolution
  'monthly' : {
    'step' : 'monthly',
    'resolution' : '1d'
  }
}

SCHEMAS = {
  
  # Track the meta data about statsd operations
  'statsd_metadata' : {
    'type': 'count',
    'host' : 'sqlite:///%s/statsd_metadata.db'%(STORAGE_DIR),
    'host_settings' : {
      'isolation_level' : 'READ UNCOMMITTED'
    },
    'match' : [
      '^statsd\.',
      '^stats_counts\.statsd',
      '^stats\.gauges\.statsd',
      '^stats\.timers\.statsd'
    ],
    'intervals' : INTERVALS,
  },

  # Track data that is not statsd metadata
  # TODO: support legacy and new namespacing
  'stats_counters' : {
    'type': 'count',
    'host' : 'sqlite:///%s/counters.db'%(STORAGE_DIR),
    'host_settings' : {
      'isolation_level' : 'READ UNCOMMITTED'
    },
    'match' : '^stats_counts\.(?!statsd\.)',
    'intervals' : INTERVALS,
  },

  'stats_timers' : {
    'type': 'histogram',
    'host' : 'sqlite:///%s/timers.db'%(STORAGE_DIR),
    'host_settings' : {
      'isolation_level' : 'READ UNCOMMITTED'
    },
    'match' : '^stats\.timers\.(?!statsd\.)',
    'intervals' : INTERVALS,
    'write_func' : timer_hash,
    'read_func' : float,
  },

  'stats_gauges' : {
    'type': 'gauge',
    'host' : 'sqlite:///%s/gauges.db'%(STORAGE_DIR),
    'host_settings' : {
      'isolation_level' : 'READ UNCOMMITTED'
    },
    'match' : '^stats\.gauges\.(?!statsd\.)',
    'intervals' : INTERVALS,
  }

  # TODO: As of torus 0.6.0 with kairos 0.8.1, sets in SQL are not implemented.
  #'stats_sets' : {
    #'type': 'set',
    #'host' : 'sqlite:///%s/sets.db'%(STORAGE_DIR),
    #'match' : '^stats\.sets\.(?!statsd\.)',
    #'intervals' : INTERVALS,
  #}
}
