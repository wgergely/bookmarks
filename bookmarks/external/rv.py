# -*- coding: utf-8 -*-
"""Shotgun RV commands module.

"""
import subprocess

from .. import common

RV_PUSH_COMMAND = '"{RV}" -tag {PRODUCT} url \'rvlink:// -reuse 1 -inferSequence ' \
                  '-l -play -fullscreen -nofloat -lookback 0 -nomb \"{PATH}\"\''


@common.error
@common.debug
def push(path):
    """Uses `rvpush` to view a given footage."""
    bin_path = common.get_binary('rvpush')
    if not bin_path:
        return

    cmd = RV_PUSH_COMMAND.format(
        RV=bin_path,
        PRODUCT=common.product,
        PATH=path
    )

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    subprocess.Popen(cmd, startupinfo=startupinfo)
