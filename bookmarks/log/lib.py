import enum
import logging
import os
from collections import deque
from logging.handlers import RotatingFileHandler

from PySide2 import QtCore

from .. import common

__all__ = ['init_log', 'teardown_log', 'HandlerType', 'get_logging_level', 'set_logging_level', 'get_logger',
           'get_records', 'get_handler', 'clear_records', 'debug', 'info', 'warning', 'error', 'critical']

LOG_FORMAT = '%(asctime)s,%(msecs)d [%(levelname)s] [%(name)s] [thread.%(thread)d] >> %(message)s'
LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'

LOG_DIR = f'{QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.GenericDataLocation)}/{common.product}/log'
ERR_LOG_PATH = f'{LOG_DIR}/error.log'


class HandlerType(enum.Enum):
    Console = 1
    File = 2
    Memory = 3


HANDLERS = {
    HandlerType.Console: None,
    HandlerType.File: None,
    HandlerType.Memory: None,
}
LOGGERS = {}
LOGGING_LEVEL = logging.INFO

mutex = QtCore.QMutex()


class TankHandler(logging.Handler):
    """In-memory tank for storing recent logs."""

    def __init__(self, maxlen=1000):
        super().__init__()
        self._lock = QtCore.QMutex()
        self.records = deque(maxlen=maxlen)

    def emit(self, record):
        msg = self.format(record)
        self._lock.lock()
        try:
            self.records.append((record.levelno, msg))
        finally:
            self._lock.unlock()

    def get_records(self, level=logging.WARNING, remove=False):
        """Return logs at or above the specified level.

        By default, only returns logs without altering the tank.
        If remove=True, logs at or above level are removed from the tank.
        """
        self._lock.lock()
        try:
            filtered = [r[1] for r in self.records if r[0] >= level]
            if remove:
                self.records = deque([r for r in self.records if r[0] < level],
                                     maxlen=self.records.maxlen)
            return filtered
        finally:
            self._lock.unlock()


def init_log_handlers(max_bytes, maxlen, backup_count, init_memory=True, init_console=False, init_file=False):
    """Initialize module-level logging components."""
    global HANDLERS

    # Create the log directory if it doesn't exist
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)

    if any(h is not None for h in HANDLERS.values()):
        raise RuntimeError('Log handlers already initialized')

    if init_memory:
        HANDLERS[HandlerType.Memory] = TankHandler(maxlen=maxlen)
        HANDLERS[HandlerType.Memory].setLevel(logging.DEBUG)
        HANDLERS[HandlerType.Memory].setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATEFMT))
    else:
        HANDLERS[HandlerType.Memory] = logging.NullHandler()

    if init_console:
        HANDLERS[HandlerType.Console] = logging.StreamHandler()
        HANDLERS[HandlerType.Console].setLevel(logging.INFO)
        HANDLERS[HandlerType.Console].setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATEFMT))
    else:
        HANDLERS[HandlerType.Console] = logging.NullHandler()

    if init_file:
        HANDLERS[HandlerType.File] = RotatingFileHandler(ERR_LOG_PATH, maxBytes=max_bytes, backupCount=backup_count)
        HANDLERS[HandlerType.File].setLevel(logging.ERROR)
        HANDLERS[HandlerType.File].setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATEFMT))
    else:
        HANDLERS[HandlerType.File] = logging.NullHandler()


def qt_message_handler(mode, context, message):
    """Redirect Qt messages to the appropriate logger."""
    if mode == QtCore.QtDebugMsg:
        debug('Qt', message)
    elif mode == QtCore.QtInfoMsg:
        debug('Qt', message)
    elif mode == QtCore.QtWarningMsg:
        warning('Qt', message)
    elif mode == QtCore.QtCriticalMsg:
        error('Qt', message)
    elif mode == QtCore.QtFatalMsg:
        critical('Qt', message)


def init_log(max_bytes=5 * 1024 * 1024, maxlen=1000, backup_count=3):
    init_log_handlers(max_bytes=max_bytes, maxlen=maxlen, backup_count=backup_count)

    logger = get_logger('Qt')
    logger.setLevel(LOGGING_LEVEL)

    QtCore.qInstallMessageHandler(qt_message_handler)


def teardown_log():
    """Remove all logging handlers."""
    global HANDLERS
    global LOGGERS

    for logger in LOGGERS.values():
        for handler in logger.handlers:
            logger.removeHandler(handler)

    for key in HANDLERS.keys():
        try:
            HANDLERS[key].close()
        except AttributeError:
            pass

        HANDLERS[key] = None

    LOGGERS.clear()


def get_logger(name):
    """Return a logger with the specified name."""
    if HANDLERS[HandlerType.Memory] is None:
        raise RuntimeError('Log handlers not initialized')

    if name not in LOGGERS:
        LOGGERS[name] = logging.getLogger(name)
        LOGGERS[name].addHandler(HANDLERS[HandlerType.Memory])
        LOGGERS[name].addHandler(HANDLERS[HandlerType.Console])
        LOGGERS[name].addHandler(HANDLERS[HandlerType.File])

        # Ensure the logger respects the global logging level
        LOGGERS[name].setLevel(LOGGING_LEVEL)
    return LOGGERS[name]


def get_records(level=logging.WARNING, remove=False):
    """Return and remove all warnings and errors from the in-memory tank."""
    if HANDLERS[HandlerType.Memory] is None:
        raise RuntimeError('Log handlers not initialized')

    return HANDLERS[HandlerType.Memory].get_records(level=level, remove=remove)


def clear_records():
    """Clear all records from the in-memory tank."""
    if HANDLERS[HandlerType.Memory] is None:
        raise RuntimeError('Log handlers not initialized')

    HANDLERS[HandlerType.Memory].records.clear()


def get_handler(handler_type):
    """Return the specified handler."""
    if handler_type not in HANDLERS:
        raise ValueError(f'Invalid handler type: {handler_type}, must be one of {list(HandlerType)}')
    return HANDLERS[handler_type]


def _thread_save_log(name, level, msg):
    logger = get_logger(name)

    if level < LOGGING_LEVEL:
        return

    mutex.lock()
    try:
        if level == logging.DEBUG:
            logger.debug(msg)
        elif level == logging.INFO:
            logger.info(msg)
        elif level == logging.WARNING:
            logger.warning(msg)
        elif level == logging.ERROR:
            logger.error(msg, exc_info=True)
        elif level == logging.CRITICAL:
            logger.critical(msg, exc_info=True)
        else:
            raise ValueError(f'Invalid log level: {level}, expected one of {list(logging._nameToLevel)}')

        try:
            # Emit a signal to update the log viewer
            common.signals.logRecordAdded.emit(name, level, msg)
        except AttributeError:
            # Signals might not be initialized yet
            pass

    finally:
        mutex.unlock()


def set_logging_level(level):
    """Update the global logging level.

    Args:
        level (int): The new logging level.

    """
    global LOGGING_LEVEL
    LOGGING_LEVEL = level

    if level == LOGGING_LEVEL:
        return

    # Update all existing loggers
    for logger in LOGGERS.values():
        logger.setLevel(LOGGING_LEVEL)


def get_logging_level():
    """Return the current logging level."""
    return LOGGING_LEVEL


def debug(name, msg):
    """Log a debug message."""
    _thread_save_log(name, logging.DEBUG, msg)


def info(name, msg):
    """Log an info message."""
    _thread_save_log(name, logging.INFO, msg)


def warning(name, msg):
    """Log a warning message."""
    _thread_save_log(name, logging.WARNING, msg)


def error(name, msg):
    """Log an error message."""
    _thread_save_log(name, logging.ERROR, msg)


def critical(name, msg):
    """Log a critical message."""
    _thread_save_log(name, logging.CRITICAL, msg)
