"""The application launcher item viewer.

"""
from PySide2 import QtWidgets

from .. import actions
from .. import common
from .. import database
from .. import ui


def close():
    """Opens the :class:`ApplicationLauncherWidget` editor.

    """
    if common.launcher_widget is None:
        return
    try:
        common.launcher_widget.close()
        common.launcher_widget.deleteLater()
    except:
        pass
    common.launcher_widget = None


def show():
    """Shows the :class:`ApplicationLauncherWidget` editor.

    """
    close()
    common.launcher_widget = ApplicationLauncherWidget()
    common.launcher_widget.open()
    return common.launcher_widget


class ApplicationLauncherWidget(ui.GalleryWidget):
    """A generic gallery widget used to let the user pick an item.

    """

    def __init__(self, parent=None):
        super().__init__(
            'Application Launcher',
            item_height=common.size(common.size_row_height) * 4,
            parent=parent
        )

    def item_generator(self):
        """Yields the available launcher items stored in the bookmark item database.

        """
        server = common.active('server')
        job = common.active('job')
        root = common.active('root')

        if not all((server, job, root)):
            return

        db = database.get(server, job, root)
        v = db.value(
            db.source(),
            'applications',
            database.BookmarkTable
        )

        if not isinstance(v, dict) or not v:
            self.close()

            if common.show_message(
                    'The application launcher has not yet been configured.',
                    body='You can add new items in the current bookmark item\'s property editor. '
                         'Do you want to open it now?',
                    buttons=[common.YesButton, common.NoButton],
                    modal=True,
            ) == QtWidgets.QDialog.Rejected:
                return
            actions.edit_bookmark()

        for k in sorted(v, key=lambda _k: v[_k]['name']):
            yield v[k]['name'], v[k]['path'], v[k]['thumbnail']
