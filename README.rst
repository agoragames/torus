=====
Torus
=====

:Version: 0.7.1
:Download: http://pypi.python.org/pypi/torus
:Source: https://github.com/agoragames/torus
:Keywords: python, redis, time, rrd, gevent, carbon, graphite, whisper, statsd, kairos

A suite of tools designed to replace `Graphite`__ and expand on its capabilities. 
Uses `kairos <https://github.com/agoragames/kairos>`_ to support storing and 
reading data from many different types of data stores, and focuses on providing
programmatic tools for storing, retrieving and processing of streaming 
timeseries data.

__ http://graphite.readthedocs.org

.. contents::
       :local:

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

StatsD Quick Start
==================

A configuration file that tracks hourly, daily and monthly data in SQLite is
available in ``examples/statsd.py``. The default will create a temp directory
for the current user to store the databases (e.g. ``/tmp/torus.user`` on Unix).
Change ``STORAGE_DIR`` at the top of the file to set a permanent location.

If you have installed torus in a virtual env, you can use ``foreman`` to start
both ``karbon`` and ``torus``. If you're running torus out of the repository,
then you can use ``foreman start -f Procfile.dev``.

The example configuration includes support for performance testing (see below).

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

All torus applications load one or more configurations, where a configuration
is a python module that is loaded into the application. Torus looks for the
constants documented below, but as the configuration is a full python module,
extensions, plugins and additional runtime configuration can be included. For
example, one can connect torus' use of the standard python 
`logger <http://docs.python.org/2.7/library/logging.html#module-logging>`_
to syslog, logstash or one of many error reporting tools, such as Sentry.
For ``torus``, log messages prioritize the header ``X-Forwarded-For`` and 
then use the remote IP address if that's not available. For this reason and 
general security, you should always use a proxy server in front of ``torus``.

The configuration for ``torus`` includes a definition for schemas, aggregates,
custom functions that can be used in queries, and debugging settings. The 
schema for ``torus`` is an extension of the ``kairos`` schema; each of the 
key-value pairs in a schema definition will be passed to the timeseries
`constructor <https://github.com/agoragames/kairos#constructor>`_.
The configuration files can include 1 or more of the following.

on_load
-------

If this is a callable, will be called the first time the configuration is 
loaded. Useful for one-time configuration such as Sentry logging handlers.

on_reload
---------

If this is a callable, will be called when the configuration module is
reloaded.

SCHEMAS
-------

A dictionary of unique names to the configuration for capturing and storing 
the statistics which match the regular expressions. A schema definition
supports the following fields, many of which are passed directly to
`kairos <https://github.com/agoragames/kairos>`_.

* type

    Required, defines the type of the timeseries. One of 
    ``[series, histogram, count, set, gauge]``, depending on what the backend
    supports.

* host

    Required, the URL connection string or an instance of a supported
    connection type. See 
    `Storage Engines`__ 

__ https://github.com/agoragames/kairos#storage-engines

* client_config

    Optional, is a dictionary of parameters to use in the connection 
    constructor associated with the ``host`` URL. See `Storage Engines`__

__ https://github.com/agoragames/kairos#storage-engines

* match

    A string, or a list of strings, which are regular expressions that define
    the stat names which should be stored and queried in this schema. In the
    case where a ``transform`` is defined, it is likely the one or more 
    expressions will define the input stats, and another expression will define
    the stat which can be queried. See GitHub 
    `issue <https://github.com/agoragames/torus/issues/1>`_.

* rolling

    Optional, defines how many intervals before (negative) or after (positive) 
    that a copy of data should be written to whenever data is inserted. The
    extra storage size offsets much faster calculation of aggregates over
    pre-determined date range. For example, when storing daily values, a value
    of ``-30`` will store a value as if it occurred any time in the last 30 days.

* prefix

    Optional, is used to scope data in redis data stores. If supplied and it
    doesn't end with ":", it will be automatically appended.

* transform
        
    Optional, allows one to replace the stat name and value with another.
    Takes two arguments and must return a tuple of two items (statistic,
    value). If the statistic is None, will skip writing the statistic.
    The value will be a string on input, and on output must be acceptable
    to any write_func defined.
    Example: ``transform: lambda s,v: (None,None) if 0>long_or_float(v)>3.14 else (s,v)``

* read_func

    Optional, is a function applied to all values read back from the
    database. Without it, values will be strings. Must accept a string
    value and can return anything. Defaults to ``long_or_float``, which
    tries to cast to a long and failing that, cast to a float.
    ``long_or_float`` is available for all schemas to use.

* write_func

    Optional, is a function applied to all values when writing. Can be
    used for histogram resolution, converting an object into an id, etc.
    Must accept whatever can be inserted into a timeseries and return an
    object which can be cast to a string.  Defaults to ``long_or_float``,
    which tries to cast to a long and failing that, cast to a float.
    Example: ``write_func: lambda v: '%0.3f'%(v)``

* intervals

    Required, defines the `intervals <https://github.com/agoragames/kairos#constructor>`_
    in which data should be stored.

* generator

    Optional, defines a function which can be used to generate load tests. Must
    return a tuple in the form ``(stat_name, value)``.
    Example: ``lambda: ('application.hits.%d'%(random.choice([200,404,500])), 1)``

Example: ::

    SCHEMAS = {

      'response_times' : {
        'type': 'histogram'
        'host': 'redis://localhost:6379/0'
        'match': [ 'application.*.response_time', 'application.response_time' ]
        'read_func': float
        'write_func': lambda v: '%0.3f'%(v)

        'intervals': {
          'minute': {
            'step': 60,
            'steps': 240,
           },
          'daily' : {
            'step': 'daily',
            'steps': 30
          }
        },
      }
    }


AGGREGATES
----------

Similar to Carbon aggregator but without the time buffer. Matching stats
will be processed through any matching schemas.  Is a list of tuples to
support rolling up any number of dissimilar stats into a single one. At
this time key names must be in the character set ``[a-zA-Z0-9_-]``. Each aggregate
is defined as a tuple in the form of ``(rollup_stat, source_stat)``. Captures
can be defined in the form of ``<capture>`` and used in each rollup.

Example: ::
    
    AGGREGATES = [
      ('application.response_time', 'application.*.response_time'),
      ('application.<status_code>', 'application.*.status.<status_code>'),
    ]


TRANSFORMS
----------

A named mapping of functions which can be used in queries. 

Example: ::

    TRANSFORMS = {
      # Returns the number of elements
      'size' : lambda row: len(row)
    }

MACROS
------

A named map of configuration options so that "foo(stat)" will result in
a fixed set of options passed to kairos. This is especially useful for
using the customized read feature of kairos. This example assumes a 
histogram stored in redis. A more complicated macro might use server-side
scripting. All custom read functions exposed in kairos can be defined here.
All fields of the query string, other than 'stat', can be set in the
macro definition and will override those query parameters if they're
provided. To use a transform in a macro, set the 'transform' field to
either a string or a callable. Macros can make use of transforms defined
in ``TRANSFORMS``.

Example: ::

    MACROS = {
      'unique' : {
        'fetch' : lambda handle,key: handle.hlen(key)
        'condense' : lambda data: sum(data.values()),
        'process_row' : lambda data: data,
        'join_rows' : lambda rows: sum(rows),
      }
    }

DEBUG
-----

A boolean or integer to define the amount of log output. 

* 0 or ``False``

  Only errors are logged.

* 1 or ``True``

  Basic information is logged, should not generate substantial output.

* 2

  Significant information is logged, particularly from the ``karbon`` process.
    

Debugging
=========

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

Performance Testing
===================

To test your schema for performance and regressions, torus includes 
``schema_test``. The tool looks for ``generator`` definitions in schemas,
and continually calls them to emit data points that are processed through
all the schemas and aggregates. Prints out some basic statistics. ::

    usage: schema_test [-h] [--config CONFIG] [--clear] [--duration DURATION]

    Tool for performance testing of schemas

    optional arguments:
      -h, --help           show this help message and exit
      --config CONFIG      Configuration file to load. Can be called multiple
                           times for multiple configuration files.
      --clear              If true, clear all data before running the test.
                           Defaults to false.
      --duration DURATION  Duration of the test. Defaults to 60 seconds.

Migration
=========

There will be times that you need to migrate data from one schema to another. 
Torus ships with ``migrate`` to facilitate that. ::

    usage: migrate [-h] --config CONFIG --source SOURCE --destination DESTINATION
                   --interval INTERVAL [--start START] [--end END]
                   [--concurrency CONCURRENCY] [--stat STAT] [--match MATCH]
                   [--dry-run] [--verbose]

    A tool to migrate data from one schema to another

    optional arguments:
      -h, --help            show this help message and exit
      --config CONFIG       Configuration file to load. Can be called multiple
                            times for multiple configuration files.
      --source SOURCE       The name of the source schema [required]
      --destination DESTINATION
                            The name of the destination schema [required]
      --interval INTERVAL   The name of the interval from which to read data
                            [required]
      --start START         Only copy stats occurring on or after this date. Same
                            format as web parameter. [optional]
      --end END             Only copy stats occurring on or before this date. Same
                            format as web parameter. [optional]
      --concurrency CONCURRENCY
                            Set the concurrency on the schema target writing.
                            Defaults to 10.
      --stat STAT           The name of the stat to copy. Can be called multiple
                            times for a list of stats. If not provided, all stats
                            will be copied. [optional]
      --match MATCH         Pattern match to migrate a subset of the data.
                            [optional]
      --dry-run             Print out status but do not save results in the
                            destination schema. [optional]
      --verbose             Print out even more information during the migration
                            [optional]


Installation
============

Torus is available on `pypi <http://pypi.python.org/pypi/torus>`_ and can be installed using     ``pip`` ::

  pip install torus


If installing from source:

* with development requirements (e.g. testing frameworks) ::

    pip install -r development.pip

* without development requirements ::

    pip install -r requirements.pip

SQL
---

Torus installs SQLAlchemy to support SQL. To use your dialect of choice, you
will likely have to install additional packages.  Refer to the
`documentation <http://docs.sqlalchemy.org/en/latest/dialects/index.html>`_ 
for more details.

Tests
=====

Use `nose <https://github.com/nose-devs/nose/>`_ to run the test suite. ::

  $ nosetests

Roadmap
=======

* Record metrics on karbon and torus usage
* Add "dead letter" support for tracking stats that don't match any schema
* Add stat delete endpoint to ``torus``
* Command line tools for querying data and optionally plotting using `bashplotlib <http://www.yaksis.com/posts/bashplotlib.html>`_
* Add tools for generating tasseo configurations (https://github.com/obfuscurity/tasseo)
* Add ability to set transaction-commit intervals for Redis and SQLite backends
* Investigate faster regular expression engines. `pyre2 <https://github.com/facebook/pyre2>`_ is currently in the running.
* Expand supported stat naming (unicode, symbols, etc)
* A ``relay`` host type for forwarding karbon data to another Carbon-compatible host
* Schema migration tools
* log and stdout for ``torus`` and ``karbon``
