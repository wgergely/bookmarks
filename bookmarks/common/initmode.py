"""Get/set the the current application mode.

Bookmarks can run either embedded in a DCC, or as a standalone application.
Make sure to initialize ``APP_MODE`` when starting Bookmarks.

"""
from .. import common

StandaloneMode = 0
EmbeddedMode = 1


def get_initmode():
    return common.init_mode


def set_initmode(v):
    if v not in (StandaloneMode, EmbeddedMode):
        raise ValueError('Invalid mode value.')

    common.init_mode = v
