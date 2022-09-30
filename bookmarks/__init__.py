# -*- coding: utf-8 -*-
""".. centered:: |logo|

.. centered:: |label1| |label2| |label3| |label4|


=====================
Welcome to Bookmarks!
=====================


Bookmarks is a lightweight Python asset manager designed to browse and manage content
of animation, VFX and film projects.


Features
--------

Bookmarks displays project content as :mod:`bookmark<bookmarks.items.bookmark_items>`,
:mod:`asset<bookmarks.items.asset_items>` and :mod:`file<bookmarks.items.file_items>`
items. Each bookmark item contains a series of asset items that in turn contain the
file items. Bookmark and asset items can be configured independently to link with,
for instance, `ShotGrid` entities or be set up with properties, like frame-rate,
resolution, and custom URLs. These properties can be used to quickly configure scenes
in host applications, e.g. Maya, and to access related external resources.

The app provides simple tools to create jobs and assets using ZIP templates, templated
file-names and options to annotate and filter existing items, and preview images using
`OpenImageIO`.


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

* `Python3 <https://github.com/python/cpython>`_ -  Tested against 3.9
* `PySide2 <https://pypi.org/project/PySide2>`_ - Tested against Qt 5.15.2
* `OpenImageIO <https://github.com/OpenImageIO/oiio>`_ - Tested against 2.3
* `numpy <https://pypi.org/project/numpy>`_
* `slack_sdk <https://pypi.org/project/slack_sdk>`_
* `psutil <https://pypi.org/project/psutil>`_
* `shotgun_api3 <https://github.com/shotgunsoftware/python-api>`_

Warning:

    * Currently, Windows is the only supported platform (although much of the codebase should be platform-agnostic).
    * OpenImageIO does not currently maintain installable python packages.


.. |logo| image:: https://github.com/wgergely/bookmarks/blob/main/bookmarks/rsc/gui/icon.png?raw=true
   :height: 300px
   :width: 300px
   :alt: Bookmarks - Lightweight asset manager designed for VFX, animation, film productions

.. |label1| image:: https://img.shields.io/badge/Python-3.8%2B-lightgrey
   :height: 18px

.. |label2| image:: https://img.shields.io/badge/Python-PySide2-lightgrey
   :height: 18px

.. |label3| image:: https://img.shields.io/badge/Platform-Windows-lightgrey
   :height: 18px

.. |label4| image:: https://img.shields.io/badge/Version-v0.6.0-green
   :height: 18px

"""
import importlib
import os
import platform
import sys

from PySide2 import QtWidgets

#: Package author
__author__ = 'Gergely Wootsch'

#: Project homepage
__website__ = 'https://github.com/wgergely/bookmarks'

#: Author email
__email__ = 'hello@gergely-wootsch.com'

#: Project version
__version__ = '0.6.0'

#: Project version
__version_info__ = __version__.split('.')

#: Project copyright
__copyright__ = f'Copyright (c) 2022 {__author__}'

# Specify python support
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


def exec(print_info=True):
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


def exec_(*args, **kwargs):
    """Shadows :func:`exec`. Exists for compatibility.

    """
    return exec(*args, **kwargs)
