Usage
=====

Since you're using Elasticsearch to store log data, you probably don't want to
just store messages as strings.  Good!  Lumberjack supports (and encourages)
logging dicts to be stored directly in Elasticsearch as JSON::

    a_logger.info({'message': 'User did something.',
                   'username': 'rory',
                   'uid': 23})

Note: the 'type' of the document in Elasticsearch is determined by the logger's
name.  For ``a_logger`` that's ``__name__``.  This means that it's a good idea
to register several sub-loggers, one for each type of event being logged, and
then attach the handler to the parent for all of them.

Schemas
-------

Lumberjack also abstracts away creating mappings and templates for your data.

Before you log any events, it's a good idea to tell Elasticsearch what kind of
data to expect in them.  To do this you use the ``register_schema`` method:

Schemas correspond closely with mappings in Elasticsearch, but are processed by
Lumberjack to include some sensible defaults.  An example schema might be::

    {
        '_source': True,
        'properties': {
            'ip_address': {'type': 'ip'},
            'user_id': {'type': 'long'},
            'username': {'type': 'string'}
        }
    }

This method should be called once per schema to register; it's probably a good
idea to call it at the same time as attaching your handler to a
``logging.Logger`` object.

A complete example
------------------

So now we've covered an introduction, basic usage and how to use schemas, let's
put it all together.

Suppose we are writing a web app, and we want to log logins and searches:

In the general initialisation we put::

    from logging import getLogger, INFO
    from lumberjack import Lumberjack

    lj = Lumberjack(hosts=[{'host': 'localhost', 'port': 9200}])

    # Register a schema for logins
    lj.register_schema('appname.login',
        {
            'properties': {
                'ip_address': {'type': 'ip'},
                'username': {'type': 'string'},
                'successful': {'type': 'boolean'},
                'attempt_number': {'type': 'short'}
            }
        })

    # Register a schema for searches
    lj.register_schema('appname.search',
        {
            'properties': {
                'ip_address': {'type': 'ip'},
                'query': {
                    'type': 'string',
                    'index': 'analyzed'
                }
            }
        })

    logger = getLogger('appname')
    handler = lj.get_handler()

    logger.addHandler(handler)
    logger.setLevel(INFO)

In the login handling function we put::

    from logging import getLogger

    logger = getLogger('appname.login')

    log_event = {'ip_address': some_ip_address_variable,
                 'username': the_username,
                 'successful': login_ok,
                 'attempt_number': attempt_number}
    logger.info(log_event)

And in the search handling function we put::

    from logging import getLogger

    logger = getLogger('appname.search')

    log_event = {'ip_address': some_ip_address_variable,
                 'query': query_string}
    logger.info(log_event)

Now we've integrated elasticsearch logging into our web application.

Next steps
----------

At the minimum, you should read the index prefixes bit of the Configuration
section.
