# -*- coding: utf-8 -*-
"""Template actions.

"""
import zipfile
from PySide2 import QtCore, QtWidgets, QtGui

from .. import common
from .. import ui


def add_zip_template(source, mode, prompt=False):
    """Adds the selected source zip archive as a `mode` template file.

    Args:
        source (unicode): Path to a source file.
        mode (unicode): A template mode, eg. 'job' or 'asset'

    Returns:
        unicode: Path to the saved template file, or `None`.

    """
    if not isinstance(source, unicode):
        raise TypeError('Invalid type. Expected {}, got {}.'.format(
            unicode, type(source)))
    if not isinstance(mode, unicode):
        raise TypeError(
            'Invalid type. Expected {}, got {}.'.format(unicode, type(mode)))

    file_info = QtCore.QFileInfo(source)
    if not file_info.exists():
        raise RuntimeError('Source does not exist.')

    # Test the zip before saving it
    if not zipfile.is_zipfile(source):
        raise RuntimeError('Source is not a zip file.')

    with zipfile.ZipFile(source) as f:
        corrupt = f.testzip()
        if corrupt:
            raise RuntimeError(
                'The zip archive seems corrupted: {}'.format(corrupt))

    from . import templates
    root = templates.get_template_folder(mode)
    name = QtCore.QFileInfo(source).fileName()
    file_info = QtCore.QFileInfo(u'{}/{}'.format(root, name))

    # Let's check if file exists before we copy anything...
    s = u'A template file with the same name exists already.'
    if file_info.exists() and not prompt:
        raise RuntimeError(s)

    if file_info.exists():
        mbox = ui.MessageBox(
            s,
            u'Do you want to overwrite the existing file?',
            buttons=[ui.YesButton, ui.CancelButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return None
        QtCore.QFile.remove(file_info.filePath())

    # If copied successfully, let's reload the
    if not QtCore.QFile.copy(source, file_info.filePath()):
        raise RuntimeError(u'An unknown error occured adding the template.')

    common.signals.templatesChanged.emit()
    return file_info.filePath()


def extract_zip_template(source, destination, name):
    """Expands the selected source zip archive to `destination` as `name`.

    The contents will be expanded to a `{destination}/{name}` where name is an
    arbitary name of a job or an asset item to be created.

    Args:
        source (unicode):           Path to a *.zip archive.
        description (unicode):      Path to a folder
        name (unicode):             Name of the root folder where the arhive
                                    contents will be expanded to.

    Returns:
        unicode:                    Path to the expanded archive contents.

    """
    for arg in (source, destination, name):
        if not isinstance(arg, unicode):
            raise TypeError(
                'Invalid type. Expected {}, got {}'.format(unicode, type(arg)))

    if not destination:
        raise ValueError('Destination not set')

    file_info = QtCore.QFileInfo(destination)
    if not file_info.exists():
        raise RuntimeError(
            u'Destination {} does not exist.'.format(file_info.filePath()))
    if not file_info.isWritable():
        raise RuntimeError(
            'Destination {} not writable'.format(file_info.filePath()))
    if not name:
        raise ValueError('Must enter a name.')

    source_file_info = file_info = QtCore.QFileInfo(source)
    if not source_file_info.exists():
        raise RuntimeError(u'{} does not exist.'.format(
            source_file_info.filePath()))

    dest_file_info = QtCore.QFileInfo(u'{}/{}'.format(destination, name))
    if dest_file_info.exists():
        raise RuntimeError(u'{} exists already.'.format(
            dest_file_info.fileName()))

    with zipfile.ZipFile(source_file_info.absoluteFilePath(), 'r', zipfile.ZIP_DEFLATED) as f:
        corrupt = f.testzip()
        if corrupt:
            raise RuntimeError(
                'This zip archive seems to be corrupt: {}'.format(corrupt))

        f.extractall(
            dest_file_info.absoluteFilePath(),
            members=None,
            pwd=None
        )

    common.signals.templateExpanded.emit(dest_file_info.filePath())
    return dest_file_info.filePath()


def remove_zip_template(source, prompt=True):
    """Deletes a zip template file from the disk.

    Args:
        source (unicode): Path to a zip template file.

    """
    if not isinstance(source, unicode):
        raise TypeError('Invalid type. Expected {}, got {}'.format(
            unicode, type(source)))
    file_info = QtCore.QFileInfo(source)

    if not file_info.exists():
        raise RuntimeError('Template does not exist.')

    if prompt:
        mbox = ui.MessageBox(
            u'Are you sure you want to delete this template?',
            buttons=[ui.CancelButton, ui.YesButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return

    if not QtCore.QFile.remove(source):
        raise RuntimeError('Could not delete the template archive.')

    common.signals.templatesChanged.emit()


@common.error
@common.debug
def pick_template(mode):
    """Prompts the user to pick a new `*.zip` file containing a template
    directory structure.

    The template is copied to ``%localappdata%/[product]/[mode]_templates/*.zip``
    folder.

    Args:
        mode (unicode): A template mode, eg. `JobTemplateMode`.

    """
    if not isinstance(mode, unicode):
        raise TypeError(
            'Invalid type. Expected {}, got {}'.format(unicode, type(mode)))

    dialog = QtWidgets.QFileDialog(parent=None)
    dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
    dialog.setViewMode(QtWidgets.QFileDialog.List)
    dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
    dialog.setNameFilters([u'*.zip', ])
    dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
    dialog.setLabelText(
        QtWidgets.QFileDialog.Accept,
        u'Select a {} template'.format(mode.title())
    )
    dialog.setWindowTitle(
        u'Select *.zip archive to use as a {} template'.format(mode.lower())
    )
    if dialog.exec_() == QtWidgets.QDialog.Rejected:
        return
    source = next((f for f in dialog.selectedFiles()), None)
    if not source:
        return

    add_zip_template(source, mode)
