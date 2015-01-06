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

from __future__ import absolute_import
import unittest
import time
import elasticsearch
import logging
import json

import lumberjack

from .common import LumberjackTestCase, HOSTS, MOCK, TestHandler, skipIfNotMock

INTERVAL_SHORT = 2
INTERVAL_LONG = 10*INTERVAL_SHORT
MAX_QUEUE_LENGTH = 20


class ActionsTestCase(LumberjackTestCase):
    def setUp(self):
        super(ActionsTestCase, self).setUp()

        self.config['interval'] = INTERVAL_SHORT
        self.config['max_queue_length'] = MAX_QUEUE_LENGTH
        
        self.getLumberjackObject()
        self.lj.register_schema(__name__, {'_source': {'enabled': True}})
        self.elasticsearch = self.lj.elasticsearch

    def test_params_passed_to_action_queue(self):
        self.assertEqual(INTERVAL_SHORT,
                         self.lj.action_queue.config['interval'])
        self.assertEqual(MAX_QUEUE_LENGTH,
                         self.lj.action_queue.config['max_queue_length'])

    def test_basic_flush(self):
        if MOCK:
            def mock_bulk_f(es, actions):
                self.assertEqual(es, self.elasticsearch)
                if len(actions) == 0:
                    return
                self.assertEqual(len(actions), 1)
                action = actions[0]

                self.assertEqual(action['_type'], __name__)
                self.assertEqual(action['_index'],
                                 self.config['index_prefix'] + 'test')
                self.assertEqual(action['_source'], {'message': 'testD'})

            self.lj.action_queue.bulk = mock_bulk_f
        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body={'message': 'testD'})
        self.lj.trigger_flush()

        if not MOCK:
            time.sleep(3)
            res = self.elasticsearch.search(
                index=self.config['index_prefix'] + '*', doc_type=__name__,
                body={
                    'query': {
                        'match': {'message': 'testD'}
                    }
                })
            self.assertEqual(res['hits']['total'], 1)

    def test_basic_timeouts(self):
        if MOCK:
            actions_list = []
            def mock_bulk_f(es, actions):
                actions_list.extend(actions)

            self.lj.action_queue.bulk = mock_bulk_f
        self.lj.trigger_flush()
        time.sleep(1)

        if MOCK:
            self.assertEqual(len(actions_list), 0)

        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body={'message': 'testE'})
        time.sleep(INTERVAL_SHORT + 3)

        if MOCK:
            self.assertEqual(len(actions_list), 1)
            self.assertEqual(actions_list[0]['_source'], {'message': 'testE'})
        else:
            res = self.elasticsearch.search(
                index=self.config['index_prefix'] + '*', doc_type=__name__,
                body={
                    'query': {
                        'match': {'message': 'testE'}
                    }
                })
            self.assertEqual(res['hits']['total'], 1)

    def test_change_update_interval(self):
        if MOCK:
            actions_list = []
            def mock_bulk_f(es, actions):
                actions_list.extend(actions)

            self.lj.action_queue.bulk = mock_bulk_f

        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body={'message': 'testA'})
        time.sleep(INTERVAL_SHORT + 3)

        if not MOCK:
            res = self.elasticsearch.search(
                index=self.config['index_prefix'] + '*', doc_type=__name__,
                body={
                    'query': {
                        'match': {
                            'message': 'testA'
                        }
                    }
                })
            self.assertEqual(res['hits']['total'], 1)
        else:
            self.assertEqual(len(actions_list), 1)
            self.assertDictContainsSubset(
                {'_source': {'message': 'testA'},
                 '_type': __name__,
                 '_index': self.config['index_prefix'] + 'test'},
                actions_list[-1])

        self.lj.action_queue.config['interval'] = INTERVAL_LONG
        self.lj.trigger_flush()

        # Wait for the flush to complete before adding to the queue.
        time.sleep(1)

        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body={'message': 'testB'})
        time.sleep(INTERVAL_SHORT + 3)
        b_query = {
            'query': {
                'match': {
                    'message': 'testB'
                }
            }
        }

        # Should not have been procesed yet.
        if not MOCK:
            res = self.elasticsearch.search(
                index=self.config['index_prefix'] + '*', doc_type=__name__,
                body=b_query)
            self.assertEqual(res['hits']['total'], 0)
        else:
            self.assertEqual(len(actions_list), 1)

        time.sleep(INTERVAL_LONG)

        if not MOCK:
            res = self.elasticsearch.search(
                index=self.config['index_prefix'] + '*', doc_type=__name__,
                body=b_query)
            self.assertEqual(res['hits']['total'], 1)
        else:
            self.assertEqual(len(actions_list), 2)
            self.assertDictContainsSubset(
                {'_source': {'message': 'testB'},
                 '_type': __name__,
                 '_index': self.config['index_prefix'] + 'test'},
                actions_list[-1])

    def test_max_queue_length(self):
        if MOCK:
            actions_list = []
            def mock_bulk_f(es, actions):
                actions_list.extend(actions)

            self.lj.action_queue.bulk = mock_bulk_f

        # Disable periodic flushing
        self.lj.action_queue.config['interval'] = None
        self.lj.trigger_flush()

        # Wait for flush to complete
        time.sleep(1)

        self.assertEqual(len(self.lj.action_queue.queue), 0)

        doc = {'message': 'testC'}
        while len(self.lj.action_queue.queue) < MAX_QUEUE_LENGTH-1:
            self.lj.action_queue.queue_index(suffix='test',
                                             doc_type=__name__,
                                             body=doc)
        # Wait for ES indexing in case the test failed and already flushed.
        time.sleep(3)

        if not MOCK:
            res = self.elasticsearch.search(
                index=self.config['index_prefix'] + '*', doc_type=__name__,
                body={
                    'query': {
                        'match': doc
                    }
                })
            self.assertEqual(res['hits']['total'], 0)
        else:
            self.assertEqual(len(actions_list), 0)

        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body=doc)
        # Wait for flush and ES indexing
        time.sleep(3)

        if not MOCK:
            res = self.elasticsearch.search(
                index=self.config['index_prefix'] + '*', doc_type=__name__,
                body={
                    'query': {
                        'match': doc
                    }
                })
            self.assertEqual(res['hits']['total'], MAX_QUEUE_LENGTH)
        else:
            self.assertEqual(len(actions_list), MAX_QUEUE_LENGTH)

    def test_transport_error(self):
        my_handler = TestHandler()
        logging.getLogger('lumberjack.actions').addHandler(my_handler)

        self.getLumberjackObject()

        test_exception = elasticsearch.TransportError(400, 'Test exception')
        def mock_bulk_f(es, actions):
            raise test_exception
        self.lj.action_queue.bulk = mock_bulk_f

        with self.lj.action_queue.queue_lock:
            self.lj.action_queue.queue.append(None)

        self.lj.trigger_flush()
        self.lj.action_queue.running = False
        self.lj.action_queue.join(timeout=10)
        self.assertFalse(self.lj.action_queue.is_alive())

        my_handler.assertLoggedWithException(
            'lumberjack.actions', 'ERROR',
            'Error in flushing queue. Falling back to file.',
            test_exception)

    def test_general_error(self):
        my_handler = TestHandler()
        logging.getLogger('lumberjack.actions').addHandler(my_handler)

        self.getLumberjackObject()

        class TestException(Exception):
            pass
        test_exception = TestException()
        def mock_bulk_f(es, actions):
            raise test_exception
        self.lj.action_queue.bulk = mock_bulk_f

        self.lj.trigger_flush()
        self.lj.action_queue.join(timeout=10)
        self.assertFalse(self.lj.action_queue.is_alive())

        self.assertEqual(type(self.lj.action_queue.last_exception),
                         TestException)
        self.lj.action_queue.last_exception = None

        my_handler.assertLoggedWithException(
            'lumberjack.actions', 'ERROR',
            'Action queue thread terminated unexpectedly.',
            test_exception)

    def test_fallback_log_config(self):
        self.getLumberjackObject()
        self.assertIn('fallback_log_file', self.lj.config)

    @skipIfNotMock
    def test_fallback_log(self):
        with open(self.lj.config['fallback_log_file'], 'w') as f:
            f.write('')
        self.getLumberjackObject()
        self.lj.config['max_queue_length'] = MAX_QUEUE_LENGTH

        class TestException(Exception): pass

        completed_actions = []
        called = {'called': False}
        def mock_bulk_f(es, actions):
            if len(completed_actions) > MAX_QUEUE_LENGTH:
                called['called'] = True
                raise elasticsearch.TransportError(400, 'Test exception.')
            else:
                completed_actions.extend(actions)
        self.lj.action_queue.bulk = mock_bulk_f

        doc = {'message': 'test'}
        while len(self.lj.action_queue.queue) <= MAX_QUEUE_LENGTH:
            self.lj.action_queue.queue_index(suffix='test',
                                            doc_type=__name__,
                                            body=doc)
        time.sleep(0.1)
        self.assertGreater(len(completed_actions), MAX_QUEUE_LENGTH)

        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body=doc)
        self.lj.action_queue._flush()
        time.sleep(0.1)
        self.assertTrue(called['called'])
        with open(self.lj.config['fallback_log_file'], 'r') as f:
            line = f.next()
            self.assertEqual(json.loads(line), completed_actions[0])
