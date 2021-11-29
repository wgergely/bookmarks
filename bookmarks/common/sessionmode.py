from .. import common


SyncronisedActivePaths = 0
PrivateActivePaths = 1

def set_session_mode(mode):
    if mode not in (SyncronisedActivePaths, PrivateActivePaths):
        raise ValueError('Invalid mode value.')

    common.session_mode = mode
