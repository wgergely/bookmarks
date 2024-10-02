import collections
import os

from .. import common, log

ActivePathSegmentTypes = (
    'server',
    'job',
    'root',
    'asset',
    'task',
    'file',
)
_ActivePathSegmentTypes = {f for f in ActivePathSegmentTypes}

SynchronizedActivePaths = 0
PrivateActivePaths = 1
EnvActivePaths = 2


def init_active(clear_all=True, load_settings=True, load_env=True, load_private=True):
    if clear_all:
        # Initialize the active_paths object
        common.active_paths = {
            SynchronizedActivePaths: collections.OrderedDict(),
            PrivateActivePaths: collections.OrderedDict(),
            EnvActivePaths: collections.OrderedDict(),
        }

        # Init none values
        for k in (SynchronizedActivePaths, PrivateActivePaths, EnvActivePaths):
            for f in ActivePathSegmentTypes:
                common.active_paths[k][f] = None

    if load_settings:
        # Load values from the user settings file
        if not common.settings:
            raise ValueError('User settings not initialized')

        common.settings.sync()
        for k in ActivePathSegmentTypes:
            v = common.settings.value(f'active/{k}')
            v = v if isinstance(v, str) and v else None
            common.active_paths[common.SynchronizedActivePaths][k] = v
        verify_path(common.SynchronizedActivePaths)


    if load_env:
        # Get the values from the environment
        for k in ActivePathSegmentTypes:
            v = os.environ.get(f'Bookmarks_ACTIVE_{k.upper()}', None)
            common.active_paths[EnvActivePaths][k] = v
        verify_path(common.EnvActivePaths)

        # Override the synchronized paths with the Env if they're valid.
        # Envs take precedence over synchronized paths, but only if a valid
        # asset has been set.
        _keys = ActivePathSegmentTypes[:ActivePathSegmentTypes.index('asset') + 1]
        if all(common.active_paths[EnvActivePaths][k] for k in _keys):
            for k in _keys:
                common.active_paths[SynchronizedActivePaths][k] = common.active_paths[EnvActivePaths][k]
        verify_path(SynchronizedActivePaths)

    if load_private:
        # Copy values from the synchronized paths to the private paths
        for k in ActivePathSegmentTypes:
            common.active_paths[PrivateActivePaths][k] = common.active_paths[SynchronizedActivePaths][k]
        verify_path(PrivateActivePaths)


def verify_path(active_mode):
    """Verify the active path values and unset any item, that refers to an invalid path.

    Args:
        active_mode (int): One of ``SynchronizedActivePaths`` or ``PrivateActivePaths``.

    """
    p = []
    for k in ActivePathSegmentTypes:
        if common.active_paths[active_mode][k]:
            p.append(common.active_paths[active_mode][k])

        # Check if the path exists
        _p = '/'.join(p)
        if not os.path.exists(_p) or _p not in common.bookmarks:
            common.active_paths[active_mode][k] = None

            # Unset all items that depend on the current path segment
            if active_mode == common.SynchronizedActivePaths:
                common.settings.setValue(f'active/{k}', None)



def active(k, path=False, args=False, mode=None):
    """Get an active path segment stored in the user settings.

    Args:
        k (str): One of the following segment names: `'server', 'job', 'root', 'asset', 'task', 'file'`
        path (bool, optional): If True, will return a path to the active item.
        args (bool, optional): If `True`, will return all components that make up the active path.
        mode (int, optional): One of `SynchronizedActivePaths`, `PrivateActivePaths` or `EnvActivePaths`.

    Returns:
        str: If `path` is `True`, will return a path to the active item or `None` if the path can't be constructed.
        tuple: If `args` is `True`, will return all components that make up the active path or
            `None` if the args can't be constructed.


    """
    if k not in _ActivePathSegmentTypes:
        raise KeyError('Invalid key')

    if path or args:
        _path = None
        _args = None
        idx = ActivePathSegmentTypes.index(k)
        v = tuple(
            common.active_paths[common.active_mode][k]
            for k in ActivePathSegmentTypes[:idx + 1]
        )

        if path:
            _path = '/'.join(v) if all(v) else None
            if args:
                return _path, _args
            return _path

        if args:
            _args = v if all(v) else None
            if path:
                return _path, _args
            return _args

    if mode is None:
        mode = common.active_mode
    return common.active_paths[mode][k]
