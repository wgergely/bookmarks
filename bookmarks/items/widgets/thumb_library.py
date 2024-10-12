"""Generic item gallery widget.

"""
import os

from ... import common
from ... import ui


def close():
    """Closes the :class:`ThumbnailLibrary` editor.

    """
    if common.gallery_widget is None:
        return
    try:
        common.gallery_widget.close()
        common.gallery_widget.deleteLater()
    except:
        pass
    common.gallery_widget = None


def show():
    """Opens the :class:`ThumbnailLibrary` editor.

    """
    close()
    common.gallery_widget = ThumbnailLibrary()
    common.gallery_widget.open()
    return common.gallery_widget


class ThumbnailLibrary(ui.GalleryWidget):
    """The editor used to show a list of predefined thumbnail icons.

    """

    def __init__(self, parent=None):
        super().__init__('Pick a Thumbnail', parent=parent)

    def item_generator(self):
        """Yields a list of predefined thumbnail icons.

        """

        with os.scandir(common.rsc(common.ThumbnailResource)) as it:
            for entry in it:
                if not entry.name.endswith(common.thumbnail_format):
                    continue
                label = entry.name.replace('thumb_', '').split('.')[0]
                path = entry.path.replace('\\', '/')
                yield label, path, path
