from .. import common

SyncronisedActivePaths = 0
PrivateActivePaths = 1


def get_sync_mode():
    return common.init_mode


def set_sync_mode(v):
    if v not in (SyncronisedActivePaths, PrivateActivePaths):
        raise ValueError('Invalid mode value.')

    common.init_mode = v
