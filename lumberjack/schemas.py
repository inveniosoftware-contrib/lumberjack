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
from elasticsearch import NotFoundError, TransportError
from copy import deepcopy


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

        self.config = config

    def register_schema(self, logger, schema):
        """Take a new schema and add it to the roster.

        This also automatically parses the schema into a mapping and adds it
        into the appropriate index template in Elasticsearch.

        :param logger: The name of the logger which the log data will be
            emitted on.

        :param schema: The schema data to be processed into a mapping.

        """
        mapping = self._build_mapping(schema)

        template = {
            'template': self.config['index_prefix'] + '*',
            'mappings': {
                logger: mapping
            }
        }
        logging.getLogger(__name__).debug(
            'Registering a new template for %s.', logger)
        try:
            self.elasticsearch.indices.put_template(
                name='lumberjack-' + self.config['index_prefix'] +
                logger,
                body=template
            )
        except TransportError:
            logging.getLogger(__name__).warning(
                'Error putting new template in Elasticsearch: %s.',
                logger,
                exc_info=True)

        # Try to update existing things.
        try:
            self.elasticsearch.indices.put_mapping(
                index=self.config['index_prefix'] + '*',
                doc_type=logger,
                body=mapping
            )
        except NotFoundError:
            pass
        except TransportError:
            logging.getLogger(__name__).warning(
                'There was an error putting the new mapping on some ' +
                'indices.  If you try to log new data to these, you ' +
                'will see errors.',
                exc_info=True)

    def _build_mapping(self, schema):
        """Parse the schema into an Elasticsearch mapping."""
        # Shorthand
        default_type_props = self.config['default_type_properties']

        this_mapping = deepcopy(self.config['default_mapping'])
        working_schema = deepcopy(schema)

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
                    field_info['type'] in default_type_props):
                expanded_properties[field_name].update(
                    default_type_props[field_info['type']])

            expanded_properties[field_name].update(field_info)

        # Put the expanded properties into the mapping for this type.
        this_mapping['properties'] = expanded_properties

        # Overwrite the defaults where applicable.
        this_mapping.update(working_schema)

        return this_mapping
