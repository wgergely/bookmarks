""":class:`PreferenceEditor` and helper classes used to set application-wide preferences.

"""
import functools
import importlib

from PySide2 import QtWidgets, QtCore, QtGui

from . import base
from .. import actions
from .. import common
from .. import ui


def close():
    """Closes the :class:`PreferenceEditor` widget.

    """
    if common.preference_editor_widget is None:
        return
    try:
        common.preference_editor_widget.close()
        common.preference_editor_widget.deleteLater()
    except:
        pass
    common.preference_editor_widget = None


def show():
    """Shows the :class:`PreferenceEditor` widget.

    """
    close()
    common.preference_editor_widget = PreferenceEditor()
    common.restore_window_geometry(common.preference_editor_widget)
    common.restore_window_state(common.preference_editor_widget)
    return common.preference_editor_widget


class UIScaleFactorsCombobox(QtWidgets.QComboBox):
    """Editor used to pick a ui scale value.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        """Initializes data.

        """
        size = QtCore.QSize(1, common.Size.RowHeight(0.8))

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


class PreferenceEditor(base.BasePropertyEditor):
    """Property editor used to edit application preferences.

    """
    #: UI layout definition
    sections = {
        0: {
            'name': 'Interface',
            'icon': 'icon',
            'color': None,
            'groups': {
                0: {
                    0: {
                        'name': 'Interface Scale',
                        'key': 'settings/ui_scale',
                        'validator': None,
                        'widget': UIScaleFactorsCombobox,
                        'placeholder': '',
                        'description': 'Scales Bookmark\'s interface by the specified '
                                       'amount.\nUseful for high-dpi displays if the '
                                       'text is too small to read.\n\nTakes effect the '
                                       'next time Bookmarks is launched.',
                    },
                    1: {
                        'name': 'Hide Context Menu Icons',
                        'key': 'settings/show_menu_icons',
                        'validator': None,
                        'widget': functools.partial(
                            QtWidgets.QCheckBox, 'Enable'
                        ),
                        'placeholder': 'Check to icons',
                        'description': 'Check to icons',
                    },
                    2: {
                        'name': 'Hide Thumbnail Backgrounds',
                        'key': 'settings/paint_thumbnail_bg',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                        'placeholder': 'Check to hide thumbnail background colors',
                        'description': 'Check to hide thumbnail background colors'
                    },
                    3: {
                        'name': 'Hide item descriptions',
                        'key': 'settings/hide_item_descriptions',
                        'validator': None,
                        'widget': functools.partial(
                            QtWidgets.QCheckBox, 'Enable'
                        ),
                        'placeholder': 'Check to hide item descriptions',
                        'description': 'Check to hide item descriptions',
                    },
                    4: {
                        'name': 'Disable Image Thumbnails',
                        'key': 'settings/disable_oiio',
                        'validator': None,
                        'widget': functools.partial(
                            QtWidgets.QCheckBox, 'Disable'
                        ),
                        'placeholder': 'Check to disable generating thumbnails from '
                                       'image files using OpenImageIO',
                        'description': 'Check to disable generating thumbnails from '
                                       'image files using OpenImageIO',
                    },
                },
                1: {
                    0: {
                        'name': 'Default to scene folder',
                        'key': 'settings/default_to_scenes_folder',
                        'validator': None,
                        'widget': functools.partial(
                            QtWidgets.QCheckBox, 'Enable'
                        ),
                        'placeholder': 'Default to scene folder',
                        'description': 'Default to the scene Folder when the active asset changes',
                        'help': 'If enabled, the files tab will always show the '
                                'contents of the scene folder (instead of the last '
                                'selected folder) when the active asset changes.',
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
            'name': 'ShotGrid',
            'icon': 'sg',
            'color': None,
            'groups': {
                0: {
                    0: {
                        'name': 'Login',
                        'key': 'sg_auth/login',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': '',
                        'description': 'Your ShotGrid login name',
                    },
                    1: {
                        'name': 'Password',
                        'key': 'sg_auth/password',
                        'validator': None,
                        'protect': True,
                        'widget': ui.LineEdit,
                        'placeholder': '',
                        'description': 'Your ShotGrid password',
                    },
                },
            },
        },
        4: {
            'name': 'Maya',
            'icon': 'maya',
            'color': None,
            'groups': {
                0: {
                    0: {
                        'name': 'Set Maya Workspace',
                        'key': 'maya/sync_workspace',
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
                        'key': 'maya/workspace_save_warnings',
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
                        'key': 'maya/push_capture_to_rv',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                        'placeholder': None,
                        'description': 'When ShotGrid RV is available the latest '
                                       'capture will automatically be pushed to RV for '
                                       'viewing. Check the box above to disable.',
                    },
                    1: {
                        'name': 'Reveal Capture',
                        'key': 'maya/reveal_capture',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                        'placeholder': None,
                        'description': 'Check the box above to disable showing '
                                       'captures in the file explorer.',
                    },
                    2: {
                        'name': 'Copy capture to "latest" folder',
                        'key': 'maya/publish_capture',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                        'placeholder': None,
                        'description': 'The last capture by default will be '
                                       'published into a "latest" folder with using a '
                                       'generic filename.\nThis can be useful for '
                                       'creating quick edits in RV. Check the box '
                                       'above to disable.',
                    },
                },
                3: {
                    0: {
                        'name': 'Set ShotGrid context',
                        'key': 'maya/set_sg_context',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Disable'),
                        'placeholder': None,
                        'description': 'If an asset is associated with a valid ShotGrid task, activating it will'
                                       'automatically set the ShotGrid context in Maya. Check the box above to '
                                       'disable.',
                    },
                },
            },
        },
        5: {
            'name': 'About',
            'icon': None,
            'color': common.Color.SecondaryText(),
            'groups': {
                0: {
                    0: {
                        'name': 'Help',
                        'key': None,
                        'validator': None,
                        'widget': None,
                        'placeholder': '',
                        'description': 'Show the online documentation',
                        'button': 'Open Documentation',
                    },
                    1: {
                        'name': 'Latest Version',
                        'key': 'app_version',
                        'validator': None,
                        'widget': None,
                        'placeholder': '',
                        'description': 'Check online for new versions.',
                        'button': 'Check for Updates',
                    },
                },
                1: {
                    0: {
                        'name': 'Current Versions',
                        'key': None,
                        'validator': None,
                        'widget': None,
                        'placeholder': '',
                        'description': '',
                        'help': importlib.import_module(
                            __name__.split('.', maxsplit=1)[0]
                        ).info(),
                    },
                },
                2: {
                    0: {
                        'name': 'Debugging',
                        'key': None,
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                        'placeholder': '',
                        'description': 'Enable debug messages.',
                    },
                    1: {
                        'name': '',
                        'key': 'reset_image_cache',
                        'validator': None,
                        'widget': None,
                        'placeholder': '',
                        'description': '',
                        'button': 'Reset Image Cache'
                    },
                },
            },
        },
    }

    def __init__(self, parent=None):
        super().__init__(
            None,
            None,
            None,
            db_table=None,
            fallback_thumb='settings',
            parent=parent
        )

        self.setWindowTitle('Preferences')

        self.settings_disable_oiio_editor.stateChanged.connect(
            actions.generate_thumbnails_changed
        )
        self.debugging_editor.stateChanged.connect(actions.toggle_debug)

    @common.error
    @common.debug
    def init_data(self, *args, **kwargs):
        """Initializes data.

        """
        self.thumbnail_editor.setDisabled(True)

        # Make sure to manually activate saving and loading of settings when adding
        # new sections.
        for k in ('settings', 'maya', 'sg_auth'):
            self.load_saved_user_settings(common.SECTIONS[k])
            self._connect_settings_save_signals(common.SECTIONS[k])

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        return None

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        return True

    @common.error
    @common.debug
    @QtCore.Slot()
    def help_button_clicked(self, *args, **kwargs):
        """Info button click action.

        """
        QtGui.QDesktopServices.openUrl(common.documentation_url)

    @common.error
    @common.debug
    @QtCore.Slot()
    def app_version_button_clicked(self, *args, **kwargs):
        """Info button click action.

        """
        common.show_message('Checking version', message_type=None, disable_animation=True, buttons=[])
        from ..versioncontrol import versioncontrol
        versioncontrol.check()

    @common.error
    @common.debug
    @QtCore.Slot()
    def reset_image_cache_button_clicked(self, *args, **kwargs):
        from .. import images
        images.init_image_cache()
