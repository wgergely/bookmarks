# -*- coding: utf-8 -*-
"""Simple thumbnail image picker.

"""
from PySide2 import QtCore, QtWidgets, QtGui

from .. import common
from .. import images


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


def show(server=None, job=None, root=None, source=None):
    global instance

    close()
    instance = PickThumbnail(
        server,
        job,
        root,
        source
    )
    instance.open()
    return instance


class PickThumbnail(QtWidgets.QFileDialog):
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
        if not all((self.server, self.job, self.root, self.source)):
            return
        images.load_thumbnail_from_image(
            self.server,
            self.job,
            self.root,
            self.source,
            image
        )
