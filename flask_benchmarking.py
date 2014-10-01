from flask import Flask
app = Flask(__name__)

import lumberjack
from elasticsearch import Elasticsearch
import logging
import sys
from time import time
from flask import request

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
    lj = lumberjack.Lumberjack(
        index_prefix='flask-benchmark-',
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
