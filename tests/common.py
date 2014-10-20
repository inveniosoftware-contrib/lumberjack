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

import logging
import sys
import unittest
import lumberjack
from random import randint
from elasticsearch import NotFoundError
import time

HOSTS = [{'host': 'localhost', 'port': 9199}]
INDEX_PREFIX = 'test-lumberjack-'
ES_LOGLEVEL = logging.ERROR
LJ_LOGLEVEL = logging.ERROR

LOG_FORMAT = "%(asctime)s %(name)s\t%(message)s"
DATE_FORMAT = "%c"

MOCK = True

class LumberjackTestCase(unittest.TestCase):
    def setUp(self, config=None):
        if config is None:
            self.config = lumberjack.DEFAULT_CONFIG.copy()        
            self.config['index_prefix'] = (INDEX_PREFIX +
                                           str(randint(0, 2**30)) + '-')
        else:
            self.config = config

        # handler = logging.FileHandler('tests.log', mode='w')
        handler = logging.StreamHandler(stream=sys.stderr)
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)

        #es_logger = logging.getLogger('elasticsearch')
        #es_logger.setLevel(ES_LOGLEVEL)
        #es_logger.handlers = []
        #es_logger.addHandler(handler)

        #lj_logger = logging.getLogger('lumberjack')
        #lj_logger.setLevel(LJ_LOGLEVEL)
        #lj_logger.handlers = []
        #lj_logger.addHandler(handler)

        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.deleteIndices()
        if hasattr(self, 'lj'):
            self.lj.action_queue.running = False
            self.lj.interval = 0
            self.lj.action_queue.trigger_flush()
            self.lj.action_queue.join()
            if self.lj.action_queue.last_exception is not None:
                raise self.lj.action_queue.last_exception

    def getLumberjackObject(self):
        self.lj = lumberjack.Lumberjack(hosts=HOSTS, config=self.config)
        self.elasticsearch = self.lj.elasticsearch
        if MOCK:
            patchLumberjackObject(self.lj)

    def deleteIndices(self, elasticsearch=None):
        if not MOCK:
            if elasticsearch is None:
                elasticsearch = self.lj.elasticsearch
            elasticsearch.indices.delete(
                index=self.config['index_prefix'] + '*')
            try:
                elasticsearch.indices.delete_template(
                    name=self.config['index_prefix'] + '*')
            except NotFoundError:
                pass


class TestHandler(logging.Handler):
            def __init__(self):
                super(TestHandler, self).__init__()
                self.records = []

            def emit(self, record):
                self.format(record)
                self.records.append(record)

            def assertLastLog(self, name, levelname, message):
                assert len(self.records) > 0
                last_record = self.records[-1]
                assert last_record.name == name
                assert last_record.levelname == levelname
                assert last_record.message == message


def patchLumberjackObject(lj):
    def noop(*args, **kwargs):
        pass
    lj.action_queue.bulk = noop
    lj.elasticsearch.indices.put_mapping = noop
    lj.elasticsearch.indices.put_template = noop