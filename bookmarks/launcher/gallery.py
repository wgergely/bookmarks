"""The application launcher item viewer.

"""

from .. import common
from .. import database
from .. import ui


def close():
    """Opens the :class:`LauncherGallery` editor.

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
    """Shows the :class:`LauncherGallery` editor.

    """
    close()
    common.launcher_widget = LauncherGallery()
    common.launcher_widget.open()
    return common.launcher_widget


class LauncherGallery(ui.GalleryWidget):
    """A generic gallery widget used to let the user pick an item.

    """

    def __init__(self, parent=None):
        super().__init__(
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

        db = database.get_db(server, job, root)
        v = db.value(
            db.source(),
            'applications',
            database.BookmarkTable
        )

        if not isinstance(v, dict) or not v:
            ui.MessageBox(
                'There are no items configured yet.',
                'Add new application launcher items in the bookmark property editor.'
            ).exec_()
            self.close()
            return

        for k in sorted(v, key=lambda _k: v[_k]['name']):
            yield v[k]['name'], v[k]['path'], v[k]['thumbnail']

    def focusOutEvent(self, event):
        """Event handler.

        """
        self.close()
