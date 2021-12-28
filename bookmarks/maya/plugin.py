# -*- coding: utf-8 -*-
"""Bookmarks' Maya plugin.

Make sure Bookmark is installed before trying to load the plugin. The `k`
environment is set by the installer and is required to find and load all the
necessary Python modules.

"""
import sys
import os

from maya.api import OpenMaya
from maya import cmds


env_key = 'BOOKMARKS_ROOT'
product = 'bookmarks'

__author__ = 'Gergely Wootsch'
__version__ = '0.5.0'

maya_useNewAPI = True


def init_environment(env_key, add_private=False):
    """Add the dependencies to the Python environment.

    The method requires that `env_key` is set. The key is usually set
    by the Bookmark installer to point to the install root directory.
    The

    Raises:
            EnvironmentError: When the `env_key` is not set.
            RuntimeError: When the `env_key` is invalid or a directory missing.

    """
    if env_key not in os.environ:
        raise EnvironmentError(
            f'"{env_key}" environment variable is not set.')

    v = os.environ[env_key]

    if not os.path.isdir(v):
        raise RuntimeError(
            f'"{v}" is not a falid folder. Is "{env_key}" environment variable set?')

    # Add env_key to the PATH
    v = os.path.normpath(os.path.abspath(v)).strip()
    if v.lower() not in os.environ['PATH'].lower():
        os.environ['PATH'] = v + ';' + os.environ['PATH'].strip(';')

    def _add_path_to_sys(p):
        _v = f'{v}{os.path.sep}{p}'
        if not os.path.isdir(_v):
            raise RuntimeError(f'{_v} does not exist.')

        if _v in sys.path:
            return
        sys.path.append(_v)

    _add_path_to_sys('shared')
    if add_private:
        _add_path_to_sys('private')
    if v not in sys.path:
        sys.path.append(v)


def initializePlugin(name):
    plugin = OpenMaya.MFnPlugin(
        name,
        vendor=__author__,
        version=__version__
    )

    OpenMaya.MGlobal.displayInfo(f'Loading {product.title()}...')
    init_environment(env_key)

    from bookmarks import maya
    cmds.evalDeferred(maya.initialize)


def uninitializePlugin(name):
    plugin = OpenMaya.MFnPlugin(
        name,
        vendor=__author__,
        version=__version__
    )
    OpenMaya.MGlobal.displayInfo(f'Unloading {product.title()}...')
    from bookmarks import maya
    cmds.evalDeferred(maya.uninitialize)
