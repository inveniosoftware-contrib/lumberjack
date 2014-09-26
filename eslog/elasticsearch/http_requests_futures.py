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

## This file is based heavily on
## elasticsearch.connection.http_requests, which is part of the
## elasticsearch-py package.

## Elasticsearch-py is copyright 2013 Elasticsearch, and this
## modification is under the terms of the Apache License, Version 2.0,
## as found at <http://www.apache.org/licenses/LICENSE-2.0>.

from __future__ import absolute_import

import time
try:
    from requests_futures import sessions
    REQUESTS_FUTURES_AVAILABLE = True
except ImportError:
    REQUESTS_FUTURES_AVAILABLE = False

## TODO: assuming python 2
from futures import ThreadPoolExecutor

from elasticsearch import Connection
from elasticsearch.compat import urlencode
from elasticsearch.exceptions import ImproperlyConfigured

class RequestsFuturesHttpConnection(Connection):
    """Connection using the `requests_futures` library.

    You should only use this with the RequestsFuturesTransport, since
    the default Transport class expects synchronicity to determine
    which connections are still alive.

    :arg http_auth: optional http auth information as either ':' separated
        string or a tuple
    :arg use_ssl: use ssl for the connection if `True`

    """
    def __init__(self, host='localhost', port=9200, http_auth=None,
                 use_ssl=False, max_workers=2, **kwargs):
        if not REQUESTS_FUTURES_AVAILABLE:
            raise ImproperlyConfigured("Please install requests_futures to "
                                       "use RequestsHttpConnection.")

        super(RequestsFuturesHttpConnection, self).__init__(host=host,
                                                            port=port,
                                                            **kwargs)
        self.session = sessions.FuturesSession(executor=ThreadPoolExecutor(
            max_workers=max_workers))
        if http_auth is not None:
            if not isinstance(http_auth, (tuple, list)):
                http_auth = http_auth.split(':', 1)
            http_auth = tuple(http_auth)
            self.session.auth = http_auth
        self.base_url = 'http%s://%s:%d%s' % (
            's' if use_ssl else '',
            host, port, self.url_prefix
        )


    def perform_request(self, method, url, params=None, body=None, timeout=None,
                        ignore=()):
        url = self.base_url + url
        if params:
            url = '%s?%s' % (url, urlencode(params or {}))

        start = time.time()
        return_future = self.session.request(method, url, data=body,
                                             timeout=timeout or self.timeout)

        ## Because we return the future object instead of a tuple of
        ## response data, this class doesn't work with the standard
        ## transport classes.
        return return_future
