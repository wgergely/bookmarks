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
        size = QtCore.QSize(1, common.size(common.size_row_height) * 0.8)

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


#: UI layout definition
SECTIONS = {
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
                    'name': 'Jobs have clients',
                    'key': 'settings/jobs_have_clients',
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                    'placeholder': '',
                    'description': 'In case your job folder uses a client/project like '
                                   'structure, tick this box. Leave it un-ticked if the '
                                   'project folders are nested directly in the server'
                                   'folder.',
                    'help': 'Enable if jobs have separate <span style="color:white">client/project</span> folders. By '
                            'default, Bookmarks assumes jobs are kept directly in the '
                            'root of the server folder but you can override this here.'
                },
                1: {
                    'name': 'Bookmark item search depth',
                    'key': 'settings/job_scan_depth',
                    'validator': base.int_validator,
                    'widget': ui.LineEdit,
                    'placeholder': '3',
                    'description': 'Set the maximum folder depth to parse. Parsing large '
                                   'project folders will take a long time. This setting '
                                   'will limit the number of sub-directories the editor '
                                   'parses when looking for bookmark items.',
                    'help': 'This setting will limit the number of sub-directories the '
                            'editor will look into when looking for bookmark items.',
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
                    'name': 'Disable "Latest" Capture',
                    'key': 'maya/publish_capture',
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
        'color': common.color(common.color_secondary_text),
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
                        __name__.split('.', maxsplit=1)[0]).info(),
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
                2: {
                    'name': '',
                    'key': 'reset_databases',
                    'validator': None,
                    'widget': None,
                    'placeholder': '',
                    'description': '',
                    'button': 'Reset Database Connections'
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

        self.settings_disable_oiio_editor.stateChanged.connect(
            actions.generate_thumbnails_changed
        )
        self.setWindowTitle('Preferences')

        self.debugging_editor.stateChanged.connect(actions.toggle_debug)

    @common.error
    @common.debug
    def init_data(self, *args, **kwargs):
        """Initializes data.

        """
        self.thumbnail_editor.setDisabled(True)
        self.load_saved_user_settings(common.SECTIONS['settings'])
        self._connect_settings_save_signals(common.SECTIONS['settings'])

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
        ui.MessageBox('Checking version...').open()
        from ..versioncontrol import versioncontrol
        versioncontrol.check()

    @common.error
    @common.debug
    @QtCore.Slot()
    def reset_image_cache_button_clicked(self, *args, **kwargs):
        from .. import images
        images.init_image_cache()

    @common.error
    @common.debug
    @QtCore.Slot()
    def reset_databases_button_clicked(self, *args, **kwargs):
        from .. import database
        database.remove_all_connections()
