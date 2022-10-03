"""Basic logging classes and methods.

"""
import sys
import time
import traceback

from PySide2 import QtCore

from . import common

mutex = QtCore.QMutex()

ESC = r''
OKBLUE = rf'{ESC}[94m'
OKGREEN = rf'{ESC}[92m'
WARNING = rf'{ESC}[93m'
FAIL = rf'{ESC}[91m'
RESET = rf'{ESC}[0m'
BOLD = rf'{ESC}[1m'
UNDERLINE = rf'{ESC}[4m'


def _log(message):
    mutex.lock()
    print(message)
    mutex.unlock()


def success(message):
    """Logs a message when an action succeeds.

    """
    message = '{color}{ts} [Success]:  {reset}{message}{reset}'.format(
        ts=time.strftime('%H:%M:%S'),
        color=OKGREEN,
        reset=RESET,
        message=message
    )
    _log(message)


def debug(message, cls=None):
    """Log a debug message to help analyze program flow.

    """
    if not common.debug_on:
        return

    message = '{color}{ts} [Debug]:{reset}    {cls}{message}{reset}'.format(
        ts=time.strftime('%H:%M:%S'),
        color=OKBLUE,
        reset=RESET,
        message=message,
        cls=cls.__class__.__name__ + '.' if cls else ''
    )
    _log(message)


def error(message, exc_info=None):
    """Log an error.

    If available, a traceback will automatically be included in the output.

    """
    if exc_info is None:
        exc_info = sys.exc_info()
        exc_type, exc_value, exc_traceback = exc_info
    else:
        exc_type, exc_value, exc_traceback = exc_info

    if all(exc_info):
        tb = ''.join(
            traceback.format_exception(exc_type, exc_value, exc_traceback, limit=None)
        )
        tb = '\n\033[91m'.join(tb.strip('\n').split('\n'))
        message = '{fail}{underline}{ts} [Error]:{reset}    {message}\n{fail}{traceback}{reset}\n'.format(
            ts=time.strftime('%H:%M:%S'),
            fail=FAIL,
            underline=UNDERLINE,
            reset=RESET,
            message=message,
            traceback=tb
        )
    else:
        message = '{fail}{underline}{ts} [Error]:{reset}    {message}{reset}\n'.format(
            ts=time.strftime('%H:%M:%S'),
            fail=FAIL,
            underline=UNDERLINE,
            reset=RESET,
            message=message,
        )
    _log(message)
