# -*- coding: utf-8 -*-
"""Bookmarks' Maya plugin.

Make sure the BOOKMARKS_ROOT environment variable is set to point the root of the
Bookmarks distribution package as it is required to find and load all the
necessary dependencies.

"""
import os
import sys

try:
    from maya import cmds
    from maya.api import OpenMaya
except ImportError:
    raise ImportError('Could not find the Maya modules.')

env_key = 'BOOKMARKS_ROOT'
product = 'bookmarks'

__author__ = 'Gergely Wootsch'
__version__ = '0.6.0'
__version_info__ = (0, 6, 0)

maya_useNewAPI = True


def _add_path_to_sys(v, p):
    _v = f'{v}{os.path.sep}{p}'
    if not os.path.isdir(_v):
        raise RuntimeError(f'{_v} does not exist.')
    if _v in sys.path:
        return
    sys.path.append(os.path.normpath(_v))


def _add_path_to_path(v, p):
    _v = os.path.normpath(f'{v}{os.path.sep}{p}')
    if not os.path.isdir(_v):
        raise RuntimeError(f'{_v} does not exist.')

    # Windows DLL loading has changed in Python 3.8+ and PATH is no longer used
    if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
        os.add_dll_directory(_v)

    if _v.lower() not in os.environ['PATH'].lower():
        os.environ['PATH'] = f'{os.path.normpath(_v)};{os.environ["PATH"].strip(";")}'


def init_environment(key, add_private=False):
    """Add the dependencies to the Python environment.

    The method requires that `env_key` is set. The key is usually set
    by the Bookmark installer to point to the installation root directory.

    Raises:
            EnvironmentError: When the `key` environment is not set.
            RuntimeError: When the `key` environment is invalid or points to a missing
            directory.

    """
    if key not in os.environ:
        raise EnvironmentError(
            f'"{key}" environment variable is not set.'
        )
    v = os.environ[key]
    if not os.path.isdir(v):
        raise RuntimeError(
            f'"{v}" is not a valid folder. Is "{key}" environment variable set?'
        )

    _add_path_to_path(v, '.')
    _add_path_to_path(v, 'bin')

    _add_path_to_sys(v, 'shared')
    if add_private:
        _add_path_to_sys(v, 'core')
    if v not in sys.path:
        sys.path.append(v)


def is_batch():
    return OpenMaya.MGlobal.mayaState() == OpenMaya.MGlobal.kBatch


def initializePlugin(name):
    OpenMaya.MFnPlugin(
        name,
        vendor=__author__,
        version=__version__
    )

    if is_batch():
        return

    OpenMaya.MGlobal.displayInfo(f'Loading {product.title()}...')
    init_environment(env_key)

    from bookmarks import maya
    cmds.evalDeferred(maya.initialize)


def uninitializePlugin(name):
    OpenMaya.MFnPlugin(
        name,
        vendor=__author__,
        version=__version__
    )

    if is_batch():
        return

    OpenMaya.MGlobal.displayInfo(f'Unloading {product.title()}...')
    from bookmarks import maya
    cmds.evalDeferred(maya.uninitialize)
