"""ShotGrid RV commands module.

TODO: This module is a stub and needs more testing and development.

"""
import os
import subprocess

from .. import common
from .. import database
from .. import log

#: The base command used to call an RV push command
URL = f'"{{executable}}" -tag {common.product} url \'rvlink:// {{rv_command}}\''
MERGE = f'"{{executable}}" -tag {common.product} merge {{rv_command}}'

PushAndClear = 'PushAndClear'
PushAndClearFullScreen = 'PushAndClearFullScreen'
Add = 'Add'

RV_COMMANDS = {
    PushAndClearFullScreen: '-reuse 1 -inferSequence -l -play -fullscreen -nofloat -lookback 0 -nomb -fps {framerate} '
                            '\"{source}\"',
    PushAndClear: '-reuse 1 -inferSequence -l -play -lookback 0 -fps {framerate} \"{source}\"',
    Add: '\"{source}\"',
}


def _execute_rvpush_command(cmd):
    """Executes the given command.

    Args:
        cmd (str): The command to execute.

    """
    # Execute the command
    if common.get_platform() == common.PlatformWindows:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        with open(os.devnull, 'w') as devnull:
            subprocess.Popen(cmd, stdout=devnull, stderr=devnull, startupinfo=startupinfo)

    else:
        raise NotImplementedError('RV push is not implemented for this platform.')


@common.error
@common.debug
def execute_rvpush_command(source, command, basecommand=URL):
    """Calls rvpush with the given source and commands.

    Args:
        source (str): The path to a footage source.
        command (str): An RV command enum.
        basecommand (str): The base command to use when calling rvpush.

    """
    common.check_type(source, str)
    common.check_type(command, str)
    common.check_type(basecommand, str)

    if command not in RV_COMMANDS:
        raise ValueError(f'Invalid RV command: {command}. Valid commands are: {RV_COMMANDS.keys()}')

    # Get the command string
    command = RV_COMMANDS[command]

    # Get the path to the executable
    executable = common.get_binary('rvpush')
    if not executable:
        log.error(f'Could not find rvpush.')
        return

    # Get the framerate from the database
    db = database.get(*common.active('root', args=True))
    framerate = db.value(db.source(), 'framerate', database.BookmarkTable)
    framerate = float(framerate) if framerate else 24.0

    # Format the command
    rv_command = command.format(framerate=framerate, source=source)
    cmd = basecommand.format(executable=executable, rv_command=rv_command)

    _execute_rvpush_command(cmd)
