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

"""Provide classes to fit into the Python logging framework."""

import logging
import time
from copy import deepcopy


class ElasticsearchFormatter(logging.Formatter):

    """Formatter which prepares logs for insertion into Elasticsearch."""

    def format(self, record):
        """Add some metadata and deals with string logs.

        It adds a ``@timestamp`` field and a ``level`` field.  ``level``
        contains the loglevel as an integer.

        Log data should be in a ``dict``, but to be compatible with the generic
        Python logging recommendations, it can also format log data received as
        a string.  In this case, a dict is returned containing a single
        ``message`` field, whose data is the string message.

        :param record: The ``logging.LogRecord`` object to be formatted.

        """
        # TODO don't glomp @timestamp and level if they already exist?
        if not type(record.msg) == dict:
            es_document = {'message': record.msg}
        else:
            es_document = deepcopy(record.msg)

        # Milliseconds
        es_document['@timestamp'] = record.created * 1000
        es_document['level'] = record.levelno

        record.message = es_document

        es_type = record.name
        return (es_type, es_document)


class ElasticsearchHandler(logging.Handler):

    """Elasticsearch-specific subclass of ``logging.LogHandler``.

    :param action_queue: A ``lumberjack.ActionQueue`` object to which the
        formatted log entries are passed.

    :param suffix_format: The format from which to generate the time-based
        index suffixes for Elasticsearch.  `strftime()` format.

    """

    # TODO: suffix_format in config
    def __init__(self, action_queue, suffix_format='%Y.%m'):
        """Init method.  See class docstring."""
        logging.Handler.__init__(self)
        self.action_queue = action_queue
        self.setFormatter(ElasticsearchFormatter())

        self.suffix_format = suffix_format

    def emit(self, record):
        """Format the log and pass it to an ElasticsearchContext instance.

        Generates the appropriate index time-suffix based on
        ``self.suffix_format``.

        :param record: The ``logging.LogRecord`` object to format and index.

        """
        self.last_formatted_record = record

        suffix = time.strftime(self.suffix_format, time.gmtime(record.created))
        (es_type, document) = self.format(record)

        self.action_queue.queue_index(suffix=suffix, doc_type=es_type,
                                      body=document)
