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


k = 'BOOKMARKS_ROOT'
PRODUCT = 'bookmarks'
VENDOR = 'Gergely Wootsch'

maya_useNewAPI = True


def init_environment():
    # Check if the environment variable is set
    if k not in os.environ:
        raise EnvironmentError(
            'Cannot load the plugin, because the "{}" environment variable is not set.'.format(k))

    # Check if it points to a valid directory
    if not os.path.isdir(os.environ[k]):
        raise EnvironmentError(
            'Cannot load the plugin, because "{}" does not exist.'.format(os.environ[k]))

    # Add the package root to bin
    r = os.path.normapth(os.environ[k])
    if r not in os.environ['PATH']:
        os.environ['PATH'] = r + ';' + os.environ['PATH']

    # Add install directories to sys.path
    for d in ('shared', 'bin'):
        p = os.path.normpath(os.environ[k] + os.path.sep + d)
        if not os.path.isdir(p):
            raise EnvironmentError(
                'Cannot load the plugin, because "{}" does not exist.'.format(p))

        if d == 'shared':
            # Add the `shared` folder to the python path
            if p not in sys.path:
                sys.path.insert(0, p)
        if d == 'bin':
            # Add the `bin` folder to the current path envrionment
            if p not in os.environ['PATH']:
                os.environ['PATH'] = p + ';' + os.environ['PATH']


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
    cmds.evalDeferred(module.common.uninitialize)
