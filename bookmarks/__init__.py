# -*- coding: utf-8 -*-
"""Bookmarks is a lightweight asset manager designed to browse project content of
animation, VFX and film projects.


Features
--------

To provide an overview, Bookmarks displays content as separate ``bookmark``,
``asset`` and ``file`` items. These items can be configured to link with
``ShotGrid`` entities or set up with properties, like frame-rate, resolution,
and custom urls. These can be used, for instance, to quickly configure scenes in
host applications, such as Maya.

Bookmarks provides a simple tools to create job and asset items using on zipped
templates, and options to annotate and filter items. It can also preview
images files thanks to OpenImageIO


Installation
------------

Download the latest release from https://github.com/wgergely/bookmarks/releases.

Whilst the code base should be compatible  with most systems, Windows is the only
supported platform at the moment. If you'd like to try Bookmarks on another
system, you'll have to make sure all the requirements are built and available:

* ``Python3``: Tested with 3.7 and 3.9.
* ``PySide2``: Tested with Qt 5.15.2. https://pypi.org/project/PySide2
* ``OpenImageIO``: Used to generate thumbnails for image items.
https://github.com/OpenImageIO/oiio
* ``numpy``: https://pypi.org/project/numpy
* ``slack_sdk``: https://pypi.org/project/slack_sdk
* ``psutil``: https://pypi.org/project/psutil
* ``shotgun_api3``: https://github.com/shotgunsoftware/python-api

"""
import importlib
import platform
import sys

from PySide2 import QtWidgets

__author__ = 'Gergely Wootsch'
__website__ = 'https://github.com/wgergely/bookmarks'
__email__ = 'hello@gergely-wootsch.com'
__version__ = '0.5.0'
__copyright__ = f'Copyright (C) 2021 {__author__}'

# Python 2 is not supported
if sys.version_info[0] < 3 and sys.version_info[1] < 7:
    raise RuntimeError('Bookmarks requires Python 3.7.0 or later.')


def info():
    """Returns an informative string about the project environment and author.

    Returns:
        str: An informative string.

    """
    py_ver = platform.python_version()
    py_c = platform.python_compiler()
    oiio_ver = importlib.import_module('OpenImageIO').__version__
    qt_ver = importlib.import_module('PySide2.QtCore').__version__
    sg_ver = importlib.import_module('shotgun_api3').__version__
    slack_ver = importlib.import_module('slack_sdk.version').__version__

    return '\n'.join(
        (
            __copyright__,
            f'E-Mail:    {__email__}',
            f'Website:  {__website__}',
            '\nPackages\n'
            f'Python {py_ver} {py_c}',
            f'Bookmarks {__version__}',
            f'PySide2 {qt_ver}',
            f'OpenImageIO {oiio_ver}',
            f'{alembic_ver}',
            f'ShotGrid API {sg_ver}',
            f'SlackClient {slack_ver}'
        )
    )


def exec_():
    """Opens the Bookmark application.

    The method creates :class:`bookmarks.standalone.BookmarksApp`,
    and initializes all required submodules and data.

    Make sure to check the :doc:`list of dependencies <index>` before running.

    """
    print(info())

    from . import common
    common.verify_dependencies()
    common.initialize(common.StandaloneMode)

    from . import standalone
    standalone.show()

    QtWidgets.QApplication.instance().exec_()
