# -*- coding: utf-8 -*-
"""Preferences widget used to set Application-wide preferences.

"""
import functools

from PySide2 import QtWidgets, QtCore, QtGui


from .. import common
from .. import ui
from .. import actions
from . import base


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
    instance = PreferenceEditor()
    instance.open()
    return instance


class ScaleWidget(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.init_data()

    def init_data(self):
        size = QtCore.QSize(1, common.size(common.HeightRow) * 0.8)

        self.blockSignals(True)
        for n in common.ui_scale_factors:
            name = '{}%'.format(int(n * 100))
            self.addItem(name)

            self.setItemData(
                self.count() - 1,
                n,
                role=QtCore.Qt.UserRole
            )
            self.setItemData(
                self.count() - 1,
                size,
                role=QtCore.Qt.SizeHintRole
            )
        self.setCurrentText('100%')
        self.blockSignals(False)


class AboutLabel(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet(
            'background-color:{bg};border: {bd}px solid {bc};border-radius:{r}px;color:{c};padding: {r}px {r}px {r}px {r}px;'.format(
                bg=common.rgb(common.color(common.BackgroundDarkColor)),
                bd=common.size(common.HeightSeparator),
                bc=common.rgb(common.color(common.SeparatorColor)),
                r=common.size(common.WidthMargin) * 0.5,
                c=common.rgb(common.color(common.TextDisabledColor))
            )
        )
        self.init_data()

    def init_data(self):
        import importlib
        mod = importlib.import_module(__name__.split('.', maxsplit=1)[0])
        self.setText(mod.get_info())

    def mouseReleaseEvent(self, event):
        QtGui.QDesktopServices.openUrl(common.ABOUT_URL)


class AboutWidget(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        if not self.parent():
            common.set_custom_stylesheet(self)

        self.label = None
        self.ok_button = None

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.size(common.WidthMargin)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        self.label = AboutLabel(parent=self)
        self.ok_button = ui.PaintedButton('Close', parent=self)

        self.layout().addWidget(self.label, 1)
        self.layout().addWidget(self.ok_button, 0)

    def _connect_signals(self):
        self.ok_button.clicked.connect(self.close)


SECTIONS = {
    0: {
        'name': 'Basic Settings',
        'icon': 'icon',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': 'Interface Scale',
                    'key': common.UIScaleKey,
                    'validator': None,
                    'widget': ScaleWidget,
                    'placeholder': '',
                    'description': 'Scales Bookmark\'s interface by the specified amount.\nUseful for high-dpi displays if the text is too small to read.\n\nTakes effect the next time Bookmarks is launched.',
                },
                1: {
                    'name': 'Context Menu Icon',
                    'key': common.ShowMenuIconsKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Hide Menu Icons'),
                    'placeholder': 'Check to hide menu icons',
                    'description': 'Check to hide menu icons',
                },
                2: {
                    'name': 'Thumbnail Background Color',
                    'key': common.ShowThumbnailBackgroundKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Show Color'),
                    'placeholder': 'Check to show a generic thumbnail background color for transparent images',
                    'description': 'Check to show a generic thumbnail background color for transparent images',
                },
            },
            1: {
                0: {
                    'name': 'Shotgun RV',
                    'key': common.RVKey,
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'Path to RV, eg. "C:/apps/rv.exe"',
                    'description': 'Path to the RV executable.\n\nWhen specified, compatible media can be previewed in RV.',
                    'button': 'Pick',
                    'button2': 'Reveal'
                },
                1: {
                    'name': 'FFMpeg',
                    'key': common.FFMpegKey,
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
                    'key': common.WorkspaceSyncKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'By default, {} always sets the Maya Workspace to the currently active asset item. Check here to disable this behaviour.'.format(common.product),
                },
            },
            1: {
                0: {
                    'name': 'Warn Workspace',
                    'key': common.WorkspaceWarningsKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'Disabled warnings when the\ncurrent Workspace is changed by {}.'.format(common.product),
                },
                1: {
                    'name': 'Warning on Save',
                    'key': common.SaveWarningsKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'Bookmarks will show a warning when a file is saved outside the current Workspace. Check the box above to disable.',
                },
            },
            2: {
                0: {
                    'name': 'Push Capture',
                    'key': common.PushCaptureToRVKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'When Shotgun RV is available the latest capture will automatically be pushed to RV for viewing. Check the box above to disable.',
                },
                1: {
                    'name': 'Reveal Capture',
                    'key': common.RevealCaptureKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'Check the box above to disable showing captures in the file explorer.',
                },
                2: {
                    'name': 'Publish Capture',
                    'key': common.PublishCaptureKey,
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
        'color': common.color(common.TextSecondaryColor),
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


class PreferenceEditor(base.BasePropertyEditor):
    def __init__(self, parent=None):
        super().__init__(
            SECTIONS,
            None,
            None,
            None,
            db_table=None,
            fallback_thumb='settings_sm',
            hide_thumbnail_editor=True,
            parent=parent
        )

        self.debug_editor.stateChanged.connect(self.toggle_debug)
        self.setWindowTitle('Preferences')

    def toggle_debug(self, state):
        common.debug_on = self.debug_editor.isChecked()

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
                        v = common.settings.value(
                            common.SettingsSection,
                            row['key'],
                        )
                        self.current_data[row['key']] = v

                        if v is not None:
                            editor.blockSignals(True)
                            try:
                                if hasattr(editor, 'setCheckState') and v is not None:
                                    editor.setCheckState(
                                        QtCore.Qt.CheckState(v))
                                elif hasattr(editor, 'setText') and v is not None:
                                    editor.setText(v)
                                elif hasattr(editor, 'setCurrentText') and v is not None:
                                    editor.setCurrentText(v)
                            except:
                                pass
                            finally:
                                editor.blockSignals(False)

                        self._connect_editor_signals(row['key'], None, editor)

    @common.error
    @common.debug
    def save_changes(self, *args, **kwargs):
        for k, v in self.changed_data.items():
            common.settings.setValue(common.SettingsSection, k, v)
        return True

    @common.error
    @common.debug
    @QtCore.Slot()
    def info_button_clicked(self, *args, **kwargs):
        from ..versioncontrol import versioncontrol
        versioncontrol.check()

    @common.error
    @common.debug
    @QtCore.Slot()
    def info_button2_clicked(self, *args, **kwargs):
        w = AboutWidget(parent=self)
        w.open()

    @common.error
    @common.debug
    @QtCore.Slot()
    def RVPath_button_clicked(self, *args, **kwargs):
        self._pick_file(common.RVKey)

    @common.error
    @common.debug
    @QtCore.Slot()
    def RVPath_button2_clicked(self, *args, **kwargs):
        editor = getattr(self, common.RVKey + '_editor')
        if not editor.text():
            return
        actions.reveal(editor.text())

    @common.error
    @common.debug
    @QtCore.Slot()
    def FFMpegPath_button_clicked(self, *args, **kwargs):
        self._pick_file(common.FFMpegKey)

    @common.error
    @common.debug
    @QtCore.Slot()
    def FFMpegPath_button2_clicked(self, *args, **kwargs):
        editor = getattr(self, common.FFMpegKey + '_editor')
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

    def sizeHint(self):
        return QtCore.QSize(common.size(common.DefaultWidth), common.size(common.DefaultHeight) * 1.5)
