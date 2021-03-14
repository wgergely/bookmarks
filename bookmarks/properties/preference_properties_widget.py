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
        'name': u'Basic Settings',
        'icon': u'icon',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': u'Interface Scale',
                    'key': settings.UIScaleKey,
                    'validator': None,
                    'widget': preference_properties_widgets.ScaleWidget,
                    'placeholder': u'',
                    'description': u'Scales Bookmark\'s interface by the specified amount.\nUseful for high-dpi displays if the text is too small to read.\n\nTakes effect the next time Bookmarks is launched.',
                },
                1: {
                    'name': u'Show Menu Icons',
                    'key': settings.ShowMenuIconsKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Hide Menu Icons'),
                    'placeholder': u'Check to hide menu icons',
                    'description': u'Check to hide menu icons',
                },
            },
            1: {
                0: {
                    'name': u'Shotgun RV',
                    'key': settings.RVKey,
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': u'Path to RV, eg. "C:/apps/rv.exe"',
                    'description': u'Path to the RV executable.\n\nIf specified compatible media can be previewed in RV.',
                    'button': u'Pick',
                    'button2': u'Reveal'
                },
                1: {
                    'name': u'FFMpeg',
                    'key': settings.FFMpegKey,
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': u'Path to FFMpeg, eg. "C:/apps/ffmpeg.exe"',
                    'description': u'Path to the FFMpeg executable.\n\nIf specified, bookmarks can convert images sequences using FFMpeg.',
                    'button': u'Pick',
                    'button2': u'Reveal'
                },
            },
        },
    },
    1: {
        'name': u'Maya',
        'icon': u'maya',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': u'Set Workspace',
                    'key': settings.WorkspaceSyncKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Disable'),
                    'placeholder': None,
                    'description': u'By default, {} always sets the Maya Workspace to the currently active asset item. Check here to disable this behaviour.'.format(common.PRODUCT),
                },
            },
            1: {
                0: {
                    'name': u'Warn Workspace',
                    'key': settings.WorksapceWarningsKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Disable'),
                    'placeholder': None,
                    'description': u'Disabled warnings when the\ncurrent Workspace is changed by {}.'.format(common.PRODUCT),
                },
                1: {
                    'name': u'Warning on Save',
                    'key': settings.SaveWarningsKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Disable'),
                    'placeholder': None,
                    'description': u'Bookmarks will show a warning when a file is saved outside the current Workspace. Check the box above to disable.',
                },
            },
            2: {
                0: {
                    'name': u'Push Capture',
                    'key': settings.PushCaptureToRVKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Disable'),
                    'placeholder': None,
                    'description': u'When Shotgun RV is available the latest capture will automatically be pushed to RV for viewing. Check the box above to disable.',
                },
                1: {
                    'name': u'Reveal Capture',
                    'key': settings.RevealCaptureKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Disable'),
                    'placeholder': None,
                    'description': u'Check the box above to disable showing captures in the file explorer.',
                },
                2: {
                    'name': u'Publish Capture',
                    'key': settings.PublishCaptureKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Disable'),
                    'placeholder': None,
                    'description': u'The latest capture by default will be published into a "Latest" folder with using a generic filename.\nThis can be useful for creating quick edits with RV. Check the box above to disable.',
                },
            },
        },
    },
    2: {
        'name': u'About',
        'icon': None,
        'color': common.SECONDARY_TEXT,
        'groups': {
            0: {
                0: {
                    'name': u'Info',
                    'key': None,
                    'validator': None,
                    'widget': None,
                    'placeholder': u'',
                    'description': u'Check for new versions.',
                    'button': u'Check for Updates',
                    'button2': u'Build Info',
                },
                1: {
                    'name': u'Debug',
                    'key': None,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Enable Debug'),
                    'placeholder': u'',
                    'description': u'Enable Debug Messages.',
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
            fallback_thumb=u'settings_sm',
            parent=parent
        )

        self.debug_editor.stateChanged.connect(self.toggle_debug)

    def toggle_debug(self, state):
        common.DEBUG = self.debug_editor.isChecked()

    @common.error
    @common.debug
    def init_data(self, *args, **kwargs):
        self.thumbnail_editor.setDisabled(True)

        for section in SECTIONS.itervalues():
            for _section in section.itervalues():
                if not isinstance(_section, dict):
                    continue
                for group in _section.itervalues():
                    if not isinstance(group, dict):
                        continue
                    for row in group.itervalues():
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
        for k, v in self.changed_data.iteritems():
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
        _bin = k.replace(u'Path', u'')
        _filter = u'{}.exe'.format(
            _bin) if common.get_platform() == common.PlatformWindows else u'*.*'
        res = QtWidgets.QFileDialog.getOpenFileName(
            caption=u'Select {} Executable...'.format(_bin),
            filter=_filter,
            dir=u'/'
        )
        path, _ = res
        if not path:
            return
        editor.setText(path)
