"""Set the version string."""
import os
import re
import sys

from PySide2 import QtCore

pkg_root = QtCore.QFileInfo(f'{__file__}{os.path.sep}..').absoluteFilePath()


STRINGS = {
    f'{pkg_root}/docs/source/conf.py': (re.compile(r'')),
    f'{pkg_root}/bookmarks/__init__.py': {},
    f'{pkg_root}/README.md': {},
    f'{pkg_root}/bookmarks/maya/plugin.py': {},
    f'{pkg_root}/installer/installer.iss': {},
    f'{pkg_root}/launcher/CMakeLists.txt': {},
}


for k, v in STRINGS.items():
    if not os.path.isfile(k):
        raise RuntimeError(f'{k} does not exist.')


