# -*- coding: utf-8 -*-
"""Bookmarks is a lightweight asset manager written in Python designed to
browse and manage project content of animation, VFX and film projects.


Features
--------

Bookmarks display content as separate ``bookmark``, ``asset`` and ``file``
items. Each bookmark item contains a series of asset items that in turn
contain file items. Bookmark and asset items can be configured independently
to link with, for instance, ``ShotGrid`` entities or set up with properties,
like frame-rate, resolution, and custom urls. These properties can be used to
quickly configure scenes in host applications, like Maya, and to access
related external resources.

The application provides a simple tools to create job and asset items using
zipped file templates, and options to annotate and filter items. It can also
preview images files using ``OpenImageIO``.


History
-------

This project was born out of my desire to manage my project content and is
adapted to my own custom way of setting projects up and interacting with
content. That is to say, Bookmarks expects certain patters to be respected to
read files and folders correctly. Still, I tried my best to make things
easily customizable to adapt to existing production environments.


Quick Start
-----------

The simples way to start Bookmarks as a standalone application is by running:

.. code-block:: python

    import bookmarks
    bookmarks.exec_()


Whilst the code base should be compatible with most systems, Windows is the only
supported platform. The following python packages are required to run Bookmarks:

* ``Python3``: Tested against 3.9.
* ``PySide2``: Tested against Qt 5.15.2. https://pypi.org/project/PySide2
* ``OpenImageIO``: Used to generate thumbnails for image items https://github.com/OpenImageIO/oiio
* ``numpy``: https://pypi.org/project/numpy
* ``slack_sdk``: https://pypi.org/project/slack_sdk
* ``psutil``: https://pypi.org/project/psutil
* ``shotgun_api3``: https://github.com/shotgunsoftware/python-api


Standalone and Embedded modes
-----------------------------

Bookmarks can be run in two modes. As a standalone application, or embedded in
a PySide2 environment. The base-layers can be initialized with:

.. code-block:: python

    from bookmarks import common
    common.initialize(common.EmbeddedMode) # or common.StandaloneMode

:func:`bookmarks.exec_()` is a utility method for starting Bookmarks in :attr:`common.StandaloneMode`,
whilst :attr:`common.StandaloneMode` mode will omit creating a Qt5 application.
See :mod:`bookmarks.common` for the related methods.

"""
import importlib
import platform
import sys

from PySide2 import QtWidgets

__author__ = 'Gergely Wootsch'
__website__ = 'https://github.com/wgergely/bookmarks'
__email__ = 'hello@gergely-wootsch.com'
__version__ = '0.5.0'
__copyright__ = f'Copyright (C) 2022 {__author__}'

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
