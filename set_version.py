"""Set the version string."""
import os
import re

from PySide2 import QtWidgets, QtCore

pkg_root = QtCore.QFileInfo(f'{__file__}{os.path.sep}..').absoluteFilePath()

STRINGS = {
    f'{pkg_root}/docs/source/conf.py': re.compile(r"release = \'([0-9]\.[0-9]\.[0-9])\'",
                                                  flags=re.MULTILINE),
    f'{pkg_root}/bookmarks/__init__.py': re.compile(r"Version-v([0-9]\.[0-9]\.[0-9])",
                                                    flags=re.MULTILINE),
    f'{pkg_root}/bookmarks/__init__.py': re.compile(
        r"__version__ = \'([0-9]\.[0-9]\.[0-9])\'", flags=re.MULTILINE),
    f'{pkg_root}/README.md': re.compile(r"Version-v([0-9]\.[0-9]\.[0-9])",
                                        flags=re.MULTILINE),
    f'{pkg_root}/bookmarks/maya/plugin.py': re.compile(
        r"__version__ = \'([0-9]\.[0-9]\.[0-9])\'", flags=re.MULTILINE),
    f'{pkg_root}/package/CMakeLists.txt': re.compile(
        r"VERSION ([0-9]\.[0-9]\.[0-9])", flags=re.MULTILINE),
    f'{pkg_root}/docs/source/guide.rst': re.compile(r'.*([0-9]\.[0-9]\.[0-9]).*',
                                                    flags=re.MULTILINE),
}

app = QtWidgets.QApplication()
version, res = QtWidgets.QInputDialog.getText(None, 'Enter Version', 'New Version')

if not res:
    raise RuntimeError('Stopping...')
if not version:
    raise RuntimeError('Must enter a valid version')

for k, v in STRINGS.items():
    if not os.path.isfile(k):
        raise RuntimeError(f'{k} does not exist.')

    with open(k, 'r', encoding='utf-8') as f:
        v = f.read()
        s = STRINGS[k].search(v)
        if not s:
            raise RuntimeError(f'Could not parse {k}')
        v = re.sub(s.group(1), version, v)

    with open(k, 'w', encoding='utf-8') as f:
        f.write(v)
