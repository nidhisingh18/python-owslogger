from datetime import datetime
from flask import Flask
from flask import g
from unittest.mock import Mock
from unittest.mock import patch
import logging
import pytest
import uuid

from owslogger import logger
from sample import app


def test_handler_creation():
    """Test the creation of the handler.
    """

    dsn = 'dsn value'
    environment = 'qa'
    service_name = 'service_name'
    service_version = '1.0.0'
    handler = logger.DSNHandler(dsn, environment, service_name, service_version)
    assert handler.dsn == dsn
    assert handler.environment == environment
    assert handler.service_name == service_name
    assert handler.service_version == service_version


def test_get_full_message():
    """Test getting a full message.
    """

    record = Mock()
    message = 'Message'
    record.msg = message
    record.levelno = 10
    record.exc_info = None
    handler = logger.DSNHandler('dsn', 'qa', 'logging', '1.0.0')
    assert handler.get_full_message(record) == message


@patch('traceback.format_exception')
def test_get_full_message_with_exception(trace):
    """Test getting message from exception
    """

    record = Mock()
    record.levelno = 50
    record.exc_info = ['one', 'two']
    trace.return_value = ['trace', 'two']
    handler = logger.DSNHandler('dsn', 'qa', 'logging', '1.0.0')
    assert handler.get_full_message(record)
    trace.assert_called_once_with('one', 'two')


@patch('owslogger.logger.session')
def test_session_post_called_on_message_emit(session):
    """Test session post called when a message is emitted.
    """

    record = Mock()
    message = 'Message'
    correlation_id = uuid.uuid1()
    record.levelno = 10
    record.msg = message
    record.created = datetime.now().timestamp()
    record.exc_info = None
    record.correlation_id = correlation_id
    handler = logger.DSNHandler('dsn', 'qa', 'logging', '1.0.0')
    handler.emit(record)
    assert session.post.called


@patch('owslogger.logger.session')
def test_emit_message_on_post_failure(session):
    """Test emiting a message with the session post triggering an exception.
    """

    # SystemExit won't be an error that will be throw, it will just
    # be an exception. To test this is
    session.post = Mock(side_effect=SystemExit())

    record = Mock()
    record.msg = 'Message'
    record.levelno = 10
    record.created = datetime.now().timestamp()
    record.exc_info = None
    record.correlation_id = uuid.uuid1()
    handler = logger.DSNHandler('dsn', 'qa', 'logging', '1.0.0')

    with pytest.raises(SystemExit):
        handler.emit(record)


@patch('owslogger.logger.session')
def test_emit_message_with_normal_exception(session):
    """Test emiting a message with a normal exception thrown from post request.
    """

    session.post = Mock(side_effect=Exception())

    record = Mock()
    record.msg = 'Message'
    record.levelno = 10
    record.exc_info = None
    record.correlation_id = uuid.uuid1()
    handler = logger.DSNHandler('dsn', 'qa', 'logging', '1.0.0')
    handler.handleError = Mock()
    handler.emit(record)
    handler.handleError.assert_called_with(record)


def test_configure_handler_without_dsn():
    """Test configuration of the handler.
    """

    current_logging = logging.getLogger('test_logger')
    logger.configure_handler(current_logging, '', 'qa', 'logging', '1.0.0')
    assert isinstance(current_logging.handlers[0], logging.StreamHandler)


def test_setting_up_flask_app():
    """Test setting up a flask application.
    """

    app = Flask(__name__)
    logger.setup(app, '', 'qa', 'logging', logging.INFO, 'service',  '1.0.0')


def test_configure_handler_with_dsn():
    """Test configuration of the handler.
    """

    current_logging = logging.getLogger('test_logger_with_dsn')
    logger.configure_handler(current_logging, 'dsn', 'qa', 'logging', '1.0.0')
    assert isinstance(current_logging.handlers[0], logger.DSNHandler)
    assert current_logging.handlers[0].dsn == 'dsn'


def test_app_correlation_id_creation():
    """Test creation of the correlation id.
    """

    with app.test_request_context('/hello/'):
        app.global_correlation_id()
        assert g.correlation_id


def test_app_correlation_id_reuse():
    """Test correlation id reuse.

    When passed from the header, the correlation id should be reused.
    """

    correlation_id = str(uuid.uuid1())
    with app.test_request_context(
            '/hello/', headers={'Correlation-Id': correlation_id}):
        app.global_correlation_id()
        assert g.correlation_id == correlation_id


def test_logger_creation():
    """Test creation of the logger.
    """

    with app.test_request_context('/hello/'):
        app.global_logger()
        assert g.correlation_id
        assert isinstance(g.log, logging.LoggerAdapter)
        assert 'correlation_id' in g.log.extra
        assert g.log.extra.get('correlation_id') == g.correlation_id


@pytest.mark.parametrize(('level', 'expected'), [
    (10, ('INFO', 100)),
    (20, ('DEBUG', 200)),
    (25, ('NOTICE', 250)),
    (30, ('WARNING', 300)),
    (40, ('ERROR', 400)),
    (50, ('CRITICAL', 500)),
    (1, ('INFO', 100)),
    (600, ('CRITICAL', 500))
])
def test_get_standard_level_from_record(level, expected):
    """Test the standardization of the python levels.
    """

    record = Mock()
    record.levelno = level
    response = logger.get_standard_level_from_record(record)
    assert response == expected
