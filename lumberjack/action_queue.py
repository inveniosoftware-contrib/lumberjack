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

from __future__ import absolute_import

from elasticsearch import ElasticsearchException
from elasticsearch.helpers import bulk
from threading import Thread, Event, Lock
import traceback
import logging

LOG = logging.getLogger(__name__)

class ActionQueue(Thread):
    interval = None
    max_queue_length = None
    elasticsearch = None
    index_prefix = None

    flush_event = None
    queue_lock = None
    queue = None

    def __init__(self, elasticsearch, index_prefix, max_queue_length,
                 interval):
        super(ActionQueue, self).__init__()

        self.elasticsearch = elasticsearch
        self.interval = interval
        self.max_queue_length = max_queue_length
        self.index_prefix = index_prefix

        self.queue = []
        self.flush_event = Event()
        self.queue_lock = Lock()
        
        self.daemon = True

    def _flush(self):
        u"""Perform all actions in the queue.

        Uses elasticsearch.helpers.bulk, and empties the queue on
        success.

        """

        self.queue_lock.acquire(True)
        queue = list(self.queue)
        self.queue = []
        self.queue_lock.release()

        try:
            bulk(self.elasticsearch, queue)
        except TransportError, exception:
            LOG.error('Error in flushing queue.  Lost %d logs', len(queue),
                      exc_info=exception)
        else:
            LOG.debug('Flushed %d logs into Elasticsearch.', len(queue))
            self.flush_event.clear()

    def run(self):
        while True:
            try:
                self._flush()
                interval = self.interval
                triggered = self.flush_event.wait(interval)
                if triggered:
                    LOG.debug('Flushing on external trigger.')
                else:
                    LOG.debug('Flushing after timeout of %.1fs.', interval)
            except ElasticsearchException, exc:
                traceback.print_exc(exc)
            except Exception, exc:
                LOG.error('Action queue thread terminated unexpectedly.')
                raise

    ## These two methods to be called externally, i.e. from the main thread.
    ## TODO: Consider refactoring.

    def trigger_flush(self):
        LOG.debug('Flush triggered; setting event object.')
        self.flush_event.set()

    def queue_index(self, suffix, doc_type, body):
        u"""Queue a new document to be added to Elasticsearch.

        If the queue becomes longer than self.max_queue_length then it
        is automatically flushed.

        """

        action = {
            '_op_type': 'index',
            '_index': self.index_prefix + suffix,
            '_type': doc_type,
            '_source': body
        }

        self.queue_lock.acquire(True)
        self.queue.append(action)
        self.queue_lock.release()

        LOG.debug('Put an action in the queue. qlen = %d, doc_type = %s',
                  len(self.queue), doc_type)

        ## TODO: do default schema

        if self.max_queue_length is not None and \
            len(self.queue) >= self.max_queue_length:
            LOG.debug('Hit max_queue_length.')
            self.trigger_flush()
