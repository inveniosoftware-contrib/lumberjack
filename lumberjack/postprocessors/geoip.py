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

"""Postprocessor to provide GeoIP lookup."""

from __future__ import absolute_import
from geoip import geolite2


def geoip(field='ip'):
    """Postprocessor to collect GeoIP data from an IP field in the log entry.

    :param field: The name of the field which contains the IP.
    """
    def _inner(doc):
        ip_data = geolite2.lookup(doc[field])
        if ip_data is not None:
            doc['geoip'] = {
                'country_code': ip_data.country,
                'location': {
                    'lat': ip_data.location[0],
                    'lon': ip_data.location[1]
                }
            }
        return doc
    return _inner
