# -*- coding: utf-8 -*-
"""Shotgun RV commands module.

"""
import subprocess
from PySide2 import QtCore

from . import common
from . import log
from . import settings


RV_PUSH_COMMAND = u'"{RV}" -tag {PRODUCT} url \'rvlink:// -reuse 1 -inferSequence -l -play -fullscreen -nofloat -lookback 0 -nomb \"{PATH}\"\''


@common.error
@common.debug
def push(path):
    """Uses `rvpush` to view a given footage."""

    rv_path = common.get_path_to_executable(settings.RVKey)
    if not rv_path:
        s = u'Shotgun RV not found.\n'
        s += u'To push footage to Shotgun RV, you can add RV in the preferences or add it to your PATH environment variable.'
        raise RuntimeError(s)

    rv_info = QtCore.QFileInfo(rv_path)
    if not rv_info.exists():
        s = u'Invalid Shotgun RV path set.\n'
        s += u'Make sure the currently set RV path is valid and try again!'
        raise RuntimeError(s)

    if common.get_platform() == common.PlatformWindows:
        rv_push_path = u'{}/rvpush.exe'.format(rv_info.path())
        if not QtCore.QFileInfo(rv_push_path).exists():
            raise RuntimeError('Could not find rvpush.exe')

        cmd = RV_PUSH_COMMAND.format(
            RV=rv_push_path,
            PRODUCT=common.PRODUCT,
            PATH=path
        )
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        subprocess.Popen(cmd, startupinfo=startupinfo)


        log.success(u'Footage sent to RV. Command used was {}'.format(cmd))
    else:
        s = u'Function not yet implemented on this platform.'
        raise NotImplementedError(s)
