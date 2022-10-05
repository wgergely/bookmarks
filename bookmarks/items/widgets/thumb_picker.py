"""Simple thumbnail image picker.

"""
from PySide2 import QtCore, QtWidgets

from ... import common
from ... import images

instance = None


def close():
    """Closes :class:`PickThumbnail`.

    """
    if common.pick_thumbnail_widget is None:
        return
    try:
        common.pick_thumbnail_widget.close()
        common.pick_thumbnail_widget.deleteLater()
    except:
        pass
    common.pick_thumbnail_widget = None


def show(server=None, job=None, root=None, source=None):
    """Shows :class:`PickThumbnail`.

    """
    global instance

    close()
    common.pick_thumbnail_widget = PickThumbnail(
        server,
        job,
        root,
        source
    )
    common.pick_thumbnail_widget.open()
    return common.pick_thumbnail_widget


class PickThumbnail(QtWidgets.QFileDialog):
    """Simple file picker dialog used to select an image file.

    """

    def __init__(self, server, job, root, source, parent=None):
        super(PickThumbnail, self).__init__(parent=parent)

        self.server = server
        self.job = job
        self.root = root
        self.source = source

        self.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        self.setViewMode(QtWidgets.QFileDialog.List)
        self.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)

        self.setNameFilter(images.get_oiio_namefilters())
        self.setFilter(
            QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot
        )
        self.setLabelText(
            QtWidgets.QFileDialog.Accept,
            'Pick thumbnail'
        )

    def _connect_signals(self):
        pass

    @common.error
    @common.debug
    def save_image(self, image):
        """Saves the picked image.

        """
        if not all((self.server, self.job, self.root, self.source)):
            return
        images.create_thumbnail_from_image(
            self.server,
            self.job,
            self.root,
            self.source,
            image
        )
