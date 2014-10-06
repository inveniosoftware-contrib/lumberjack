# -*- coding: utf-8 -*-
#
# This file is part of Lumberjack.
# Copyright (C) 2014 CERN.
#
# Lumberjack is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Lumberjack is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Lumberjack; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Provide the ActionQueue class."""

from __future__ import absolute_import

from elasticsearch import ElasticsearchException, TransportError
from elasticsearch.helpers import bulk
from threading import Thread, Event, Lock
import traceback
import logging

LOG = logging.getLogger(__name__)


class ActionQueue(Thread):

    """Hold a queue of actions and a thread to bulk-perform them.

    This is instantiated automatically by the ``lumberjack.Lumberjack`` object.
    It will keep a queue of indexing actions to be performed in Elasticsearch,
    and perform them bulk ('flush') when one of three things happens:

    1. It has waited ``interval`` seconds without flushing, or

    2. The length of the queue has exceeded ``max_queue_length``, or

    3. A flush is triggered manually.

    :note: You should not need to instantiate, or even interact with, this
        yourself.  It is intended to be wrapped by ``lumberjack.Lumberjack``.
        If you do, for some reason, use this yourself, it is a subclass of
        ``threading.Thread``, so you should call its ``start()`` method after
        initialisation.

    :param elasticsearch: The ``elasticsearch.Elasticsearch`` object on which
        to perform the bulk indexing.

    :param index_prefix: The prefix of the indices to be created in
        Elasticsearch.

    :param max_queue_length: The maximum length the queue can reach before a
        flush is triggered automaticall.

    :param interval: The maximum time that can elapse between automatic
        flushes.

    """

    def __init__(self, elasticsearch, config):
        super(ActionQueue, self).__init__()

        self.elasticsearch = elasticsearch
        self.config = config

        self.queue = []
        self.flush_event = Event()
        self.queue_lock = Lock()

        self.daemon = True

    def _flush(self):
        """Perform all actions in the queue.

        Uses elasticsearch.helpers.bulk, and empties the queue on success.
        Uses the ``self.queue_lock`` to prevent a race condition.

        """
        self.queue_lock.acquire(True)
        queue = list(self.queue)
        self.queue = []
        self.queue_lock.release()

        try:
            bulk(self.elasticsearch, queue)
        except TransportError as exception:
            LOG.error('Error in flushing queue.  Lost %d logs', len(queue),
                      exc_info=exception)
        else:
            LOG.debug('Flushed %d logs into Elasticsearch.', len(queue))
            self.flush_event.clear()

    def run(self):
        while True:
            try:
                self._flush()
                interval = self.config['interval']
                triggered = self.flush_event.wait(interval)
                if triggered:
                    LOG.debug('Flushing on external trigger.')
                else:
                    LOG.debug('Flushing after timeout of %.1fs.', interval)
            except ElasticsearchException as exc:
                traceback.print_exc(exc)
            except Exception as exc:
                LOG.error('Action queue thread terminated unexpectedly.')
                raise

    # These two methods to be called externally, i.e. from the main thread.
    # TODO: Consider refactoring.

    def trigger_flush(self):
        """Manually trigger a flush of the queue.

        This is to be called from the main thread, and fires an interrupt in
        the timeout of the main loop.  As such it is not guaranteed to
        immediately trigger a flush, only to skip the countdown to the next
        one.  This means the flush will happen the next time this thread gets
        switched to by the Python interpreter.

        """
        LOG.debug('Flush triggered; setting event object.')
        self.flush_event.set()

    def queue_index(self, suffix, doc_type, body):
        """Queue a new document to be added to Elasticsearch.

        If the queue becomes longer than self.max_queue_length then a flush is
        automatically triggered.

        :param suffix: The suffix of the index into which we should index the
            document.

        :param doc_type: The Elasticsearch type of the document to be indexed.
            Usually this should correspond to a registered schema in
            Lumberjack.

        :param body: The actual document contents, as a dict.

        """
        action = {
            '_op_type': 'index',
            '_index': self.config['index_prefix'] + suffix,
            '_type': doc_type,
            '_source': body
        }

        self.queue_lock.acquire(True)
        self.queue.append(action)
        self.queue_lock.release()

        LOG.debug('Put an action in the queue. qlen = %d, doc_type = %s',
                  len(self.queue), doc_type)

        # TODO: do default schema

        if self.config['max_queue_length'] is not None and \
                len(self.queue) >= self.config['max_queue_length']:
            LOG.debug('Hit max_queue_length.')
            self.trigger_flush()
