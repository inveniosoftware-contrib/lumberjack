# -*- coding: utf-8 -*-
##
## This file is part of ESLog.
## Copyright (C) 2014 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

import logging
from elasticsearch import Elasticsearch
import time

class ElasticsearchFormatter(logging.Formatter):
    def format(self, record):
        # TODO don't glomp @timestamp and level if they already exist?
        if not (type(record.msg) == dict):
            es_document = { 'message': record.msg }
        else:
            es_document = record.msg.copy()

        es_document['@timestamp'] = record.created
        es_document['level'] = record.levelno
        
        record.message = es_document

        es_type = record.name
        return (es_type, es_document)

class ElasticsearchHandler(logging.Handler):
    context = None
    lastFormattedRecord = None
    index_prefix = None

    def __init__(self, context,
      suffix_format = '%Y.%m'):
        logging.Handler.__init__(self)
        self.context = context
        self.setFormatter(ElasticsearchFormatter())

        self.suffix_format = suffix_format

    def emit(self, record):
        self.lastFormattedRecord = record

        suffix = time.strftime(self.suffix_format, time.gmtime(record.created))
        (es_type, document) = self.format(record)

        self.context.queue_index(suffix = suffix, doc_type = es_type, \
          body = document)

## Filter out ES-related errors so we don't feedback
class ElasticsearchFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, 'elasticsearch') and record.elasticsearch == True:
            return 0
        else:
            return 1
