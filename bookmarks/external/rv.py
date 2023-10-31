"""ShotGrid RV commands module.

TODO: This module is a stub and needs more testing and development.

"""
import uuid

from PySide2 import QtCore

from .. import common
from .. import database


tag = f'{common.product}{uuid.uuid4().hex}'

PushAndClear = common.idx(reset=True, start=0)
PushAndClearFullScreen = common.idx()
Add = common.idx()
InitializeSession = common.idx()

RV_COMMANDS = {
    InitializeSession: '-tag {tag} py-eval-return "print(\'Starting RV\')"',
    PushAndClearFullScreen: '-tag {tag} url rvlink:// "-reuse 1 -inferSequence -l -play -fullscreen -nofloat -lookback 0 -nomb -fps {framerate} "{source}""',
    PushAndClear: '-tag {tag} url rvlink:// "-reuse 1 -inferSequence -l -play -lookback 0 -fps {framerate} "{source}""',
    Add: '-tag {tag} merge "{source}"',
}


@common.error
@common.debug
def execute_rvpush_command(source, command):
    """Calls rvpush with the given source and commands.

    Args:
        source (str): The path to a footage source.
        command (str): An RV command enum.

    """
    common.check_type(source, str)
    common.check_type(command, int)

    if command not in RV_COMMANDS:
        raise ValueError(f'Invalid RV command: {command}')

    # Get the command string
    command = RV_COMMANDS[command]
    # Get the path to the executable
    executable = common.get_binary('rvpush')
    if not executable:
        raise RuntimeError(f'Could not find RV. Make sure the app is added as an Application Launcher Item,'
                           f'or that the RV binary is added to the PATH environment variable.')

    # Get the framerate from the database
    db = database.get(*common.active('root', args=True))
    framerate = db.value(db.source(), 'framerate', database.BookmarkTable)
    framerate = float(framerate) if framerate else 24.0

    # The url protocol cannot communicate with RV unless there's already an instance running.
    # So, let's execute a dummy python command to start RV. I'm assuming after calling
    # rvpush initialized RV with the correct tag we can push commands to it.

    process1 = QtCore.QProcess()
    env = QtCore.QProcessEnvironment.systemEnvironment()
    process1.setProcessEnvironment(env)

    _cmd = RV_COMMANDS[InitializeSession].format(tag=tag)
    _cmd = f'"{executable}" {_cmd}'
    process1.start(_cmd)
    process1.waitForFinished(7000)

    # Wait 3 seconds for the process
    QtCore.QThread.msleep(3000)

    # Format the command
    cmd = command.format(
        tag=tag,
        framerate=framerate,
        source=source
    )
    cmd = f'"{executable}" {cmd}'
    process2 = QtCore.QProcess()
    process2.setProcessEnvironment(env)
    process2.start(cmd)
    process2.waitForFinished(7000)
