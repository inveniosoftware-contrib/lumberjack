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

from __future__ import absolute_import
import unittest

import eslog

import logging
import elasticsearch
import sys
import time

from .common import HOSTS, INDEX_PREFIX, ES_LOGLEVEL

LOGGER_NAME = 'test'
LOGGER_CHILD_NAME = 'test.child'

class LogTestCase(unittest.TestCase):
    def setUp(self):
        self.esl = eslog.ESLog(hosts=HOSTS, index_prefix=INDEX_PREFIX)
        self.es = self.esl.context.elasticsearch
        
        self.logger = logging.getLogger(LOGGER_NAME)
        self.child_logger = logging.getLogger(LOGGER_CHILD_NAME)

        self.handler = self.esl.get_handler()
        self.logger.addHandler(self.handler)

        l = logging.getLogger('elasticsearch')
        l.setLevel(ES_LOGLEVEL)
        l.addHandler(logging.StreamHandler(stream=sys.stderr))

    def tearDown(self):
        self.logger.handlers = []
        self.esl.context.elasticsearch.indices.delete(
            index=INDEX_PREFIX + '*')

    def test_log_not_dynamic(self):
        schema = {
            'dynamic': 'strict',
            '_source': {'enabled': True},
            'properties': {
                'a': {
                    'type': 'string',
                    'fields': {
                        'raw': {
                            'index': 'not_analyzed',
                            'type': 'string'
                        }
                    }
                },
                'b': {
                    'type': 'long'
                }
            }
        }
        self.esl.context.register_schema(schema=schema,
                                         logger=LOGGER_NAME)
        self._test_log(log_dict={
            'a': 'mice rice right across the page',
            'b': 24
        })
        res = self.es.search(index=INDEX_PREFIX + '*', doc_type=LOGGER_NAME,
                             body={
                                'query': {
                                    'terms': {
                                        'a': 'rice'
                                    }
                                }
                            })
        assert res['hits']['total'] == 1
    
    def test_log_dynamic(self):
        self._test_log()
    
    def _test_log(self, level=logging.ERROR, log_dict={'a': 1, 'b': 2}):
        self.logger.log(level, log_dict)
        self.esl.context.flush()

        time.sleep(2)

        musts = []
        # Build query
        for (k, v) in log_dict.items():
            musts.append({'match': {k: v}})
        musts.append({'match': {'level': level}})
        
        res = self.es.search(index=INDEX_PREFIX + '*', doc_type=LOGGER_NAME,
                             body={
                                'query': {
                                    'bool': {
                                        'must': musts
                                    }
                                }
                            })
        assert res['hits']['total'] == 1

def suite():
    suite = unittest.makeSuite(LogTestCase, 'test')
    return suite
