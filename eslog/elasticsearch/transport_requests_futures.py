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

from elasticsearch import Transport
from elasticsearch.exceptions import ImproperlyConfigured
from .http_requests_futures import RequestsFuturesHttpConnection

#from futures import Future

import logging

class RequestsFuturesTransport(Transport):
    u"""Transport class for use with RequestsFuturesHttpConnection.

    This manages dead connections with callbacks instead of
    synchronicity.

    Sniffing new hosts from the cluster is not implemented, so you
    should provide all the hosts you want to connect to explicitly.

    """

    def __init__(self, hosts, connection_class, *args, **kwargs):
        if not issubclass(connection_class, RequestsFuturesHttpConnection):
            logging.getLogger(__name__).warn(
                "%s should not be used with a connection_class other than "
                "RequestsFuturesHttpConnection", str(self.__class__))
        super(RequestsFuturesTransport, self).__init__(hosts, connection_class,
                                                       *args, **kwargs)


    def sniff_hosts(self):
        u"""Method not (yet) implemented."""
        pass

    ## This method is based heavily on
    ## elasticsearch.transport.Transport.perform_request, which is
    ## part of the elasticsearch-py package.

    ## Elasticsearch-py is copyright 2013 Elasticsearch, and this
    ## modification is under the terms of the Apache License, Version
    ## 2.0, as found at <http://www.apache.org/licenses/LICENSE-2.0>.
    def perform_request(self, method, url, params=None, body=None, depth=0,
                        last_error=None, callback=None):
        if body is not None:
            body = self.serializer.dumps(body)

            # some clients or environments don't support sending GET with body
            if method == 'GET' and self.send_get_body_as != 'GET':
                # send it as post instead
                if self.send_get_body_as == 'POST':
                    method = 'POST'

                # or as source parameter
                elif self.send_get_body_as == 'source':
                    if params is None:
                        params = {}
                    params['source'] = body
                    body = None

        if body is not None:
            try:
                body = body.encode('utf-8')
            except (UnicodeDecodeError, AttributeError):
                # bytes/str - no need to re-encode
                pass

        ignore = ()
        timeout = None
        if params:
            timeout = params.pop('request_timeout', None)
            ignore = params.pop('ignore', ())
            if isinstance(ignore, int):
                ignore = (ignore, )

        ## TODO: What if last_error is None?
        if depth > self.max_retries:
            raise last_error

        connection = self.get_connection()
        future = connection.perform_request(method, url, params, body,
                                            ignore=ignore, timeout=timeout)

        def wrapper_callback(future):
            exception = future.exception()
            if exception is not None:
                self.mark_dead(connection)
                self.perform_request(method, url, params, body, (depth+1),
                                     last_error=exception, callback=callback)
            else:
                res = future.result()
                callback(result)

        future.add_done_callback(wrapper_callback)

        ## Hack: Bulk operations need particular things to be returned here.
        return 0, {'items': []}


