# -*- coding: utf-8 -*-
"""Bookmarks is a simple an asset manager designed to help VFX/Animation
productions. It can help you create, browse, annotate shots, assets and project
files.


Features
--------

I (Gergely, an animation director/CG generalist) started developing Bookmarks as
a personal project to help manage in-house and freelance jobs. What can I say,
I'm a digitally messy person!

Bookmarks essentially is a file browser and strives to provide the tools needed
to find and view items. It can link local assets with ``Autodesk ShotGrid`` and
set project properties (like framerate and resolution) that we can use to set
scenes up in DCCs.

But for me, it helps me most to provide a quick access point to my project and
to hop and jump between assets and shots quickly when working on a project with
many different parts.

I work on Windows with Maya, so that's where Bookmarks' focus lies. In theory,
the codebase is largely platform-agnostic and should run on Linux or Mac OS
(given that its dependencies are available) but I never tested these.



Getting Bookmarks
-----------------

Bookmarks is open-source and the latest source can be downloaded from
https://github.com/wgergely/bookmarks.

To download the latest binary release for Windows visit:
https://github.com/wgergely/bookmarks/releases


Requirements
------------

Bookmarks requires Python 3.6.0 or later and the following Python packages:

* ``scandir``: If your Python distribution is missing _scandir.pyd, you might have to build it from source. https://github.com/benhoyt/scandir.
* ``PySide2``: Tested against Qt 5.15. https://pypi.org/project/PySide2
* ``OpenImageIO``: We're using this brilliant library to generate thumbnails for image items. https://github.com/OpenImageIO/oiio
* ``numpy``: https://pypi.org/project/numpy
* ``slack``: https://pypi.org/project/slackclient
* ``psutil``: https://pypi.org/project/psutil
* ``shotgun_api3``: https://github.com/shotgunsoftware/python-api
* ``alembic``: Alembic's Python library. https://github.com/alembic/alembic


Running Bookmarks from Python
-----------------------------

To run bookmarks, make sure all the dependencies are available and simply call:

.. code-block:: python
    :linenos:

    import bookmarks
    bookmarks.exec_()

This will initialize the PySide2 application and all the oebjects Bookmarks
needs to run. See :doc:`bookmarks.standalone <./bookmarks.standalone>` for more
information.

"""
import sys
import os
import importlib
import traceback
import platform

__author__ = 'Gergely Wootsch'
__website__ = 'https://github.com/wgergely/bookmarks'
__email__ = 'hello@gergely-wootsch.com'
__version__ = '0.5.0'
__copyright__ = f'Copyright (C) 2021  {__author__}'
__dependencies__ = (
    '_scandir',
    'PySide2',
    'OpenImageIO',
    'alembic',
    'numpy',
    'psutil',
    'shotgun_api3',
    'slack',
)


# Python 2 support has been dropped and the code base only supports Python 3.
if sys.version_info[0] < 3 and sys.version_info[1] < 6:
    raise RuntimeError('Bookmarks requires Python 3.6.0 or later.')


def get_info():
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
    slack_ver = importlib.import_module('slack.version').__version__

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



def _verify_dependecies():
    """Checks the presence of all required python modules.

    Raises:
        ModuleNotFoundError: When a required python library was not found.

    """
    for mod in __dependencies__:
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                f'Bookmarks cannot be run. A required dependency was not found\n>> {mod}') from e


def exec_():
    """Opens the Bookmark application.

    The method creates :class:`bookmarks.standalone.BookmarksApp`,
    and initializes all required submodules and data.

    Make sure to check the :doc:`list of dependencies <index>` before running.

    """
    print(get_info())
    from . import common
    common.initialize(common.StandaloneMode)



_verify_dependecies()
