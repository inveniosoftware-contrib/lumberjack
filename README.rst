
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

Documentation can be built using Sphinx.

Testing
=======

To run the test suite, simply run ::

    python run_tests.py
