"""Widgets to create jobs and edit bookmark items.

Job is a pseudo-entity in the Bookmarks as it is simply a folder on a server that contains
a bookmarks items. This module allows adding a server path to the user settings,
create new jobs using templates and pick folders from within the job to use as
bookmark items.

To show the main editor call:

.. code-block:: python
    :linenos:

    from bookmarks import actions
    bookmarks.actions.show_job_editor()


"""

from PySide2 import QtCore

from . import base
from . import jobs_widgets
from .. import common


def close():
    """Closes the :class:`JobsEditor` editor.

    """
    if common.job_editor is None:
        return
    try:
        common.job_editor.close()
        common.job_editor.deleteLater()
    except:
        pass
    common.jobs_editor = None


def show():
    """Shows the :class:`JobsEditor` editor.

    """
    close()
    common.job_editor = JobsEditor()

    common.restore_window_geometry(common.job_editor)
    common.restore_window_state(common.job_editor)

    return common.bookmark_property_editor


class JobsEditor(base.BasePropertyEditor):
    """The :class:`JobsEditor` class provides a widget for creating jobs and
    the bookmark items within the job.

    """
    #: UI Layout definition

    sections = {
        0: {
            'name': 'Edit Jobs',
            'icon': 'icon_bw',
            'color': common.Color.Green(),
            'groups': {
                0: {
                    0: {
                        'name': None,
                        'key': 'server_btn',
                        'validator': None,
                        'widget': None,
                        'placeholder': None,
                        'description': 'Edit the list of servers Bookmarks should read jobs from.',
                        'button': 'Add server...'
                    },
                    1: {
                        'name': None,
                        'key': 'server',
                        'validator': None,
                        'widget': jobs_widgets.ServersWidget,
                        'placeholder': None,
                        'description': 'List of servers added to the user preferences.',
                    },
                },
                1: {
                    0: {
                        'name': None,
                        'key': 'job_btn',
                        'validator': None,
                        'widget': None,
                        'placeholder': None,
                        'description': 'Add jobs and bookmark items',
                        # 'help': 'Add jobs to the current server. A job is a folder on a server that contains  '
                        #         'bookmark items. To mark a folder as a bookmark item, right-click on a job and '
                        #         'select "Add bookmark item...".',
                        'button': 'Add job...'
                    },
                    1: {
                        'name': None,
                        'key': 'job',
                        'validator': None,
                        'widget': jobs_widgets.JobsView,
                        'placeholder': None,
                        'description': 'The list of jobs in the current server',
                    },
                },
            }
        }
    }

    def __init__(self, parent=None):
        super().__init__(
            None,
            None,
            None,
            buttons=('Close',),
            fallback_thumb='icon_bw',
            hide_thumbnail_editor=True,
            section_buttons=False,
            parent=parent
        )

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Edit Jobs')

    def init_data(self):
        self.load_saved_user_settings(common.SECTIONS['jobs'])
        self._connect_settings_save_signals(common.SECTIONS['jobs'])

        self.server_editor.selectionModel().selectionChanged.connect(self.server_selection_changed)
        self.server_editor.model().modelAboutToBeReset.connect(self.server_selection_changed)
        self.server_editor.model().modelReset.connect(self.server_selection_changed)

        self.server_editor.progressUpdate.connect(self.show_message)
        self.job_editor.progressUpdate.connect(self.show_message)

        self.server_editor.init_data()

    @QtCore.Slot(str)
    @QtCore.Slot(str)
    def show_message(self, title, body):
        """Shows a progress message as the models are loading.

        """
        if not title:
            common.close_message()
            return

        try:
            common.message_widget.set_labels(title, body)
            return
        except:
            pass

        common.show_message(
            title,
            body=body,
            disable_animation=True,
            message_type=None,
            buttons=[],
        )

    def save_changes(self):
        return True

    def get_args(self):
        """Returns the server, job and root arguments based on the current
        bookmark item selection.

        Returns:
            tuple: The server, job and root arguments.

        """
        editor = self.job_editor
        model = editor.model()
        server = model.root_node.name

        if not server or server == 'server':
            return None, None, None

        if not editor.selectionModel().hasSelection():
            return None, None, None

        index = next(f for f in editor.selectionModel().selectedIndexes())
        node = index.internalPointer()

        if not node:
            return None, None, None

        if not isinstance(node, jobs_widgets.BookmarkItemNode):
            return None, None, None

        job = node.parent.name[len(server) + 1:]
        root = node.name[len(server) + len(job) + 2:]
        return server, job, root

    @QtCore.Slot()
    def server_selection_changed(self, *args, **kwargs):
        """Slot -> called when the server editor's selection changes.

        """
        model = self.server_editor.selectionModel()

        if not model.hasSelection():
            return self.job_editor.model().init_data('server')

        index = next(f for f in model.selectedIndexes())

        if not index.isValid():
            return self.job_editor.model().init_data('server')

        v = index.data(QtCore.Qt.UserRole)
        if not v:
            return self.job_editor.model().init_data('server')

        self.job_editor.model().init_data(v)

    @QtCore.Slot()
    def server_btn_button_clicked(self):
        """Slot -> Called when the server editor's 'Add' button is clicked.

        """
        self.server_editor.add()

    @QtCore.Slot()
    def job_btn_button_clicked(self):
        """Slot -> Called when the server editor's 'Add' button is clicked.

        """
        self.job_editor.add()

    def hideEvent(self, event):
        self._disconnect_signals()

    def _disconnect_signals(self):
        self.server_editor.selectionModel().selectionChanged.disconnect()
        self.server_editor.model().modelAboutToBeReset.disconnect()
        self.server_editor.model().modelReset.disconnect()

        self.job_editor.selectionModel().selectionChanged.disconnect()
        self.job_editor.model().modelAboutToBeReset.disconnect()
        self.job_editor.model().modelReset.disconnect()
