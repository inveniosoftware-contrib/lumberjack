# -*- coding: utf-8 -*-
#
# This file is part of Lumberjack.
# Copyright (C) 2014 CERN.
#
# Lumberjack is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Lumberjack is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Lumberjack; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Python Elasticsearch Logging Handler."""

from __future__ import absolute_import

from elasticsearch import Elasticsearch
from .handler import ElasticsearchHandler
from .schemas import SchemaManager
from .actions import ActionQueue

import logging

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

    :param index_prefix: A prefix for the created indices in Elasticsearch.

    :param hosts: A list of Elasticsearch nodes to connect to, in the form
        ``[{'host': '127.0.0.1', 'port': 9200}]``.  This is passed directly to
        elasticsearch.Elasticsearch.

    :param elasticsearch: An already-instantiated
        ``elasticsearch.Elasticsearch`` object, perhaps with custom transports
        etc.

    :param interval: A number of seconds between calls to flush the queue of
        log entries.

    :param max_queue_length: The maximum length that the queue of log entries
        is allowed to grow to before being flushed.

    """

    elasticsearch = None
    schema_manager = None
    action_queue = None

    index_prefix = None

    def __init__(self, index_prefix='generic-logging-',
                 hosts=None, elasticsearch=None, interval=30,
                 max_queue_length=None,):
        self.index_prefix = index_prefix

        # TODO: clean this up.  Error if both or neither are provided.
        if elasticsearch is not None:
            LOG.debug('Using provided ES instance.')
            self.elasticsearch = elasticsearch
        elif hosts is None:
            LOG.warn('No Elasticsearch config specified. ' +
                     'This is very probably a bad idea.')
        else:
            LOG.debug('Using provided hosts.')
            self.elasticsearch = Elasticsearch(hosts=hosts)

        # TODO: read args from a config here.
        self.schema_manager = SchemaManager(self.elasticsearch, index_prefix)
        self.action_queue = ActionQueue(self.elasticsearch, index_prefix,
                                        interval=interval,
                                        max_queue_length=max_queue_length)

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

        Schemas correspond closely with mappings in Elasticsearch, but are
        processed by Lumberjack to include some sensible defaults.  An example
        schema might be::

            {
                '_source': True,
                'properties': {
                    'ip_address': {'type': 'ip'},
                    'user_id': {'type': 'long'},
                    'username': {'type': 'string'}
                }
            }

        This method should be called once per schema to register; it's probably
        a good idea to call it at the same time as attaching your handler to a
        ``logging.Logger`` object.

        :note: This method will block until the mapping is registered with
            Elasticsearch, so you should do it in your initialisation.

        :param logger: The name of the logger this schema will apply to.

        :param schema: The schema to be used.

        """
        self.schema_manager.register_schema(logger, schema)
