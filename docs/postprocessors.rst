Post-processors
===============

Post-processors are arbitrary functions which are applied to log entries
directly before they go into Elasticsearch.  They can be specified easily in the
call to ``logging.Logger.log()`` and family::

    from logging import getLogger
    my_logger = getLogger(__name__)
    # Assume we set up Lumberjack and attach it somewhere in the heirarchy of
    # this logger.

    my_logger.info({'a': 'message'}, {'postprocessors': [some_postprocessor]})

In this example, the post-processor ``some_postprocessor`` will be applied to
the logged document immediately before sending to Elasticsearch.

A post-processor is simply a function which is passed the document, and should
return a modified version of it.  For example, a postprocessor might add the
hostname of the machine currently running the program::

    import socket
    def hostname(doc):
        doc['hostname'] = socket.gethostname()

    my_logger.info({'a': 'message'}, {'postprocessors': [hostname]})

On a system with hostname ``load-balancer-01``, this would result in the
following document being sent to Elasticsearch::

    {
        'a': 'message',
        '@timestamp': 1438353254000, # Timestamp added automatically
        'level': 20, # Log level (logging.INFO) added automatically
        'hostname': 'load-balancer-01'
    }

Included post-processors
------------------------

Lumberjack provides some postprocessors out-of-the-box for you to use, which you
can find in ``lumberjack.postprocessors``.

GeoIP
+++++

This post-processor will perform a GeoIP lookup on a field containing an IP
address, and include the results in the document::

    from lumberjack.postprocessors import geoip
    my_geoip = geoip(field='ip')

    my_logger.info({
        'a': 'message',
        'ip': '128.141.43.1'
    }, {'postprocessors': [my_geoip]})

This will result in the following document being sent to Elasticsearch::

    {
        'a': 'message',
        '@timestamp': 1438353254000, # Timestamp added automatically
        'level': 20, # Log level (logging.INFO) added automatically
        'ip': '128.141.43.1',
        'geoip': {
            'country_code': 'CH',
            'location': {'lat': 46.1956, 'lon': 6.1481}
        }
    }
