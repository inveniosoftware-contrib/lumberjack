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
from .common import LumberjackTestCase, HOSTS, MOCK, patchLumberjackObject

import lumberjack
import elasticsearch

class APITestCase(LumberjackTestCase):
    def test_init_hosts(self):
        lj = lumberjack.Lumberjack(hosts=HOSTS,
                                   config=self.config)
        if MOCK: patchLumberjackObject(lj)

        self.assert_general_sanity(lj)
        self.assertEqual(lj.elasticsearch.transport.hosts, HOSTS)

    def test_init_es(self):
        es = elasticsearch.Elasticsearch(
            hosts=['esnode1', 'esnode2'],
            connection_class=elasticsearch.Connection)
        lj = lumberjack.Lumberjack(elasticsearch=es,
                                   config=self.config)
        if MOCK: patchLumberjackObject(lj)

        self.assert_general_sanity(lj)
        self.assertEqual(lj.elasticsearch.transport.connection_class,
                         elasticsearch.Connection)
        self.assertEqual(lj.elasticsearch, es)

    def test_init_warnings(self):
        with self.assertRaises(TypeError):
            lj = lumberjack.Lumberjack(config=self.config)

    def test_init_no_config(self):
        lj = lumberjack.Lumberjack(hosts=HOSTS)
        if MOCK: patchLumberjackObject(lj)

        self.assertEqual(lj.config, lumberjack.get_default_config())

    def assert_general_sanity(self, lj):
        self.assertEqual(lj.config, self.config)
        self.assertEqual(lj.schema_manager.config, self.config)
        self.assertEqual(lj.schema_manager.elasticsearch, lj.elasticsearch)
        self.assertEqual(lj.action_queue.config, self.config)
        self.assertEqual(lj.action_queue.elasticsearch, lj.elasticsearch)
        self.assertTrue(lj.action_queue.is_alive())
