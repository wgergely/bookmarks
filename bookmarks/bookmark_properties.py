# -*- coding: utf-8 -*-
"""The widget used to edit bookmark item properties.

"""
from PySide2 import QtCore, QtGui

from . import actions
from . import common
from . import database
from . import ui
from .editor import base
from .editor import base_widgets
from .launcher import launcher
from .shotgun import actions as sg_actions
from .shotgun import shotgun

SLACK_API_URL = 'https://api.slack.com/apps'

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


def show(server, job, root):
    global instance
    close()
    instance = BookmarkPropertyEditor(
        server,
        job,
        root,
    )
    instance.open()
    return instance


SECTIONS = {
    0: {
        'name': 'Settings',
        'icon': 'bookmark',
        'color': common.color(common.BackgroundDarkColor),
        'groups': {
            0: {
                0: {
                    'name': 'Prefix',
                    'key': 'prefix',
                    'validator': base.namevalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Custom prefix, eg. \'MYB\'',
                    'description': 'A short name of the bookmark (or job) used '
                                   'when saving files.\n\nEg. '
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
                    'placeholder': 'A short description, eg. \'Character assets\'',
                    'description': 'A description of this bookmark, '
                                   'eg. \'Character assets\'.',
                },
            },
            2: {
                0: {
                    'name': 'Framerate',
                    'key': 'framerate',
                    'validator': base.floatvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Framerate, eg. \'23.976\'',
                    'description': 'The framerate of the bookmark, eg, '
                                   '\'25.0\'.\n\nUsed by Bookmarks to control the '
                                   'format of scenes inside hosts, eg. Maya.'
                },
                1: {
                    'name': 'Width',
                    'key': 'width',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Width in pixels',
                    'description': 'The output width in pixels, eg. \'1920\''
                },
                2: {
                    'name': 'Height',
                    'key': 'height',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Height in pixels',
                    'description': 'The output height in pixels, eg. \'1080\''
                },
                3: {
                    'name': 'Default Start Frame',
                    'key': 'startframe',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Start frame, eg. \'1001\'',
                    'description': 'A default start frame for all subsequent '
                                   'assets.\n\nThis can be useful when the project '
                                   'has a custom start frame, eg. \'1001\' instead '
                                   'of \'1\' or \'0\'.',
                },
                4: {
                    'name': 'Default Duration',
                    'key': 'duration',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Duration, eg. \'150\'',
                    'description': 'The default duration of an asset in frames, '
                                   'eg. \'150\'',
                },
            },
            3: {
                'identifier': {
                    'name': 'Asset Identifier',
                    'key': 'identifier',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'A file name, eg. \'workspace.mel\'',
                    'description': 'Only folders containing the file specified '
                                   'above will be read as assets.\n\nUsing the '
                                   'default Maya Workspace the identifier normally '
                                   'is \'workspace.mel\', however any other '
                                   'arbitary file can be used as long it is '
                                   'present in the root of an asset '
                                   'folder.\n\nWhen left empty all folders in the '
                                   'bookmark will be read.',
                    'help': 'Only folders containing the file specified here will '
                            'be read as assets.\nUsing the default Maya Workspace '
                            'the identifier normally is \'workspace.mel\', '
                            'however any other arbitary file can be used as long '
                            'it is present in the root of an asset folder.\n\nWhen '
                            'left empty, all folders in the bookmark will be '
                            'interpeted as assets.',
                }
            }
        }
    },
    1: {
        'name': 'Slack',
        'icon': 'slack',
        'color': common.color(common.BackgroundDarkColor),
        'groups': {
            0: {
                0: {
                    'name': 'OAuth Token',
                    'key': 'slacktoken',
                    'validator': None,
                    'protect': True,
                    'widget': ui.LineEdit,
                    'description': 'A valid Slack App OAuth token',
                    'placeholder': 'xoxb-01234567890-0123456',
                    'help': 'Paste a valid <a href="{slack_api_url}">{start}Slack '
                            'App OAuth token{end}</a> above (usually starting with '
                            '{start}xoxb{end}).\n\nMake sure the app has {'
                            'start}users:read{end} and {start}chat:write{end} '
                            'scopes enabled. To send messages to channels the bot '
                            'is not part of, add {start}chat:write.public{end}. '
                            'Scopes {start}channels:read{end} and {'
                            'start}groups:read{end} are needed to list available '
                            'Slack Channels.\n\nSee <a href="{slack_api_url}">{'
                            'start}Slack API{end}</a> for more information. '.format(
                        slack_api_url=SLACK_API_URL, **base.span
                    ),
                    'button': 'Visit',
                    'button2': 'Verify',
                }
            }
        }
    },
    2: {
        'name': 'Shotgun Connection',
        'icon': 'sg',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': 'Domain',
                    'key': 'shotgun_domain',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'Domain, eg. https://mystudio.shotgunstudio.com',
                    'description': 'The domain, including http:// or https://, '
                                   'used by shotgun. Eg. '
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
                    'description': 'A name of a Shotgun Script.',
                },
                2: {
                    'name': 'API Key',
                    'key': 'shotgun_api_key',
                    'validator': None,
                    'protect': True,
                    'widget': ui.LineEdit,
                    'placeholder': 'abcdefghijklmno3bqr*1',
                    'description': 'A Shotgun Script API Key, '
                                   'eg. \'abcdefghijklmno3bqr*1\'.\n\nA valid '
                                   'script has to be set up for your ogranisation '
                                   'for Bookmarks to be able to connect to '
                                   'Shotgun. Consult the Shotgun documentation for '
                                   'details on how to set this up.',
                    'help': 'Make sure Shotgun has a valid API Script set up. This '
                            'can be done from the Shotgun Admin - Scripts option.',
                },
            },
        },
    },
    3: {
        'name': 'Shotgun Entity',
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
                    'description': 'Link item with a Shotgun Entity',
                    'button': 'Link with Shotgun Entity',
                },
                1: {
                    'name': 'Type',
                    'key': 'shotgun_type',
                    'validator': base.intvalidator,
                    'widget': base_widgets.ProjectTypesWidget,
                    'placeholder': None,
                    'description': 'Select the item\'s Shotgun type',
                },
                2: {
                    'name': 'ID',
                    'key': 'shotgun_id',
                    'validator': base.intvalidator,
                    'widget': ui.LineEdit,
                    'placeholder': 'Shotgun Project ID, eg. \'123\'',
                    'description': 'The Shotgun ID number this item is associated '
                                   'with. Eg. \'123\'.',
                },
                3: {
                    'name': 'Name',
                    'key': 'shotgun_name',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'Shotgun project name, eg. \'MyProject\'',
                    'description': 'The Shotgun project name',
                },
            }
        }
    },
    4: {
        'name': 'Links',
        'icon': 'link',
        'color': common.color(common.BackgroundDarkColor),
        'groups': {
            0: {
                0: {
                    'name': 'Link 1',
                    'key': 'url1',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'https://my.custom-url.com',
                    'description': 'A custom url of the bookmarks, '
                                   'eg. https://sheets.google.com/123',
                    'button': 'Visit',
                },
                1: {
                    'name': 'Link 2',
                    'key': 'url2',
                    'validator': None,
                    'widget': ui.LineEdit,
                    'placeholder': 'https://my.custom-url.com',
                    'description': 'A custom url of the bookmarks, '
                                   'eg. https://sheets.google.com/123',
                    'button': 'Visit',
                }
            }
        }
    },
    5: {
        'name': 'Application Launcher',
        'icon': 'icon',
        'color': common.color(common.BackgroundDarkColor),
        'groups': {
            0: {
                0: {
                    'name': 'Applications:',
                    'key': 'applications',
                    'validator': None,
                    'widget': launcher.LauncherListWidget,
                    'placeholder': None,
                    'description': 'Edit the list of applications this bookmark '
                                   'item uses.',
                },
            }
        }
    },
    6: {
        'name': 'Database',
        'icon': 'bookmark',
        'color': common.color(common.BackgroundDarkColor),
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


class BookmarkPropertyEditor(base.BasePropertyEditor):
    """The widget containing all the UI elements used to edit
    bookmark item properties (such as frame-rate, resolution, or SG linking).

    """

    def __init__(self, server, job, root, parent=None):
        super(BookmarkPropertyEditor, self).__init__(
            SECTIONS,
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
        super(BookmarkPropertyEditor, self)._connect_signals()
        self.thumbnailUpdated.connect(common.signals.thumbnailUpdated)

    def db_source(self):
        return self.server + '/' + self.job + '/' + self.root

    def init_data(self):
        self.init_db_data()

    @common.error
    @common.debug
    def save_changes(self):
        self.save_changed_data_to_db()
        self.tokens_editor.save_changes()
        self.thumbnail_editor.save_image()
        self.thumbnailUpdated.emit(self.db_source())
        self.itemUpdated.emit(self.db_source())
        return True

    def shotgun_properties(self):
        """Returns the properties needed to connect to shotgun.

        """
        sg_properties = shotgun.ShotgunProperties(
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
        from .tokens import tokens_editor
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
    def slacktoken_button_clicked(self):
        QtGui.QDesktopServices.openUrl(SLACK_API_URL)

    @QtCore.Slot()
    def slacktoken_button2_clicked(self):
        """Verifies the entered Slack API token.

        """
        token = self.slacktoken_editor.text()
        actions.test_slack_token(token)

    @QtCore.Slot()
    def link_button_clicked(self):
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
        """Check the validity of the Shotgun token.

        """
        sg_actions.test_shotgun_connection(self.shotgun_properties())
