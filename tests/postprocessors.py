# -*- coding: utf-8 -*-
#
# This file is part of Lumberjack.
# Copyright 2015 CERN.
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
import logging
from mock import MagicMock

import lumberjack

from .common import LumberjackTestCase, skipIfNotMock, TestHandler

LOGGER_NAME = 'test'


class MyException(Exception):
    pass


class PostprocessorsTestCase(LumberjackTestCase):
    def setUp(self):
        super(PostprocessorsTestCase, self).setUp()
        self.getLumberjackObject()

        self.logger = logging.getLogger(LOGGER_NAME)

        self.handler = self.lj.get_handler()
        self.logger.addHandler(self.handler)

    def tearDown(self):
        self.logger.handlers = []
        super(PostprocessorsTestCase, self).tearDown()

    def _disable_action_queue(self):
        """Stop the queue now so we don't call things twice accidentally"""
        self.lj.action_queue.running = False
        self.lj.action_queue.trigger_flush()
        self.lj.action_queue.join()

    def _check_source_in_queue(self, source):
        # We only ever call bulk with 2 positional arguments, so if this raises
        # a KeyError, we have bigger problems
        called_queue = self.lj.action_queue._bulk.call_args[0][1]
        self.assertEqual(len(called_queue), 1)

        queue_source = called_queue[0]['_source']
        for k, v in source.items():
            self.assertIn(k, queue_source)
            self.assertEqual(v, queue_source[k])

    @skipIfNotMock
    def test_postprocessors(self):
        self._disable_action_queue()

        postprocessor_return = {'a': 1, 'b': 2}
        postprocessor = MagicMock(return_value=postprocessor_return)

        data = {'a': 1}
        self.logger.info(data, {'postprocessors': [postprocessor]})
        self.lj.action_queue._flush()

        try:
            called_msg = postprocessor.call_args[0][0]
        except KeyError:
            self.fail('Postprocessor not called with right parameter: ' +
                repr(called_msg))
        except TypeError:
            self.fail('Postprocessor not called')
        else:
            for k, v in data.items():
                self.assertIn(k, called_msg)
                self.assertEqual(v, called_msg[k])

        self._check_source_in_queue(postprocessor_return)

    @skipIfNotMock
    def test_postprocessors_error(self):
        self._disable_action_queue()
        self.lj.action_queue._bulk = MagicMock()

        my_handler = TestHandler()
        logging.getLogger('lumberjack.actions').addHandler(my_handler)

        my_exception = MyException('This exception should be handled')
        postprocessor = MagicMock(
            side_effect=my_exception)

        data = {'a': 1}
        self.logger.info(data, {'postprocessors': [postprocessor]})
        try:
            self.lj.action_queue._flush()
        except MyException:
            self.fail('Uncaught exception in a postprocessor')
        finally:
            my_handler.assertLoggedWithException('lumberjack.actions', 'ERROR',
                'Postprocessor ' + repr(postprocessor) +
                ' raised an exception.', my_exception)

        self._check_source_in_queue(data)

    @skipIfNotMock
    def test_postprocessors_error_after_dict_mutation(self):
        def my_postprocessor(doc):
            doc['canary'] = 'shouldn\'t be here'
            raise MyException('This exception should be handled and logged')

        data = {'a': 1}
        self.logger.info(data, {'postprocessors': [my_postprocessor]})
        self.lj.action_queue._flush()

        queue_source = self.lj.action_queue._bulk.call_args[0][1][0]['_source']
        self.assertNotIn('canary', queue_source)

    @skipIfNotMock
    def test_geoip(self):
        from lumberjack.postprocessors import geoip
        from geoip import geolite2

        self._disable_action_queue()
        self.lj.action_queue._bulk = MagicMock()

        ip = '128.141.43.1'
        ip_lookup_data = geolite2.lookup(ip)
        geopoint = {
            'lat': ip_lookup_data.location[0],
            'lon': ip_lookup_data.location[1]
        }

        self.logger.info({'ip': ip},
            {'postprocessors': [geoip(field='ip')]})
        self.lj.action_queue._flush()

        self._check_source_in_queue({
            'ip': ip,
            'geoip': {
                'country_code': ip_lookup_data.country,
                'location': geopoint
            }
        })
