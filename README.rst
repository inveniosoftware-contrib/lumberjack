
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

    sphinx-build -qnNW docs docs/_build/html

Testing
=======

To run the test suite, you should have an Elasticsearch node available at
http://localhost:9199.  (My setup is that I forward this port over SSH to the
actual node I want to connect to; that way I can firewall the nodes and also
easily switch between them.)

To run the tests themselves, you should run::

    ./run_tests.sh
