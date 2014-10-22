# -*- coding: utf-8 -*-
#
# This file is part of Lumberjack.
# Copyright 2014 CERN.
#
# Lumberjack is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Lumberjack is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Lumberjack.  If not, see <http://www.gnu.org/licenses/>.

"""Python Elasticsearch Logging Handler."""

from __future__ import absolute_import

from elasticsearch import Elasticsearch
from .handler import ElasticsearchHandler
from .schemas import SchemaManager
from .actions import ActionQueue
from .config import get_default_config

import logging
from copy import deepcopy

LOG = logging.getLogger(__name__)


# TODO: debug mode -- synchronous, no queueing
class Lumberjack(object):

    """This is the initialisation point for using the lumberjack library.

    In the intended use-case, this class is instantiated once and creates
    handlers for use with Python's logging module.

    For each type of log you want to store, you should provide a schema.  If
    you don't, nothing bad will happen, but it makes your cluster rather
    space-inefficient by default.

    You should provide either a list of Elasticsearch hosts, or an
    already-instantiated ``Elasticsearch`` object from elasticsearch-py.

    :param hosts: A list of Elasticsearch nodes to connect to, in the form
        ``[{'host': '127.0.0.1', 'port': 9200}]``.  This is passed directly to
        elasticsearch.Elasticsearch.

    :param elasticsearch: As an alternative to hosts, an already-instantiated
        ``elasticsearch.Elasticsearch`` object, perhaps with custom transports
        etc.

    :param config: A configuration for Lumberjack.  See the Configuration
        section in the docs for details.

    """

    def __init__(self, hosts=None, elasticsearch=None, config=None):
        """Init method.  See class docstring."""
        # TODO: clean this up.  Error if both or neither are provided.
        if elasticsearch is not None:
            LOG.debug('Using provided ES instance.')
            self.elasticsearch = elasticsearch
        elif hosts is None:
            raise TypeError('You must provide either hosts or elasticsearch.')
        else:
            LOG.debug('Using provided hosts.')
            self.elasticsearch = Elasticsearch(hosts=hosts)

        if config is None:
            self.config = get_default_config()
        else:
            self.config = config

        self.schema_manager = SchemaManager(self.elasticsearch, self.config)
        self.action_queue = ActionQueue(self.elasticsearch, self.config)

        self.action_queue.start()

    def trigger_flush(self):
        """Manually trigger a flush of the log queue.

        :note: This is not guaranteed to flush immediately; it merely cancels
            the wait before the next flush in the ``ActionQueue`` thread.

        """
        self.action_queue.trigger_flush()

    def get_handler(self, suffix_format='%Y.%m'):
        """Spawn a new logging handler.

        You should use this method to get a ``logging.Handler`` object to
        attach to a ``logging.Logger`` object.

        :note: It is almost definitely unwise to set the formatter of this
            handler yourself.  The integrated formatter prepares documents
            ready to be inserted into Elasticsearch.

        :param suffix_format: The time format string to use as the suffix for
            the indices.  By default your indices will be called, e.g.,
            ``generic-logging-2014.09``.

        """
        handler = ElasticsearchHandler(action_queue=self.action_queue,
                                       suffix_format=suffix_format)
        return handler

    def register_schema(self, logger, schema):
        """Register a new log entry schema.

        It is a good idea to register a 'schema' for every logger that you
        attach a handler to.  This helps Elasticsearch store the data you
        provide optimally.

        :note: This method will block until the mapping is registered with
            Elasticsearch, so you should do it in your initialisation.

        :param logger: The name of the logger this schema will apply to.

        :param schema: The schema to be used.

        """
        self.schema_manager.register_schema(logger, schema)
