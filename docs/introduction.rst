Introduction
============

To use Lumberjack, you should have an Elasticsearch cluster already running.

You should instantiate the main Lumberjack class once in your application,
specifying a list of Elasticsearch nodes to connect to::

    from lumberjack import Lumberjack
    lj = Lumberjack(hosts=[{'host': 'localhost', 'port': 9200}])

for an Elasticsearch node running locally on port 9200.

Once you have your Lumberjack object, you can then create log handlers to
attach to loggers from ``logging``::

    from logging import getLogger, INFO

    a_logger = getLogger(__name__)
    a_logger.setLevel(INFO)

    handler = lj.get_handler()

    a_logger.addHandler(handler)

Then, you can log events to ``a_logger`` (or any of its children in the
logger hierarchy) and they will be stored in Elasticsearch::

    a_logger.error('Oh no!  Something bad happened...')

Isn't that easy!

Note: you might need to wait for the periodic flush of the log queue before the
entry actually appears in Elasticsearch.  By default this is every 30 seconds.
