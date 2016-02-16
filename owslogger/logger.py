"""
Logging
=======

The logging library provides the handler that sends the logs to a regular HTTPS
provider (in our case we use Loggly). The message is also formatted in a
specific format (json), which includes fields that are specific to the Orchard,
such as the service name, the correlation id.
"""

from flask import g
from flask import request
from functools import partial
from requests_futures.sessions import FuturesSession
import datetime
import logging
import logging.handlers
import socket
import traceback
import uuid


session = FuturesSession()


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

    logger = logging.getLogger(logger_name)
    logger.setLevel(logger_level)
    configure_handler(logger, dsn, environment, service_name, service_version)

    app.global_correlation_id = partial(global_correlation_id, logger)
    app.global_logger = partial(global_logger, logger)

    app.before_request(app.global_correlation_id)
    app.before_request(app.global_logger)


def configure_handler(logger, dsn, environment, service_name, service_version):
    """Configure the logger based on a provided DSN.

    Args:
        logger (Logger): the logger instance.
        dsn (str): the data source name.
        environment (str): the application's environment.
        service_name (str): the service name.
        service_version (str): the service version.
    """

    if dsn:
        logger.addHandler(
            DSNHandler(dsn, environment, service_name, service_version))
    else:
        logger.addHandler(
            logging.StreamHandler())


def callback(session, resp):
    """Post callback.

    When the post has been dispatched to loggly, handle the response (in our
    case we don't have anything to do).

    Args:
        session (FutureSession): the session that triggered the request.
        resp (object): the response of the request to the service.
    """

    pass


class DSNHandler(logging.Handler):

    def __init__(self, dsn, environment, service_name, service_version):
        """Constructor of HTTPSHandler.

        Args:
            dsn (str): the full dsn to send the log to.
            environment (str): the current environment.
            service_name (str): the service name.
            service_version (str): the service version.

        Return:
            HTTPSHandler: the created handler.
        """

        logging.Handler.__init__(self)
        self.dsn = dsn
        self.environment = environment
        self.service_name = service_name
        self.service_version = service_version

    def get_full_message(self, record):
        """Get the full message for a record.

        Some of our systems might still require this data to be sent to loggly,
        so instead of sending the message of the record, we send the exception
        information.

        Args:
            record (LogRecord): the record to log.
        Return:
            mixed: the string or an object (dictionary).
        """

        if record.exc_info:
            return '\n'.join(traceback.format_exception(*record.exc_info))
        else:
            return record.msg

    def emit(self, record):
        """Emit a record.
        From the documentation: do whatever it takes to actually log the
        specified logging record. Here: we send it to the provider. The payload
        matches Orchard format.
        Args:
            record (LogRecord): the record to log.
        """

        try:
            payload = {
                'tag': 'ows1',
                'timestamp': datetime.datetime.fromtimestamp(
                    record.created).isoformat(),
                'level': record.levelname,
                'correlation_id': record.correlation_id,
                'message': self.get_full_message(record),
                'service': self.service_name,
                'service_version': self.service_version,
                'environment': self.environment,
                'meta': {
                    'file_name': record.filename,
                    'function_name': record.funcName,
                    'line': record.lineno
                }
            }
            session.post(self.dsn, data=payload, background_callback=callback)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def global_correlation_id(logger):
    """Global correlation id.

    The correlation id is either provided by the request, and if not, it is
    created by the service and used whenever a call is made to another system.
    We are using flask.g, since Flask is thread safe.

    Args:
        logger (Logger): the app logger.

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

    global_logger(logger)
    g.log.info(message)


def global_logger(logger):
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

    global_correlation_id(logger)
    context = dict(correlation_id=g.correlation_id)
    g.log = logging.LoggerAdapter(logger, context)
