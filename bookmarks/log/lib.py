"""Logging module for the app.

The module provides a logging system that can be used to log messages to the console, a file, and an in-memory tank.
The main logging functions are available from the parent module, `bookmarks.log`. For example:

.. code-block:: python

    import bookmarks.log as log
    log.debug(__name__, 'This is a debug message')


"""
import enum
import functools
import json
import logging
import os
import re
import threading
from collections import deque
from logging.handlers import RotatingFileHandler

from PySide2 import QtCore

__all__ = [
    'init_log',
    'init_log_handlers',
    'teardown_log',
    'HandlerType',
    'get_logging_level',
    'set_logging_level',
    'get_logger',
    'get_records',
    'get_handler',
    'clear_records',
    'debug',
    'info',
    'warning',
    'error',
    'critical',
    'save_tank_to_file',
    'get_log_dir',
    'get_err_log_path'
]

#: The current app logging level
LOGGING_LEVEL = logging.INFO

#: The format string for log messages.
LOG_FORMAT = '%(asctime)s,%(msecs)03d [%(levelname)s] [%(name)s] [thread.%(thread)d] >> %(message)s'
#: The date format string for log messages.
LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'

#: The regular expression pattern for parsing formatted log lines.
LOG_LINE_REGEX = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) "
    r"\[(?P<level>[A-Za-z]+)\] "
    r"\[(?P<name>.*?)\] "
    r"\[thread\.(?P<thread>\d+)\] >> "
    r"(?P<message>[\s\S]*)$",
    re.MULTILINE | re.DOTALL
)


class HandlerType(enum.Enum):
    """Logging handler types."""
    Console = 1
    File = 2
    Memory = 3


#: The log handler instances
HANDLERS = {
    HandlerType.Console: None,
    HandlerType.File: None,
    HandlerType.Memory: None,
}

#: The logger instances
LOGGERS = {}


@functools.lru_cache
def get_log_dir():
    from .. import common
    return f"{QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.GenericDataLocation)}/{common.product}/log"


@functools.lru_cache
def get_err_log_path():
    return f"{get_log_dir()}/error.log"


class TankHandler(logging.Handler):
    """In-memory tank for storing recent logs."""

    def __init__(self, maxlen=1000):
        super().__init__()
        self._lock = threading.Lock()
        # Store tuples of (levelno, formatted_msg, raw_msg)
        self.records = deque(maxlen=maxlen)

    def emit(self, record):
        formatted_msg = self.format(record)
        raw_msg = record.getMessage()
        with self._lock:
            self.records.append((record.levelno, formatted_msg, raw_msg))

    def get_records(self, level=logging.WARNING, remove=False):
        """Return formatted logs at or above the specified level."""
        with self._lock:
            filtered = [r[1] for r in self.records if r[0] >= level]
            if remove:
                self.records = deque((r for r in self.records if r[0] < level), maxlen=self.records.maxlen)
            return filtered


def init_log_handlers(max_bytes, maxlen, backup_count, init_memory=True, init_console=False, init_file=False):
    """Initialize the log handlers.

    """
    log_dir = get_log_dir()
    err_log_path = get_err_log_path()

    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    if any(h is not None for h in HANDLERS.values()):
        raise RuntimeError('Log handlers already initialized')

    if init_memory:
        mem_handler = TankHandler(maxlen=maxlen)
        mem_handler.setLevel(logging.DEBUG)
        mem_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATEFMT))
        HANDLERS[HandlerType.Memory] = mem_handler
    else:
        HANDLERS[HandlerType.Memory] = logging.NullHandler()

    if init_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATEFMT))
        HANDLERS[HandlerType.Console] = console_handler
    else:
        HANDLERS[HandlerType.Console] = logging.NullHandler()

    if init_file:
        file_handler = RotatingFileHandler(err_log_path, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATEFMT))
        HANDLERS[HandlerType.File] = file_handler
    else:
        HANDLERS[HandlerType.File] = logging.NullHandler()


def qt_message_handler(mode, context, message):
    """Custom message handler for Qt messages."""
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


def init_log(
        max_bytes=5 * 1024 * 1024,
        maxlen=1000,
        backup_count=3,
        log_level=logging.INFO,
        init_memory=True,
        init_console=False,
        init_file=False,
        init_qt=True
):
    """Initialize the logging system.

    Args:
        max_bytes (int): The maximum size of the log file in bytes.
        maxlen (int): The maximum number of log records to store in memory.
        backup_count (int): The number of backup log files to keep.
        log_level (int): The logging level.
        init_memory (bool): Initialize the memory log handler.
        init_console (bool): Initialize the console log handler.
        init_file (bool): Initialize the file log handler.
        init_qt (bool): Initialize the Qt message handler.

    """
    init_log_handlers(
        max_bytes=max_bytes,
        maxlen=maxlen,
        backup_count=backup_count,
        init_memory=init_memory,
        init_console=init_console,
        init_file=init_file
    )

    global LOGGING_LEVEL
    LOGGING_LEVEL = log_level

    if init_qt:
        logger = get_logger('Qt')
        logger.setLevel(log_level)
        QtCore.qInstallMessageHandler(qt_message_handler)


def teardown_log():
    """Teardown the logging system."""
    global HANDLERS, LOGGERS
    for logger in LOGGERS.values():
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
    for key in HANDLERS:
        handler = HANDLERS[key]
        if handler and hasattr(handler, 'close'):
            handler.close()
        HANDLERS[key] = None
    LOGGERS.clear()


def get_logger(name):
    """Get a logger with the specified name.

    """
    if HANDLERS[HandlerType.Memory] is None:
        raise RuntimeError('Log handlers not initialized')
    if name not in LOGGERS:
        logger = logging.getLogger(name)
        for h in HANDLERS.values():
            logger.addHandler(h)
        logger.setLevel(LOGGING_LEVEL)
        LOGGERS[name] = logger
    return LOGGERS[name]


def get_records(level=logging.WARNING, remove=False):
    """Get all log records at or above the specified level from the memory tank.

    """
    if HANDLERS[HandlerType.Memory] is None:
        raise RuntimeError('Log handlers not initialized')
    return HANDLERS[HandlerType.Memory].get_records(level=level, remove=remove)


def clear_records():
    """Clear all log records from the memory tank.

    """
    if HANDLERS[HandlerType.Memory] is None:
        raise RuntimeError('Log handlers not initialized')
    HANDLERS[HandlerType.Memory].records.clear()


def get_handler(handler_type):
    """Get the handler for the specified handler type.

    """
    if handler_type not in HANDLERS:
        raise ValueError(f'Invalid handler type: {handler_type}')
    return HANDLERS[handler_type]


def _thread_save_log(name, level, msg):
    from .. import common

    logger = get_logger(name)
    logger.log(level, msg, exc_info=(level >= logging.ERROR))
    try:
        common.signals.logRecordAdded.emit(name, level, msg)
    except AttributeError:
        pass


def set_logging_level(level):
    """Set the logging level for the app.

    """
    global LOGGING_LEVEL
    if level == LOGGING_LEVEL:
        return
    LOGGING_LEVEL = level
    for logger in LOGGERS.values():
        logger.setLevel(LOGGING_LEVEL)


def get_logging_level():
    """Get the current logging level for the app.

    """
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


def _parse_formatted_line(formatted_line):
    """Parse the formatted_line into a dictionary with date, level, name, thread, message."""
    match = LOG_LINE_REGEX.match(formatted_line)
    if match:
        return {
            "date": match.group("date"),
            "level": match.group("level"),
            "name": match.group("name"),
            "thread": match.group("thread"),
            "message": match.group("message")
        }
    else:
        # If parsing fails, return a dictionary with minimal info
        return {
            "date": "N/A",
            "level": "UNKNOWN",
            "name": "Unknown",
            "thread": "N/A",
            "message": formatted_line
        }


def _save_as_json(filepath, log_entries):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(log_entries, f, ensure_ascii=False, indent=4)


def _save_as_text(filepath, log_entries):
    with open(filepath, 'w', encoding='utf-8') as f:
        for entry in log_entries:
            # Split the message into lines
            message_lines = entry['message'].splitlines(keepends=True)

            if message_lines:
                # Print the first line of the message with the header
                f.write(
                    f"{entry['date']} [{entry['level']}] [{entry['name']}] [thread.{entry['thread']}] >> {message_lines[0]}")

                # Print subsequent lines of the message on their own
                for line in message_lines[1:]:
                    f.write(line)
            else:
                # No message (rare case), just print the header
                f.write(f"{entry['date']} [{entry['level']}] [{entry['name']}] [thread.{entry['thread']}] >> \n")

            f.write('\n')  # Add a blank line after each entry
            f.write('\n')  # Add a blank line after each entry


def save_tank_to_file(filepath):
    """Save the in-memory tank to a file.

    Args:
        filepath (str): The path to the file to save.

    """
    if HANDLERS[HandlerType.Memory] is None:
        raise RuntimeError('Log handlers not initialized')

    mem_handler = HANDLERS[HandlerType.Memory]
    if not isinstance(mem_handler, TankHandler):
        raise RuntimeError('Memory handler is not a TankHandler')

    records_list = list(mem_handler.records)

    parsed_entries = []
    for (levelno, formatted_msg, raw_msg) in records_list:
        data = _parse_formatted_line(formatted_msg)
        parsed_entries.append(data)

    _, ext = os.path.splitext(filepath)
    if ext.lower() == '.json':
        _save_as_json(filepath, parsed_entries)
    else:
        _save_as_text(filepath, parsed_entries)
