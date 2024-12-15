import io
import os
import shutil
import tempfile
import unittest
import zipfile

from .error import *
from .lib import *
from .. import common
from .. import database


class TestTemplatesLib(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp().replace('\\', '/')
        self.server = os.path.join(self.temp_dir, 'test_server')
        self.job = 'test_job'
        self.root = 'test_root'
        self.asset = 'test_asset'

        os.makedirs(f'{self.server}/{self.job}/{self.root}/{self.asset}', exist_ok=True)

        # Initialize the app with active overrides
        common.initialize(
            mode=common.Mode.Core,
            run_app=False,
            server=self.server,
            job=self.job,
            root=self.root,
            asset=self.asset
        )

        # Verify the active overrides
        self.assertEqual(common.active('server'), self.server)
        self.assertEqual(common.active('job'), self.job)
        self.assertEqual(common.active('root'), self.root)
        self.assertEqual(common.active('asset'), self.asset)
        self.assertEqual(common.active('root', path=True), f'{self.server}/{self.job}/{self.root}')
        self.assertEqual(common.active('root', args=True), (self.server, self.job, self.root))

    def tearDown(self):
        common.shutdown()
        shutil.rmtree(self.temp_dir)

    def _assert_type_user_template(self, t):
        self.assertEqual(t.type, TemplateType.UserTemplate,
                         f"Expected a user template type but got {t.type}")

    def _assert_type_database_template(self, t):
        self.assertEqual(t.type, TemplateType.DatabaseTemplate,
                         f"Expected a database template type but got {t.type}")

    def test_get_saved_templates_database_empty(self):
        self.assertFalse(builtin_template_exists(TemplateType.DatabaseTemplate))
        results = list(get_saved_templates(TemplateType.DatabaseTemplate))
        for templ in results:
            self._assert_type_database_template(templ)
        self.assertTrue(builtin_template_exists(TemplateType.DatabaseTemplate))
        self.assertEqual(len(results), 2)  # TokenConfig and Empty

    def test_get_saved_templates_user_empty(self):
        if os.path.exists(default_user_folder):
            shutil.rmtree(default_user_folder)
        self.assertFalse(builtin_template_exists(TemplateType.UserTemplate))
        results = list(get_saved_templates(TemplateType.UserTemplate))
        for templ in results:
            self._assert_type_user_template(templ)
        self.assertTrue(builtin_template_exists(TemplateType.UserTemplate))
        self.assertEqual(len(results), 1)

    def test_builtin_template_exists_invalid_type(self):
        with self.assertRaises(ValueError):
            builtin_template_exists("InvalidType")

    def test_templateitem_create_empty(self):
        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        self.assertEqual(t['name'], BuiltInTemplate.Empty.value)
        t.save(force=True)
        list(get_saved_templates(TemplateType.DatabaseTemplate))
        self.assertTrue(builtin_template_exists(TemplateType.DatabaseTemplate))

    def test_templateitem_create_from_tokens(self):
        t = TemplateItem()
        self._assert_type_database_template(t)
        self.assertEqual(t['name'], BuiltInTemplate.TokenConfig.value)
        t.save(force=True)

        args = common.active('root', args=True)
        if not args:
            raise RuntimeError('A root item must be active to rename the template in the database')
        db = database.get(*args)
        _hashes = db.get_column('id', database.TemplateDataTable)
        _hash = common.get_hash(t['name'])
        self.assertIn(_hash, _hashes)

    def test_templateitem_create_from_data_invalid(self):
        with self.assertRaises(ValueError):
            TemplateItem(path="somepath", data=b"somebinary")

    def test_templateitem_create_empty_with_data(self):
        with self.assertRaises(ValueError):
            TemplateItem(data=b"somebinary", empty=True)

    def test_templateitem_missing_metadata(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('thumbnail.png', b'fakeimage')
            zf.writestr('template.zip', b'content')
        buf.seek(0)
        with self.assertRaises(TemplateError):
            TemplateItem(data=buf.read())

    def test_templateitem_missing_thumbnail(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('metadata.json', '{"name":"Test","description":"","author":"","date":""}')
            zf.writestr('template.zip', b'content')
        buf.seek(0)
        with self.assertRaises(TemplateError):
            TemplateItem(data=buf.read())

    def test_templateitem_missing_template_zip(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('metadata.json', '{"name":"Test","description":"","author":"","date":""}')
            zf.writestr('thumbnail.png', b'fakeimage')
        buf.seek(0)
        with self.assertRaises(TemplateError):
            TemplateItem(data=buf.read())

    def test_templateitem_metadata_keys(self):
        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        t['name'] = 'MyTemplate'
        t['description'] = 'A test template'
        t['author'] = 'Tester'
        t['date'] = '2024-01-01'
        self.assertEqual(t['name'], 'MyTemplate')
        self.assertEqual(t['description'], 'A test template')
        with self.assertRaises(KeyError):
            t['invalidkey'] = 'nope'

    def test_templateitem_rename_user_template(self):
        user_template_path = TemplateItem.get_save_path('UserTemp')
        t = TemplateItem(path=user_template_path, empty=True)
        self._assert_type_user_template(t)
        t.save(force=True)
        self.assertTrue(os.path.exists(user_template_path))
        t.rename('RenamedUserTemp')
        new_path = TemplateItem.get_save_path('RenamedUserTemp')
        self.assertTrue(os.path.exists(new_path))
        self.assertFalse(os.path.exists(user_template_path))

    def test_templateitem_rename_database_template(self):
        t = TemplateItem()
        self._assert_type_database_template(t)
        t['name'] = 'DBTemp'
        t.save(force=True)
        t.rename('RenamedDBTemp')
        self.assertFalse(t.is_builtin())
        found = any(x['name'] == 'RenamedDBTemp' for x in get_saved_templates(TemplateType.DatabaseTemplate))
        self.assertTrue(found)

    def test_templateitem_delete_user_template(self):
        user_template_path = TemplateItem.get_save_path('DelUserTemp')
        t = TemplateItem(path=user_template_path, empty=True)
        self._assert_type_user_template(t)
        t.save(force=True)
        self.assertTrue(os.path.exists(user_template_path))
        t.delete()
        self.assertFalse(os.path.exists(user_template_path))

    def test_templateitem_delete_db_template(self):
        t = TemplateItem()
        self._assert_type_database_template(t)
        t['name'] = 'DelDBTemp'
        t.save(force=True)
        t.delete()
        found = any(x['name'] == 'DelDBTemp' for x in get_saved_templates(TemplateType.DatabaseTemplate))
        self.assertFalse(found)

    def test_templateitem_thumbnail_set(self):
        valid_png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc`\x00\x00\x00\x02'
            b'\x00\x01M\xa2\x15\x17\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        temp_img_path = os.path.join(self.temp_dir, 'testthumb.png')
        with open(temp_img_path, 'wb') as f:
            f.write(valid_png)

        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        t.set_thumbnail(temp_img_path)
        self.assertFalse(t.qimage.isNull())

    def test_templateitem_thumbnail_invalid_path(self):
        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        with self.assertRaises(FileNotFoundError):
            t.set_thumbnail('/invalid/path/to/thumb.png')

    def test_templateitem_links(self):
        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        self.assertFalse(t.has_links)
        with self.assertRaises(ValueError):
            t.set_link_preset('NonExistentPreset')
        presets = t.get_links()
        self.assertIsInstance(presets, list)

    def test_templateitem_save_conflicts_user(self):
        path = TemplateItem.get_save_path('ConfUserTemp')
        t = TemplateItem(path=path, empty=True)
        self._assert_type_user_template(t)
        t.save(force=False)
        t2 = TemplateItem(path=path, empty=True)
        self._assert_type_user_template(t2)
        with self.assertRaises(FileExistsError):
            t2.save(force=False)

    def test_templateitem_save_conflicts_db(self):
        t = TemplateItem()
        self._assert_type_database_template(t)
        t['name'] = 'ConfDBTemp'
        t.save(force=True)
        t2 = TemplateItem()
        self._assert_type_database_template(t2)
        t2['name'] = 'ConfDBTemp'
        with self.assertRaises(ValueError):
            t2.save(force=False)

    def test_templateitem_template_from_folder(self):
        source_folder = os.path.join(self.temp_dir, 'source_data')
        os.makedirs(source_folder, exist_ok=True)
        file_path = os.path.join(source_folder, 'testfile.txt')
        with open(file_path, 'w') as f:
            f.write('Hello')

        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        files, folders = t.template_from_folder(source_folder)

        self.assertIn('testfile.txt', files, "The returned list of files should include 'testfile.txt'")
        self.assertTrue(t.contains_file('testfile.txt'), "TemplateItem should report that 'testfile.txt' is contained")

        self.assertIsNotNone(t._template, "t._template should not be None after template_from_folder")

        inner_zp = io.BytesIO(t._template)
        with zipfile.ZipFile(inner_zp, 'r') as zf:
            namelist = zf.namelist()
            self.assertIn('testfile.txt', namelist,
                          "The 'testfile.txt' should be present in the inner template.zip file list")

    def test_templateitem_template_from_folder_too_large(self):
        source_folder = os.path.join(self.temp_dir, 'large_source')
        os.makedirs(source_folder, exist_ok=True)
        big_file = os.path.join(source_folder, 'bigfile.bin')
        with open(big_file, 'wb') as f:
            f.write(b'0' * (101 * 1024 * 1024))
        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        with self.assertRaises(TemplateSizeError):
            t.template_from_folder(source_folder, max_size_mb=100)

    def test_templateitem_template_to_folder(self):
        source_folder = os.path.join(self.temp_dir, 'template_source')
        os.makedirs(source_folder, exist_ok=True)
        test_file = os.path.join(source_folder, 'myfile.txt')
        with open(test_file, 'w') as f:
            f.write('contents')

        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        t.template_from_folder(source_folder)
        t.save(force=True)

        self.assertIsNotNone(t._template, "t._template should not be None after save.")
        inner_zp = io.BytesIO(t._template)
        with zipfile.ZipFile(inner_zp, 'r') as zf:
            namelist = zf.namelist()
            self.assertIn('myfile.txt', namelist, "The 'myfile.txt' should be present inside t._template")

        dest_folder = os.path.join(self.temp_dir, 'extracted')
        t.template_to_folder(dest_folder, extract_contents_to_links=False)

        self.assertTrue(os.path.exists(os.path.join(dest_folder, 'myfile.txt')),
                        "The extracted folder should contain 'myfile.txt' after extraction.")

    def test_unicode_compatibility(self):
        unicode_name = 'テンプレート'
        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        t['name'] = unicode_name
        t.save(force=True)
        found = any(x['name'] == unicode_name for x in get_saved_templates(TemplateType.DatabaseTemplate))
        self.assertTrue(found)

    def test_templateitem_invalid_metadata_key(self):
        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        with self.assertRaises(KeyError):
            t.get_metadata('invalid_key')

    def test_templateitem_no_active_root_db_operations(self):
        common.set_active('root', None, force=True)
        self.assertIsNone(common.active('root', args=True))

        v = builtin_template_exists(TemplateType.DatabaseTemplate)
        self.assertFalse(v)

        with self.assertRaises(RuntimeError):
            t = TemplateItem(empty=True)
            self._assert_type_database_template(t)
            t['name'] = 'NoRootDBTemp'
            t.save(force=True)

    def test_templateitem_delete_nonexistent(self):
        t = TemplateItem(path=TemplateItem.get_save_path('DoesNotExist'), empty=True)
        self._assert_type_user_template(t)
        with self.assertRaises(FileNotFoundError):
            t.delete()

    def test_templateitem_rename_conflict_user(self):
        p1 = TemplateItem.get_save_path('UserA')
        t1 = TemplateItem(path=p1, empty=True)
        self._assert_type_user_template(t1)
        t1.save(force=True)

        p2 = TemplateItem.get_save_path('UserB')
        t2 = TemplateItem(path=p2, empty=True)
        self._assert_type_user_template(t2)
        t2.save(force=True)

        with self.assertRaises(FileExistsError):
            t1.rename('UserB')

    # --- Additional Tests for Links ---

    def test_templateitem_template_to_folder_with_links(self):
        source_folder = os.path.join(self.temp_dir, 'links_source')
        os.makedirs(source_folder, exist_ok=True)
        # Create files
        with open(os.path.join(source_folder, 'file1.txt'), 'w') as f:
            f.write('File1 contents')
        with open(os.path.join(source_folder, 'file2.txt'), 'w') as f:
            f.write('File2 contents')
        # Create a .links file
        with open(os.path.join(source_folder, '.links'), 'w') as f:
            f.write('subdir1\nsubdir2/subsubdir\n')

        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        t.template_from_folder(source_folder)
        t.save(force=True)

        dest_folder = os.path.join(self.temp_dir, 'extracted_links')
        t.template_to_folder(dest_folder, extract_contents_to_links=True)

        # Check that subdir1 and subdir2/subsubdir were created
        self.assertTrue(os.path.exists(os.path.join(dest_folder, 'subdir1')), "subdir1 should be created from .links")
        self.assertTrue(os.path.exists(os.path.join(dest_folder, 'subdir2', 'subsubdir')),
                        "subdir2/subsubdir should be created from .links")

        # Files should appear in both link directories
        self.assertTrue(os.path.exists(os.path.join(dest_folder, 'subdir1', 'file1.txt')))
        self.assertTrue(os.path.exists(os.path.join(dest_folder, 'subdir1', 'file2.txt')))
        self.assertTrue(os.path.exists(os.path.join(dest_folder, 'subdir2', 'subsubdir', 'file1.txt')))
        self.assertTrue(os.path.exists(os.path.join(dest_folder, 'subdir2', 'subsubdir', 'file2.txt')))

    def test_templateitem_template_to_folder_with_links_no_links_file(self):
        source_folder = os.path.join(self.temp_dir, 'no_links_source')
        os.makedirs(source_folder, exist_ok=True)
        with open(os.path.join(source_folder, 'myfile.txt'), 'w') as f:
            f.write('No links here')

        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        t.template_from_folder(source_folder)
        t.save(force=True)

        dest_folder = os.path.join(self.temp_dir, 'extracted_no_links')
        with self.assertRaises(TemplateError):
            t.template_to_folder(dest_folder, extract_contents_to_links=True)

    def test_templateitem_template_to_folder_ignore_links(self):
        source_folder = os.path.join(self.temp_dir, 'ignore_links_source')
        os.makedirs(source_folder, exist_ok=True)
        with open(os.path.join(source_folder, 'myfile.txt'), 'w') as f:
            f.write('contents')
        with open(os.path.join(source_folder, '.links'), 'w') as f:
            f.write('linkdir\n')

        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        t.template_from_folder(source_folder)
        t.save(force=True)

        dest_folder = os.path.join(self.temp_dir, 'extracted_ignore_links')
        t.template_to_folder(dest_folder, ignore_links=True)

        # Since we ignore links, no linkdir is created. Files remain in root.
        self.assertTrue(os.path.exists(os.path.join(dest_folder, 'myfile.txt')))
        self.assertFalse(os.path.exists(os.path.join(dest_folder, 'linkdir')))

    def test_templateitem_template_to_folder_link_conflict(self):
        source_folder = os.path.join(self.temp_dir, 'link_conflict_source')
        os.makedirs(source_folder, exist_ok=True)
        with open(os.path.join(source_folder, 'myfile.txt'), 'w') as f:
            f.write('contents')
        with open(os.path.join(source_folder, '.links'), 'w') as f:
            f.write('existing_dir\n')

        # Create a directory that conflicts with the links creation
        dest_folder = os.path.join(self.temp_dir, 'extracted_link_conflict')
        os.makedirs(os.path.join(dest_folder, 'existing_dir'), exist_ok=True)

        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        t.template_from_folder(source_folder)
        t.save(force=True)

        # Since existing_dir already exists and ignore_existing_folders=False, this should raise FileExistsError
        with self.assertRaises(FileExistsError):
            t.template_to_folder(dest_folder, extract_contents_to_links=True)

    def test_templateitem_template_to_folder_multiple_links(self):
        source_folder = os.path.join(self.temp_dir, 'multi_links_source')
        os.makedirs(source_folder, exist_ok=True)
        with open(os.path.join(source_folder, 'a.txt'), 'w') as f:
            f.write('File A')
        with open(os.path.join(source_folder, 'b.txt'), 'w') as f:
            f.write('File B')
        with open(os.path.join(source_folder, '.links'), 'w') as f:
            f.write('dirA\n')
            f.write('dirB\n')

        t = TemplateItem(empty=True)
        self._assert_type_database_template(t)
        t.template_from_folder(source_folder)
        t.save(force=True)

        dest_folder = os.path.join(self.temp_dir, 'extracted_multi_links')
        t.template_to_folder(dest_folder, extract_contents_to_links=True)

        # Files should be extracted into both dirA and dirB
        self.assertTrue(os.path.exists(os.path.join(dest_folder, 'dirA', 'a.txt')))
        self.assertTrue(os.path.exists(os.path.join(dest_folder, 'dirA', 'b.txt')))
        self.assertTrue(os.path.exists(os.path.join(dest_folder, 'dirB', 'a.txt')))
        self.assertTrue(os.path.exists(os.path.join(dest_folder, 'dirB', 'b.txt')))

    def test_templateitem_user_template_read_back(self):
        # Create a source folder with files and subfolders
        source_folder = os.path.join(self.temp_dir, 'user_template_source')
        os.makedirs(source_folder, exist_ok=True)

        # Create a file in the source folder
        file_path = os.path.join(source_folder, 'readme.txt')
        with open(file_path, 'w') as f:
            f.write('User template test file')

        # Create a subfolder and another file
        subfolder = os.path.join(source_folder, 'docs')
        os.makedirs(subfolder, exist_ok=True)
        doc_file_path = os.path.join(subfolder, 'manual.txt')
        with open(doc_file_path, 'w') as f:
            f.write('User template manual')

        # Create a thumbnail image file
        valid_png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc`\x00\x00\x00\x02'
            b'\x00\x01M\xa2\x15\x17\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        thumb_path = os.path.join(self.temp_dir, 'thumb.png')
        with open(thumb_path, 'wb') as f:
            f.write(valid_png)

        # Create a user template and set metadata, thumbnail
        user_template_path = TemplateItem.get_save_path('UserReadbackTest')
        t = TemplateItem(path=user_template_path, empty=True)
        self._assert_type_user_template(t)

        t['name'] = 'User Readback Template'  # This will be changed to 'UserReadbackTemplate' when saved
        t['description'] = 'A template created from files on disk and read back again.'
        t['author'] = 'Tester'
        t['date'] = '2025-01-01'

        # Set thumbnail
        t.set_thumbnail(thumb_path)

        # Add files from the source folder
        files, folders = t.template_from_folder(source_folder)
        self.assertIn('readme.txt', files, "The returned list of files should include 'readme.txt'")
        self.assertIn('docs/manual.txt', files, "The returned list of files should include 'docs/manual.txt'")

        # Save the template to disk
        t.save(force=True)
        self.assertTrue(os.path.exists(user_template_path), "The user template should be saved on disk")

        # Now read it back from disk using path-only (no empty=True)
        t2 = TemplateItem(path=user_template_path)
        self._assert_type_user_template(t2)

        # Check metadata
        self.assertEqual(t2['name'], 'UserReadbackTest')
        self.assertEqual(t2['description'], 'A template created from files on disk and read back again.')
        self.assertEqual(t2['author'], 'Tester')
        self.assertEqual(t2['date'], '2025-01-01')

        # Check thumbnail
        self.assertFalse(t2.qimage.isNull(), "The thumbnail image should be loaded successfully")

        # Check that the files are present inside t2._template
        self.assertTrue(t2.contains_file('readme.txt'), "t2 should contain 'readme.txt'")
        self.assertTrue(t2.contains_file('docs/manual.txt'), "t2 should contain 'docs/manual.txt'")

        # Additionally, open t2._template as a zip and verify files
        self.assertIsNotNone(t2._template, "t2._template should not be None after reading from disk")
        inner_zp = io.BytesIO(t2._template)
        with zipfile.ZipFile(inner_zp, 'r') as zf:
            namelist = zf.namelist()
            self.assertIn('readme.txt', namelist, "'readme.txt' should be inside the template zip")
            self.assertIn('docs/manual.txt', namelist, "'docs/manual.txt' should be inside the template zip")


if __name__ == '__main__':
    unittest.main()
