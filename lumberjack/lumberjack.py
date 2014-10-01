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
from .schemas import SchemaManager
from .actions import ActionQueue

import logging

LOG = logging.getLogger(__name__)

class Lumberjack(object):
    ## TODO describe parameters for __init__
    u"""Main entry point to the module.

    Initialises the Elasticsearch connection pool and the prefix for
    the index names.

    """
    elasticsearch = None
    schema_manager = None
    action_queue = None

    index_prefix = None

    def __init__(self, index_prefix='generic-logging-',
                 hosts=None, elasticsearch=None, interval=30,
                 max_queue_length=None,):
        self.index_prefix = index_prefix

        if elasticsearch is not None:
            LOG.debug('Using provided ES instance.')
            self.elasticsearch = elasticsearch
        elif hosts is None:
            LOG.warn('No Elasticsearch config specified. ' +
                     'This is very probably a bad idea.')
        else:
            LOG.debug('Using provided hosts.')
            self.elasticsearch = Elasticsearch(hosts=hosts)

        ## TODO: read args from a config here.
        self.schema_manager = SchemaManager(self.elasticsearch, index_prefix)
        self.action_queue = ActionQueue(self.elasticsearch, index_prefix,
                                        interval=interval,
                                        max_queue_length=max_queue_length)

        self.action_queue.start()

    def trigger_flush(self):
        self.action_queue.trigger_flush()

    def get_handler(self, suffix_format='%Y.%m'):
        u"""Get a new logging handler."""
        handler = ElasticsearchHandler(action_queue=self.action_queue,
                                       suffix_format=suffix_format)
        return handler

    def register_schema(self, logger, schema):
        u"""Wrapper for self.schema_manager.register_schema."""
        self.schema_manager.register_schema(logger, schema)
