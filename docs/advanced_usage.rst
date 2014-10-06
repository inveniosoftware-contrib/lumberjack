Advanced Usage
==============

This details some more advanced usages of Lumberjack.  You don't need to read
this just to get up and running, but it might be handy when tweaking your
cluster later on.

Custom Elasticsearch objects
----------------------------

You can also create an ``elasticsearch.Elasticsearch`` object yourself and pass
it in.  This is useful if you want to do some customisation of the
Elasticsearch connection, for example to connect using Thrift::

    from elasticsearch import Elasticsearch
    from lumberjack import Lumberjack

    es = Elasticsearch(connection_class=ThriftConnection)
    lj = Lumberjack(elasticsearch=es)

Index suffixes
--------------

Indices created by Lumberjack are named using a constant prefix and a
time-based suffix, so might be named generic-logging-2014.10 for log entries
from an unconfigured Lumberjack instance in October 2014.  (For details about
the prefix, see the Configuration section of the documentation.)

When calling the ``lumberjack.Lumberjack.get_handler()`` method, you can
specify a 'suffix format'.  When the handler receives a new log event, it
determines the suffix by formatting the time of the event with this string
using ``time.strftime()``.  In this way you can alter the time-period your
indices span::

    from lumberjack import Lumberjack
    import logging

    lj = Lumberjack(hosts=[...])
    
    day_handler = lj.get_handler(suffix_format='%Y.%m.%d')

    my_logger = logging.getLogger(__name__)
    my_logger.setLevel(logging.INFO)
    my_logger.addHandler(day_handler)

In this example a log event that happened on 2014-10-07 would be stored in a
different index to one that happened on 2014-10-08.  This is useful if you end
up with lots of indices that are too small, or too few indices that are too
big.  (Both of these cases are inefficient.)

In fact you can even customise your handlers based on the frequency of various
different events that Lumberjack is attached to::

    from lumberjack import Lumberjack
    import logging

    lj = Lumberjack(hosts=[...])

    day_handler = lj.get_handler(suffix_format='%Y.%m.%d')
    month_handler = lj.get_handler(suffix_format='%Y.%m') # The default

    high_volume_logger = logging.getLogger('pageviews')
    high_volume_logger.setLevel(logging.INFO)
    high_volume_logger.addHandler(day_handler)

    low_volume_logger = logging.getLogger('logins.by.admin')
    low_volume_logger.setLevel(logging.INFO)
    low_volume_logger.addHandler(month_handler)

