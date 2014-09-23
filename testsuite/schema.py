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

from __future__ import absolute_import
import unittest

import eslog

import logging
import elasticsearch
import sys
import time

from .common import HOSTS, INDEX_PREFIX, ES_LOGLEVEL

class SchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.esl = eslog.ESLog(hosts=HOSTS, index_prefix=INDEX_PREFIX)
        self.es = self.esl.context.elasticsearch
        
        l = logging.getLogger('elasticsearch')
        l.setLevel(ES_LOGLEVEL)
        l.addHandler(logging.StreamHandler(stream=sys.stderr))

    def tearDown(self):
        self.esl.context.elasticsearch.indices.delete(
            index=INDEX_PREFIX + '*')

    def test_register_schema(self):
        schema = {
            'dynamic': 'strict',
            '_source': {'enabled': True},
            'properties': {
                'a': {
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
        self.esl.register_schema('a_type', schema)

        # Test it's now in ES.
        res = self.es.get_template(id=INDEX_PREFIX + '*')
        assert res['mappings']['a_type'] == schema

def suite():
    suite = unittest.makeSuite(SchemaTestCase, 'test')
    return suite
