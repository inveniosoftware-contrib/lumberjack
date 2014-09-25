# -*- coding: utf-8 -*-
##
## This file is part of ESLog.
## Copyright (C) 2014 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

import logging
import sys
import unittest
import eslog
from random import randint

HOSTS = [{'host': 'localhost', 'port': 9199}]
INDEX_PREFIX = 'test-eslog-'
ES_LOGLEVEL = logging.CRITICAL
FUTURES_LOGLEVEL = logging.CRITICAL

class ESLogTestCase(unittest.TestCase):
    def setUp(self):
        self.index_prefix = INDEX_PREFIX + str(randint(0, 2**30)) + '-'

        stderrHandler = logging.StreamHandler(stream=sys.stderr)

        es_logger = logging.getLogger('elasticsearch')
        es_logger.setLevel(ES_LOGLEVEL)
        es_logger.addHandler(stderrHandler)

        futures_logger = logging.getLogger('concurrent.futures')
        futures_logger.setLevel(FUTURES_LOGLEVEL)
        futures_logger.addHandler(stderrHandler)

    def getESLogObject(self):
        self.esl = eslog.ESLog(hosts=HOSTS,
                               index_prefix=self.index_prefix)
        self.es = self.esl.context.elasticsearch

    def deleteIndices(self, elasticsearch=None):
        if elasticsearch is None:
            elasticsearch = self.esl.context.elasticsearch
        elasticsearch.indices.delete(index=self.index_prefix + '*')
