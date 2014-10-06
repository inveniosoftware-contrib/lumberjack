from __future__ import absolute_import

DEFAULT_CONFIG = {
    'default_mapping': {
        '_source': {'enabled': True},
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
    },
    'default_type_properties': {
        'string': {
            'index': 'not_analyzed',
            'norms': {'enabled': False}
        },
        'date': {
            'format': 'dateOptionalTime'
        }
    },
    'default_index_settings': {
        'number_of_shards': 6,
        'number_of_replicas': 1
    },
    'index_prefix': 'generic-logging-',
    'interval': 30,
    'max_queue_length': None
}
