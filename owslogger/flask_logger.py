"""
Flask Logging
=============

Util to quickly and easily setup logging on any flask application by calling
one single method: `setup`. Example::

    from flask import Flask
    from owslogger import flask_logger

    app = Flask(__name__)
    flask_logger.setup(
        app, 'https://logglyurl', 'dev', 'logger_name', logging.INFO,
        'service_name', '1.0.0')
"""

from flask import g
from flask import request
from functools import partial
import logging
import uuid

from owslogger import logger


def setup(
        app, dsn, environment, logger_name, logger_level, service_name,
        service_version):
    """Setup logging for the flask application.

    Args:
        app (Flask): the application to add logging to.
        dsn (str): the data source name.
        environment (str): the application's environment.
        logger_name (str): name of the logger.
        logger_level (str): logging level of the logger.
        service_name (str): the service name.
        service_version (str): the service version.
    """

    current_logger = logger.setup(
        dsn, environment, logger_name, logger_level, service_name,
        service_version)

    app.global_correlation_id = partial(global_correlation_id, current_logger)
    app.global_logger = partial(global_logger, current_logger)

    app.before_request(app.global_correlation_id)
    app.before_request(app.global_logger)


def global_correlation_id(current_logger):
    """Global correlation id.

    The correlation id is either provided by the request, and if not, it is
    created by the service and used whenever a call is made to another system.
    We are using flask.g, since Flask is thread safe.

    Args:
        current_logger (Logger): the app logger.

    Return:
        str: the correlation id.
    """

    if hasattr(g, 'correlation_id'):
        return g.correlation_id

    g.correlation_id = request.headers.get('Correlation-Id')
    if not g.correlation_id:
        g.correlation_id = str(uuid.uuid1())
        message = (
            'Correlation-Id ({id}) created.'.format(id=g.correlation_id))
    else:
        message = (
            'Correlation-Id ({id}) received.'.format(id=g.correlation_id))

    global_logger(current_logger)
    g.log.info(message)


def global_logger(current_logger):
    """Global logger

    The global logger is used everywhere through the application. It formats
    the logs following our standards and it attaches additional information
    such as the correlation id.

    Code sample:

        from flask import g

        @app.route('/')
        def homepage():
            g.log.info('User has hit the homepage')

    Args:
        logger (Logger): the application logger.
    """

    global_correlation_id(current_logger)
    context = dict(correlation_id=g.correlation_id)
    g.log = logger.OwsLoggingAdaptor(current_logger, context)
