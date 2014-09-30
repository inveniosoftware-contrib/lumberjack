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

from __future__ import absolute_import
import unittest
from .common import LumberjackTestCase, HOSTS

import json
from time import sleep
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from lumberjack.elasticsearch import (RequestsFuturesHttpConnection,
                                 RequestsFuturesTransport)

DOCUMENT = {
    '@timestamp': 0,
    'a_bool_value': False,
    'a_string': 'mice rice right across the page'
}

class RequestsFuturesTestCase(LumberjackTestCase):
    def setUp(self):
        super(RequestsFuturesTestCase, self).setUp()
        self.es_sync = Elasticsearch(hosts=HOSTS)
        self.es_async = Elasticsearch(
            hosts=HOSTS,
            transport_class=RequestsFuturesTransport,
            connection_class=RequestsFuturesHttpConnection)

    def tearDown(self):
        self.deleteIndices(self.es_sync)

DEAD_HOST = {'host': '240.0.0.1', 'port': 9200}
class TransportTestCase(RequestsFuturesTestCase):
    def testDeadConnection(self):
        my_hosts = list(HOSTS)
        my_hosts.append(DEAD_HOST)
        deadhost_str = 'http://%s:%s' % (DEAD_HOST['host'], DEAD_HOST['port'])

        self.es_async = Elasticsearch(
            hosts=my_hosts,
            transport_class=RequestsFuturesTransport,
            connection_class=RequestsFuturesHttpConnection,
            max_retries=10)

        hosts = map(
            lambda connection: connection.host,
            self.es_async.transport.connection_pool.connections)

        self.assertIn(deadhost_str, hosts)

        futures = []
        def append_to_futures(future):
            futures.append(future)

        # Doing this 10 times with 2 connections means we have a
        # >99.9% chance of hitting the dead connection at some point,
        # provided the selection is uniformly random.
        for _ in range(10):
            self.es_async.index(index=self.index_prefix + 'ttest',
                                doc_type='type_a', body=DOCUMENT,
                                params={'callback': append_to_futures,
                                        'timeout': 5})

        # Block until requests finished.
        for future in futures:
            future.exception()

        hosts = map(
            lambda connection: connection.host,
            self.es_async.transport.connection_pool.connections)
        self.assertNotIn(deadhost_str, hosts)

class ConnectionTestCase(RequestsFuturesTestCase):
    def testIndex(self):
        futures = []
        def append_to_futures(future):
            futures.append(future)

        self.es_async.index(
            index=self.index_prefix + 'rftest',
            doc_type='type_a',
            body=DOCUMENT)

        # Block until all requests finished.
        for future in futures:
            future.exception()
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
        self.assertEqual(resp_doc['_index'], self.index_prefix + 'rftest')
        self.assertEqual(resp_doc['_type'], 'type_a')
        self.assertEqual(resp_doc['_source'], DOCUMENT)

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
        self.assertEqual(resp_doc['_index'], self.index_prefix + 'rftest')
        self.assertEqual(resp_doc['_type'], 'type_a')
        self.assertEqual(resp_doc['_source'], DOCUMENT)

        self.assertEqual(response['hits']['total'], 1000)

def suite():
    connection_suite = unittest.makeSuite(ConnectionTestCase, 'test')
    transport_suite = unittest.makeSuite(TransportTestCase, 'test')
    suit = unittest.TestSuite([connection_suite, transport_suite])
    return suite
