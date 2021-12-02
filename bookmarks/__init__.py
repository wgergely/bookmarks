# -*- coding: utf-8 -*-
"""Bookmarks is a simple an asset manager designed to help VFX/Animation
productions. It can help you create, browse, annotate shots, assets and project
files.


Features
--------

Bookmarks can help provide an overview project files and makes it easy to hop
between assets and shots. It organises items into separate ``bookmark``,
``asset`` and ``file`` items that can be configured to link with ``ShotGrid``
entities or to have properties, like frame-rate and resolution. These properties
can be used to set up scene files in host applications, like Maya.


Getting Bookmarks
-----------------

The source can be downloaded from https://github.com/wgergely/bookmarks.

Bookmarks is developed on Windows and the latest binary release is available at
https://github.com/wgergely/bookmarks/releases.


Requirements
------------

* ``Python3``: Tested against version 3.7 and 3.9.
* ``PySide2``: Tested against Qt 5.15. https://pypi.org/project/PySide2
* ``OpenImageIO``: We're using this brilliant library to generate thumbnails for image items. https://github.com/OpenImageIO/oiio
* ``numpy``: https://pypi.org/project/numpy
* ``slack_sdk``: https://pypi.org/project/slack_sdk
* ``psutil``: https://pypi.org/project/psutil
* ``shotgun_api3``: https://github.com/shotgunsoftware/python-api
* ``alembic``: Alembic's Python library. https://github.com/alembic/alembic


Running Bookmarks
-----------------

Bookmarks can be initialized in ``standalone`` or ``embedded`` mode. To start
the  ``standalone`` app, simply call :func:`.exec_`:

    .. code-block:: python
        :linenos:

        import bookmarks
        bookmarks.exec_()

        # The above is a shortcut of:
        from bookmarks import common
        common.initialize(common.StandaloneMode)
        from bookmarks import standalone
        standalone.show()


To run it from a host application, you'll have to first initialize in
``EmbeddedMode``:

    .. code-block:: python
        :linenos:

        from bookmarks import common
        common.initialize(common.EmbeddedMode)

Regardless of the initialization mode, the main widget instance will be saved to
``common.main_widget``.

"""
import sys
import importlib
import platform

from PySide2 import QtWidgets

__author__ = 'Gergely Wootsch'
__website__ = 'https://github.com/wgergely/bookmarks'
__email__ = 'hello@gergely-wootsch.com'
__version__ = '0.5.0'
__copyright__ = f'Copyright (C) 2021  {__author__}'


# Python 2 support has been dropped and the code base only supports Python 3.
if sys.version_info[0] < 3 and sys.version_info[1] < 6:
    raise RuntimeError('Bookmarks requires Python 3.6.0 or later.')


def info():
    """Returns an informative string about the project environment and author.

    Returns:
        str: An informative string.

    """
    py_ver = platform.python_version()
    py_c = platform.python_compiler()
    oiio_ver = importlib.import_module('OpenImageIO').__version__
    alembic_ver = importlib.import_module('alembic').Abc.GetLibraryVersion()
    qt_ver = importlib.import_module('PySide2.QtCore').__version__
    sg_ver = importlib.import_module('shotgun_api3').__version__
    slack_ver = importlib.import_module('slack_sdk.version').__version__

    return '\n'.join((
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
    ))


def exec_():
    """Opens the Bookmark application.

    The method creates :class:`bookmarks.standalone.BookmarksApp`,
    and initializes all required submodules and data.

    Make sure to check the :doc:`list of dependencies <index>` before running.

    """
    print(info())
    from . import common
    common.verify_dependecies()
    common.initialize(common.StandaloneMode)
    from . import standalone
    standalone.show()
    QtWidgets.QApplication.instance().exec_()
