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

"""Provides SchemaManager class."""

from __future__ import absolute_import

import logging
from elasticsearch import NotFoundError

class SchemaManager(object):

    """Manage the 'schemas' for different types of log data.

    A detailed description of schemas is given in the documentation for
    ``lumberjack.Lumberjack.register_schema``.

    This class manages a list of schemas registered and ensures that they are
    processed and passed into Elasticsearch as appropriate.

    :param elasticsearch: The ``elasticsearch.Elasticsearch`` object to
        register mappings and templates with.

    :param config: The Lumberjack config.  See the Configuration section in the
        docs for details.

    """

    def __init__(self, elasticsearch, config):
        """Init method.  See class docstring."""
        self.elasticsearch = elasticsearch
        self.schemas = {}

        self.config = config

    def register_schema(self, logger, schema):
        """Take a new schema and add it to the roster.

        This also automatically parses the schema into a mapping and adds it
        into the appropriate index template in Elasticsearch.

        :param logger: The name of the logger which the log data will be
            emitted on.

        :param schema: The schema data to be processed into a mapping.

        """
        self.schemas[logger] = schema
        self._update_index_templates()

    def _update_index_templates(self):
        """Parse schemas into mappings and insert into Elasticsearch.

        Put mappings into Elasticsearch templates.  Should also update mappings
        in existing indices, but this is currently broken.

        """
        mappings = self._build_mappings()
        template = {
            'template': self.config['index_prefix'] + '*',
            'settings': self.config['default_index_settings'],
            'mappings': mappings
        }
        logging.getLogger(__name__).debug('Registering a new template.')
        self.elasticsearch.indices.put_template(
            name=self.config['index_prefix'] + '*',
            body=template
        )
        # Try to update existing things.
        # TODO: fix this
        for (doc_type, mapping) in mappings.items():
            try:
                self.elasticsearch.indices.put_mapping(
                    index=self.config['index_prefix'] + '*',
                    doc_type=doc_type,
                    body=mapping
                )
            except NotFoundError:
                pass

    def _build_mappings(self):
        """Parse the schemas into Elasticsearch mappings."""
        mappings = {}
        for (type_name, schema) in self.schemas.items():
            this_mapping = self.config['default_mapping'].copy()
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
                        self.config['default_type_properties']):
                    expanded_properties[field_name].update(
                        self.config['default_type_properties'] \
                            [field_info['type']])

                expanded_properties[field_name].update(field_info)

            # Put the expanded properties into the mapping for this type.
            this_mapping['properties'] = expanded_properties

            # Overwrite the defaults where applicable.
            this_mapping.update(working_schema)

            mappings[type_name] = this_mapping
        return mappings
