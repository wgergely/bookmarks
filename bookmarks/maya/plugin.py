# -*- coding: utf-8 -*-
# pylint: disable=E0401
"""Bookmarks' Maya plugin.

Make sure Bookmark is installed before trying to load the plugin. The `k`
environment is set by the installer and is required to find and load all the
necessary Python modules.

"""
import sys
import os
import importlib
import functools

import maya.api.OpenMaya as OpenMaya
import maya.cmds as cmds


env_key = 'BOOKMARKS_ROOT'
product = 'bookmarks'
author = 'Gergely Wootsch'

maya_useNewAPI = True



def init_environment(env_key, add_private=False):
    """Add the dependencies to the Python environment.

    The method requires that BOOKMARKS_ENV_KEY is set. The key is usually set
    by the Bookmark installer to point to the install root directory.
    The

    Raises:
            EnvironmentError: When the BOOKMARKS_ENV_KEY is not set.
            RuntimeError: When the BOOKMARKS_ENV_KEY is invalid or a directory missing.

    """
    if env_key not in os.environ:
        raise EnvironmentError(
            f'"{env_key}" environment variable is not set.')

    v = os.environ[env_key]

    if not os.path.isdir(v):
        raise RuntimeError(
            f'"{v}" is not a falid folder. Is "{env_key}" environment variable set?')

    # Add BOOKMARKS_ENV_KEY to the PATH
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
    sys.path.append(v)


def get_modules():
    package_root = os.path.abspath(
        os.environ[k] + os.path.sep + 'shared' + os.path.sep + PRODUCT)

    assert os.path.isdir(package_root)

    modules = [PRODUCT, ]

    def list_dir(path):
        for f in os.listdir(path):
            p = path + os.path.sep + f
            if os.path.isdir(p):
                list_dir(p)
            if not f.endswith('.py'):
                continue
            mod = (path + os.path.sep + f).replace(package_root, '')
            mod = PRODUCT + '.' + \
                mod.replace('.py', '').strip('\\').replace('\\', '.')
            if '__init__' in mod:
                continue
            modules.append(mod)

    list_dir(package_root)

    return sorted(modules)


def import_modules():
    for _k in get_modules():
        importlib.import_module(_k)


def delete_modules():
    for _k in get_modules():
        if _k not in sys.modules:
            continue
        del sys.modules[_k]


def reload_modules():
    for _k in get_modules():
        module = importlib.import_module(_k)
        reload(module)


def initializePlugin(name):
    init_environment()

    import_modules()
    module = importlib.import_module(PRODUCT)

    pluginFn = OpenMaya.MFnPlugin(
        name,
        vendor=VENDOR,
        version=module.__version__
    )

    def init():
        # Make sure docking is not locked when we're about to show our widget
        currentval = cmds.optionVar(q='workspacesLockDocking')
        cmds.optionVar(intValue=('workspacesLockDocking', False))

        # Initialize widgets
        import_modules()
        module = importlib.import_module(PRODUCT)
        module.common.STANDLONE = False
        module.common.init_signals()
        module.common.init_dirs_dir()
        module.common.init_settings()
        module.common.init_font_db()
        module.common.init_pixel_ratio()
        module.common.init_ui_scale()
        module.common.init_resources()
        module.common.init_session_lock()
        module.maya.widget.init_tool_button()
        module.maya.widget.show()

        from PySide2 import QtCore
        def initialize():
            QtCore.QTimer.singleShot(100, module.main.instance().initialize)

        # Restore original docking state
        cmds.evalDeferred(
            functools.partial(
                cmds.optionVar,
                intValue=('workspacesLockDocking', currentval)
            )
        )
        cmds.evalDeferred(initialize)

    cmds.evalDeferred(init)


def uninitializePlugin(name):
    from PySide2 import QtWidgets

    import_modules()
    module = importlib.import_module(PRODUCT)
    res = module.ui.MessageBox(
        'Are you sure you want to disable Bookmarks?',
        'Reloading the plugin is not supported (sorry!) and will require a Maya restart to re-enable.',
        buttons=[module.ui.OkButton, module.ui.CancelButton]
    ).exec_()
    if res == QtWidgets.QDialog.Rejected:
        return

    pluginFn = OpenMaya.MFnPlugin(
        name,
        vendor=VENDOR,
        version=module.__version__
    )

    cmds.evalDeferred(module.maya.actions.uninitialize)
    cmds.evalDeferred(module.actions.uninitialize)
