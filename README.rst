=====
Torus
=====

:Version: 0.5.0
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

    usage: karbon [-h] [--tcp TCP] [--config CONFIG]

    Karbon, a Carbon-replacement data collection server

    optional arguments:
      -h, --help       show this help message and exit
      --tcp TCP        TCP binding, in the form of "host:port", ":port", or
                       "port". Defaults to "localhost:2003".
      --config CONFIG  Configuration file to load. Can be called multiple times
                       for multiple configuration files.


The configuration is documented below. To reload the configuration(s), send a 
``SIGHUP`` to the ``karbon`` process.

Query Server
============

The `torus` application is a replacement for `Graphite <http://graphite.wikidot.com>`_.
It is not API compatible with Graphite though it does aim to be familiar to
Graphite users and provides a graphite-compatible JSON format for ease in integrating
with existing toolchains. ::

    usage: torus [-h] [--tcp TCP] [--config CONFIG]

    Torus, a web server for mining data out of kairos

    optional arguments:
      -h, --help       show this help message and exit
      --tcp TCP        TCP binding, in the form of "host:port", ":port", or
                       "port". Defaults to "localhost:8080".
      --config CONFIG  Configuration file to load. Can be called multiple times
                       for multiple configuration files.


For most use cases it can share a configuration with ``karbon``. However, one 
could use ``Chef``, ``puppet`` or a similar tool to templatize the 
configuration, and replace strings such as the ``host`` definition, so as to 
target a specific set of resources at reading the data.

To reload the configuration(s), send a ``SIGHUP`` to the ``torus`` process.

``torus`` will respond to ``http://$tcp/$command?$parameters`` for the 
following commands, where ``$parameters`` is a standard URL encoded 
parameter list.

Commands
--------

/series
#######

DEPRECATED: formerly ``/data``


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

    Additionally, ``$func`` can be either a transform or a macro defined in the
    configuration. The ``$func`` can be anything that matches the 
    pattern ``[a-zA-Z0-9_]``.

* format

    One of ``[graphite, json]``, where ``graphite`` is a Graphite-compatible json
    format and ``json`` offers more nuanced representation of ``kairos``' data
    structures.

* condense

    One of ``[true, false]``, if ``kairos`` resolutions are configured for a 
    schema, determines whether resolutions are flattened or returned as-is. 
    Forced to ``true`` for ``graphite`` format.

* collapse

    One of ``[true, false]``, if ``true`` then all of the data for each time
    interval will be collapsed into a single value. This is useful for
    calculating aggregates across a range (e.g. "all hits in last 5 days"). 

* schema

    In cases where multiple schemas match a stat name, force a particular 
    schema to be used.

* interval

    The interval to choose, one of the intervals available in whatever schema
    matches ``stat``.  Must apply to all ``stat`` arguments.

* start

    An optional timestamp for the beginning of the return interval. Can be in
    the form of a unix timestamp, a ``strftime``-formatted string, or a 
    human-readable relative value such as "today", "5 days ago", "last week",
    etc.

* end

    An optional timestamp for the end of the return interval. Can accept the
    same values as ``start``. With no arguments, this is implicitely the time
    at which the query is made.

* steps

    Given either a ``start`` or ``end`` timestamp, this parameter defines the
    number of intervals (inclusive) after or before (respectively) to return. 
    So if ``start`` is "last week" and ``steps=7``, the result data will end 
    with yesterday's data. If no timestamps are given, this is the number of
    intervals before the current time (inclusive).


Returns
*******

A json structure. ::

    [{
      'function': 'avg',
      'interval': 'hour',
      'schema': 'calls',
      'stat': 'avg(calls.system)',
      'stat_name' : 'calls.system',
      'target': 'calls.system',
      'datapoints': [[0.0391, 1362153600], [0, 1362157200]],

     }, 
     ...
    ]

The ``stat`` field will be the full name of the corresponding parameter, 
including the function (if any).  The ``stat_name`` field will be just the
name of the statistic that was matched to the schema, and ``target`` will
be a copy of the same for clients which are expecting data in ``graphite``
format.


Configuration
=============

The configuration for ``torus`` includes a definition for schemas, aggregates,
custom functions that can be used in queries, and debugging settings. The 
schema for ``torus`` is an extension of the ``kairos`` schema. The 
configuration files can include 1 or more of the following: ::

    SCHEMAS = {

      # The name of the time series
      unique_counts : {

        # A dictionary similar to kairos with a few additions

        # One of (series, histogram, count, gauge). Optional, defaults to "count".
        type: 'histogram'

        # The database type, host and database identifier in which the 
        # timeseries is stored. If this is not a string, assumed to be a 
        # connection instance and will be used natively (e.g. for Redis
        # unix domain sockets). The full redis and mongodb URI schemes are
        # supported (requires redis 2.7.5).
        #
        # http://docs.mongodb.org/manual/reference/connection-string/
        #
        # host: 'redis://localhost'
        # host: 'redis://localhost/3'
        # host: 'mongodb://localhost'
        # host: 'mongodb://localhost:27018/timeseries'
        # host: 'mongodb://guest:host@localhost/authed_db'
        host: 'redis://localhost:6379/0'

        # Patterns for any matching stats to store in this schema. If this is
        # a string, matches just one pattern, else if it's a list of strings,
        # matches any of the patterns. The pattern(s) will be used as-is in the
        # python regex library with no flags.
        match: [ 'application.hits.*',  ]

        # Defines how many intervals before (negative) or after (positive) that
        # a copy of data should be written to whenever data is inserted. The
        # extra storage size offsets much faster calculation of aggregates over
        # pre-determined date range.
        #
        # Example: for a schema storing daily values, will store a value as if
        # it occurred any time in the last 30 days.
        # rolling: -30

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

            # Required. The number of seconds that the interval will cover,
            # or one of the Gregorian intervals "daily", "weekly", "monthly"
            # or "yearly"
            step: 60,

            # Optional. The maximum number of intervals to maintain. If supplied,
            # will use redis expiration to delete old intervals, else intervals
            # exist in perpetuity.
            steps: 240,

            # Optional. Defines the resolution of the data, i.e. the number of
            # seconds in which data is assumed to have occurred "at the same time".
            # So if you're tracking a month long time series, you may only need
            # resolution down to the day, or resolution=86400. Defaults to same
            # value as "step". Can also be one of the supported Gregorian intevals.
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

    # A named map of functions which can be used in requests to torus
    TRANSFORMS = {
      # Returns the number of elements
      'size' : lambda row: len(row)
    }

    # A named map of configuration options so that "foo(stat)" will result in
    # a fixed set of options passed to kairos. This is especially useful for
    # using the customized read feature of kairos. This example assumes a 
    # histogram stored in redis. A more complicated macro might use server-side
    # scripting. All custom read functions exposed in kairos can be defined here.
    # All fields of the query string, other than 'stat', can be set in the
    # macro definition and will override those query parameters if they're
    # provided. To use a transform in a macro, set the 'transform' field to
    # either a string or a callable. Macros can make use of transforms defined
    # in TRANSFORMS.
    MACROS = {
      'unique' : {
        'fetch' : lambda handle,key: handle.hlen(key)
        'condense' : lambda data: sum(data.values()),
        'process_row' : lambda data: data,
        'join_rows' : lambda rows: sum(rows),
      }
    }
    

Debugging
---------

Debugging a schema or set of schemas can pose a challenge. Torus ships with ``schema_debug``,
a tool for testing any number of input strings against any number of schemas. It will 
output which rules match the input string, which database that match will be stored in, any
aggregates that will be generated from the input rule, and then recursively any schemas and
aggregates that match each aggregate. ::

    usage: schema_debug [-h] [--config CONFIG] strings [strings ...]

    Debugging tool for schemas

    positional arguments:
      strings          One or more input strings to test against the scheams

    optional arguments:
      -h, --help       show this help message and exit
      --config CONFIG  Configuration file to load. Can be called multiple times
                       for multiple configuration files.

Torus also supports the ``DEBUG`` flag which can be defined in any of the
configuration files and which will cause ``karbon`` to print to stdout. If 
it is ``0``, or not defined, no output will be generated. If it is ``1``,
``karbon`` will log when it stores a raw value (``STOR``) or aggregate
(``AGRT``), and statistics on the quantity and duration of processing
(``DONE``). If ``DEBUG==2``, ``karbon`` will also log every line it 
recieves (``RECV``) and lines that it skips (``SKIP``).

To use the debugging flag, you can change the value in one of the configuration
files loaded by ``karbon``, and then signal the process to reload with the 
command ``kill -SIGHUP `pidof karbon```.


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

Roadmap
=======

* Record metrics on karbon and torus usage
* Add stat submission endpoint to ``torus``
* Add stat delete endpoint to ``torus``
* Add ability to set transaction-commit intervals for Redis and SQLite backends
* Investigate faster regular expression engines. `pyre2 <https://github.com/facebook/pyre2>`_ is currently in the running.
* Expand supported stat naming (unicode, symbols, etc)
* A ``relay`` host type for forwarding karbon data to another Carbon-compatible host
* Schema migration tools
* log and stdout for ``torus`` and ``karbon``
