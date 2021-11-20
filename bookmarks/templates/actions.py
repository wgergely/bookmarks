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
        source (str): Path to a source file.
        mode (str): A template mode, eg. 'job' or 'asset'

    Returns:
        str: Path to the saved template file, or `None`.

    """
    common.check_type(source, str)
    common.check_type(mode, str)

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
    file_info = QtCore.QFileInfo('{}/{}'.format(root, name))

    # Let's check if file exists before we copy anything...
    s = 'A template file with the same name exists already.'
    if file_info.exists() and not prompt:
        raise RuntimeError(s)

    if file_info.exists():
        mbox = ui.MessageBox(
            s,
            'Do you want to overwrite the existing file?',
            buttons=[ui.YesButton, ui.CancelButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return None
        QtCore.QFile.remove(file_info.filePath())

    # If copied successfully, let's reload the
    if not QtCore.QFile.copy(source, file_info.filePath()):
        raise RuntimeError('An unknown error occured adding the template.')

    common.signals.templatesChanged.emit()
    return file_info.filePath()


def extract_zip_template(source, destination, name):
    """Expands the selected source zip archive to `destination` as `name`.

    The contents will be expanded to a `{destination}/{name}` where name is an
    arbitary name of a job or an asset item to be created.

    Args:
        source (str):           Path to a *.zip archive.
        description (str):      Path to a folder
        name (str):             Name of the root folder where the arhive
                                    contents will be expanded to.

    Returns:
        str:                    Path to the expanded archive contents.

    """
    for arg in (source, destination, name):
        common.check_type(arg, str)

    if not destination:
        raise ValueError('Destination not set')

    file_info = QtCore.QFileInfo(destination)
    if not file_info.exists():
        raise RuntimeError(
            'Destination {} does not exist.'.format(file_info.filePath()))
    if not file_info.isWritable():
        raise RuntimeError(
            'Destination {} not writable'.format(file_info.filePath()))
    if not name:
        raise ValueError('Must enter a name.')

    source_file_info = file_info = QtCore.QFileInfo(source)
    if not source_file_info.exists():
        raise RuntimeError('{} does not exist.'.format(
            source_file_info.filePath()))

    dest_file_info = QtCore.QFileInfo('{}/{}'.format(destination, name))
    if dest_file_info.exists():
        raise RuntimeError('{} exists already.'.format(
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
        source (str): Path to a zip template file.

    """
    common.check_type(source, str)

    file_info = QtCore.QFileInfo(source)

    if not file_info.exists():
        raise RuntimeError('Template does not exist.')

    if prompt:
        mbox = ui.MessageBox(
            'Are you sure you want to delete this template?',
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
        mode (str): A template mode, eg. `JobTemplateMode`.

    """
    common.check_type(mode, str)

    dialog = QtWidgets.QFileDialog(parent=None)
    dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
    dialog.setViewMode(QtWidgets.QFileDialog.List)
    dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
    dialog.setNameFilters(['*.zip', ])
    dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
    dialog.setLabelText(
        QtWidgets.QFileDialog.Accept,
        'Select a {} template'.format(mode.title())
    )
    dialog.setWindowTitle(
        'Select *.zip archive to use as a {} template'.format(mode.lower())
    )
    if dialog.exec_() == QtWidgets.QDialog.Rejected:
        return
    source = next((f for f in dialog.selectedFiles()), None)
    if not source:
        return

    add_zip_template(source, mode)
