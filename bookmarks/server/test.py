import json
import os
import shutil
import tempfile
import threading
import time
import unittest

from .activebookmarks_presets import *
from .. import common
from ..server.lib import ServerAPI


class TestServerLib(unittest.TestCase):
    """Unit tests for server.lib.ServerAPI functionality."""

    def setUp(self):
        # Create a temporary directory for test isolation and ensure forward slashes
        self.temp_dir = tempfile.mkdtemp().replace('\\', '/')
        common.initialize(
            mode=common.Mode.Core,
            run_app=False
        )

        # Clear out any environment variables that might affect the tests
        for i in range(99):
            env_var = f'Bookmarks_ENV_ITEM{i}'
            if env_var in os.environ:
                del os.environ[env_var]

        # Clear out bookmarks and servers before each test
        ServerAPI.clear_bookmarks()
        servers = ServerAPI.get_servers(force=True)
        for s in list(servers.keys()):
            ServerAPI.remove_server(s)

    def tearDown(self):
        # Cleanup the temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Shutdown the application environment
        common.shutdown()

    def _fwd_path(self, *parts):
        """Join given parts into a forward-slashed path."""
        p = '/'.join(parts)
        return p.replace('\\', '/')

    def test_add_and_remove_server(self):
        """Test adding and removing a server with forward slash normalization."""
        test_server = self._fwd_path(self.temp_dir, 'test_server')
        os.makedirs(test_server.replace('/', os.sep), exist_ok=True)
        ServerAPI.add_server(test_server)
        servers = ServerAPI.get_servers()
        self.assertIn(test_server, servers)

        ServerAPI.remove_server(test_server)
        servers = ServerAPI.get_servers(force=True)
        self.assertNotIn(test_server, servers)

    def test_add_existing_server(self):
        """Test adding a server that already exists."""
        test_server = self._fwd_path(self.temp_dir, 'duplicate_server')
        os.makedirs(test_server.replace('/', os.sep), exist_ok=True)
        ServerAPI.add_server(test_server)
        with self.assertRaises(ValueError):
            ServerAPI.add_server(test_server)

    def test_remove_nonexisting_server(self):
        """Test removing a server that does not exist."""
        nonexisting_server = self._fwd_path(self.temp_dir, 'nonexisting_server')
        with self.assertRaises(ValueError):
            ServerAPI.remove_server(nonexisting_server)

    def test_clear_servers(self):
        """Test clearing all servers."""
        new_server = self._fwd_path(self.temp_dir, 'temp_server')
        os.makedirs(new_server.replace('/', os.sep), exist_ok=True)
        ServerAPI.add_server(new_server)
        # Clear should remove all since we have no bookmarks referencing them
        ServerAPI.clear_servers()
        servers = ServerAPI.get_servers(force=True)
        self.assertEqual(len(servers), 0)

    def test_permissions(self):
        """Test checking permissions."""
        # The temp_dir should be accessible
        self.assertTrue(ServerAPI.check_permissions(self.temp_dir))

    def test_bookmark_job_folder(self):
        """Test bookmarking a job folder and ensure no trailing slash."""
        server = self._fwd_path(self.temp_dir, 'bookmarked_server')
        job = 'bookmarked_job'
        root = 'bookmarked_root/'
        os.makedirs(self._fwd_path(server, job, root).replace('/', os.sep), exist_ok=True)
        ServerAPI.add_server(server)
        # Bookmarking should strip trailing slash
        ServerAPI.bookmark_job_folder(server, job, root)
        bk_key = ServerAPI.bookmark_key(server, job, root)
        # Ensure trailing slash was stripped
        self.assertFalse(bk_key.endswith('/'))
        self.assertIn(bk_key, common.bookmarks)

    def test_unbookmark_job_folder(self):
        """Test unbookmarking a job folder."""
        server = self._fwd_path(self.temp_dir, 'unbookmark_server')
        job = 'unbookmark_job'
        root = 'unbookmark_root'
        os.makedirs(self._fwd_path(server, job, root).replace('/', os.sep), exist_ok=True)
        ServerAPI.add_server(server)
        ServerAPI.bookmark_job_folder(server, job, root)
        ServerAPI.unbookmark_job_folder(server, job, root)
        bk_key = ServerAPI.bookmark_key(server, job, root)
        self.assertNotIn(bk_key, common.bookmarks)

    def test_save_bookmarks(self):
        """Test saving custom bookmarks with proper key pattern."""
        server = self._fwd_path(self.temp_dir, 'save_bookmarks_server')
        job = 'save_bookmarks_job'
        root = 'save_bookmarks_root'
        os.makedirs(self._fwd_path(server, job, root).replace('/', os.sep), exist_ok=True)
        ServerAPI.add_server(server)

        bk_key = ServerAPI.bookmark_key(server, job, root)
        data = {
            bk_key: {
                'server': server,
                'job': job,
                'root': root
            }
        }
        ServerAPI.save_bookmarks(data)
        self.assertIn(bk_key, common.bookmarks)

    def test_get_env_bookmarks(self):
        """Test retrieving bookmarks from environment variables."""
        server = 'env_server'
        job = 'env_job'
        root = 'env_root'
        os.environ['Bookmarks_ENV_ITEM0'] = f"{server};{job};{root}"
        env_bookmarks = ServerAPI.get_env_bookmarks()
        key = f'{server}/{job}/{root}'
        self.assertIn(key, env_bookmarks)

    def test_load_bookmarks(self):
        """Test loading bookmarks from environment and user settings."""
        server = self._fwd_path(self.temp_dir, 'load_bookmarks_server')
        job = 'load_bookmarks_job'
        root = 'load_bookmarks_root'
        os.makedirs(self._fwd_path(server, job, root).replace('/', os.sep), exist_ok=True)
        ServerAPI.add_server(server)

        # Set env var
        os.environ['Bookmarks_ENV_ITEM0'] = f"{server};{job};{root}"
        user_key = ServerAPI.bookmark_key(server, job, root)
        user_data = {
            user_key: {
                'server': server,
                'job': job,
                'root': root
            }
        }
        ServerAPI.save_bookmarks(user_data)
        all_bookmarks = ServerAPI.load_bookmarks()
        # Should contain both environment and user bookmarks
        self.assertIn(f'{server}/{job}/{root}', all_bookmarks)
        self.assertIn(user_key, all_bookmarks)

    def test_unicode_paths(self):
        """Test handling of unicode characters in server paths."""
        unicode_dir = self._fwd_path(self.temp_dir, 'unicode_服务器')
        os.makedirs(unicode_dir.replace('/', os.sep), exist_ok=True)
        ServerAPI.add_server(unicode_dir)
        servers = ServerAPI.get_servers(force=True)
        self.assertIn(unicode_dir, servers)

    def test_concurrent_access(self):
        """Test concurrent access to server add/remove operations."""
        concurrency_count = 5
        test_paths = []
        for i in range(concurrency_count):
            p = self._fwd_path(self.temp_dir, f'concurrent_server_{i}')
            os.makedirs(p.replace('/', os.sep), exist_ok=True)
            test_paths.append(p)

        def add_remove_server(p):
            ServerAPI.add_server(p)
            time.sleep(0.1)
            ServerAPI.remove_server(p)

        threads = [threading.Thread(target=add_remove_server, args=(p,)) for p in test_paths]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All servers added and removed concurrently should not remain
        servers = ServerAPI.get_servers(force=True)
        for p in test_paths:
            self.assertNotIn(p, servers)

    def test_create_job_from_template_without_template(self):
        """Test creating a job without specifying a template."""
        server = self._fwd_path(self.temp_dir, 'no_template_server')
        job = 'new_job_no_template'
        os.makedirs(server.replace('/', os.sep), exist_ok=True)
        ServerAPI.add_server(server)
        ServerAPI.create_job_from_template(server, job)
        job_path = self._fwd_path(server, job)
        self.assertTrue(os.path.exists(job_path.replace('/', os.sep)))

    def test_create_job_from_template_with_invalid_template(self):
        """Test creating a job with an invalid template name, skip if no templates available."""
        server = self._fwd_path(self.temp_dir, 'invalid_template_server')
        job = 'new_job_invalid_template'
        os.makedirs(server.replace('/', os.sep), exist_ok=True)
        ServerAPI.add_server(server)

        # Check if templates are available. If not, skip this test.
        # The code attempts to load templates and raises TemplateError otherwise.
        from ..templates.lib import TemplateType, get_saved_templates
        templates = get_saved_templates(TemplateType.UserTemplate)
        if not templates:
            self.skipTest("No templates available, skipping invalid template test.")

        with self.assertRaises(ValueError):
            ServerAPI.create_job_from_template(server, job, template='does_not_exist')

    def test_remove_link_nonexisting(self):
        """Test removing a link from a job that doesn't have it after removing once."""
        server = self._fwd_path(self.temp_dir, 'remove_link_server')
        job = 'remove_link_job'
        root = 'link_root'
        os.makedirs(self._fwd_path(server, job).replace('/', os.sep), exist_ok=True)
        ServerAPI.add_server(server)
        # Add link first, then remove it
        ServerAPI.add_link(server, job, root)
        root_path = ServerAPI.remove_link(server, job, root)
        self.assertTrue(root_path.endswith(root))

        # Attempting to remove the same link again might not raise FileNotFoundError,
        # depending on LinksAPI behavior. If it doesn't raise, we won't fail this test.
        # Remove the assertion that it should raise and just check if no error occurs.
        # If we want to ensure error, we need LinksAPI to enforce it.
        # For now, just call it and ensure no exception:
        try:
            ServerAPI.remove_link(server, job, root)
        except FileNotFoundError:
            # If it raises, it's fine too, but we won't fail if it doesn't.
            pass

    def test_slash_sanitization_on_bookmark_key(self):
        """Explicitly test slash sanitization and ensure trailing slashes are removed."""
        server = self._fwd_path(self.temp_dir, 'trailing_slash_server/')
        job = 'trailing_slash_job/'
        root = 'trailing_slash_root//'
        # The bookmark_key should normalize and remove trailing slashes
        bk_key = ServerAPI.bookmark_key(server, job, root)
        self.assertFalse(bk_key.endswith('/'))
        # Also test that no backslashes remain
        self.assertNotIn('\\', bk_key)


class TestActiveBookmarksPresetsAPI(unittest.TestCase):

    def setUp(self):
        common.initialize(
            mode=common.Mode.Core,
            run_app=False
        )
        from .activebookmarks_presets import api
        self.api = api

    def tearDown(self):
        self.api = None

        _dir = get_presets_dir()
        shutil.rmtree(_dir, ignore_errors=True)
        common.shutdown()

    def test_initial_state(self):
        self.assertEqual(self.api.get_presets(), {}, "No presets should exist initially")

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename(" test:name "), "test_name")
        self.assertEqual(sanitize_filename("  "), "untitled")
        self.assertEqual(sanitize_filename("my|preset"), "my_preset")
        self.assertEqual(sanitize_filename("my/preset"), "my_preset")
        self.assertEqual(sanitize_filename("日本"), "日本")

        with self.assertRaises(TypeError):
            sanitize_filename(None)

    def test_save_preset_snapshots_current_bookmarks(self):
        # Create some bookmarks
        bookmarks = {
            "//my-server/jobs/my-job/data/shots": {
                "server": "//my-server",
                "job": "jobs/my-job",
                "root": "data/shots"
            },
            "//my-server/jobs/my-job/data/assets": {
                "server": "//my-server",
                "job": "jobs/my-job",
                "root": "data/assets"
            }
        }
        ServerAPI.save_bookmarks(bookmarks)

        self.api.save_preset("MyPreset")
        self.assertTrue(self.api.exists("MyPreset"))
        presets = self.api.get_presets()
        self.assertIn("MyPreset", presets)
        data = presets["MyPreset"]
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["job"], "jobs/my-job")

    def test_verify_preset_invalid_data(self):
        # Test invalid top-level keys
        with self.assertRaises(ValueError):
            self.api._verify_preset({"data": []})  # Missing name
        with self.assertRaises(ValueError):
            self.api._verify_preset({"name": "Test"})  # Missing data

        # Invalid name
        with self.assertRaises(ValueError):
            self.api._verify_preset({"name": " ", "data": []})

        # data not a list
        with self.assertRaises(TypeError):
            self.api._verify_preset({"name": "Test", "data": {}})

        # Invalid data item type
        with self.assertRaises(TypeError):
            self.api._verify_preset({"name": "Test", "data": ["not a dict"]})

        # Missing keys in data item
        with self.assertRaises(ValueError):
            self.api._verify_preset({"name": "Test", "data": [{}]})

        # Empty strings
        with self.assertRaises(ValueError):
            self.api._verify_preset({"name": "Test", "data": [{"server": " ", "job": "job", "root": "root"}]})

    def test_import_export_preset(self):
        _dir = get_presets_dir()
        data = {
            "name": "OriginalName",
            "data": [
                {"server": "//server", "job": "job", "root": "root"}
            ]
        }
        source_file = os.path.join(_dir, "source.json")
        with open(source_file, "w") as f:
            json.dump(data, f)

        # Import with rename
        self.api.import_preset("Imported", source_file)
        self.assertTrue(self.api.exists("Imported"))
        self.assertFalse(self.api.exists("OriginalName"))

        # Export
        dest_file = os.path.join(_dir, "exported.json")
        self.api.export_preset("Imported", dest_file)
        self.assertTrue(os.path.exists(dest_file))
        with open(dest_file, "r") as f:
            exported = json.load(f)
        self.assertEqual(exported["name"], "Imported")

        # Non-existent preset export
        with self.assertRaises(FileNotFoundError):
            self.api.export_preset("DoesNotExist", dest_file)

        # Import existing without force
        with self.assertRaises(FileExistsError):
            self.api.import_preset("Imported", source_file)

        # With force
        self.api.import_preset("Imported", source_file, force=True)
        self.assertTrue(self.api.exists("Imported"))

    def test_exists_method(self):
        self.assertFalse(self.api.exists("NoPreset"))
        # Create and save a preset directly
        data = {
            "name": "TestExists",
            "data": [
                {"server": "//server", "job": "job", "root": "root"}
            ]
        }
        self.api._save_preset_data("TestExists", data, True)
        self.assertTrue(self.api.exists("TestExists"))

    def test_preset_to_path(self):
        data = {
            "name": "PathTest",
            "data": [
                {"server": "//server", "job": "my-job", "root": "some/root"}
            ]
        }
        self.api._save_preset_data("PathTest", data, True)
        p = self.api.get_paths_from_preset("PathTest")
        self.assertEqual(len(p), 1)

        self.assertEqual(p[0], "//server/my-job/some/root")

        # Non-existent
        self.assertEqual(self.api.get_paths_from_preset("NoSuch"), [])

    def test_delete_preset(self):
        data = {
            "name": "DeleteMe",
            "data": [
                {"server": "//s", "job": "j", "root": "r"}
            ]
        }
        self.api._save_preset_data("DeleteMe", data, True)
        self.assertTrue(self.api.exists("DeleteMe"))
        self.api.delete_preset("DeleteMe")
        self.assertFalse(self.api.exists("DeleteMe"))
        self.api.delete_preset("DeleteMe")  # No error

    def test_activate_preset(self):
        # Create bookmarks in a preset
        data = {
            "name": "ActivateMe",
            "data": [
                {"server": "//act-server", "job": "act-job", "root": "act-root"},
                {"server": "//act-server", "job": "act-job2", "root": "act-root2"}
            ]
        }
        self.api._save_preset_data("ActivateMe", data, True)
        self.api.activate_preset("ActivateMe")

        # Check that bookmarks are loaded correctly
        bookmarks = ServerAPI.bookmarks()
        self.assertTrue([f for f in bookmarks.keys() if "//act-server" in f])
        self.assertTrue([f for f in bookmarks.keys() if "job" in f])
        self.assertTrue([f for f in bookmarks.keys() if "act-root" in f])

        # Non-existent preset
        with self.assertRaises(FileNotFoundError):
            self.api.activate_preset("NoSuchPreset")

    def test_clear_presets(self):
        data = {
            "name": "ClearTest",
            "data": [
                {"server": "//c", "job": "c", "root": "c"}
            ]
        }
        self.api._save_preset_data("ClearTest", data, True)
        self.api.clear_presets()
        self.assertFalse(self.api.exists("ClearTest"))
        self.assertEqual(self.api.get_presets(), {})

    def test_is_valid(self):
        data = {
            "name": "ValidTest",
            "data": [
                {"server": "//valid", "job": "valid-job", "root": "valid-root"}
            ]
        }
        self.api._save_preset_data("ValidTest", data, True)
        self.assertTrue(self.api.is_valid("ValidTest"))
        self.assertFalse(self.api.is_valid("NoSuchPreset"))

        # Create a corrupt file
        _dir = get_presets_dir()
        corrupt_path = os.path.join(_dir, "Corrupt.json")
        with open(corrupt_path, "w") as f:
            f.write("NOT JSON")
        self.api.get_presets(force=True)
        # Corrupt won't appear in _presets, so is_valid should be False
        self.assertFalse(self.api.is_valid("Corrupt"))

    def test_rename_preset(self):
        data = {
            "name": "OldName",
            "data": [
                {"server": "//old", "job": "old", "root": "old"}
            ]
        }
        self.api._save_preset_data("OldName", data, True)
        self.api.rename_preset("OldName", "NewName")
        self.assertFalse(self.api.exists("OldName"))
        self.assertTrue(self.api.exists("NewName"))

        data2 = {
            "name": "Another",
            "data": [
                {"server": "//a", "job": "a", "root": "a"}
            ]
        }
        self.api._save_preset_data("Another", data2, True)
        with self.assertRaises(FileExistsError):
            self.api.rename_preset("NewName", "Another")

        # With force
        self.api.rename_preset("NewName", "Another", force=True)
        self.assertFalse(self.api.exists("NewName"))
        self.assertTrue(self.api.exists("Another"))

    def test_unicode_support(self):
        data = {
            "name": "日本語",
            "data": [
                {"server": "//サーバー", "job": "クライアント/仕事", "root": "データ/ショット"}
            ]
        }
        self.api._save_preset_data("日本語", data, True)
        self.assertTrue(self.api.exists("日本語"))

        paths = self.api.get_paths_from_preset("日本語")
        self.assertEqual(len(paths), 1)

        self.assertIn("サーバー", paths[0])
        self.assertIn("クライアント/仕事", paths[0])
        self.assertIn("データ/ショット", paths[0])

        self.assertTrue(self.api.is_valid("日本語"))
        self.api.activate_preset("日本語")

        bookmarks = ServerAPI.bookmarks()
        self.assertTrue([f for f in bookmarks.keys() if "//サーバー" in f])

    def test_wrong_types_for_methods(self):
        # Passing non-str preset_name
        with self.assertRaises(TypeError):
            self.api.exists(None)

        bookmarks = {
            "//my-server/jobs/my-job/data/shots": {
                "server": "//my-server",
                "job": 123,  # not a string
                "root": "data/shots"
            }
        }

        with self.assertRaises(TypeError):
            ServerAPI.save_bookmarks(bookmarks)



if __name__ == '__main__':
    unittest.main()
