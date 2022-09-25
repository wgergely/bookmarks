# -*- coding: utf-8 -*-
""":class:`PreferenceEditor` and helper classes used to set application-wide preferences.

Attributes:

    SECTIONS (dict): UI structure and content definitions.

"""
import functools
import importlib

from PySide2 import QtWidgets, QtCore, QtGui

from . import base
from .. import actions
from .. import common
from .. import ui

instance = None


def close():
    """Closes the :class:`PreferenceEditor` widget.

    """
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
    """Shows the :class:`PreferenceEditor` widget.

    """
    global instance
    close()
    instance = PreferenceEditor()
    instance.open()
    return instance


class ScaleWidget(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        size = QtCore.QSize(1, common.size(common.HeightRow) * 0.8)

        self.blockSignals(True)
        for n in common.ui_scale_factors:
            self.addItem(f'{int(n * 100)}%')

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

        bg = common.rgb(common.color(common.BackgroundDarkColor))
        bd = common.size(common.HeightSeparator)
        bc = common.rgb(common.color(common.SeparatorColor))
        r = common.size(common.WidthMargin) * 0.5
        c = common.rgb(common.color(common.TextDisabledColor))

        self.setStyleSheet(
            f'background-color:{bg};'
            f'border: {bd}px solid {bc};'
            f'border-radius:{r}px;'
            f'color:{c};'
            f'padding: {r}px {r}px {r}px {r}px;'
        )

        self.init_data()

    def init_data(self):
        mod = importlib.import_module(__name__.split('.', maxsplit=1)[0])
        self.setText(mod.info())

    def mouseReleaseEvent(self, event):
        mod = importlib.import_module(__name__.split('.', maxsplit=1)[0])
        QtGui.QDesktopServices.openUrl(mod.__website__)


class AboutWidget(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        if not self.parent():
            common.set_stylesheet(self)

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
        'name': 'Interface',
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
                    'description': 'Scales Bookmark\'s interface by the specified '
                                   'amount.\nUseful for high-dpi displays if the '
                                   'text is too small to read.\n\nTakes effect the '
                                   'next time Bookmarks is launched.',
                },
                1: {
                    'name': 'Context Menu Icon',
                    'key': common.ShowMenuIconsKey,
                    'validator': None,
                    'widget': functools.partial(
                        QtWidgets.QCheckBox, 'Hide Menu Icons'
                    ),
                    'placeholder': 'Check to hide menu icons',
                    'description': 'Check to hide menu icons',
                },
                2: {
                    'name': 'Thumbnail Background Color',
                    'key': common.ShowThumbnailBackgroundKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Show Color'),
                    'placeholder': 'Check to show a generic thumbnail background '
                                   'color for transparent images',
                    'description': 'Check to show a generic thumbnail background '
                                   'color for transparent images',
                },
                3: {
                    'name': 'Image Thumbnails',
                    'key': common.DontGenerateThumbnailsKey,
                    'validator': None,
                    'widget': functools.partial(
                        QtWidgets.QCheckBox, 'Don\'t Generate Thumbnails'
                    ),
                    'placeholder': 'Check to disable generating thumbnails from '
                                   'image files',
                    'description': 'Check to disable generating thumbnails from '
                                   'image files',
                },
            },
        },
    },
    1: {
        'name': 'Bookmark Editor',
        'icon': 'bookmark_item',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': 'Use Client/Project folders',
                    'key': common.JobsHaveSubdirs,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox,
                                                'Use Client/Project'),
                    'placeholder': '',
                    'description': 'In case your job folder uses a client/project like'
                                   'structure, tick this box. Leave it un-ticked if the'
                                   'project folders are nested directly in the server'
                                   'folder.',
                },
                1: {
                    'name': 'Maximum search depth',
                    'key': common.RecurseDepth,
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': '3',
                    'description': 'Set the maximum folder depth to parse.\nParsing large'
                                   'project folders will take a long time. This setting'
                                   'will limit the number of sub-directories the editor'
                                   'parses when looking for bookmark items.',
                },
            },
        },
    },
    2: {
        'name': 'Binaries',
        'icon': 'icon',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': None,
                    'key': 'environment',
                    'validator': None,
                    'widget': common.EnvPathEditor,
                    'placeholder': '',
                    'description': 'Edit external binary paths',
                },
            },
        },
    },
    3: {
        'name': 'Maya',
        'icon': 'maya',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': 'Set Maya Workspace',
                    'key': common.WorkspaceSyncKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': f'Click to disable setting the Maya workspace. By '
                                   f'default the Maya workspace is always set to be the'
                                   f'current active asset.',
                },
            },
            1: {
                0: {
                    'name': 'Workspace Save Warning',
                    'key': common.SaveWarningsKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'Click to disable warnings when saving files outside '
                                   'the current Workspace.'
                },
            },
            2: {
                0: {
                    'name': 'Push Capture to RV',
                    'key': common.PushCaptureToRVKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'When ShotGrid RV is available the latest '
                                   'capture will automatically be pushed to RV for '
                                   'viewing. Check the box above to disable.',
                },
                1: {
                    'name': 'Reveal Capture',
                    'key': common.RevealCaptureKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'Check the box above to disable showing '
                                   'captures in the file explorer.',
                },
                2: {
                    'name': 'Disable "Latest" Capture',
                    'key': common.PublishCaptureKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                    'placeholder': None,
                    'description': 'The last capture by default will be '
                                   'published into a "Latest" folder with using a '
                                   'generic filename.\nThis can be useful for '
                                   'creating quick edits in RV. Check the box '
                                   'above to disable.',
                },
            },
        },
    },
    4: {
        'name': 'About',
        'icon': None,
        'color': common.color(common.TextSecondaryColor),
        'groups': {
            0: {
                0: {
                    'name': 'Documentation',
                    'key': None,
                    'validator': None,
                    'widget': None,
                    'placeholder': '',
                    'description': 'Check for new versions.',
                    'button': 'GitHub',
                    'button2': 'Documentation',
                },
                1: {
                    'name': 'Info',
                    'key': None,
                    'validator': None,
                    'widget': None,
                    'placeholder': '',
                    'description': 'Check for new versions.',
                    'button': 'Check for Updates',
                    'button2': 'Build Info',
                },
                2: {
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
    """Property editor used to edit application preferences.

    """

    def __init__(self, parent=None):
        super().__init__(
            SECTIONS,
            None,
            None,
            None,
            db_table=None,
            fallback_thumb='settings',
            parent=parent
        )

        self.debug_editor.stateChanged.connect(self.toggle_debug)
        getattr(
            self, f'{common.DontGenerateThumbnailsKey}_editor'
        ).stateChanged.connect(actions.generate_thumbnails_changed)

        self.setWindowTitle('Preferences')

    def toggle_debug(self, state):
        common.debug_on = self.debug_editor.isChecked()

    @common.error
    @common.debug
    def init_data(self, *args, **kwargs):
        self.thumbnail_editor.setDisabled(True)
        self.load_saved_user_settings(common.SECTIONS['settings'])
        self._connect_settings_save_signals(common.SECTIONS['settings'])

    @common.error
    @common.debug
    def save_changes(self, *args, **kwargs):
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
    def documentation_button_clicked(self, *args, **kwargs):
        QtGui.QDesktopServices.openUrl(common.github_url)

    @common.error
    @common.debug
    @QtCore.Slot()
    def documentation_button2_clicked(self, *args, **kwargs):
        QtGui.QDesktopServices.openUrl(common.documentation_url)
