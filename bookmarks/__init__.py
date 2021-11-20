# -*- coding: utf-8 -*-
"""Initilization script.

Bookmarks is a simple asset manager used in VFX/Animation productions, intended
to help to browse and annotate shots, assets and project files.

It was written in Python and can run as a standalone PySide2 application or run
embedded in a compatible host application (Note: only Maya has a plugin thus
far).


Requirements
------------

Bookmarks requires the following Python packages:

    `scandir`: Specifically, the '_scandir' library. See <https://github.com/benhoyt/scandir>
    `slack: <https://pypi.org/project/slackclient>
    `OpenImageIO`: <https://github.com/OpenImageIO/oiio>
    `PySide2`: <https://pypi.org/project/PySide2>
    `alembic`: <https://github.com/alembic/alembic>
    `psutil`: <https://pypi.org/project/psutil>
    `shotgun_api3`: ShotGrid's python API. See <https://github.com/shotgunsoftware/python-api>


"""
import sys
import os
import importlib
import traceback
import platform

__author__ = 'Gergely Wootsch'
__website__ = 'https://gergely-wootsch.com'
__email__ = 'hello@gergely-wootsch.com'
__version__ = '0.5.0'
__copyright__ = f'Copyright (C) 2021  {__author__}'
__dependencies__ = (
    '_scandir',
    'slack',
    'OpenImageIO',
    'PySide2',
    'alembic',
    'psutil',
    'shotgun_api3'
)


if sys.version_info[0] < 3 and sys.version_info[1] < 6:
    raise RuntimeError('Bookmarks requires Python 3.6.0 or later.')



def get_info():
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


def verify_dependecies():
    for mod in __dependencies__:
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(f'Bookmarks cannot be run. A required dependency was not found\n>>   {mod}')


def exec_():
    """Starts `Bookmarks` as a standalone PySide2 application.

    .. code-block:: python

        import bookmarks
        bookmarks.exec_()

    """
    print(get_info())

    from . import standalone

    app = standalone.StandaloneApp([])
    standalone.show()
    app.exec_()


verify_dependecies()
