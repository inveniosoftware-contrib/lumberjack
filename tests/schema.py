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
from .common import LumberjackTestCase, MOCK, skipIfNotMock, TestHandler, HOSTS

import lumberjack

import logging
import elasticsearch
import sys
import time
from random import randint
from mock import Mock, call

SCHEMA_A = {
    'dynamic': 'strict',
    '_source': {'enabled': True},
    'properties': {
        'a': {
            'index': 'analyzed',
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

SCHEMA_B = {
    '_source': {'enabled': False},
    '_ttl': {'enabled': False},
    'properties': {
        'c': {
            'type': 'string'
        },
        'd': {
            'type': 'ip'
        }
    }
}


class SchemaTestCase(LumberjackTestCase):
    def test_build_mapping(self):
        self.getLumberjackObject()
        expected_mapping_a = {
            'dynamic': 'strict',
            '_source': {'enabled': True},
            '_all': {'enabled': False},
            '_ttl': {'enabled': True},
            'properties': {
                'message': {
                    'type': 'string',
                    'index': 'not_analyzed',
                    'norms': {'enabled': False}
                },
                '@timestamp': {
                    'type': 'date',
                    'format': 'dateOptionalTime',
                },
                'level': {
                    'type': 'integer'
                },
                'a': {
                    'type': 'string',
                    'index': 'analyzed',
                    'fields': {
                        'raw': {
                            'index': 'not_analyzed',
                            'type': 'string'
                        }
                    },
                    'norms': {'enabled': False}
                },
                'b': {
                    'type': 'long'
                }
            }
        }
        expected_mapping_b = {
            '_source': {'enabled': False},
            '_all': {'enabled': False},
            '_ttl': {'enabled': False},
            'properties': {
                'message': {
                    'type': 'string',
                    'index': 'not_analyzed',
                    'norms': {'enabled': False}
                },
                '@timestamp': {
                    'type': 'date',
                    'format': 'dateOptionalTime'
                },
                'level': {'type': 'integer'},
                'c': {
                    'type': 'string',
                    'index': 'not_analyzed',
                    'norms': {'enabled': False}
                },
                'd': {
                    'type': 'ip'
                }
            }
        }

        self.assertEqual(self.lj.schema_manager._build_mapping(SCHEMA_A),
                         expected_mapping_a)
        self.assertEqual(self.lj.schema_manager._build_mapping(SCHEMA_B),
                         expected_mapping_b)

    def test_build_mapping_non_default(self):
        self.config['default_mapping'] = {
            '_source': {'enabled': False},
            '_ttl': {'enabled': False},
            'properties': {
                'ip': {
                    'type': 'ip'
                },
                'level': {
                    'type': 'string'
                }
            }
        }
        self.config['default_type_properties'] = {
            'string': {
                'index': 'analyzed',
            }
        }

        custom_schema = {
            'dynamic': 'strict',
            '_all': {'enabled': False},
            'properties': {
                'username': {'type': 'string', 'index': 'not_analyzed'},
                'message': {'type': 'string'}
            }
        }

        expected_mapping = {
            'dynamic': 'strict',
            '_source': {'enabled': False},
            '_all': {'enabled': False},
            '_ttl': {'enabled': False},
            'properties': {
                'ip': {'type': 'ip'},
                'level': {'type': 'string', 'index': 'analyzed'},
                'username': {'type': 'string', 'index': 'not_analyzed'},
                'message': {'type': 'string', 'index': 'analyzed'}
            }
        }

        self.getLumberjackObject()

        self.assertEqual(self.lj.schema_manager._build_mapping(custom_schema),
                         expected_mapping)

    def test_register_schema(self):
        self.getLumberjackObject()
        expected_template = self.build_expected_template('type_a', SCHEMA_A)

        if MOCK:
            def mock_put_template_f(name, body):
                self.assertEqual(
                    name,
                    'lumberjack-' + self.config['index_prefix'] + 'type_a')
                self.assertEqual(body, expected_template)

            def mock_put_mapping_f(index, body, doc_type):
                self.assertEqual(
                    body,
                    expected_template['mappings']['type_a'])

            self.elasticsearch.indices.put_template = mock_put_template_f
            self.elasticsearch.indices.put_mapping = mock_put_mapping_f

        self.lj.register_schema('type_a', SCHEMA_A)

        if not MOCK:
            res = self.elasticsearch.indices.get_template(
                name='lumberjack-' + self.config['index_prefix'] + '*')
            self.assertDictContainsSubset(expected_template,
                res['lumberjack-' + self.config['index_prefix'] +'type_a'])

    def build_expected_template(self, name, schema, lj=None):
        if lj is None:
            lj = self.lj
        mapping = lj.schema_manager._build_mapping(schema)
        template = {
            'template': self.config['index_prefix'] + '*',
            'mappings': { name: mapping }
        }
        return template

    def test_register_multiple_schemas(self):
        self.getLumberjackObject()

        expected_templates = {
            'type_a': self.build_expected_template('type_a', SCHEMA_A),
            'type_b': self.build_expected_template('type_b', SCHEMA_B)
        }

        if MOCK:
            mock_put_template_f = Mock(return_value=None)
            self.elasticsearch.indices.put_template = mock_put_template_f

            mock_put_mapping_f = Mock(return_value=None)
            self.elasticsearch.indices.put_mapping = mock_put_mapping_f

        self.lj.register_schema('type_a', SCHEMA_A)
        self.lj.register_schema('type_b', SCHEMA_B)

        if MOCK:
            self.assertEqual(mock_put_template_f.call_count, 2)
            mock_put_template_f.assert_has_calls([
                call(name='lumberjack-' + self.config['index_prefix'] +
                    'type_a',
                     body=expected_templates['type_a']),
                call(name='lumberjack-' + self.config['index_prefix'] +
                     'type_b',
                     body=expected_templates['type_b'])
                ])

        if not MOCK:
            res = self.elasticsearch.indices.get_template(
                name='lumberjack-' + self.config['index_prefix'] + '*')

            self.assertDictContainsSubset(
                expected_templates['type_a'],
                res['lumberjack-' + self.config['index_prefix'] + 'type_a'])
            self.assertDictContainsSubset(
                expected_templates['type_b'],
                res['lumberjack-' + self.config['index_prefix'] + 'type_b'])

    def test_register_single_schema_multiple_lumberjacks(self):
        lj1 = lumberjack.Lumberjack(hosts=HOSTS, config=self.config)
        lj2 = lumberjack.Lumberjack(hosts=HOSTS, config=self.config)

        expected_template = self.build_expected_template('type_a', SCHEMA_A,
                                                         lj=lj1)
        if MOCK:
            mock_put_template_f1 = Mock(return_value=None)
            lj1.elasticsearch.indices.put_template = mock_put_template_f1

            mock_put_template_f2 = Mock(return_value=None)
            lj2.elasticsearch.indices.put_template = mock_put_template_f2

        if not MOCK:
            self.addCleanup(self.deleteIndices, lj1.elasticsearch)

        lj1.register_schema('type_a', SCHEMA_A)
        lj2.register_schema('type_a', SCHEMA_A)

        if MOCK:
            self.assertEqual(mock_put_template_f1.call_count, 1)
            self.assertEqual(mock_put_template_f2.call_count, 1)

            mock_put_template_f1.assert_called_with(
                name='lumberjack-' + self.config['index_prefix'] + 'type_a',
                body=expected_template)
            mock_put_template_f2.assert_called_with(
                name='lumberjack-' + self.config['index_prefix'] + 'type_a',
                body=expected_template)

        if not MOCK:
            res = lj1.elasticsearch.indices.get_template(
                name='lumberjack-' + self.config['index_prefix'] + '*')
            self.assertDictContainsSubset(
                expected_template,
                res['lumberjack-' + self.config['index_prefix'] + 'type_a'])

    @skipIfNotMock
    def test_put_mapping_transport_error(self):
        my_handler = TestHandler()
        logging.getLogger('lumberjack.schemas').addHandler(my_handler)

        self.getLumberjackObject()

        test_exception = elasticsearch.TransportError(400, 'Test exception')
        called = {'called': False}
        def mock_put_mapping_f(index, body, doc_type):
            called['called'] = True
            raise test_exception
        self.elasticsearch.indices.put_mapping = mock_put_mapping_f
        self.lj.register_schema('type_a', SCHEMA_A)
        self.assertTrue(called['called'])

        my_handler.assertLoggedWithException(
            'lumberjack.schemas', 'WARNING',
            'There was an error putting the new mapping on some indices.  ' +
            'If you try to log new data to these, you will see errors.',
            test_exception)
        # No crash

    @skipIfNotMock
    def test_put_template_transport_error(self):
        my_handler = TestHandler()
        logging.getLogger('lumberjack.schemas').addHandler(my_handler)

        self.getLumberjackObject()

        test_exception = elasticsearch.TransportError(400, 'Test exception')
        called = {'called': False}
        def mock_put_template_f(name, body):
            called['called'] = True
            raise test_exception
        self.elasticsearch.indices.put_template = mock_put_template_f
        self.lj.register_schema('type_a', SCHEMA_A)
        self.assertTrue(called['called'])

        my_handler.assertLoggedWithException(
            'lumberjack.schemas', 'WARNING',
            'Error putting new template in Elasticsearch: type_a.',
            test_exception)
        # No crash
