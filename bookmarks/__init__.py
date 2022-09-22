# -*- coding: utf-8 -*-
"""Bookmarks is a lightweight asset manager written in Python designed to
browse and manage project content of animation, VFX and film projects.


Features
--------

The app displays content as separate ``bookmark``, ``asset`` and ``file`` items. Each
``bookmark`` item contains a series of ``asset`` items that in turn contain ``file``
items. ``Bookmark`` and ``asset`` items can be configured independently to link with,
for instance, ``ShotGrid`` entities or set up with properties, like frame-rate,
resolution, and custom urls. These properties can be used to quickly configure scenes
in host applications, like Maya, and to access related external resources.

The app provides simple tools to create new jobs from ZIP file templates (although this
is usually something very site specific) and options to annotate and filter existing
items. It can also preview images files using ``OpenImageIO``.


Background
----------

This project was developed to manage my project personal projects and is adapted to my
own custom way of setting them up. This is to say, Bookmarks expects certain patterns to
be respected to read files and folders correctly, but I tried my best to make things
easily customizable to adapt to site specific environments.


Quick Start
-----------

The simplest way to start Bookmarks as a standalone application is to run:

.. code-block:: python

    import bookmarks
    bookmarks.exec_()


Dependencies
------------

The following python packages are required to run Bookmarks:

* ``Python3``: Tested against 3.9.
* ``PySide2``: Tested against Qt 5.15.2. https://pypi.org/project/PySide2
* ``OpenImageIO``: Used to generate thumbnails for image items https://github.com/OpenImageIO/oiio
* ``numpy``: https://pypi.org/project/numpy
* ``slack_sdk``: https://pypi.org/project/slack_sdk
* ``psutil``: https://pypi.org/project/psutil
* ``shotgun_api3``: https://github.com/shotgunsoftware/python-api

Currently, Windows is the only supported platform (although much of the codebase should
be platform-agnostic).

Note:

    OpenImageIO does not currently maintain installable python packages.



Modes
-----

Bookmarks can be run in two modes. As a standalone application, or embedded in a
PySide2 environment. The base-layers can be initialized with:

.. code-block:: python

    from bookmarks import common
    common.initialize(common.EmbeddedMode) # or common.StandaloneMode

:func:`exec_()` is a utility method for starting Bookmarks in
:attr:`common.StandaloneMode`, whilst :attr:`common.EmbeddedMode` is useful when
running from inside a host DCC. Currently only the Maya plugin makes use of this mode.
See :mod:`bookmarks.maya` and :mod:`bookmarks.common` for the related methods.


Links
-----

`Github Repository <https://github.com/wgergely/bookmarks>`_

`Documentation <https://bookmarks.gergely-wootsch.com/html/index.html>`_


"""
import importlib
import os
import platform
import sys

from PySide2 import QtWidgets

__author__ = 'Gergely Wootsch'
__website__ = 'https://github.com/wgergely/bookmarks'
__email__ = 'hello@gergely-wootsch.com'
__version__ = '0.6.0'
__version_info__ = (0, 6, 0)
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

    from . import common
    if common.env_key not in os.environ:
        env = f'{common.env_key} is not set!'
    else:
        env = f'{common.env_key}={os.environ[common.env_key]}'

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
            f'Slack SDK {slack_ver}',
            f'{env}'
        )
    )


def exec_(print_info=True):
    """Opens the Bookmark app.

    The method creates :class:`bookmarks.standalone.BookmarksApp`,
    and initializes all required submodules and data.

    """
    if print_info:
        print(info())

    from . import common
    common.verify_dependencies()
    common.initialize(common.StandaloneMode)

    from . import standalone
    standalone.show()

    QtWidgets.QApplication.instance().exec_()
