# -*- coding: utf-8 -*-
#
# This file is part of Lumberjack.
# Copyright (C) 2014 CERN.
#
# Lumberjack is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Lumberjack is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Lumberjack; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

from __future__ import absolute_import
import unittest

import lumberjack

import logging
import elasticsearch
import sys
import time
from random import randint

from .common import LumberjackTestCase

LOGGER_NAME = 'test'
LOGGER_CHILD_NAME = 'test.child'


class LogTestCase(LumberjackTestCase):
    def setUp(self):
        super(LogTestCase, self).setUp()
        self.getLumberjackObject()

        self.logger = logging.getLogger(LOGGER_NAME)
        self.child_logger = logging.getLogger(LOGGER_CHILD_NAME)

        self.handler = self.lj.get_handler()
        self.logger.addHandler(self.handler)

    def tearDown(self):
        self.logger.handlers = []
        self.deleteIndices()

    def test_log_not_dynamic(self):
        schema = {
            'dynamic': 'strict',
            '_source': {'enabled': True},
            'properties': {
                'a': {
                    'type': 'string',
                    'index': 'analyzed',
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
        self.lj.register_schema(schema=schema, logger=LOGGER_NAME)
        self._test_log(log_dict={
            'a': 'mice rice right across the page',
            'b': 24
        })
        res = self.elasticsearch.search(
            index=self.config['index_prefix'] + '*', doc_type=LOGGER_NAME,
            body={
                'query': {
                    'match': {
                        'a': 'rice'
                    }
                }
            })
        self.assertEqual(res['hits']['total'], 1)

    def test_log_dynamic(self):
        self._test_log()

    def _test_log(self, level=logging.ERROR, log_dict={'a': 1, 'b': 2}):
        self.logger.log(level, log_dict)

        # Blocking flush
        self.lj.action_queue._flush()

        # ES is *near*-realtime
        time.sleep(2)

        musts = []
        # Build query
        for (k, v) in log_dict.items():
            musts.append({'match': {k: v}})
        musts.append({'match': {'level': level}})

        res = self.elasticsearch.search(
            index=self.config['index_prefix'] + '*', doc_type=LOGGER_NAME,
            body={
                'query': {
                    'bool': {
                        'must': musts
                    }
                }
            })
        self.assertGreater(res['hits']['total'], 0)
