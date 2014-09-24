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

from elasticsearch import TransportError, NotFoundError
from elasticsearch.helpers import bulk
import logging


DEFAULT_BASE_MAPPING = {
    #'dynamic': 'strict',
    '_source': {'enabled': False},
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
}

DEFAULT_TYPES_PROPERTIES = {
    'string': {
        'index': 'not_analyzed',
        'norms': {'enabled': False}
    },
    'date': {
        'format': 'dateOptionalTime'
    }
}

## TODO: put this in a config option
DEFAULT_INDEX_SETTINGS = {
    'number_of_shards': 6,
    'number_of_replicas': 1
}

## Wraps an Elasticsearch instance, maintaining schemas etc.
class ElasticsearchContext(object):
    elasticsearch = None
    schemas = None
    index_prefix = None
    queue = None

    default_base_mapping = None
    default_types_properties = None
    default_index_settings = None
    max_queue_length = None

    def __init__(self, elasticsearch, index_prefix='generic-logging-',
                 default_base_mapping=None, default_types_properties=None,
                 default_index_settings=None, max_queue_length=None):
        self.elasticsearch = elasticsearch
        self.schemas = {}
        self.index_prefix = index_prefix
        self.queue = []

        self.default_base_mapping = default_base_mapping \
            if default_base_mapping is not None \
            else DEFAULT_BASE_MAPPING

        self.default_types_properties = default_types_properties \
            if default_types_properties is not None \
            else DEFAULT_TYPES_PROPERTIES

        self.default_index_settings = default_index_settings \
            if default_types_properties is not None \
            else DEFAULT_INDEX_SETTINGS

        self.max_queue_length = max_queue_length

    ## TODO: move this to ESLog
    def register_schema(self, logger, schema):
        self.schemas[logger] = schema
        self._update_index_templates()

    def queue_index(self, suffix, doc_type, body):
        ## TODO: async
        action = {
            '_op_type': 'index',
            '_index': self.index_prefix + suffix,
            '_type': doc_type,
            '_source': body
        }
        self.queue.append(action)
        logging.getLogger(__name__) \
            .debug('Put an action in the queue. qlen = %d, doc_type = %s',
                   len(self.queue), doc_type)

        ## TODO: move this into ES itself
        if doc_type not in self.schemas:
            self.register_schema(doc_type, {
                ## TODO: fix this
                'dynamic': 'default'
            })

        if self.max_queue_length is not None and \
            len(self.queue) >= self.max_queue_length:
            self.flush()

    def flush(self):
        try:
            bulk(self.elasticsearch, self.queue)
            self.queue = []
            #logging.getLogger(__name__).debug('Flushed the queue.')
            #self.es.index(index = index, *args, **kwargs)
        except TransportError, exception:
            logging.getLogger(__name__).error(
                'Error in flushing queue.',
                exc_info=exception)

    def _update_index_templates(self):
        mappings = self._build_mappings()
        template = {
            'template': self.index_prefix + '*',
            'settings': self.default_index_settings,
            'mappings': mappings
        }
        #logging.getLogger(__name__).debug('Registering a new template.')
        self.elasticsearch.indices.put_template(
            name=self.index_prefix + '*',
            body=template
        )
        # Try to update existing things.
        ## TODO: fix this
        for (doc_type, mapping) in mappings.items():
            try:
                self.elasticsearch.indices.put_mapping(
                    index=self.index_prefix + '*',
                    doc_type=doc_type,
                    body=mapping
                )
            except NotFoundError:
                pass

    ## TODO: investigate using setdefault
    def _build_mappings(self):
        mappings = {}
        for (type_name, schema) in self.schemas.items():
            this_mapping = self.default_base_mapping.copy()
            working_schema = schema.copy()

            # Combine the unprocessed properties into this_mapping.
            if 'properties' in working_schema:
                this_mapping['properties'].update(schema['properties'])
                # So we don't overwrite this_mapping['properties'] later
                del working_schema['properties']

            # Expand the fields in this_mapping['properties'] based on type.
            expanded_properties = {}
            for (field_name, field_info) in this_mapping['properties'].items():
                expanded_properties[field_name] = {}

                if ('type' in field_info and
                        field_info['type'] in
                        self.default_types_properties):
                    expanded_properties[field_name].update(
                        self.default_types_properties[field_info['type']])

                expanded_properties[field_name].update(field_info)

            # Put the expanded properties into the mapping for this type.
            this_mapping['properties'] = expanded_properties

            # Overwrite the defaults where applicable.
            this_mapping.update(working_schema)

            mappings[type_name] = this_mapping
        return mappings
