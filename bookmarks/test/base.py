# -*- coding: utf-8 -*-
"""Bookmarks test environment setup and teardown."""
import uuid
import shutil
import unittest
import os
import string
import random

from PySide2 import QtCore, QtGui, QtWidgets


PRODUCT = f'bookmarks_test_{uuid.uuid1().hex}'
PRODUCT_ROOT = '{}/{}'.format(
    QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.GenericDataLocation),
    PRODUCT
)


ranges = (
    # (0x0030, 0x0039),
    (0x0041, 0x005A),
    (0x00C0, 0x0240),
)

def random_str(length):
    r = str()
    for _ in range(int(length / len(ranges))):
        for _range in ranges:
            r += chr(random.randrange(*_range))
    return r

def random_ascii(length):
    latters = string.ascii_uppercase + string.ascii_lowercase + string.digits
    # Create a list of str characters within the range 0000-D7FF
    random_strs = [''.join(random.choice(latters))
                       for _ in range(0, length)]
    return ''.join(random_strs)


class BaseCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseCase, cls).setUpClass()

        import bookmarks.common as common
        common.initialize(common.StandaloneMode)

        # Set mock product name
        common.product = PRODUCT

        # Create folder used to test the app
        if not os.path.exists(PRODUCT_ROOT):
            os.makedirs(PRODUCT_ROOT)

        # Create server folder
        if not os.path.isdir(PRODUCT_ROOT + '/' + 'server'):
            os.makedirs(PRODUCT_ROOT + '/' + 'server')

    @classmethod
    def tearDownClass(cls):
        super(BaseCase, cls).tearDownClass()
        try:
            shutil.rmtree(PRODUCT_ROOT)
        except:
            pass
