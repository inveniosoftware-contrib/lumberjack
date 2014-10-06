#!/bin/sh

pep257 lumberjack
sphinx-build -qnNW docs docs/_build/html
python setup.py test
