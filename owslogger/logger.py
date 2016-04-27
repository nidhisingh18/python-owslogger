"""
Logging
=======

The logging library provides the handler that sends the logs to a regular HTTPS
provider (in our case we use Loggly). The message is also formatted in a
specific format (json), which includes fields that are specific to the Orchard,
such as the service name, the correlation id.
"""

import datetime
import logging
import logging.handlers
import traceback

from requests_futures.sessions import FuturesSession


LEVELS = {
    100: 'DEBUG',
    200: 'INFO',
    250: 'NOTICE',
    300: 'WARNING',
    400: 'ERROR',
    500: 'CRITICAL'
}

session = FuturesSession()


def setup(
        dsn, environment, logger_name, logger_level, service_name,
        service_version, correlation_id=None):
    """Setup logging.

    If the correlation id is provided, this will create a logger (if not
    already created) and an adapter.

    Args:
        dsn (str): the data source name.
        environment (str): the application's environment.
        logger_name (str): name of the logger.
        logger_level (str): logging level of the logger.
        service_name (str): the service name.
        service_version (str): the service version.
        correlation_id (str or int): optional correlation id.

    Returns:
        Logger: the logger
    """

    current_logger = logging.getLogger(logger_name)
    current_logger.setLevel(logger_level)
    configure_handler(
        current_logger, dsn, environment, service_name, service_version)

    if correlation_id:
        context = dict(correlation_id=correlation_id)
        return OwsLoggingAdapter(current_logger, context)

    return current_logger


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
    """Custom DSN handler.

    Custom DSN handler that sends a JSON payload complying with OWS1
    standard.
    """

    def __init__(self, dsn, environment, service_name, service_version):
        """Constructor of HTTPSHandler.

        Args:
            dsn (str): the full dsn to send the log to.
            environment (str): the current environment.
            service_name (str): the service name.
            service_version (str): the service version.

        Returns:
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
            level_name, level_number = get_standard_level_from_record(record)

            # Calculate the timestamp.
            local_date = datetime.datetime.fromtimestamp(record.created)
            utc_delta = datetime.datetime.utcnow() - datetime.datetime.now()
            utc_date = local_date + utc_delta

            payload = {
                'tag': 'ows1',
                'timestamp': utc_date.isoformat(),
                'level': level_number,
                'level_name': level_name,
                'correlation_id': str(record.correlation_id),
                'message': self.get_full_message(record),
                'resources': getattr(record, 'resources', {}),
                'service': self.service_name,
                'service_version': self.service_version,
                'environment': self.environment,
                'meta': {
                    'file_name': record.filename,
                    'function_name': record.funcName,
                    'line': record.lineno
                }
            }

            session.post(self.dsn, json=payload, background_callback=callback)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class OwsLoggingAdapter(logging.LoggerAdapter):
    """Custom class for Adapters.

    The default adapter doesn't allow to pass in an extra field on logging,
    which is used in our case to append labels to messages.
    """

    def process(self, msg, kwargs):
        """Process the logging message and keyword arguments passed in.

        The main method just sets the extra fields to be equal to self.extra.
        So if we need to provide local data as part of the context, we can't
        (it will be removed as part of the override).

        Args:
            msg (obj): the log messge.
        """

        extra = dict(resources=kwargs.pop('resources', {}))
        extra.update(self.extra)
        kwargs.update(extra=extra)
        return msg, kwargs


def get_standard_level_from_record(record):
    """Get standard level from a log record.

    This methods takes the information from the LogRecord and return a two
    value tuple which contains the level name and level number.

    Args:
        record (LogRecord): the record of the level.

    Returns:
        tuple: contains the level name (str) and the level number (int).
    """

    # python levels are in 10 ... 50, we need them in the hundred.
    value = record.levelno * 10
    if value < 100:
        value = 100
    if value > 500:
        value = 500
    return LEVELS.get(value, ''), value
