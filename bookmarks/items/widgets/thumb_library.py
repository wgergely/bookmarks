# -*- coding: utf-8 -*-
"""Generic item gallery widget.

"""
import os

from PySide2 import QtCore, QtWidgets, QtGui

from ... import common
from ... import images
from ... import ui


def close():
    if common.gallery_widget is None:
        return
    try:
        common.gallery_widget.close()
        common.gallery_widget.deleteLater()
    except:
        pass
    common.gallery_widget = None


def show():
    close()
    common.gallery_widget = ThumbnailLibrary()
    common.gallery_widget.open()
    return common.gallery_widget


class ThumbnailLibrary(ui.GalleryWidget):
    def item_generator(self):
        for entry in os.scandir(common.get_rsc(common.ThumbnailResource)):
            if not entry.name.endswith(common.thumbnail_format):
                continue
            label = entry.name.replace('thumb_', '').split('.')[0]
            path = entry.path.replace('\\', '/')
            yield label, path, path
