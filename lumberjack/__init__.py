# -*- coding: utf-8 -*-
##
## This file is part of Lumberjack.
## Copyright (C) 2014 CERN.
##
## Lumberjack is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Lumberjack is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Lumberjack; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

u"""Python Elasticsearch Logging Handler"""

from __future__ import absolute_import

from elasticsearch import Elasticsearch
from .handler import ElasticsearchHandler
from .context import ElasticsearchContext

import logging

LOG = logging.getLogger(__name__)

class Lumberjack(object):
    ## TODO describe parameters for __init__
    u"""Main entry point to the module.

    Initialises the Elasticsearch connection pool and the prefix for
    the index names.

    """
    context = None
    index_prefix = None

    ## TODO: **kwargs doesn't work here
    def __init__(self, index_prefix='generic-logging-',
                 hosts=None, elasticsearch=None, context=None, **kwargs):
        if context is not None:
            LOG.debug('Using provided ES context.')
            self.context = context

        elif elasticsearch is not None:
            LOG.debug('Using provided ES instance.')
            self.context = ElasticsearchContext(
                elasticsearch, index_prefix=index_prefix, **kwargs)

        elif hosts is None:
            LOG.warn('No Elasticsearch config specified. ' +
                     'This is very probably a bad idea.')

        else:
            LOG.debug('Using provided hosts.')
            self.context = ElasticsearchContext(
                Elasticsearch(hosts=hosts),
                index_prefix=index_prefix, **kwargs)

        self.index_prefix = index_prefix

    def get_handler(self, suffix_format='%Y.%m'):
        u"""Get a new logging handler."""
        handler = ElasticsearchHandler(context=self.context,
                                       suffix_format=suffix_format)
        return handler

    ## TODO: doesn't work with async
    def register_schema(self, logger, schema):
        u"""Wrapper for self.context.register_schema."""
        self.context.register_schema(logger, schema)

def reset_everything(loggername='test',
                     hosts=[{'host': 'localhost', 'port': 9199}],
                     index_prefix='lumberjack-test-'):
    u"""Useful function to reset a debugging environment."""
    # pylint: disable=dangerous-default-value

    import sys
    from . import context

    es_logger = logging.getLogger('elasticsearch')
    for logger in [LOG, es_logger]:
        logger.handlers = []
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler(stream=sys.stderr))

    logger = logging.getLogger(loggername)
    logger.handlers = []
    base_mapping = context.DEFAULT_BASE_MAPPING
    base_mapping['_source'] = {'enabled': True}
    esl = Lumberjack(hosts=hosts, index_prefix=index_prefix,
                default_base_mapping=base_mapping)

    esl.context.elasticsearch.indices.delete(index=index_prefix + '*')

    handler = esl.get_handler()
    logger.addHandler(handler)

    return logger
