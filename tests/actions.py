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
from mock import MagicMock
from contextlib import contextmanager

import lumberjack

from .common import LumberjackTestCase, HOSTS, MOCK, TestHandler, skipIfNotMock

INTERVAL_SHORT = 1
INTERVAL_LONG = 10*INTERVAL_SHORT
INTERVAL_JUMP_THREAD = 0.1
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

    @skipIfNotMock
    def test_unexpected_exception(self):
        my_handler = TestHandler()
        logging.getLogger('lumberjack.actions').addHandler(my_handler)

        self.getLumberjackObject()
        class TestException(Exception):
            pass
        test_exception = TestException()
        self.lj.action_queue._flush = MagicMock(side_effect=test_exception)

        self.lj.trigger_flush()
        time.sleep(INTERVAL_JUMP_THREAD)

        my_handler.assertLoggedWithException(
            'lumberjack.actions', 'ERROR',
            'Unexpected exception in actions thread. Continuing anyway.',
            test_exception)

        self.assertIn(test_exception, self.lj.action_queue.exceptions)
        self.assertTrue(self.lj.action_queue.is_alive())

        def this_cleanup():
            self.lj.action_queue.running = False
            self.lj.action_queue.join()
            self.lj.action_queue.exceptions = []
        self.addCleanup(this_cleanup)

    @skipIfNotMock
    def test_basic_flush(self):
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

        self.lj.action_queue._bulk = mock_bulk_f
        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body={'message': 'testD'})
        self.lj.trigger_flush()

    @skipIfNotMock
    def test_basic_timeouts(self):
        actions_list = []
        def mock_bulk_f(es, actions):
            actions_list.extend(actions)

        self.lj.action_queue._bulk = mock_bulk_f
        self.lj.trigger_flush()
        time.sleep(INTERVAL_SHORT)

        self.assertEqual(len(actions_list), 0)

        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body={'message': 'testE'})
        time.sleep(INTERVAL_SHORT)

        self.assertEqual(len(actions_list), 1)
        self.assertEqual(actions_list[0]['_source'], {'message': 'testE'})

    @skipIfNotMock
    def test_change_update_interval(self):
        actions_list = []
        def mock_bulk_f(es, actions):
            actions_list.extend(actions)

        self.lj.action_queue._bulk = mock_bulk_f

        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body={'message': 'testA'})
        time.sleep(INTERVAL_SHORT)

        self.assertEqual(len(actions_list), 1)
        self.assertDictContainsSubset(
            {'_source': {'message': 'testA'},
             '_type': __name__,
             '_index': self.config['index_prefix'] + 'test'},
            actions_list[-1])

        self.lj.action_queue.config['interval'] = INTERVAL_LONG
        self.lj.trigger_flush()

        # Wait for the flush to complete before adding to the queue.
        time.sleep(INTERVAL_JUMP_THREAD)

        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body={'message': 'testB'})
        time.sleep(INTERVAL_JUMP_THREAD)
        b_query = {
            'query': {
                'match': {
                    'message': 'testB'
                }
            }
        }

        self.assertEqual(len(actions_list), 1)

        time.sleep(INTERVAL_LONG)

        self.assertEqual(len(actions_list), 2)
        self.assertDictContainsSubset(
            {'_source': {'message': 'testB'},
             '_type': __name__,
             '_index': self.config['index_prefix'] + 'test'},
            actions_list[-1])

    @skipIfNotMock
    def test_max_queue_length(self):
        actions_list = []
        def mock_bulk_f(es, actions):
            actions_list.extend(actions)

        self.lj.action_queue._bulk = mock_bulk_f

        # Disable periodic flushing
        self.lj.action_queue.config['interval'] = None
        self.lj.trigger_flush()

        # Wait for flush to complete
        time.sleep(INTERVAL_JUMP_THREAD)

        self.assertEqual(len(self.lj.action_queue.queue), 0)

        doc = {'message': 'testC'}
        while len(self.lj.action_queue.queue) < MAX_QUEUE_LENGTH-1:
            self.lj.action_queue.queue_index(suffix='test',
                                             doc_type=__name__,
                                             body=doc)
        # In case the test failed and already flushed.
        time.sleep(INTERVAL_JUMP_THREAD)

        self.assertEqual(len(actions_list), 0)

        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body=doc)
        # Wait for flush
        time.sleep(INTERVAL_JUMP_THREAD)

        self.assertEqual(len(actions_list), MAX_QUEUE_LENGTH)

    @skipIfNotMock
    def test_transport_error(self):
        my_handler = TestHandler()
        logging.getLogger('lumberjack.actions').addHandler(my_handler)

        self.getLumberjackObject()

        test_exception = elasticsearch.TransportError(400, 'Test exception')
        def mock_bulk_f(es, actions):
            raise test_exception
        self.lj.action_queue._bulk = mock_bulk_f

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

    def test_fallback_log_config(self):
        self.getLumberjackObject()
        self.assertIn('fallback_log_file', self.lj.config)

    @skipIfNotMock
    def test_fallback_log(self):
        self.getLumberjackObject()
        self.lj.config['max_queue_length'] = MAX_QUEUE_LENGTH

        args = {}
        file_ = MagicMock(spec=file)
        @contextmanager
        def my_open(filename, mode):
            args['filename'] = filename
            args['mode'] = mode
            yield file_
        self.lj.action_queue._open = my_open

        completed_actions = []
        called = {'called': False}
        def mock_bulk_f(es, actions):
            if len(completed_actions) > MAX_QUEUE_LENGTH:
                called['called'] = True
                raise elasticsearch.TransportError(400, 'Test exception.')
            else:
                completed_actions.extend(actions)
        self.lj.action_queue._bulk = mock_bulk_f

        doc = {'message': 'test'}
        while len(self.lj.action_queue.queue) <= MAX_QUEUE_LENGTH:
            self.lj.action_queue.queue_index(suffix='test',
                                            doc_type=__name__,
                                            body=doc)
        time.sleep(INTERVAL_JUMP_THREAD)
        self.assertGreater(len(completed_actions), MAX_QUEUE_LENGTH)

        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body=doc)
        self.lj.action_queue._flush()
        time.sleep(INTERVAL_JUMP_THREAD)

        self.assertTrue(called['called'])

        self.assertEqual(args['filename'], '/tmp/lumberjack_fallback.log')
        self.assertEqual(args['mode'], 'a')

        file_.write.assert_called_with(json.dumps(completed_actions[0]) + '\n')

    @skipIfNotMock
    def test_fallback_file_name(self):
        config_file = '/tmp/some_other_file.log'

        self.getLumberjackObject()
        self.lj.config['fallback_log_file'] = config_file

        args = {}
        file_ = MagicMock(spec=file)
        @contextmanager
        def my_open(filename, mode):
            args['filename'] = filename
            args['mode'] = mode
            yield file_
        self.lj.action_queue._open = my_open

        completed_actions = []
        def mock_bulk_f(es, actions):
            completed_actions.extend(actions)
            raise elasticsearch.TransportError(400, 'Test exception.')
        self.lj.action_queue._bulk = mock_bulk_f

        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body={'message': 'test'})
        self.lj.action_queue.trigger_flush()
        time.sleep(INTERVAL_JUMP_THREAD)

        self.assertEqual(args['filename'], config_file)
        self.assertEqual(args['mode'], 'a')

        self.assertEqual(len(completed_actions), 1)
        file_.write.assert_called_with(json.dumps(completed_actions[0]) + '\n')

    @skipIfNotMock
    def test_fallback_error(self):
        my_handler = TestHandler()
        logging.getLogger('lumberjack.actions').addHandler(my_handler)

        my_ioerror = IOError('Test error')

        class BadFile(object):
            def write(self, str_):
                raise my_ioerror

        @contextmanager
        def my_open(filename, mode):
            yield BadFile()

        self.getLumberjackObject()
        self.lj.action_queue._open = my_open

        def mock_bulk_f(es, actions):
            raise elasticsearch.TransportError(400, 'Test exception.')
        self.lj.action_queue._bulk = mock_bulk_f

        self.lj.action_queue.queue_index(suffix='test',
                                         doc_type=__name__,
                                         body={'message': 'test'})
        self.lj.action_queue.trigger_flush()
        time.sleep(INTERVAL_JUMP_THREAD)

        my_handler.assertLoggedWithException('lumberjack.actions', 'ERROR',
                                             'Error in fallback log. Lost ' +
                                             '1 logs.', my_ioerror)

    def test_interpreter_shutdown_bug(self):
        """Tests for a TypeError in threading

        During interpreter shutdown, time.time is destroyed and becomes None,
        raising a TypeError when Event.wait() is called.

        <http://bugs.python.org/issue14623>

        """
        my_handler = TestHandler()
        my_handler.setLevel(logging.DEBUG)
        logging.getLogger('lumberjack.actions').setLevel(logging.DEBUG)
        logging.getLogger('lumberjack.actions').addHandler(my_handler)

        my_type_error = TypeError(
            'Test error (\'NoneType\' object not callable)')
        self.getLumberjackObject()

        self.lj.action_queue._flush_event.wait = MagicMock(
            side_effect=my_type_error)
        self.lj.trigger_flush()
        time.sleep(INTERVAL_JUMP_THREAD)

        self.assertTrue(not self.lj.action_queue.is_alive())
        my_handler.assertLoggedWithException(
            'lumberjack.actions', 'DEBUG', 'Caught TypeError from ' +
            'Event.wait().  This is expected only during interpreter ' +
            'shutdown.', my_type_error)
