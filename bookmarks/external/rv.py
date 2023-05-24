"""Shotgun RV commands module.

TODO: This module is a stub and needs more testing and development.

"""
import subprocess

from .. import common

FULLSCREEN = '"{RV}" -tag {PRODUCT} url \'rvlink:// -reuse 1 -inferSequence ' \
                  '-l -play -fullscreen -nofloat -lookback 0 -nomb \"{PATH}\"\''
DEFAULT = '"{RV}" -tag {PRODUCT} url \'rvlink:// -reuse 1 -inferSequence ' \
                  '-l -play -lookback 0 \"{PATH}\"\''


@common.error
@common.debug
def push(path, command=DEFAULT):
    """Opens the given footage with rvpush.

    Args:
        path (str): The path to the footage to open.
        command (str): The command to run.

    """
    bin_path = common.get_binary('rvpush')
    if not bin_path:
        return

    # if common.get_platform() == common.PlatformWindows:
        # There's some issue with RV and Windows paths, so we need to replace
        # backslashes with forward slashes.
        # path = path.replace('/', '\\')
        pass

    cmd = command.format(
        RV=bin_path,
        PRODUCT=common.product,
        PATH=path
    )

    if common.get_platform() == common.PlatformWindows:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        subprocess.Popen(cmd, startupinfo=startupinfo)
    else:
        raise NotImplementedError('RV push is not implemented for this platform.')