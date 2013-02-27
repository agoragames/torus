=====
Torus
=====

A service implementing the Carbon protocol to store time series data using
[kairos](https://github.com/agoragames/kairos) and an HTTP server to query 
and analyze the data.

Motivation
==========

Kairos, an RRD-inspired Redis-backed library, provides an improved storage
engine and many more features than most other systems backing statsd. Compared
to traditional disk stores such as RRD and Whisper, Torus adds:

* abstraction on top of kairos for histograms, input and output processing
* compact storage for sparse data points
* scaling with per-schema hosting and sharding
* non-buffering semantics for aggregate processing
* consistent hashing of timestamps for ease in interleaving and interpolation

Carbon Server
=============

The `karbon` application runs the [Carbon](http://graphite.wikidot.com)-compatible
stat collection application. It takes the following arguments:

    TODO: paste `karbon --help`

The schema is documented below.

TODO: say something more about the server itself, integrating with statsd, etc.

Query Server
============

The `torus` application is a replacement for [Graphite](http://graphite.wikidot.com).
It is not API compatible with Graphite though it does aim to be familiar to
Graphite users and provides a graphite-compatible JSON format for ease in integrating
with existing toolchains.

    TODO: paste `torus --help`

It should share the same schema as `karbon`.

TODO: document the URI API, integration features, etc.

Schema
======

The schema for `torus` is an extension of the `kairos` schema.  It is defined
in a file reference on the command line, and includes the following:

    TIMESERIES = {

      # The name of the time series
      unique_counts : {

        # A dictionary similar to kairos with a few additions

        # One of (series, histogram, count). Optional, defaults to "histogram".
        type: 'histogram'

        # The host on which the timeseries is stored.
        host: 'localhost:6379/0'

        # Patterns for any matching stats to store in this schema. If this is
        # a string, matches just one pattern, else if it's a list of strings,
        # matches any of the patterns. The pattern will be escaped.
        match: [ 'application.hits.*',  ]

        # Optional, is a prefix for all keys in this histogram. If supplied
        # and it doesn't end with ":", it will be automatically appended.
        # prefix: 'application'

        # Optional, is a function applied to all values read back from the
        # database. Without it, values will be strings. Must accept a string
        # value and can return anything.
        read_func: float

        # Optional, is a function applied to all values when writing. Can be
        # used for histogram resolution, converting an object into an id, etc.
        # Must accept whatever can be inserted into a timeseries and return an
        # object which can be cast to a string.
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
    # support rolling up any number of dissimilar stats into a single one.
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
