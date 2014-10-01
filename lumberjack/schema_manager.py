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

import logging
from elasticsearch import NotFoundError

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

class SchemaManager(object):
    schemas = None
    elasticsearch = None
    index_prefix = None

    default_base_mapping = None
    default_types_properties = None
    default_index_settings = None

    def __init__(self, elasticsearch, index_prefix, default_base_mapping=None,
                 default_types_properties=None, default_index_settings=None):
        self.elasticsearch = elasticsearch
        self.schemas = {}
        self.index_prefix = index_prefix

        self.default_base_mapping = default_base_mapping \
            if default_base_mapping is not None \
            else DEFAULT_BASE_MAPPING

        self.default_types_properties = default_types_properties \
            if default_types_properties is not None \
            else DEFAULT_TYPES_PROPERTIES

        self.default_index_settings = default_index_settings \
            if default_types_properties is not None \
            else DEFAULT_INDEX_SETTINGS

    def register_schema(self, logger, schema):
        u"""Take a new schema and add it to the roster.

        This also automatically parses the schema into a mapping and
        adds it into the appropriate index template in Elasticsearch.

        """
        self.schemas[logger] = schema
        self._update_index_templates()

    def _update_index_templates(self):
        u"""Parse schemas into mappings and insert into Elasticsearch.

        Puts mappings into Elasticsearch templates.  Should also
        update mappings in existing indices, but this is currently
        broken.

        """
        mappings = self._build_mappings()
        template = {
            'template': self.index_prefix + '*',
            'settings': self.default_index_settings,
            'mappings': mappings
        }
        logging.getLogger(__name__).debug('Registering a new template.')
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

    def _build_mappings(self):
        u"""Parses the schemas into Elasticsearch mappings."""

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
