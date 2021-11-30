# -*- coding: utf-8 -*-
"""Bookmarks test environment setup and teardown."""
import shutil
import os
import random

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from ..templates import templates
from ..templates import actions as template_actions
from . import base


class Test(base.BaseCase):
    @classmethod
    def setUpClass(cls):
        super(Test, cls).setUpClass()

        if not os.path.isdir(common.temp_path()):
            os.makedirs(common.temp_path())

        # Get built-in templates
        root = __file__ + os.sep + os.pardir + os.sep + os.pardir + os.sep + 'rsc' + os.sep + 'templates'
        root = os.path.normpath(root)
        for f in os.listdir(root):
            if '.zip' not in f:
                continue
            shutil.copy(root + os.sep + f, common.temp_path())

        # Invalid zip file
        open(common.temp_path() + os.sep + 'invalid.zip', 'w').close()


    def test_get_template_folder(self):
        with self.assertRaises(TypeError):
            templates.get_template_folder(1)

        v = templates.get_template_folder(base.random_str(32))
        self.assertIsNotNone(v)
        self.assertIsInstance(v, str)
        self.assertTrue(QtCore.QFileInfo(v).exists())

        v = templates.get_template_folder(templates.JobTemplateMode)
        self.assertIsNotNone(v)
        self.assertIsInstance(v, str)
        self.assertTrue(QtCore.QFileInfo(v).exists())

        v = templates.get_template_folder(templates.AssetTemplateMode)
        self.assertIsNotNone(v)
        self.assertIsInstance(v, str)
        self.assertTrue(QtCore.QFileInfo(v).exists())

    def test_add_zip_template(self):
        v = templates.get_template_folder(templates.JobTemplateMode)
        self.assertIsNotNone(v)
        self.assertIsInstance(v, str)
        self.assertTrue(os.path.isdir(v))

        v = [f for f in os.listdir(v) if '.zip' in f]
        self.assertFalse(v)

        with self.assertRaises(RuntimeError):
            template_actions.add_zip_template('str', 'str')
        with self.assertRaises(RuntimeError):
            template_actions.add_zip_template(base.random_str(32), base.random_str(32))
        with self.assertRaises(RuntimeError):
            template_actions.add_zip_template(
                common.temp_path() + os.sep + 'invalid.zip',
                templates.JobTemplateMode
            )

        for f in os.listdir(common.temp_path()):
            if '.zip' not in f:
                continue
            if 'invalid' in f:
                continue

            v = template_actions.add_zip_template(
                common.temp_path() + os.sep + f,
                templates.JobTemplateMode
            )
            self.assertIsNotNone(v)
            self.assertIsInstance(v, str)
            self.assertTrue(os.path.isfile(v))

        # This should fail as it would override existing files
        for f in os.listdir(common.temp_path()):
            if '.zip' not in f:
                continue
            if 'invalid' in f:
                continue

            with self.assertRaises(RuntimeError):
                template_actions.add_zip_template(
                    common.temp_path() + os.sep + f,
                    templates.JobTemplateMode,
                    prompt=False
                )

    def test_extract_zip_template(self):
        with self.assertRaises(RuntimeError):
            template_actions.extract_zip_template('str', 'str', 'str')
        with self.assertRaises(TypeError):
            template_actions.extract_zip_template(base.random_str(32), None, None)
        with self.assertRaises(TypeError):
            template_actions.extract_zip_template(base.random_str(32), base.random_str(32), None)
        with self.assertRaises(RuntimeError):
            template_actions.extract_zip_template(base.random_str(32), base.random_str(32), base.random_str(32))

        for f in os.listdir(common.temp_path()):
            if '.zip' not in f:
                continue
            if 'invalid' in f:
                continue

            v = template_actions.extract_zip_template(
                common.temp_path() + os.sep + f,
                common.temp_path(),
                base.random_str(32)
            )
            self.assertIsNotNone(v)
            self.assertIsInstance(v, str)
            self.assertTrue(QtCore.QFileInfo(v).exists())


    def test_remove_zip_template(self):
        with self.assertRaises(TypeError):
            template_actions.remove_zip_template(1)
        with self.assertRaises(RuntimeError):
            template_actions.remove_zip_template(base.random_str(32))

        for f in os.listdir(common.temp_path()):
            if '.zip' not in f:
                continue
            if 'invalid' in f:
                continue

            v = common.temp_path() + os.sep + f
            template_actions.remove_zip_template(v, prompt=False)
            self.assertFalse(QtCore.QFileInfo(v).exists())
