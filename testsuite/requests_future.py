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
from .common import ESLogTestCase, HOSTS

import json
from time import sleep
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from eslog.elasticsearch import (RequestsFuturesHttpConnection,
                                 RequestsFuturesTransport)

DOCUMENT = {
    '@timestamp': 0,
    'a_bool_value': False,
    'a_string': 'mice rice right across the page'
}

class RequestsFutureTestCase(ESLogTestCase):
    def setUp(self):
        super(RequestsFutureTestCase, self).setUp()
        self.es_sync = Elasticsearch(hosts=HOSTS)
        self.es_async = Elasticsearch(
            hosts=HOSTS,
            #transport_class=RequestsFuturesTransport,
            connection_class=RequestsFuturesHttpConnection)

    def tearDown(self):
        self.deleteIndices(self.es_sync)

    def testIndex(self):
        self.es_async.index(
            index=self.index_prefix + 'rftest',
            doc_type='type_a',
            body=DOCUMENT)

        # Wait for async request to complete.  It would be nice to
        # block until the request got a reponse, which we could do
        # using the generated Future object.  However, it turns out
        # getting a handle to that object requires rewriting half the
        # library.
        sleep(5)
        query = {
            'query': {
                'match': {
                    'a_bool_value': False
                }
            }
        }
        response = self.es_sync.search(
            index=self.index_prefix + 'rftest',
            body=query)

        resp_doc = response['hits']['hits'][0]
        assert resp_doc['_index'] == self.index_prefix + 'rftest'
        assert resp_doc['_type'] == 'type_a'
        assert resp_doc['_source'] == DOCUMENT

    def testBulk(self):
        def generate_actions(n):
            ii = 0
            while ii < n:
                action = {
                    '_op_type': 'index',
                    '_index': self.index_prefix + 'rftest',
                    '_type': 'type_a',
                    '_source': DOCUMENT
                }

                ii += 1
                yield action

        bulk(self.es_async, generate_actions(1000))

        # Sometimes this test might fail because we haven't given ES
        # long enough to process all the documents.  Try increasing
        # the sleep time.
        sleep(10)
        query = {
            'query': {
                'match': {
                    'a_bool_value': False
                }
            }
        }
        response = self.es_sync.search(
            index=self.index_prefix + 'rftest',
            body=query)

        resp_doc = response['hits']['hits'][0]
        assert resp_doc['_index'] == self.index_prefix + 'rftest'
        assert resp_doc['_type'] == 'type_a'
        assert resp_doc['_source'] == DOCUMENT

        assert response['hits']['total'] == 1000

def suite():
    suite = unittest.makeSuite(RequestsFutureTestCase, 'test')
    return suite
