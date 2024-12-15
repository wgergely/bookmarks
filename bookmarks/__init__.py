import importlib
import platform
import sys

#: Package author
__author__ = 'Gergely Wootsch'

#: Project homepage
__website__ = 'https://bookmarks-vfx.com'

#: Author email
__email__ = 'hello@gergely-wootsch.com'

#: Project version
__version__ = '0.9.2'

#: Project version
__version_info__ = __version__.split('.')

#: Project copyright
__copyright__ = f'Copyright (c) 2024 {__author__}'

# Specify python support
if sys.version_info[0] < 3 and sys.version_info[1] < 9:
    raise RuntimeError('Bookmarks requires Python 3.9.0 or later.')


def info():
    """Returns an informative string about the project environment and author.

    Returns:
        str: An informative string.

    """
    py_ver = platform.python_version()
    py_c = platform.python_compiler()
    oiio_ver = importlib.import_module('OpenImageIO').__version__
    qt_ver = importlib.import_module('PySide2.QtCore').__version__
    sg_ver = importlib.import_module('shotgun_api3').__version__

    return '\n'.join(
        (
            __copyright__,
            f'E-Mail: {__email__}',
            f'Website: {__website__}',
            '\nPackages\n'
            f'Python {py_ver} {py_c}',
            f'Bookmarks {__version__}',
            f'PySide2 {qt_ver}',
            f'OpenImageIO {oiio_ver}',
            f'ShotGrid API {sg_ver}',
        )
    )


def exec_(print_info=True, show_ui_logs=False):
    """Initializes all required submodules and data and launches shows the app's main window.

    """
    from . import common
    with common.initialize(mode=common.Mode.Standalone, run_app=True, show_ui_logs=show_ui_logs):
        if print_info:
            print(info())

        from . import standalone
        standalone.show()
