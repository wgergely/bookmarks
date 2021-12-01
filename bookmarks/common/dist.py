import os

from PySide2 import QtCore

from .. import common


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
