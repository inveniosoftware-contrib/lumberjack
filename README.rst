
.. image:: https://travis-ci.org/jmacmahon/lumberjack.png?branch=master
    :target: https://travis-ci.org/jmacmahon/lumberjack/

============
 Lumberjack
============

About
=====

Lumberjack is a library which connects the Python logging framework to an
Elasticsearch backend.  It provides a main class which sets up an Elasticsearch
connection and exposes a method to spawn log handlers for it.

Mappings in Elasticsearch can be configured as defaults and on a per-logger basis.

Documentation
=============

Documentation is available at <http://lumberjack.readthedocs.org/>, but can
also be built using Sphinx::

    pip install -e .[docs]
    sphinx-build -qnNW docs docs/_build/html

Testing
=======

By default, the test suite works by monkey-patching bits of the
elasticsearch-py module and asserting that they were called with the right
arguments.  This is OK for automated testing like Travis, but isn't entirely
"real-world".

To run the test suite on an actual Elasticsearch cluster, you should edit the
constants at the top of tests/common.py in the obvious way.  The main thing you
should do is set MOCK = False.

By default the tests expect an Elasticsearch node at <http://localhost:9199>.
My setup is that I forward this port over SSH to the actual node I want to
connect to; that way I can firewall the nodes and also easily switch between
them.

To run the tests themselves, you should run::

    ./run_tests.sh
