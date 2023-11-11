"""The widget used to edit bookmark item properties.

"""
from PySide2 import QtCore, QtGui

from . import base
from . import base_widgets
from .. import actions
from .. import application_launcher
from .. import common
from .. import database
from .. import ui
from ..shotgun import actions as sg_actions
from ..shotgun import shotgun


def close():
    """Shows the :class:`BookmarkPropertyEditor` editor.

    """
    if common.bookmark_property_editor is None:
        return
    try:
        common.bookmark_property_editor.close()
        common.bookmark_property_editor.deleteLater()
    except:
        pass
    common.bookmark_property_editor = None


def show(server, job, root):
    """Shows the :class:`BookmarkPropertyEditor` editor.

    Args:
        server (str): 'server' path segment.
        job (str): 'job' path segment.
        root (str): 'root' path segment.

    Returns:
        The editor instance.

    """
    close()
    common.bookmark_property_editor = BookmarkPropertyEditor(
        server,
        job,
        root,
    )
    common.restore_window_geometry(common.bookmark_property_editor)
    common.restore_window_state(common.bookmark_property_editor)
    return common.bookmark_property_editor


class BookmarkPropertyEditor(base.BasePropertyEditor):
    """The widget containing all the UI elements used to edit
    bookmark item properties (such as frame-rate, resolution, or SG linking).

    """
    #: UI layout definition
    sections = {
        0: {
            'name': 'Settings',
            'icon': 'bookmark',
            'color': common.color(common.color_dark_background),
            'groups': {
                0: {
                    0: {
                        'name': 'Prefix',
                        'key': 'prefix',
                        'validator': base.name_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Custom prefix, e.g. \'MYB\'',
                        'description': 'A short name of the bookmark (or job) used '
                                       'when saving files.\n\ne.g. '
                                       '\'MYB_sh0010_anim_v001.ma\' where \'MYB\' is '
                                       'the prefix specified here.',
                        'button': 'Suggest'
                    },
                },
                1: {
                    0: {
                        'name': 'Description',
                        'key': 'description',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'A short description, e.g. \'Character assets\'',
                        'description': 'A description of this bookmark, '
                                       'e.g. \'Character assets\'.',
                    },
                },
                2: {
                    0: {
                        'name': 'Frame-rate',
                        'key': 'framerate',
                        'validator': base.float_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Frame-rate, e.g. \'23.976\'',
                        'description': 'The frame-rate of the bookmark, e.g. '
                                       '\'25.0\'.'
                    },
                    1: {
                        'name': 'Width',
                        'key': 'width',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Width in pixels',
                        'description': 'The output width in pixels, e.g. \'1920\''
                    },
                    2: {
                        'name': 'Height',
                        'key': 'height',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Height in pixels',
                        'description': 'The output height in pixels, e.g. \'1080\''
                    },
                    3: {
                        'name': 'Default Start Frame',
                        'key': 'startframe',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Start frame, e.g. \'1001\'',
                        'description': 'A default start frame for all subsequent '
                                       'assets.\n\nThis can be useful when the project '
                                       'has a custom start frame, e.g. \'1001\' instead '
                                       'of \'1\' or \'0\'.',
                    },
                    4: {
                        'name': 'Default Duration',
                        'key': 'duration',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Duration, e.g. \'150\'',
                        'description': 'The default duration of an asset in frames, '
                                       'e.g. \'150\'',
                    },
                },
                4: {
                    0: {
                        'name': 'Bookmark Display Name',
                        'key': 'bookmark_display_token',
                        'validator': base.token_validator,
                        'widget': ui.LineEdit,
                        'placeholder': '{server}/{job}/{root}',
                        'description': 'Specify the token used to display bookmark items',
                        'button': '+'
                    },
                    1: {
                        'name': 'Asset Display Name',
                        'key': 'asset_display_token',
                        'validator': base.token_validator,
                        'widget': ui.LineEdit,
                        'placeholder': '{asset}',
                        'description': 'Specify the token used to display asset items',
                        'button': '+'
                    },
                },
            }
        },
        1: {
            'name': 'ShotGrid Connection',
            'icon': 'sg',
            'color': None,
            'groups': {
                0: {
                    0: {
                        'name': 'Domain',
                        'key': 'shotgun_domain',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'Domain, e.g. https://mystudio.shotgunstudio.com',
                        'description': 'The domain, including http:// or https://, '
                                       'used by shotgun. e.g. '
                                       '\'https://mystudio.shotgunstudio.com\'',
                        'button': 'Visit',
                        'button2': 'Verify'
                    },
                    1: {
                        'name': 'Script Name',
                        'key': 'shotgun_scriptname',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'my-sg-script',
                        'description': 'A name of a ShotGrid Script.',
                    },
                    2: {
                        'name': 'API Key',
                        'key': 'shotgun_api_key',
                        'validator': None,
                        'protect': True,
                        'widget': ui.LineEdit,
                        'placeholder': 'abcdefghijklmno3bqr*1',
                        'description': 'A ShotGrid Script API Key, '
                                       'e.g. \'abcdefghijklmno3bqr*1\'.\n\nA valid '
                                       'script has to be set up for your organisation '
                                       'for Bookmarks to be able to connect to '
                                       'ShotGrid. Consult the ShotGrid documentation for '
                                       'details on how to set this up.',
                        'help': 'Make sure ShotGrid has a valid API Script set up. This '
                                'can be done from the ShotGrid Admin - Scripts option.',
                    },
                },
            },
        },
        2: {
            'name': 'ShotGrid Entity',
            'icon': 'sg',
            'color': None,
            'groups': {
                0: {
                    0: {
                        'name': 'Link',
                        'key': 'link',
                        'validator': None,
                        'widget': None,
                        'placeholder': None,
                        'description': 'Link item with a ShotGrid Entity',
                        'button': 'Link with ShotGrid Entity',
                    },
                },
                1: {
                    0: {
                        'name': 'ShotGrid Entity Type',
                        'key': 'shotgun_type',
                        'validator': base.int_validator,
                        'widget': base_widgets.SGProjectTypesWidget,
                        'placeholder': None,
                        'description': 'Select the item\'s ShotGrid type',
                    },
                    1: {
                        'name': 'ShotGrid Project Id',
                        'key': 'shotgun_id',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid Project ID, e.g. \'123\'',
                        'description': 'The ShotGrid entity id number this item is associated '
                                       'with. e.g. \'123\'.',
                    },
                    2: {
                        'name': 'ShotGrid Project Name',
                        'key': 'shotgun_name',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid project name, e.g. \'MyProject\'',
                        'description': 'The ShotGrid project name',
                    },
                },
                2: {
                    0: {
                        'name': 'ShotGrid Episode Id',
                        'key': 'sg_episode_id',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid episode id, e.g. \'123\'',
                        'description': 'The ShotGrid episode entity number this item is associated '
                                       'with. e.g. \'123\'.',
                    },
                    1: {
                        'name': 'ShotGrid Episode Name',
                        'key': 'sg_episode_name',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid episode entity name, e.g. \'Episode1\'',
                        'description': 'The ShotGrid episode entity name',
                    },
                }
            }
        },
        3: {
            'name': 'Links',
            'icon': 'link',
            'color': common.color(common.color_dark_background),
            'groups': {
                0: {
                    0: {
                        'name': 'Link 1',
                        'key': 'url1',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'https://my.custom-url.com',
                        'description': 'A custom url of the bookmarks, '
                                       'e.g. https://sheets.google.com/123',
                        'button': 'Visit',
                    },
                    1: {
                        'name': 'Link 2',
                        'key': 'url2',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'https://my.custom-url.com',
                        'description': 'A custom url of the bookmarks, '
                                       'e.g. https://sheets.google.com/123',
                        'button': 'Visit',
                    }
                }
            }
        },
        4: {
            'name': 'Application Launcher',
            'icon': 'icon',
            'color': common.color(common.color_dark_background),
            'groups': {
                0: {
                    0: {
                        'name': 'Applications:',
                        'key': 'applications',
                        'validator': None,
                        'widget': application_launcher.ApplicationLauncherListWidget,
                        'placeholder': None,
                        'description': 'Edit the list of applications this bookmark '
                                       'item uses.',
                        'button': 'Add Item',
                    },
                }
            }
        },
        5: {
            'name': 'Database',
            'icon': 'bookmark',
            'color': common.color(common.color_dark_background),
            'groups': {
                0: {
                    0: {
                        'name': 'Created on:',
                        'key': 'created',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'The time the database was created',
                        'description': 'The time the database was created',
                    },
                    1: {
                        'name': 'Created by user:',
                        'key': 'user',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'The user the database was created by',
                        'description': 'The user the database was created by',
                    },
                    2: {
                        'name': 'Created by host:',
                        'key': 'host',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'The user the database was created by',
                        'description': 'The user the database was created by',
                    },
                    3: {
                        'name': 'Bookmark Server:',
                        'key': 'server',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'The bookmark\'s original server',
                        'description': 'The bookmark\'s original server',
                    },
                    4: {
                        'name': 'Bookmark Job:',
                        'key': 'job',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'The bookmark\'s original job',
                        'description': 'The bookmark\'s original job',
                    },
                    5: {
                        'name': 'Bookmark Root:',
                        'key': 'root',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'The bookmark\'s original job',
                        'description': 'The bookmark\'s original job',
                    },
                }
            }
        }
    }

    def __init__(self, server, job, root, parent=None):
        super().__init__(
            server,
            job,
            root,
            asset=None,
            db_table=database.BookmarkTable,
            fallback_thumb='thumb_bookmark0',
            parent=parent
        )

        self.tokens_editor = None
        self._create_tokens_editor(self.scroll_area.widget())

    def _connect_signals(self):
        super()._connect_signals()
        self.thumbnailUpdated.connect(common.signals.thumbnailUpdated)

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        return f'{self.server}/{self.job}/{self.root}'

    def init_data(self):
        """Initializes data.

        """
        self.init_db_data()
        self.description_editor.setFocus(QtCore.Qt.PopupFocusReason)

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        self.save_changed_data_to_db()
        self.tokens_editor.save_changes()
        self.thumbnail_editor.save_image()
        self.thumbnailUpdated.emit(self.db_source())
        return True

    def shotgun_properties(self):
        """Returns the properties needed to connect to shotgun.

        """
        sg_properties = shotgun.SGProperties(
            self.server, self.job, self.root
        )

        sg_properties.domain = self.shotgun_domain_editor.text()
        sg_properties.script = self.shotgun_scriptname_editor.text()
        sg_properties.key = self.shotgun_api_key_editor.text()

        _id = self.shotgun_id_editor.text()
        _id = int(_id) if _id else None
        sg_properties.bookmark_type = self.shotgun_type_editor.currentText()
        sg_properties.bookmark_id = _id
        sg_properties.bookmark_name = self.shotgun_name_editor.text()

        return sg_properties

    def _create_tokens_editor(self, parent):
        from ..tokens import tokens_editor
        self.tokens_editor = tokens_editor.TokenConfigEditor(
            self.server,
            self.job,
            self.root,
            parent=parent
        )
        parent.layout().addWidget(self.tokens_editor, 1)
        for name, widget in self.tokens_editor.header_buttons:
            self.add_section_header_button(name, widget)

    def _get_name(self):
        return self.job

    @QtCore.Slot()
    def prefix_button_clicked(self):
        """Suggest a prefix based on the job's name.

        """
        prefix = actions.suggest_prefix(self.job)
        self.prefix_editor.setText(prefix)
        self.prefix_editor.textEdited.emit(prefix)

    @QtCore.Slot()
    def link_button_clicked(self):
        """ShoGrid link button click action.

        """
        sg_actions.link_bookmark_entity(self.server, self.job, self.root)

    @QtCore.Slot()
    def shotgun_domain_button_clicked(self):
        """Opens the shotgun base domain in the browser.

        """
        v = self.shotgun_domain_editor.text()
        if v:
            QtGui.QDesktopServices.openUrl(v)

    @QtCore.Slot()
    def shotgun_domain_button2_clicked(self):
        """Check the validity of the ShotGrid token.

        """
        sg_actions.test_shotgun_connection(self.shotgun_properties())

    @QtCore.Slot()
    def applications_button_clicked(self):
        """Application Launcher add action.

        """
        self.applications_editor.add_new_item()

    @QtCore.Slot()
    def bookmark_display_token_button_clicked(self):
        k = 'bookmark_display_token'
        if not hasattr(self, f'{k}_editor'):
            raise RuntimeError(f'{k}_editor not found')

        from ..tokens import tokens_editor
        editor = getattr(self, f'{k}_editor')
        w = tokens_editor.TokenEditor(self.server, self.job, self.root, parent=editor)
        w.tokenSelected.connect(lambda x: editor.setText(f'{editor.text()}{x}'))
        w.exec_()

    @QtCore.Slot()
    def asset_display_token_button_clicked(self):
        k = 'asset_display_token'
        if not hasattr(self, f'{k}_editor'):
            raise RuntimeError(f'{k}_editor not found')

        from ..tokens import tokens_editor
        editor = getattr(self, f'{k}_editor')
        w = tokens_editor.TokenEditor(self.server, self.job, self.root, parent=editor)
        w.tokenSelected.connect(lambda x: editor.setText(f'{editor.text()}{x}'))
        w.exec_()
