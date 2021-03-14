# -*- coding: utf-8 -*-
"""Basic logging classes and methods.

"""
import time
import traceback

from PySide2 import QtGui, QtCore, QtWidgets

from . import common


mutex = QtCore.QMutex()


HEADER = (0b000000001, u'\033[95m')
OKBLUE = (0b000000010, u'\033[94m')
OKGREEN = (0b000000100, u'\033[92m')
WARNING = (0b000001000, u'\033[93m')
FAIL = (0b000010000, u'\033[91m')
FAIL_SUB = (0b000100000, u'\033[91m')
ENDC = (0b001000000, u'\033[0m')
BOLD = (0b010000000, u'\033[1m')
UNDERLINE = (0b100000000, u'\033[4m')


def _log(message):
    mutex.lock()
    print message
    mutex.unlock()


def success(message):
    """Logs a message when an action succeeds.

    """
    message = u'{color}{ts} [Ok]:  {default}{message}{default}'.format(
        ts=time.strftime(u'%H:%M:%S'),
        color=OKGREEN[1],
        default=ENDC[1],
        message=message
    )
    _log(message)


def debug(message, cls=None):
    """Log a debug message to help analyze program flow.

    """
    if not common.DEBUG:
        return

    message = u'{color}{ts} [Debug]:{default}    {cls}{message}{default}'.format(
        ts=time.strftime(u'%H:%M:%S'),
        color=OKBLUE[1],
        default=ENDC[1],
        message=message,
        cls=cls.__class__.__name__ + u'.' if cls else u''
    )
    _log(message)


def error(message):
    """Log an error.

    If available, a traceback will automatically be included in the output.

    """
    tb = traceback.format_exc()
    if tb:
        tb = u'\n\033[91m'.join(tb.strip(u'\n').split(u'\n'))
        message = u'{fail}{underline}{ts} [Error]:{default}{default}    {message}\n{fail}{traceback}{default}\n'.format(
            ts=time.strftime(u'%H:%M:%S'),
            fail=FAIL[1],
            underline=UNDERLINE[1],
            default=ENDC[1],
            message=message,
            traceback=tb
        )
    else:
        message = u'{fail}{underline}{ts} [Error]:{default}{default}    {message}{default}\n'.format(
            ts=time.strftime(u'%H:%M:%S'),
            fail=FAIL[1],
            underline=UNDERLINE[1],
            default=ENDC[1],
            message=message,
        )
    _log(message)
