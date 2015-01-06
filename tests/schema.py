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
from .common import LumberjackTestCase, MOCK, skipIfNotMock, TestHandler

import lumberjack

import logging
import elasticsearch
import sys
import time
from random import randint

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
    def test_build_mappings(self):
        self.getLumberjackObject()
        self.lj.schema_manager.schemas['type_a'] = SCHEMA_A
        self.lj.schema_manager.schemas['type_b'] = SCHEMA_B
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
        self.maxDiff = None
        mappings = self.lj.schema_manager._build_mappings()
        self.assertEqual(mappings['type_a'], expected_mapping_a)
        self.assertEqual(mappings['type_b'], expected_mapping_b)

    def test_build_mappings_non_default(self):
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
        self.lj.schema_manager.schemas['type_b'] = {
            'dynamic': 'strict',
            '_all': {'enabled': False},
            'properties': {
                'username': {'type': 'string', 'index': 'not_analyzed'},
                'message': {'type': 'string'}
            }
        }

        self.assertEqual(self.lj.schema_manager._build_mappings()['type_b'],
                         expected_mapping)

    def test_register_schema(self):
        self.getLumberjackObject()

        if MOCK:
            def mock_put_template_f(name, body):
                self.assertEqual(
                    name,
                    'lumberjack-' + self.config['index_prefix'] + '*')
                self.assertEqual(body['template'],
                                 self.config['index_prefix'] + '*')
                self.assertEqual(body['mappings'],
                                 self.lj.schema_manager._build_mappings())

            def mock_put_mapping_f(index, body, doc_type):
                self.assertEqual(
                    body,
                    self.lj.schema_manager._build_mappings()[doc_type])

            self.elasticsearch.indices.put_template = mock_put_template_f
            self.elasticsearch.indices.put_mapping = mock_put_mapping_f

        self.lj.register_schema('type_a', SCHEMA_A)

        # Test it's now in ES, unles we're in mock.
        if not MOCK:
            res = self.elasticsearch.indices.get_template(
                name='lumberjack-' + self.config['index_prefix'] + '*')

            expected_schema = self.lj.schema_manager._build_mappings()['type_a']

            self.assertEqual(
                res['lumberjack-' + self.config['index_prefix'] +'*']
                    ['mappings']['type_a'], expected_schema)

    @skipIfNotMock
    def test_put_mapping_transport_error(self):
        my_handler = TestHandler()
        logging.getLogger('lumberjack.schemas').addHandler(my_handler)

        self.getLumberjackObject()

        called = {'called': False}
        def mock_put_mapping_f(index, body, doc_type):
            called['called'] = True
            raise elasticsearch.TransportError(400, 'Test exception')
        self.elasticsearch.indices.put_mapping = mock_put_mapping_f
        self.lj.register_schema('type_a', SCHEMA_A)
        self.assertTrue(called['called'])

        my_handler.assertLogged('lumberjack.schemas', 'WARNING',
                                 'There was an error putting the new ' +
                                 'mapping on some indices.  If you try to ' +
                                 'log new data to these, you will see errors.')
        # No crash

    @skipIfNotMock
    def test_put_template_transport_error(self):
        my_handler = TestHandler()
        logging.getLogger('lumberjack.schemas').addHandler(my_handler)

        self.getLumberjackObject()

        called = {'called': False}
        def mock_put_template_f(name, body):
            called['called'] = True
            raise elasticsearch.TransportError(400, 'Test exception')
        self.elasticsearch.indices.put_template = mock_put_template_f
        self.lj.register_schema('type_a', SCHEMA_A)
        self.assertTrue(called['called'])

        my_handler.assertLogged('lumberjack.schemas', 'WARNING',
                                 'Error putting new template in Elasticsearch.')
        # No crash
