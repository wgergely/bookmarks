#!mayapy
"""Make sure the $MAYA_ROOT/bin directory is in $PATH before running the test."""

import unittest


@unittest.skip('Skipping Maya tests.')
class Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Modifiying the environment to add Bookmark's dependencies.
        This is a must, as otherwise the dependent DLLs would fail to load.

        """
        import os
        import sys

        p = os.path.dirname(__file__) + os.path.sep + '..' + os.path.sep
        p = os.path.normpath(p)
        sys.path.insert(0, p)

        k = 'BOOKMARKS_ROOT'
        if k not in os.environ:
            raise EnvironmentError(
                'Is Bookmarks installed? Could not find BOOKMARKS_ROOT environment variable'
            )

        shared = os.environ[k] + os.path.sep + 'shared'
        sys.path.insert(1, shared)

        paths = os.environ['PATH'].split(';')
        _bin = os.environ[k] + os.path.sep + 'bin'
        paths.insert(1, _bin)
        os.environ['PATH'] = ';'.join(paths)

        try:
            from PySide2 import QtWidgets
            import maya.standalone as maya_standalone
            import maya.mel as mel
            import maya.cmds as cmds
        except ImportError as e:
            raise

        try:
            import bookmarks.maya.widget as mayawidget
            import bookmarks.common as common
            import bookmarks.standalone as standalone
            import bookmarks.maya as maya
        except ImportError as e:
            raise

        app = standalone.StandaloneApp([])
        maya_standalone.initialize(name='python')
        mel.eval('')

        # Let's initialize the plugin dependencies
        cmds.loadPlugin("AbcExport.mll", quiet=True)
        cmds.loadPlugin("AbcImport.mll", quiet=True)

    @classmethod
    def tearDownClass(cls):
        try:
            from PySide2 import QtWidgets
            import maya.standalone as maya_standalone
            import maya.mel as mel
            import maya.cmds as cmds
        except ImportError as e:
            raise

        try:
            import bookmarks.maya.widget as mayawidget
            import bookmarks.common as common
            import bookmarks.standalone as standalone
            import bookmarks.maya as maya
        except ImportError as e:
            raise

        cmds.unloadPlugin("AbcExport.mll")
        cmds.unloadPlugin("AbcImport.mll")
        maya_standalone.uninitialize()
        QtWidgets.QApplication.instance().quit()

    def setUp(self):
        import maya.cmds as cmds

        meshes = []
        for n in range(10):
            s = cmds.polyCube(name='testMesh#')
            meshes.append(s[0])
        cmds.sets(meshes, name='testMesh_geo_set')
        cmds.sets([], name='emptyTestMesh_geo_set')

    def tearDown(self):
        from maya import cmds as cmds
        cmds.file(newFile=True, force=True)

    def test_MayaButtonWidget(self):
        try:
            import bookmarks.maya.widget as mayawidget
            import bookmarks.common as common
            import bookmarks.standalone as standalone
            import bookmarks.maya as maya
        except ImportError as e:
            raise

        w = mayawidget.MayaButtonWidget()
        w.show()

        try:
            from PySide2 import QtCore, QtGui
        except ImportError as e:
            raise

        e = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse, w.geometry().center())
        w.contextMenuEvent(e)
        w.clicked.emit()

    def test_widget(self):
        try:
            import os
            import bookmarks.maya.widget as mayawidget
            import bookmarks.common as common
            import bookmarks.standalone as standalone
            import bookmarks.maya as maya
            import maya.cmds as cmds
        except ImportError as e:
            raise

        maya.widget.show()

        r = maya.widget._instance.save_scene()
        r = self.assertIsInstance(r, str)

        r = maya.widget._instance.save_scene(increment=True)
        r = self.assertIsInstance(r, str)
        new_scene = maya.widget._instance.save_scene(increment=True, modal=False)
        self.assertIsInstance(new_scene, str)
        self.assertEqual(os.path.isfile(new_scene), True)

        r = maya.widget._instance.open_scene(new_scene)
        self.assertIsInstance(r, str)
        with self.assertRaises(RuntimeError):
            r = maya.widget._instance.open_scene('BOGUS/SCENE/null.ma')

        cmds.file(newFile=True, force=True)

        r = maya.widget._instance.import_scene(new_scene)
        self.assertIsInstance(r, str)
        with self.assertRaises(RuntimeError):
            r = maya.widget._instance.import_scene('BOGUS/SCENE/null.ma')

        cmds.file(newFile=True, force=True)

        r = maya.widget._instance.import_referenced_scene(new_scene)
        self.assertIsInstance(r, str)
        with self.assertRaises(RuntimeError):
            r = maya.widget._instance.import_scene('BOGUS/SCENE/null.ma')

    def test_get_geo_sets(self):
        try:
            import bookmarks.maya as maya
        except ImportError as e:
            raise

        sets = maya.widget.get_geo_sets()
        self.assertIsInstance(sets, dict)
        self.assertIn('testMesh_geo_set', sets)

    def test_alembic(self):
        try:
            import os
            from PySide2 import QtCore
            import bookmarks.maya as maya
            import maya.cmds as cmds
        except ImportError as e:
            raise

        sets = maya.widget.get_geo_sets()
        k = 'testMesh_geo_set'
        dest = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.TempLocation)
        dest = dest + os.path.sep + '{}.abc'.format(k)
        bogus_destination = 'INVALID_PATH/TO/NOWHERE/alembic.abc'

        with self.assertRaises(TypeError):
            maya.widget.export_alembic(dest, k, 1.0, 10.0, step=1.0)

        with self.assertRaises(OSError):
            maya.widget.export_alembic(bogus_destination, sets[k], 1.0, 10.0, step=1.0)

        maya.widget.export_alembic(dest, sets[k], 1.0, 10.0, step=1.0)
        self.assertTrue(os.path.isfile(dest))

        r = maya.widget._instance.open_alembic(dest)
        self.assertIsInstance(r, str)
        with self.assertRaises(RuntimeError):
            r = maya.widget._instance.open_alembic('BOGUS/SCENE/null.ma')

        cmds.file(newFile=True, force=True)

        r = maya.widget._instance.import_alembic(dest)
        self.assertIsInstance(r, str)
        with self.assertRaises(RuntimeError):
            r = maya.widget._instance.import_alembic('BOGUS/SCENE/null.ma')

        r = maya.widget._instance.import_referenced_alembic(dest)
        self.assertIsInstance(r, str)
        with self.assertRaises(RuntimeError):
            r = maya.widget._instance.import_referenced_alembic('BOGUS/SCENE/null.ma')

        os.remove(dest)

    def test_export_set_to_abc(self):
        try:
            import os
            from PySide2 import QtCore
            import bookmarks.maya as maya
            import maya.cmds as cmds
        except ImportError as e:
            raise

        sets = maya.widget.get_geo_sets()
        k = 'testMesh_geo_set'

        r = maya.widget._instance.export_set_to_abc(k, sets[k], frame=False)
        self.assertIsInstance(r, str)
        os.remove(r)

    def test_capture_viewport_destination(self):
        try:
            import os
            from PySide2 import QtCore
            import bookmarks.maya as maya
            import bookmarks.maya.capture
        except ImportError as e:
            raise

        capture_folder, workspace, dest = maya.widget.capture_viewport_destination()
        self.assertIsInstance(capture_folder, str)
        self.assertIsInstance(workspace, str)
        self.assertIsInstance(dest, str)

    def test_capture_viewport(self):
        try:
            import os
            from PySide2 import QtCore
            import maya.cmds as cmds
            import bookmarks.maya as maya
            import bookmarks.maya.capture
        except ImportError as e:
            raise

        with self.assertRaises(RuntimeError):
            maya.widget.capture_viewport()

    def test_apply_settings(self):
        try:
            import os
            from PySide2 import QtCore
            import maya.cmds as cmds
            import bookmarks.maya as maya
            import bookmarks.maya.capture
        except ImportError as e:
            raise

        maya.widget._instance.apply_settings()
