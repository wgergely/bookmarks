# -*- coding: utf-8 -*-
"""Widget used to select a Launcher item.

"""

from .. import common
from .. import database
from .. import ui


def close():
    if common.launcher_widget is None:
        return
    try:
        common.launcher_widget.close()
        common.launcher_widget.deleteLater()
    except:
        pass
    common.launcher_widget = None


def show():
    close()
    common.launcher_widget = LauncherGallery()
    common.launcher_widget.open()
    return common.launcher_widget


class LauncherGallery(ui.GalleryWidget):
    """A generic gallery widget used to let the user pick an item.

    """

    def __init__(self, parent=None):
        super().__init__(item_height=common.size(common.HeightRow) * 4, parent=parent)

    def item_generator(self):
        server = common.active(common.ServerKey)
        job = common.active(common.JobKey)
        root = common.active(common.RootKey)

        if not all((server, job, root)):
            return

        db = database.get_db(server, job, root)
        with db.connection():
            v = db.value(
                db.source(),
                'applications',
                database.BookmarkTable
            )

        if not isinstance(v, dict) or not v:
            return

        for k in sorted(v, key=lambda _k: v[_k]['name']):
            yield v[k]['name'], v[k]['path'], v[k]['thumbnail']
