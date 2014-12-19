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

"""The default configuration for Lumberjack."""

from __future__ import absolute_import
from copy import deepcopy

DEFAULT_CONFIG = {
    'default_mapping': {
        '_source': {'enabled': True},
        '_all': {'enabled': False},
        '_ttl': {'enabled': True},
        'properties': {
            'message': {
                'type': 'string'
            },
            '@timestamp': {
                'type': 'date',
            },
            'level': {
                'type': 'integer'
            }
        }
    },
    'default_type_properties': {
        'string': {
            'index': 'not_analyzed',
            'norms': {'enabled': False}
        },
        'date': {
            'format': 'dateOptionalTime'
        }
    },
    'index_prefix': 'generic-logging-',
    'interval': 30,
    'max_queue_length': None,
    'fallback_log_file': '/tmp/lumberjack_fallback.log'
}


def get_default_config():
    """Get a copy of the default config.

    The copy can be modified in-place without affecting the default config
    itself.

    """
    return deepcopy(DEFAULT_CONFIG)
