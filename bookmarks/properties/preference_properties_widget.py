# -*- coding: utf-8 -*-
"""Preferences widget used to set Application-wide preferences.

"""
import functools

from PySide2 import QtWidgets, QtCore

from .. import settings
from .. import common
from .. import ui
from .. import actions
from . import base
from . import preference_properties_widgets


instance = None


def close():
    global instance
    if instance is None:
        return
    try:
        instance.close()
        instance.deleteLater()
    except:
        pass
    instance = None


def show():
    global instance
    close()
    instance = PreferencesWidget()
    instance.open()
    return instance


SECTIONS = {
    0: {
        'name': 'Basic Settings',
        'icon': 'icon',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': 'Interface Scale',
                    'key': settings.UIScaleKey,
                    'validator': None,
                    'widget': preference_properties_widgets.ScaleWidget,
                    'placeholder': '',
                    'description': 'Scales Bookmark\'s interface by the specified amount.\nUseful for high-dpi displays if the text is too small to read.\n\nTakes effect the next time Bookmarks is launched.',
                },
                1: {
                    'name': 'Show Menu Icons',
                    'key': settings.ShowMenuIconsKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Hide Menu Icons'),
                    'placeholder': 'Check to hide menu icons',
                    'description': 'Check to hide menu icons',
                },
            },
            1: {
                0: {
                    'name': 'Shotgun RV',
                    'key': settings.RVKey,
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'Path to RV, eg. "C:/apps/rv.exe"',
                    'description': 'Path to the RV executable.\n\nIf specified compatible media can be previewed in RV.',
                    'button': 'Pick',
                    'button2': 'Reveal'
                },
                1: {
                    'name': 'FFMpeg',
                    'key': settings.FFMpegKey,
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'Path to FFMpeg, eg. "C:/apps/ffmpeg.exe"',
                    'description': 'Path to the FFMpeg executable.\n\nIf specified, bookmarks can convert images sequences using FFMpeg.',
                    'button': 'Pick',
                    'button2': 'Reveal'
                },
            },
        },
    },
    1: {
        'name': 'Maya',
        'icon': 'maya',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': 'Set Workspace',
                    'key': settings.WorkspaceSyncKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'By default, {} always sets the Maya Workspace to the currently active asset item. Check here to disable this behaviour.'.format(common.PRODUCT),
                },
            },
            1: {
                0: {
                    'name': 'Warn Workspace',
                    'key': settings.WorksapceWarningsKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'Disabled warnings when the\ncurrent Workspace is changed by {}.'.format(common.PRODUCT),
                },
                1: {
                    'name': 'Warning on Save',
                    'key': settings.SaveWarningsKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'Bookmarks will show a warning when a file is saved outside the current Workspace. Check the box above to disable.',
                },
            },
            2: {
                0: {
                    'name': 'Push Capture',
                    'key': settings.PushCaptureToRVKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'When Shotgun RV is available the latest capture will automatically be pushed to RV for viewing. Check the box above to disable.',
                },
                1: {
                    'name': 'Reveal Capture',
                    'key': settings.RevealCaptureKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'Check the box above to disable showing captures in the file explorer.',
                },
                2: {
                    'name': 'Publish Capture',
                    'key': settings.PublishCaptureKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'The latest capture by default will be published into a "Latest" folder with using a generic filename.\nThis can be useful for creating quick edits with RV. Check the box above to disable.',
                },
            },
        },
    },
    2: {
        'name': 'About',
        'icon': None,
        'color': common.SECONDARY_TEXT,
        'groups': {
            0: {
                0: {
                    'name': 'Info',
                    'key': None,
                    'validator': None,
                    'widget': None,
                    'placeholder': '',
                    'description': 'Check for new versions.',
                    'button': 'Check for Updates',
                    'button2': 'Build Info',
                },
                1: {
                    'name': 'Debug',
                    'key': None,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Enable Debug'),
                    'placeholder': '',
                    'description': 'Enable Debug Messages.',
                },
            },
        },
    },
}


class PreferencesWidget(base.PropertiesWidget):
    def __init__(self, parent=None):
        super(PreferencesWidget, self).__init__(
            SECTIONS,
            None,
            None,
            None,
            db_table=None,
            fallback_thumb='settings_sm',
            parent=parent
        )

        self.debug_editor.stateChanged.connect(self.toggle_debug)

    def toggle_debug(self, state):
        common.DEBUG = self.debug_editor.isChecked()

    @common.error
    @common.debug
    def init_data(self, *args, **kwargs):
        self.thumbnail_editor.setDisabled(True)

        for section in SECTIONS.values():
            for _section in section.values():
                if not isinstance(_section, dict):
                    continue
                for group in _section.values():
                    if not isinstance(group, dict):
                        continue
                    for row in group.values():
                        if 'key' not in row or not row['key']:
                            continue
                        if not hasattr(self, row['key'] + '_editor'):
                            continue

                        editor = getattr(self, row['key'] + '_editor')
                        v = settings.instance().value(
                            settings.SettingsSection,
                            row['key'],
                        )
                        self.current_data[row['key']] = v

                        if v is not None:
                            editor.blockSignals(True)
                            try:
                                if hasattr(editor, 'setCheckState') and v is not None:
                                    editor.setCheckState(QtCore.Qt.CheckState(v))
                                elif hasattr(editor, 'setText') and v is not None:
                                    editor.setText(v)
                                elif hasattr(editor, 'setCurrentText') and v is not None:
                                    editor.setCurrentText(v)
                            except:
                                pass
                            finally:
                                editor.blockSignals(False)

                        self._connect_editor(row['key'], None, editor)

    @common.error
    @common.debug
    def save_changes(self, *args, **kwargs):
        for k, v in self.changed_data.items():
            settings.instance().setValue(settings.SettingsSection, k, v)
        return True

    @common.error
    @common.debug
    @QtCore.Slot()
    def info_button_clicked(self, *args, **kwargs):
        import bookmarks.versioncontrol.versioncontrol as versioncontrol
        versioncontrol.check()

    @common.error
    @common.debug
    @QtCore.Slot()
    def info_button2_clicked(self, *args, **kwargs):
        w = preference_properties_widgets.AboutWidget()
        w.open()

    @common.error
    @common.debug
    @QtCore.Slot()
    def RVPath_button_clicked(self, *args, **kwargs):
        self._pick_file(settings.RVKey)

    @common.error
    @common.debug
    @QtCore.Slot()
    def RVPath_button2_clicked(self, *args, **kwargs):
        editor = getattr(self, settings.RVKey + '_editor')
        if not editor.text():
            return
        actions.reveal(editor.text())

    @common.error
    @common.debug
    @QtCore.Slot()
    def FFMpegPath_button_clicked(self, *args, **kwargs):
        self._pick_file(settings.FFMpegKey)

    @common.error
    @common.debug
    @QtCore.Slot()
    def FFMpegPath_button2_clicked(self, *args, **kwargs):
        editor = getattr(self, settings.FFMpegKey + '_editor')
        if not editor.text():
            return
        actions.reveal(editor.text())

    def _pick_file(self, k):
        editor = getattr(self, k + '_editor')
        _bin = k.replace('Path', '')
        _filter = '{}.exe'.format(
            _bin) if common.get_platform() == common.PlatformWindows else '*.*'
        res = QtWidgets.QFileDialog.getOpenFileName(
            caption='Select {} Executable...'.format(_bin),
            filter=_filter,
            dir='/'
        )
        path, _ = res
        if not path:
            return
        editor.setText(path)
