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

import logging
import sys
import unittest
import lumberjack
from random import randint

HOSTS = [{'host': 'localhost', 'port': 9199}]
INDEX_PREFIX = 'test-lumberjack-'
ES_LOGLEVEL = logging.CRITICAL
FUTURES_LOGLEVEL = logging.CRITICAL

class LumberjackTestCase(unittest.TestCase):
    def setUp(self):
        self.index_prefix = INDEX_PREFIX + str(randint(0, 2**30)) + '-'

        stderrHandler = logging.StreamHandler(stream=sys.stderr)
        stderrHandler.setLevel(ES_LOGLEVEL)

        es_logger = logging.getLogger('elasticsearch')
        es_logger.addHandler(stderrHandler)

    def getLumberjackObject(self):
        self.lj = lumberjack.Lumberjack(hosts=HOSTS,
                                        index_prefix=self.index_prefix)
        self.elasticsearch = self.lj.elasticsearch

    def deleteIndices(self, elasticsearch=None):
        if elasticsearch is None:
            elasticsearch = self.lj.elasticsearch
        elasticsearch.indices.delete(index=self.index_prefix + '*')
