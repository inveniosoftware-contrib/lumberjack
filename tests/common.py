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

import logging
import sys
import unittest
import lumberjack
from random import randint

HOSTS = [{'host': 'localhost', 'port': 9199}]
INDEX_PREFIX = 'test-lumberjack-'
ES_LOGLEVEL = logging.ERROR
LJ_LOGLEVEL = logging.ERROR

LOG_FORMAT = "%(asctime)s %(name)s\t%(message)s"
DATE_FORMAT = "%c"


class LumberjackTestCase(unittest.TestCase):
    def setUp(self):
        self.index_prefix = INDEX_PREFIX + str(randint(0, 2**30)) + '-'

        # handler = logging.FileHandler('tests.log', mode='w')
        handler = logging.StreamHandler(stream=sys.stderr)
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)

        es_logger = logging.getLogger('elasticsearch')
        es_logger.setLevel(ES_LOGLEVEL)
        es_logger.handlers = []
        es_logger.addHandler(handler)

        lj_logger = logging.getLogger('lumberjack')
        lj_logger.setLevel(LJ_LOGLEVEL)
        lj_logger.handlers = []
        lj_logger.addHandler(handler)

    def getLumberjackObject(self):
        self.lj = lumberjack.Lumberjack(hosts=HOSTS,
                                        index_prefix=self.index_prefix)
        self.elasticsearch = self.lj.elasticsearch

    def deleteIndices(self, elasticsearch=None):
        if elasticsearch is None:
            elasticsearch = self.lj.elasticsearch
        elasticsearch.indices.delete(index=self.index_prefix + '*')
