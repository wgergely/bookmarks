"""
This module provides an API for managing servers, bookmarks, and related job paths.

It allows adding, removing, and listing servers, creating jobs from templates,
managing bookmarks, and translating between drive letters and UNC paths.
"""
import enum
import os
import re
import subprocess
import threading

from .. import common, log, actions
from ..links.lib import LinksAPI
from ..templates.lib import TemplateType, get_saved_templates


class JobDepth(enum.IntEnum):
    """Represents the depth of a job directory hierarchy."""
    NoParent = 0
    HasParent = 1
    HasGrandparent = 2


class ServerAPI:
    """API for managing servers, bookmarks, and related job paths."""

    server_settings_key = 'servers/value'
    job_style_settings_key = 'servers/JobDepth'
    bookmark_settings_key = 'user/bookmarks'

    _lock = threading.RLock()

    @classmethod
    def bookmark_key(cls, server, job, root):
        """Returns a generic string representation of a bookmark item.

        Args:
            server (str): `server` path segment.
            job (str): `job` path segment.
            root (str): `root` path segment.

        Returns:
            str: The bookmark item key.
        """
        k = '/'.join([common.strip(f) for f in (server, job, root)]).rstrip('/')
        return k

    @classmethod
    def add_server(cls, path):
        """Add a server path to the user settings."""
        if not isinstance(path, str):
            raise TypeError('Expected a string')
        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        path = path.replace('\\', '/')
        if ':' in path and len(path) <= 4 and not path.endswith('/'):
            raise ValueError('Windows drive letters must end with a trailing slash')

        if not cls.check_permissions(path):
            raise PermissionError(f'Access denied to {path}')

        with cls._lock:
            values = common.settings.value(cls.server_settings_key) or {}
            values = {k: v for k, v in sorted(values.items(), key=lambda x: x[0].lower())}

            if path in values:
                raise ValueError('Server already exists in the list of user specified servers.')

            values[path] = path
            common.settings.setValue(cls.server_settings_key, values)
            common.servers = values

        common.signals.serverAdded.emit(path)
        common.signals.serversChanged.emit()

    @classmethod
    def remove_server(cls, path):
        """Remove a server path from the user settings."""
        if not isinstance(path, str):
            raise TypeError('Expected a string')
        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        path = path.replace('\\', '/')

        with cls._lock:
            # Check if server is bookmarked
            if path in {v['server'] for v in common.bookmarks.values()}:
                raise ValueError('Cannot remove server. Server is currently bookmarked.')

            values = common.settings.value(cls.server_settings_key) or {}
            if path not in values:
                raise ValueError('Server does not exist in the list of user specified servers.')

            del values[path]
            values = {k: v for k, v in sorted(values.items(), key=lambda x: x[0].lower())}
            common.settings.setValue(cls.server_settings_key, values)
            common.servers = values

        common.signals.serverRemoved.emit(path)
        common.signals.serversChanged.emit()
        common.signals.bookmarksChanged.emit()

    @classmethod
    def clear_servers(cls):
        """Clear all servers from the user settings."""
        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        with cls._lock:
            values = common.settings.value(cls.server_settings_key) or {}
            for k in list(values.keys()):
                if k in {v['server'] for v in common.bookmarks.values()}:
                    log.error(__name__, f'Cannot remove server {k} as it is in use by a bookmark item')
                    continue
                del values[k]
                if k in common.servers:
                    del common.servers[k]
                common.settings.setValue(cls.server_settings_key, values)
                common.signals.serverRemoved.emit(k)
                common.signals.serversChanged.emit()

            common.settings.setValue(cls.server_settings_key, {})
            if common.settings.value(cls.server_settings_key):
                raise RuntimeError('Failed to clear servers')

    @classmethod
    def get_servers(cls, force=False):
        """Get the list of servers from the user settings."""
        with cls._lock:
            if not force and common.servers is not None:
                return common.servers.copy()
            values = common.settings.value(cls.server_settings_key) or {}
            values = {k: v for k, v in sorted(values.items(), key=lambda x: x[0].lower())}
            common.servers = values
            return values.copy()

    @staticmethod
    def check_permissions(path):
        """Check if the current user has read/write/execute permissions on a path."""
        return os.access(path, os.R_OK | os.W_OK | os.X_OK)

    @classmethod
    def get_mapped_drives(cls):
        """Get a dictionary of mapped drives on Windows."""
        if common.get_platform() == common.PlatformUnsupported:
            raise NotImplementedError('Platform not supported')
        elif common.get_platform() == common.PlatformMacOS:
            raise NotImplementedError('Platform not supported')
        elif common.get_platform() == common.PlatformWindows:
            import string
            mapped_drives = {}
            for drive_letter in string.ascii_uppercase:
                drive = f'{drive_letter}:/'
                if os.path.exists(drive):
                    try:
                        unc_path = cls.drive_to_unc(drive)
                        if ':' in unc_path:
                            unc_path = f'{unc_path}/'
                        mapped_drives[drive] = unc_path
                    except:
                        log.error(__name__, f'Failed to convert drive letter {drive} to UNC path')
                        pass
            return mapped_drives
        return {}

    @staticmethod
    def drive_to_unc(path):
        """Convert a Windows drive letter to a UNC path."""
        if common.get_platform() == common.PlatformUnsupported:
            raise NotImplementedError('Platform not supported')
        elif common.get_platform() == common.PlatformMacOS:
            raise NotImplementedError('Platform not supported')
        elif common.get_platform() == common.PlatformWindows:
            path = path.strip('\\/').upper()
            try:
                result = subprocess.run(['net', 'use'], capture_output=True, text=True, check=True)
                output = result.stdout
            except subprocess.CalledProcessError as e:
                log.error(__name__, f'Failed to get mapped drives: {e}')
                return path
            for line in output.splitlines():
                v = re.split(r'\s{3,}', line)
                if len(v) >= 3 and v[0] == 'OK' and path in v[1]:
                    return v[2].replace('\\', '/').strip()
            return path

    @classmethod
    def unc_to_drive(cls, path):
        """Convert a UNC path to a mapped Windows drive letter if possible."""
        if common.get_platform() == common.PlatformUnsupported:
            raise NotImplementedError('Platform not supported')
        elif common.get_platform() == common.PlatformMacOS:
            raise NotImplementedError('Platform not supported')
        elif common.get_platform() == common.PlatformWindows:
            path = path.replace('\\', '/')
            if not path.startswith('//'):
                return path
            drives = cls.get_mapped_drives()
            for drive, unc_path in drives.items():
                if path in unc_path:
                    return drive
            return path
        return path

    @staticmethod
    def create_job_from_template(server, job, template=None):
        """Create a new job directory from a given template."""
        if not os.path.exists(server):
            raise FileNotFoundError(f'Server path {server} does not exist')
        if not isinstance(server, str) or not isinstance(job, str):
            raise TypeError('Expected two strings')
        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        root_path = os.path.join(server, job)
        if os.path.exists(root_path):
            raise FileExistsError(f'Job path {root_path} already exists')

        os.makedirs(root_path, exist_ok=True)
        if template is None:
            return

        templates = get_saved_templates(TemplateType.UserTemplate)
        if not templates:
            raise FileNotFoundError('No templates found')

        if template not in [f['name'] for f in templates]:
            raise ValueError(f'Invalid template name: {template}')

        template_item = next(f for f in templates if f['name'] == template)
        template_item.template_to_folder(
            root_path,
            ignore_existing_folders=False,
            extract_contents_to_links=False,
        )

    @classmethod
    def add_link(cls, server, job, root):
        """Add a relative path link to a job."""
        if not os.path.exists(server):
            raise FileNotFoundError(f'Server path {server} does not exist')
        if not isinstance(server, str) or not isinstance(job, str) or not isinstance(root, str):
            raise TypeError('Expected three strings')
        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        job_path = os.path.join(server, job)
        if not os.path.exists(job_path):
            raise FileNotFoundError(f'Job path {job_path} does not exist')

        root_path = os.path.join(job, root)
        if os.path.exists(root_path):
            raise FileExistsError(f'Root path {root_path} already exists')

        job_path = job_path.replace('\\', '/')
        api = LinksAPI(job_path)
        api.add(root, force=True)
        return root_path

    @classmethod
    def remove_link(cls, server, job, root):
        """Remove a link from a job."""
        if not os.path.exists(server):
            raise FileNotFoundError(f'Server path {server} does not exist')
        if not isinstance(server, str) or not isinstance(job, str) or not isinstance(root, str):
            raise TypeError('Expected three strings')
        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        job_path = f'{server}/{job}'
        if not os.path.exists(job_path):
            raise FileNotFoundError(f'Job path {job_path} does not exist')

        root_path = f'{server}/{job}/{root}'
        api = LinksAPI(job_path)
        api.remove(root)
        return root_path

    @classmethod
    def clear_bookmarks(cls):
        """Clear all bookmarked items."""
        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        with cls._lock:
            common.settings.setValue(cls.bookmark_settings_key, {})
            common.bookmarks = {}

        common.signals.bookmarksChanged.emit()

    @classmethod
    def bookmark_job_folder(cls, server, job, root):
        """Bookmark a job folder."""
        if not os.path.exists(server):
            raise FileNotFoundError(f'Server path {server} does not exist')
        if not isinstance(server, str) or not isinstance(job, str) or not isinstance(root, str):
            raise TypeError('Expected three strings')
        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        k = cls.bookmark_key(server, job, root)
        with cls._lock:
            if k in common.bookmarks:
                raise FileExistsError('Folder has already been bookmarked!')

            data = common.bookmarks.copy()
            data[k] = {'server': server, 'job': job, 'root': root}
            common.bookmarks = data
            common.settings.setValue(cls.bookmark_settings_key, data)

        common.signals.bookmarkAdded.emit(server, job, root)

    @classmethod
    def unbookmark_job_folder(cls, server, job, root):
        """Remove a bookmark from a job folder."""
        if not os.path.exists(server):
            raise FileNotFoundError(f'Server path {server} does not exist')
        if not isinstance(server, str) or not isinstance(job, str) or not isinstance(root, str):
            raise TypeError('Expected three strings')
        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        k = cls.bookmark_key(server, job, root)
        with cls._lock:
            if k not in common.bookmarks:
                raise FileNotFoundError('Bookmark item does not exist')

            data = common.bookmarks.copy()
            if (common.active('server') == server and
                    common.active('job') == job and
                    common.active('root') == root):
                common.set_active('server', None)
                actions.change_tab(common.BookmarkTab)

            del data[k]
            common.settings.setValue(cls.bookmark_settings_key, data)
            common.bookmarks = data

        common.signals.bookmarkRemoved.emit(server, job, root)

    @classmethod
    def save_bookmarks(cls, data):
        """Save a dictionary of bookmarks to user settings."""
        if not isinstance(data, dict):
            raise TypeError('Expected a dictionary')
        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        for v in data.values():
            if not all(k in v for k in ['server', 'job', 'root']):
                raise ValueError('Invalid bookmark item')

        with cls._lock:
            common.settings.setValue(cls.bookmark_settings_key, data.copy())
            common.bookmarks = data.copy()

        common.signals.bookmarksChanged.emit()

    @staticmethod
    def get_env_bookmarks():
        """Get bookmarks defined in environment variables."""
        delims = [';', ',']
        bookmark_items = {}
        for i in range(99):
            env_var = f'Bookmarks_ENV_ITEM{i}'
            if env_var not in os.environ:
                continue
            v = os.environ[env_var]
            if not v:
                continue
            for delim in delims:
                _v = v.split(delim)
                if len(_v) >= 3:
                    _v = [x.strip() for x in _v]
                    bookmark_items[f'{_v[0]}/{_v[1]}/{_v[2]}'] = {
                        'server': _v[0],
                        'job': _v[1],
                        'root': _v[2]
                    }
                    break
        return bookmark_items

    @classmethod
    def load_bookmarks(cls):
        """Load bookmarks from both user settings and environment variables."""
        with cls._lock:
            _current = common.bookmarks.copy()
            _static = cls.get_env_bookmarks() or {}
            common.env_bookmark_items = _static

            _user = common.settings.value(cls.bookmark_settings_key) or {}
            v = _static.copy()
            v.update(_user)

            # Validate and ensure servers exist
            for k in list(v.keys()):
                if ('server' not in v[k] or 'job' not in v[k] or 'root' not in v[k]):
                    del v[k]
                    continue
                common.servers[v[k]['server']] = v[k]['server']

            common.bookmarks = v

        if _current != common.bookmarks:
            common.signals.bookmarksChanged.emit()

        return common.bookmarks.copy()
