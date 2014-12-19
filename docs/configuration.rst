Configuration
=============

The default config is included at the end of this file for reference.

Lumberjack is configured using a dict of config options passed to the
Lumberjack object on instantiation.  A safely-modifiable copy of the default
config dict can be obtained by calling ``lumberjack.get_default_config()``::

    from lumberjack import Lumberjack, get_default_config
    lj = Lumberjack(hosts=[...], config=get_default_config())

With the exception of ``index_prefix``, these defaults should be sensible for
production.  You should change ``index_prefix`` to something different for each
of your applications.

The config returned is a deep copy of the default one, so it can be modified as
you like without breaking subsequent calls to
``lumberjack.get_default_config()``::

    from lumberjack import Lumberjack, get_default_config

    my_config = get_default_config()
    my_config['index_prefix'] = 'a-special-prefix-'

    lj = Lumberjack(hosts=[...], config=my_config)

The index prefix
----------------

This configures the prefix for the created elasticsearch indices.  Indices are
created with a constant prefix and a time-based suffix, so might be named
`generic-logging-2014.10` for log entries from an unconfigured Lumberjack
instance in October 2014.

The default mapping
-------------------

This contains the basis for generating mappings in Elasticsearch.  Its values
are overridden by the values in the `schema` dict passed to
``lumberjack.Lumberjack.register_schema()``.  It contains keys like
``_source``, ``_all``, and ``_ttl``.

Note that special processing happens to the ``properties`` key: instead of
being overwritten by the schema's ``properties`` key, the fields provided to
Elasticsearch are the union of the two, with the schema's fields taking
precedence.

Default properties for types
----------------------------

When a field is given a particular type in the schema, Lumberjack automatically
adds some properties to the field.  For example, for ``string`` type fields,
Lumberjack disables analysis on them.  (The reason for this is that while
analysis is a powerful Elasticsearch feature when dealing with natural language
documents, for log data it makes little sense.)

The interval
------------

This is the (maximum) amount of time to wait between flushes of the log event
queue to Elasticsearch.  It is an integer or floating-point value in seconds.

The maximum queue length
------------------------

This is the maximum length the queue can grow to before a flush is triggered
automatically.

The fallback log file
---------------------

If Lumberjack experiences an error when indexing to Elasticsearch, it will fall
back to dumping JSON to the file given in this variable.

The default config
------------------

.. include:: ../lumberjack/config.py
    :literal:
