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
  import tempfile, atexit, shutil
  d = tempfile.mkdtemp(suffix='torus')
  STORAGE_DIR = d

  @atexit.register
  def cleanup():
    shutil.rmtree( d )

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

  # TODO: support legacy and new namespacing
  'statsd_counters' : {
    'type': 'count',
    'host' : 'sqlite:///%s/statsd_counters.db'%(STORAGE_DIR),
    'match' : '^stats_counts\.',
    'intervals' : INTERVALS,
  },

  'statsd_timers' : {
    'type': 'histogram',
    'host' : 'sqlite:///%s/statsd_timers.db'%(STORAGE_DIR),
    'match' : '^stats\.timers',
    'intervals' : INTERVALS,
  },

  'statsd_gauges' : {
    'type': 'gauge',
    'host' : 'sqlite:///%s/statsd_guages.db'%(STORAGE_DIR),
    'match' : '^stats\.gauges',
    'intervals' : INTERVALS,
  }

  # TODO: As of torus 0.6.0 with kairos 0.8.1, sets in SQL are not implemented.
  #'statsd_sets' : {
    #'type': 'set',
    #'host' : 'sqlite:///%s/statsd_sets.db'%(STORAGE_DIR),
    #'match' : '^stats\.sets',
    #'intervals' : INTERVALS,
  #}
}
