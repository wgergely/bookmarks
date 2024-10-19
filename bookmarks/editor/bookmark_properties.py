"""The widget used to edit bookmark item properties.

"""
from PySide2 import QtCore, QtGui

from . import base
from . import base_widgets
from .. import application_launcher
from .. import common
from .. import database
from .. import ui
from ..shotgun import actions as sg_actions
from ..shotgun import shotgun
from ..config.editor import (
    FileNameConfigEditor,
    PublishConfigEditor,
    FFMpegTCConfigEditor,
    AssetFolderConfigEditor,
    FileFormatConfigEditor)


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
    bookmark item properties, like frame-rate, resolution, or SG linking.

    """
    #: UI layout definition
    sections = {
        0: {
            'name': 'Bookmark Settings',
            'icon': 'bookmark',
            'color': common.Color.DarkBackground(),
            'groups': {
                0: {
                    0: {
                        'name': 'Prefix',
                        'key': 'prefix',
                        'validator': base.name_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Custom prefix, for example, \'MYB\'',
                        'description': 'A short name of the bookmark (or job) used '
                                       'when saving files.\n\nfor example, '
                                       '\'MYB_sh0010_anim_v001.ma\' where \'MYB\' is '
                                       'the prefix specified here.'
                    },
                },
                1: {
                    0: {
                        'name': 'Description',
                        'key': 'description',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'A short description, for example, \'Character assets\'',
                        'description': 'A description of this bookmark, '
                                       'for example, \'Character assets\'.',
                    },
                },
                2: {
                    0: {
                        'name': 'Frame-rate',
                        'key': 'framerate',
                        'validator': base.float_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Frame-rate, for example, \'23.976\'',
                        'description': 'The frame-rate of the bookmark, for example, '
                                       '\'25.0\'.'
                    },
                    1: {
                        'name': 'Width',
                        'key': 'width',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Width in pixels',
                        'description': 'The output width in pixels, for example, \'1920\''
                    },
                    2: {
                        'name': 'Height',
                        'key': 'height',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Height in pixels',
                        'description': 'The output height in pixels, for example, \'1080\''
                    },
                    3: {
                        'name': 'Default Start Frame',
                        'key': 'startframe',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Start frame, for example, \'1001\'',
                        'description': 'A default start frame for all subsequent '
                                       'assets.\n\nThis can be useful when the project '
                                       'has a custom start frame, for example, \'1001\' instead '
                                       'of \'1\' or \'0\'.',
                    },
                    4: {
                        'name': 'Default Duration',
                        'key': 'duration',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'Duration, for example, \'150\'',
                        'description': 'The default duration of an asset in frames, '
                                       'for example, \'150\'',
                    },
                },
                4: {
                    0: {
                        'name': 'Bookmark Display Name',
                        'key': 'bookmark_display_token',
                        'validator': None,
                        'widget': common.TokenLineEdit,
                        'placeholder': '{server}/{job}/{root}',
                        'description': 'Specify the token used to display bookmark items',
                    },
                    1: {
                        'name': 'Asset Display Name',
                        'key': 'asset_display_token',
                        'validator': None,
                        'widget': common.TokenLineEdit,
                        'placeholder': '{asset}',
                        'description': 'Specify the token used to display asset items',
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
                        'key': 'sg_domain',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'Domain, for example, https://mystudio.shotgunstudio.com',
                        'description': 'The domain, including http:// or https://, '
                                       'used by shotgun. for example, '
                                       '\'https://mystudio.shotgunstudio.com\'',
                        'button': 'Visit',
                        'button2': 'Verify'
                    },
                    1: {
                        'name': 'Script Name',
                        'key': 'sg_scriptname',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'my-sg-script',
                        'description': 'A name of a ShotGrid Script.',
                    },
                    2: {
                        'name': 'API Key',
                        'key': 'sg_api_key',
                        'validator': None,
                        'protect': True,
                        'widget': ui.LineEdit,
                        'placeholder': 'abcdefghijklmno3bqr*1',
                        'description': 'A ShotGrid Script API Key, '
                                       'for example, \'abcdefghijklmno3bqr*1\'.\n\nA valid '
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
                        'key': 'sg_type',
                        'validator': base.int_validator,
                        'widget': base_widgets.SGProjectTypesWidget,
                        'placeholder': None,
                        'description': 'Select the item\'s ShotGrid type',
                    },
                    1: {
                        'name': 'ShotGrid Project Id',
                        'key': 'sg_id',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid Project ID, for example, \'123\'',
                        'description': 'The ShotGrid entity id number this item is associated '
                                       'with. for example, \'123\'.',
                    },
                    2: {
                        'name': 'ShotGrid Project Name',
                        'key': 'sg_name',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid project name, for example, \'MyProject\'',
                        'description': 'The ShotGrid project name',
                    },
                },
                2: {
                    0: {
                        'name': 'ShotGrid Episode Id',
                        'key': 'sg_episode_id',
                        'validator': base.int_validator,
                        'widget': ui.LineEdit,
                        'placeholder': 'ShotGrid episode id, for example, \'123\'',
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
            'name': 'Application Launcher',
            'icon': 'icon',
            'color': common.Color.DarkBackground(),
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
        4: {
            'name': 'Links',
            'icon': 'link',
            'color': common.Color.DarkBackground(),
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
        5: {
            'name': 'Scene Names',
            'icon': 'file',
            'color': common.Color.Green(),
            'groups': {
                0: {
                    0: {
                        'name': None,
                        'key': 'scene_name_template',
                        'validator': None,
                        'widget': FileNameConfigEditor,
                        'placeholder': '',
                        'description': 'These presets are used to generate scene files in the current bookmark item.',
                    }
                }
            }
        },
        6: {
            'name': 'Publish Paths',
            'icon': 'file',
            'color': common.Color.DarkBackground(),
            'groups': {
                0: {
                    0: {
                        'name': None,
                        'key': 'publish_paths',
                        'validator': None,
                        'widget': PublishConfigEditor,
                        'placeholder': '',
                        'description': 'Path presets used to publish items in the current bookmark item.',
                    },
                }
            }
        },
        7: {
            'name': 'Timecode Presets',
            'icon': 'uppercase',
            'color': common.Color.DarkBackground(),
            'groups': {
                0: {
                    0: {
                        'name': None,
                        'key': 'ffmpeg_timecode_presets',
                        'validator': None,
                        'widget': FFMpegTCConfigEditor,
                        'placeholder': '',
                        'description': 'The text overlay presets used in video exports.',
                    },
                }
            }
        },
        8: {
            'name': 'Asset Folders',
            'icon': 'folder',
            'color': common.Color.DarkBackground(),
            'groups': {
                0: {
                    0: {
                        'name': None,
                        'key': 'asset_folders',
                        'validator': None,
                        'widget': AssetFolderConfigEditor,
                        'placeholder': '',
                        'description': 'The text overlay presets used in video exports.',
                    },
                }
            }
        },
        9: {
            'name': 'Allowed File Formats',
            'icon': 'file',
            'color': common.Color.DarkBackground(),
            'groups': {
                0: {
                    0: {
                        'name': None,
                        'key': 'file_whitelist',
                        'validator': None,
                        'widget': FileFormatConfigEditor,
                        'placeholder': '',
                        'description': 'The text overlay presets used in video exports.',
                    },
                }
            }
        },
    }

    def __init__(self, server, job, root, parent=None):
        super().__init__(
            server,
            job,
            root,
            asset=None,
            db_table=database.BookmarkTable,
            fallback_thumb='icon_bw_sm',
            parent=parent
        )

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
        self.description_editor.setFocus(QtCore.Qt.OtherFocusReason)

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        self.save_changed_data_to_db()

        self.scene_name_template_editor.save_changes()
        self.publish_paths_editor.save_changes()
        self.ffmpeg_timecode_presets_editor.save_changes()
        self.asset_folders_editor.save_changes()
        self.file_whitelist_editor.save_changes()

        self.publish_paths_editor.save_changes()
        self.thumbnail_editor.save_image()
        self.thumbnailUpdated.emit(self.db_source())
        return True

    def sg_properties(self):
        """Returns the properties needed to connect to shotgun.

        """
        sg_properties = shotgun.SGProperties(
            self.server, self.job, self.root
        )

        sg_properties.domain = self.sg_domain_editor.text()
        sg_properties.script = self.sg_scriptname_editor.text()
        sg_properties.key = self.sg_api_key_editor.text()

        _id = self.sg_id_editor.text()
        _id = int(_id) if _id else None
        sg_properties.bookmark_type = self.sg_type_editor.currentText()
        sg_properties.bookmark_id = _id
        sg_properties.bookmark_name = self.sg_name_editor.text()

        return sg_properties

    def _get_name(self):
        return self.job

    @QtCore.Slot()
    def link_button_clicked(self):
        """ShoGrid link button click action.

        """
        sg_actions.link_bookmark_entity(self.server, self.job, self.root)

    @QtCore.Slot()
    def sg_domain_button_clicked(self):
        """Opens the shotgun base domain in the browser.

        """
        v = self.sg_domain_editor.text()
        if v:
            QtGui.QDesktopServices.openUrl(v)

    @QtCore.Slot()
    def sg_domain_button2_clicked(self):
        """Check the validity of the ShotGrid token.

        """
        sg_actions.test_sg_connection(self.sg_properties())

    @QtCore.Slot()
    def applications_button_clicked(self):
        """Application Launcher button click action.

        """
        self.applications_editor.add_new_item()

    @QtCore.Slot()
    def bookmark_display_token_button_clicked(self):
        k = 'bookmark_display_token'
        if not hasattr(self, f'{k}_editor'):
            raise RuntimeError(f'{k}_editor not found')

        from bookmarks.config.editor import ConfigEditor
        editor = getattr(self, f'{k}_editor')
        w = ConfigEditor(self.server, self.job, self.root, parent=editor)
        w.tokenSelected.connect(lambda x: editor.setText(f'{editor.text()}{x}'))
        w.exec_()

    @QtCore.Slot()
    def asset_display_token_button_clicked(self):
        k = 'asset_display_token'
        if not hasattr(self, f'{k}_editor'):
            raise RuntimeError(f'{k}_editor not found')

        from bookmarks.config.editor import ConfigEditor
        editor = getattr(self, f'{k}_editor')
        w = ConfigEditor(self.server, self.job, self.root, parent=editor)
        w.tokenSelected.connect(lambda x: editor.setText(f'{editor.text()}{x}'))
        w.exec_()
