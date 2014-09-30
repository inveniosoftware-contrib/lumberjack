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

u"""Provides classes to fit into the Python logging framework."""

import logging
import time

class ElasticsearchFormatter(logging.Formatter):
    u"""Formatter which prepares logs for insertion into Elasticsearch."""

    def format(self, record):
        u"""Adds some metadata and deals with string logs.

        Metadata: @timestamp and level (logging.ERROR etc.)

        Puts string logs into a dict containing the string at index
        'message'.

        """
        # TODO don't glomp @timestamp and level if they already exist?
        if not type(record.msg) == dict:
            es_document = {'message': record.msg}
        else:
            es_document = record.msg.copy()

        es_document['@timestamp'] = record.created
        es_document['level'] = record.levelno

        record.message = es_document

        es_type = record.name
        return (es_type, es_document)

class ElasticsearchHandler(logging.Handler):
    u"""Log Handler subclass to put logs in Elasticsearch."""

    action_queue = None
    last_formatted_record = None
    index_prefix = None

    def __init__(self, action_queue, suffix_format='%Y.%m'):
        logging.Handler.__init__(self)
        self.action_queue = action_queue
        self.setFormatter(ElasticsearchFormatter())

        self.suffix_format = suffix_format

    def emit(self, record):
        u"""Format the log and pass it to an ElasticsearchContext instance.

        Chooses the appropriate index time-suffix based on
        self.suffix_format.

        """
        self.last_formatted_record = record

        suffix = time.strftime(self.suffix_format, time.gmtime(record.created))
        (es_type, document) = self.format(record)

        self.action_queue.queue_index(suffix=suffix, doc_type=es_type,
                                      body=document)

## Filter out ES-related errors so we don't feedback
class ElasticsearchFilter(logging.Filter):
    u"""Filter to remove Elasticsearch-related logs.

    This is so that we don't create a feedback loop where inserting
    logs creates more logs to be inserted.

    """
    def filter(self, record):
        u"""If the record['elasticsearch'] is True, discard the record."""

        if hasattr(record, 'elasticsearch') and record.elasticsearch == True:
            return 0
        else:
            return 1
