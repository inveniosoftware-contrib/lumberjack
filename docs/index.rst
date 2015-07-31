
.. image:: https://travis-ci.org/jmacmahon/lumberjack.png?branch=master
    :target: https://travis-ci.org/jmacmahon/lumberjack/

.. image:: https://coveralls.io/repos/jmacmahon/lumberjack/badge.png?branch=master
    :target: https://coveralls.io/r/jmacmahon/lumberjack?branch=master

============
 Lumberjack
============

Lumberjack is a library which connects the Python logging framework to an
Elasticsearch backend.

It has a number of useful features, including:

- Asynchronous logging by default

- Automatic time-rotating indices

- Elasticsearch mapping management

Installation
============

Lumberjack can be installed with:

.. code-block:: console

    $ python setup.py install

Quickstart
==========

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


.. toctree::
    :maxdepth: 2

    usage
    configuration
    advanced_usage
    postprocessors
    api
    backend
    developers
