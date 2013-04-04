=====
Torus
=====

:Version: 0.1.4
:Download: http://pypi.python.org/pypi/torus
:Source: https://github.com/agoragames/torus
:Keywords: python, redis, time, rrd, gevent, carbon, graphite, whisper, statsd, kairos

A service implementing the Carbon protocol to store time series data using
`kairos <https://github.com/agoragames/kairos>`_ and an HTTP server to query 
and analyze the data.

Motivation
==========

Kairos, an RRD-inspired timeseries library, provides an improved storage
engine and many more features than most other systems backing statsd. Compared
to traditional disk stores such as RRD and Whisper, Torus adds:

* simple runtime for ease in development and deployment
* abstraction on top of kairos for histograms
* compact storage for sparse data points
* scaling with per-schema hosting and sharding
* non-buffering semantics for aggregate processing
* consistent hashing of timestamps for ease in interleaving and interpolation
* programmatic interface to data processing

Carbon Server
=============

The ``karbon`` application runs the `Carbon <http://graphite.wikidot.com>`_-compatible
stat collection application. It is a drop-in replacement for the Carbon backend of
`statsd <https://github.com/etsy/statsd>`_. It takes the following arguments: ::

    usage: karbon [-h] [--tcp TCP] [--schema SCHEMA]

    Karbon, a Carbon-replacement data collection server

    optional arguments:
      -h, --help       show this help message and exit
      --tcp TCP        TCP binding, in the form of "host:port", ":port", or
                       "port". Defaults to "localhost:2003".
      --schema SCHEMA  Configuration file for schema and aggregates. Can be called
                       multiple times for multple configuration files.


The schema is documented below. To reload the schema(s), send a ``SIGHUP`` to
the ``karbon`` process.

Query Server
============

The `torus` application is a replacement for `Graphite <http://graphite.wikidot.com>`_.
It is not API compatible with Graphite though it does aim to be familiar to
Graphite users and provides a graphite-compatible JSON format for ease in integrating
with existing toolchains. ::

    usage: torus [-h] [--tcp TCP] [--schema SCHEMA]

    Torus, a web server for mining data out of kairos

    optional arguments:
      -h, --help       show this help message and exit
      --tcp TCP        TCP binding, in the form of "host:port", ":port", or
                       "port". Defaults to "localhost:8080".
      --schema SCHEMA  Configuration file for schema and aggregates. Can be called
                       multiple times for multple configuration files.


It should share the same schema as ``karbon``, and also reloads the schema(s)
it receives a ``SIGHUP``.  

``torus`` will respond to ``http://$tcp/$command?$parameters`` for the 
following commands, where ``$parameters`` is a standard URL encoded 
parameter list.

Commands
--------

/data
#####


Parameters
**********

Fetches data for one or more statistics and returns a list of objects for each statistic. Returns data from the first schema that matches a statistic.

* stat

    The name of the statistic to fetch. Each instance of the ``stat`` parameter
    is interpreted as a separate statistic. The statistic can either be in the
    form of ``$stat_name`` or ``$func($stat_name)``, where ``$func`` can be one of:

    * avg - the average of each datapoints in each time slice.
    * min - the minimum value of datapoints in each time slice. 
    * max - the maximum value of datapoints in each time slice.
    * sum - the sum of datapoints in each time slice.
    * count - the number of datapoints in each time slice.

* format

    One of ``[graphite, json]``, where ``graphite`` is a Graphite-compatible json
    format and ``json`` offers more nuanced representation of ``kairos``' data
    structures.

* condensed

    One of ``[true, false]``, if ``kairos`` resolutions are configured for a 
    schema, determines whether resolutions are flattened or returned as-is. 
    Forced to ``true`` for ``graphite`` format.


Returns
*******

A json structure. ::

    [{
      'function': 'avg',
      'interval': 'hour',
      'schema': 'calls',
      'stat': 'calls.system',
      'target': 'calls.system'
      'datapoints': [[0.0391, 1362153600], [0, 1362157200]],

     }, 
     ...
    ]


Schema
======

The schema for `torus` is an extension of the `kairos` schema.  It is defined
in a file reference on the command line, and includes the following: ::

    SCHEMAS = {

      # The name of the time series
      unique_counts : {

        # A dictionary similar to kairos with a few additions

        # One of (series, histogram, count, gauge). Optional, defaults to "count".
        type: 'histogram'

        # The host on which the timeseries is stored. If no scheme defined,
        # defaults to redis. If this is not a string, assumed to be a 
        # connection instance and will be used natively (e.g. for Redis
        # unix domain sockets).
        host: 'localhost:6379/0'

        # Patterns for any matching stats to store in this schema. If this is
        # a string, matches just one pattern, else if it's a list of strings,
        # matches any of the patterns. The pattern(s) will be used as-is in the
        # python regex library with no flags.
        match: [ 'application.hits.*',  ]

        # Optional, is a prefix for all keys in this histogram. If supplied
        # and it doesn't end with ":", it will be automatically appended.
        # prefix: 'application'

        # Optional, allows one to replace the stat name and value with another.
        # Takes two arguments and must return a tuple of two items (statistic,
        # value). If the statistic is None, will skip writing the statistic.
        # The value will be a string on input, and on output must be acceptable
        # to any write_func defined.
        # transform: lambda s,v: (None,None) if 0>long_or_float(v)>3.14 else (s,v)

        # Optional, is a function applied to all values read back from the
        # database. Without it, values will be strings. Must accept a string
        # value and can return anything. Defaults to long_or_float, which
        # tries to cast to a long and failing that, cast to a float.
        # long_or_float is available for all schemas to use.
        read_func: float

        # Optional, is a function applied to all values when writing. Can be
        # used for histogram resolution, converting an object into an id, etc.
        # Must accept whatever can be inserted into a timeseries and return an
        # object which can be cast to a string.  Defaults to long_or_float,
        # which tries to cast to a long and failing that, cast to a float.
        write_func: lambda v: '%0.3f'%(v)

        # Required, a dictionary of interval configurations in the form of:
        intervals: {
          # interval name, used in redis keys and should conform to best practices
          # and not include ":" or "."
          minute: {

            # Required. The number of seconds that the interval will cover
            step: 60,

            # Optional. The maximum number of intervals to maintain. If supplied,
            # will use redis expiration to delete old intervals, else intervals
            # exist in perpetuity.
            steps: 240,

            # Optional. Defines the resolution of the data, i.e. the number of
            # seconds in which data is assumed to have occurred "at the same time".
            # So if you're tracking a month long time series, you may only need
            # resolution down to the day, or resolution=86400. Defaults to same
            # value as "step".
            resolution: 60,
            }
          }
        }
      },
      ...
    }

    # Similar to Carbon aggregator but without the time buffer. Matching stats
    # will be processed through any matching schemas.  Is a list of tuples to
    # support rolling up any number of dissimilar stats into a single one. At
    # this time key names must be in the character set [a-zA-Z0-9_-]
    AGGREGATES = [
      ('application.rollup', 'application.count.*'),
      ('application.result.<code>', 'application.http.status.<code>'),
    ]


Series Types
------------

TODO: discuss different series types and their features.

Hosts
-----

Intervals
---------

Aggregates
----------


Installation
============

Torus is available on `pypi <http://pypi.python.org/pypi/torus>`_ and can be installed using     ``pip`` ::

  pip install torus


If installing from source:

* with development requirements (e.g. testing frameworks) ::

    pip install -r development.pip

* without development requirements ::

    pip install -r requirements.pip

Note that torus does not by default require 
`hiredis <http://pypi.python.org/pypi/hiredis>`_ though it is
strongly recommended.

Tests
=====

Use `nose <https://github.com/nose-devs/nose/>`_ to run the test suite. ::

  $ nosetests

Future
======

* Expanded schema matching in torus' ``/data`` command
* Date range and other parameters in torus' ``/data`` command
* Investigate faster regular expression engines. `pyre2 <https://github.com/facebook/pyre2>`_ is currently in the running.
* Support for mongo when supported in kairos
* UNIX domain sockets for redis (without an instance in the schema)
* Expand supported stat naming (unicode, symbols, etc)
* A ``relay`` host type for forwarding karbon data to another Carbon-compatible host
* Schema migration tools
