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

# This file sets up a simple Flask server using lumberjack to log pageviews.
# It is intended to be used with a benchmarking tool, for example ``ab``.

from flask import Flask
app = Flask(__name__)

import lumberjack
from elasticsearch import Elasticsearch
import logging
import sys
from time import time
from flask import request
from copy import deepcopy

NAME = 'lumberjack-flask-bench'
logger = logging.getLogger(NAME)

logger_modA = logging.getLogger('some_module_A')

stderrHandler = logging.StreamHandler(stream=sys.stderr)

ljlogger = logging.getLogger('lumberjack')
ljlogger.setLevel(logging.ERROR)
ljlogger.addHandler(stderrHandler)

eslogger = logging.getLogger('elasticsearch')
eslogger.setLevel(logging.ERROR)
eslogger.addHandler(stderrHandler)

lj = None
def init():
    global lj
    config = lumberjack.get_default_config()
    config['index_prefix'] = 'flask-benchmark-'
    lj = lumberjack.Lumberjack(
        config=config,
        hosts=[{'host': 'localhost', 'port': 9199}])
    start_time = time()
    lj.register_schema(logger=NAME,
                       schema={
                            '_source': {'enabled': True},
                            'properties': {
                                'reqno': {'type': 'long'},
                                'ip': {'type': 'ip'},
                                'url': {'type': 'string'}
                            }
                        })
    lj.register_schema(logger='some_module_A',
                       schema={
                           '_source': {'enabled': True},
                           'properties': {
                               'title': {'type': 'string'},
                               'author': {'type': 'string'},
                               'uploader': {'type': 'string'}
                            }
                        })
    d_time = time() - start_time
    print('Registering took %.2fs' % d_time)

    lj.action_queue.max_queue_length = 500

    handler = lj.get_handler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

reqno = 0

@app.route('/')
def hello_world():
    global reqno
    logger.info({
        'reqno': reqno,
        'ip': request.remote_addr,
        'url': '/'
    })
    logger_modA.info({
        'title': 'Computing Machinery and Intelligence',
        'author': 'A.M. Turing',
        'uploader': 'dijkstra'
    })
    reqno += 1
    return 'Hello World!'

@app.route('/flush')
def flush():
    global lj
    lj.trigger_flush()
    return 'Flushed.'

if __name__ == '__main__':
    init()
    app.run(debug=True)
