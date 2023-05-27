"""A utility script for managing the package's version number.

The script directly modifies the above files and replaces the current version with a new specified version:
    - docs/source/conf.py
    - bookmarks/__init__.py
    - README.md
    - bookmarks/maya/plugin.py
    - package/CMakeLists.txt
    - docs/source/guide.rst

"""

import os
import re
import sys

try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    raise RuntimeError('This script requires PySide2')

pkg_root = QtCore.QFileInfo(f'{__file__}{os.path.sep}..').absoluteFilePath()
STRINGS = {f'{pkg_root}/docs/source/conf.py': re.compile(r"release = \'([0-9]\.[0-9]\.[0-9])\'", flags=re.M),
    f'{pkg_root}/bookmarks/__init__.py': re.compile(r"Version-v([0-9]\.[0-9]\.[0-9])", flags=re.M),
    f'{pkg_root}/bookmarks/__init__.py': re.compile(r"__version__ = \'([0-9]\.[0-9]\.[0-9])\'", flags=re.M),
    f'{pkg_root}/README.md': re.compile(r"Version-v([0-9]\.[0-9]\.[0-9])", flags=re.M),
    f'{pkg_root}/bookmarks/maya/plugin.py': re.compile(r"__version__ = \'([0-9]\.[0-9]\.[0-9])\'", flags=re.M),
    f'{pkg_root}/package/CMakeLists.txt': re.compile(r"VERSION ([0-9]\.[0-9]\.[0-9])", flags=re.M),
    f'{pkg_root}/docs/source/guide.rst': re.compile(r'.*([0-9]\.[0-9]\.[0-9]).*', flags=re.M), }

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    with open(f'{pkg_root}/bookmarks/__init__.py', 'r', encoding='utf-8') as f:
        v = f.read()
        s = STRINGS[f'{pkg_root}/bookmarks/__init__.py'].search(v)
        if not s:
            raise RuntimeError(f'Could not parse "{pkg_root}/bookmarks/__init__.py"')
        current_version = s.group(1)

    dialog = QtWidgets.QInputDialog()
    dialog.setInputMode(QtWidgets.QInputDialog.TextInput)
    dialog.setWindowTitle('Enter Version')
    dialog.setLabelText('New Version')
    editor = dialog.findChild(QtWidgets.QLineEdit)
    editor.setPlaceholderText(current_version)

    if not dialog.exec_():
        raise RuntimeError('Stopping...')

    # Verify version string so it is of the form x.x.x
    version = editor.text()
    if not version:
        raise RuntimeError('Must enter a valid version')
    version = version.strip()
    if not re.match(r'[0-9]\.[0-9]\.[0-9]', version):
        raise RuntimeError('Version must be of the form x.x.x')

    # show confirmation dialog
    dialog = QtWidgets.QMessageBox()
    dialog.setWindowTitle('Confirm Version')
    dialog.setText(f'Update version from {current_version} to {version}?')
    dialog.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    dialog.setDefaultButton(QtWidgets.QMessageBox.Yes)
    if dialog.exec_() == QtWidgets.QMessageBox.No:
        raise RuntimeError('Stopping...')

    for k, v in STRINGS.items():
        if not os.path.isfile(k):
            raise RuntimeError(f'{k} does not exist.')

        with open(k, 'r', encoding='utf-8') as f:
            v = f.read()
            s = STRINGS[k].search(v)
            if not s:
                raise RuntimeError(f'Could not parse {k}')

            print(f'Updating {k}: {s.group(1)} -> {version}')

            v = re.sub(s.group(1), version, v)

        print('Writing changes...')
        with open(k, 'w', encoding='utf-8') as f:
            f.write(v)

    print('Version updated successfully.')
