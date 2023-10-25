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

product = 'bookmarks'

__author__ = 'Gergely Wootsch'
__version__ = '0.8.9'

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


def init_environment(key='BOOKMARKS_ROOT', pyside=False):
    """Add the dependencies required to run Bookmarks to a python environment.

    The Bookmarks installer should set the 'BOOKMARKS_ROOT' environment variable to
    the installation directory. This is required to load the python modules into the
    current environment.

    Args:
        key (str): The environment variable used to find the distribution directory.
            Optional, defaults to 'BOOKMARKS_ROOT
        pyside (bool):
            Adds the PySide modules bundled with Bookmarks if True.
            Optional, defaults to False.

    Raises:
            EnvironmentError: When the `key` environment is not set.
            RuntimeError:
                When the `key` environment is invalid or points to a missing directory.

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
    if pyside:
        _add_path_to_sys(v, 'core')
    if v not in sys.path:
        sys.path.append(v)


def is_batch():
    """Checks if Maya is running in batch mode.
    """
    return OpenMaya.MGlobal.mayaState() == OpenMaya.MGlobal.kBatch


def initializePlugin(name):
    """Initializes the plugin.

    """
    OpenMaya.MFnPlugin(
        name,
        vendor=__author__,
        version=__version__
    )

    # The plugin won't run in batch mode
    if is_batch():
        return

    OpenMaya.MGlobal.displayInfo(f'Loading {product.title()}...')
    init_environment()

    from bookmarks import maya
    cmds.evalDeferred(maya.initialize)


def uninitializePlugin(name):
    """Un-initializes the plugin.

    """
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
