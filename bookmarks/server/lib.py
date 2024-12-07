import enum
import os
import re
import subprocess

from .. import common, log, actions
from ..links.lib import LinksAPI
from ..templates.lib import TemplateItem, TemplateType


class JobDepth(enum.IntEnum):
    NoParent = 0
    HasParent = 1
    HasGrandparent = 2


class ServerAPI:
    server_settings_key = 'servers/value'
    job_style_settings_key = 'servers/JobDepth'
    bookmark_settings_key = 'user/bookmarks'

    @classmethod
    def add_server(cls, path):
        """Adds a server item to the list of user specified servers.

        Args:
            path (str): A path to a server, for example, `Q:/jobs`.

        Emits:
            serverAdded (str): The path of the server that was added.
            serversChanged (): Emitted when the list of servers has changed.

        """
        if not isinstance(path, str):
            raise TypeError('Expected a string')

        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        path = path.replace('\\', '/')
        if ':' in path and len(path) <= 4 and not path.endswith('/'):
            raise ValueError('Windows drive letters must end with a trailing slash')

        if not cls.check_permissions(path):
            raise PermissionError(f'Access denied to {path}')

        values = common.settings.value(cls.server_settings_key)
        values = values if values else {}
        values = {k: v for k, v in sorted(values.items(), key=lambda x: x[0].lower())}

        if path in values:
            raise ValueError('Server already exists in the list of user specified servers.')

        values[path] = path
        common.settings.setValue(cls.server_settings_key, values)
        common.servers = values

        # Emit signals
        common.signals.serverAdded.emit(path)
        common.signals.serversChanged.emit()

    @classmethod
    def remove_server(cls, path):
        """Remove a server item from the list of user specified servers.

        Args:
            path (str): A path to a server, for example, `Q:/jobs`.

        """
        if not isinstance(path, str):
            raise TypeError('Expected a string')

        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        if path in {v['server'] for v in common.bookmarks.values()}:
            raise ValueError('Cannot remove server. Server is currently bookmarked.')

        path = path.replace('\\', '/')

        values = common.settings.value(cls.server_settings_key)
        values = values if values else {}

        if path not in values:
            raise ValueError('Server does not exist in the list of user specified servers.')

        del values[path]
        values = {k: v for k, v in sorted(values.items(), key=lambda x: x[0].lower())}

        common.settings.setValue(cls.server_settings_key, values)
        common.servers = values

        # Emit signals
        common.signals.serverRemoved.emit(path)
        common.signals.serversChanged.emit()
        common.signals.bookmarksChanged.emit()

    @classmethod
    def clear_servers(cls):
        """Clears the list of user specified servers."""
        values = common.settings.value(cls.server_settings_key)
        values = values if values else {}

        for k in list(values.keys()):
            if k in {v['server'] for v in common.bookmarks.values()}:
                log.error(f'Cannot remove server {k} as it is in use by a bookmark item')
                continue
            del values[k]
            del common.servers[k]

            common.settings.setValue(cls.server_settings_key, values)
            common.signals.serverRemoved.emit(k)
            common.signals.serversChanged.emit()

        common.settings.setValue(cls.server_settings_key, {})
        if common.settings.value(cls.server_settings_key):
            raise RuntimeError('Failed to clear servers')

    @classmethod
    def get_servers(cls, force=False):
        """Returns a list of available network servers.

        Args:
            force (bool): If True, the list of servers is reloaded from the user settings file.

        """
        if not force and common.servers is not None:
            return common.servers

        values = common.settings.value(cls.server_settings_key)
        values = values if values else {}
        values = {k: v for k, v in sorted(values.items(), key=lambda x: x[0].lower())}

        common.servers = values
        return values.copy()

    @staticmethod
    def check_permissions(path):
        """
        Checks if the current user has specified access rights to the given path.

        Args:
            path (str): Path to check permissions for.

        Returns:
            bool: True if the user has the specified access rights, False otherwise

        """
        if not os.access(path, os.R_OK | os.W_OK | os.X_OK):
            return False
        return True

    @classmethod
    def get_mapped_drives(cls):
        """Returns a dictionary mapping drive letters to UNC paths for mapped network drives."""
        mapped_drives = {}

        if common.get_platform() == common.PlatformUnsupported:
            raise NotImplementedError('Platform not supported')
        elif common.get_platform() == common.PlatformMacOS:
            raise NotImplementedError('Platform not supported')
        elif common.get_platform() == common.PlatformWindows:
            import string

            for drive_letter in string.ascii_uppercase:
                drive = f'{drive_letter}:/'
                if os.path.exists(drive):
                    try:
                        unc_path = cls.drive_to_unc(drive)
                        if ':' in unc_path:
                            unc_path = f'{unc_path}/'
                        mapped_drives[drive] = unc_path
                    except:
                        log.error(f'Failed to convert drive letter {drive} to UNC path')
                        pass
        return mapped_drives

    @staticmethod
    def drive_to_unc(path):
        """Converts a Windows drive letter to a UNC path.

        Args:
            path (str): Path to convert.

        Returns:
            str: UNC path or the original path if conversion is not possible.
        """
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
                log.error(f'Failed to get mapped drives: {e}')
                return path

            # Look for the line that corresponds to the drive letter
            for line in output.splitlines():
                v = re.split(r'\s{3,}', line)
                if len(v) >= 3 and v[0] == 'OK' and path in v[1]:
                    return v[2].replace('\\', '/').strip()
            return path

    @classmethod
    def unc_to_drive(cls, path):
        """Converts a UNC path to a Windows drive letter.

        Args:
            path (str): Path to convert.

        Returns:
            str: Drive-letter or the original path if conversion isn't possible.

        """
        if common.get_platform() == common.PlatformUnsupported:
            raise NotImplementedError('Platform not supported')
        elif common.get_platform() == common.PlatformMacOS:
            raise NotImplementedError('Platform not supported')
        elif common.get_platform() == common.PlatformWindows:
            path = path.replace('\\', '/')
            if not path.startswith('//'):
                return path

            for drive, unc_path in cls.get_mapped_drives().items():
                if path in unc_path:
                    return drive
            return path

    @staticmethod
    def create_job_from_template(server, job, template=None):
        """Add the given bookmark item and save it in the user settings file.

        Args:
            server (str): `server` path segment.
            job (str): `job` path segment.
            template (str): `template` path segment. Default is None.

        """
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

        templates = TemplateItem.get_saved_templates(TemplateType.UserTemplate)
        if not templates:
            raise FileNotFoundError('No templates found')

        if template not in [f['name'] for f in templates]:
            raise ValueError(f'Invalid template name: {template}')

        # Copy the template files to the new job path
        template_item = next(f for f in templates if f['name'] == template)
        template_item.extract_template(
            root_path,
            ignore_existing_folders=False,
            extract_contents_to_links=False,
        )

    @classmethod
    def add_link(cls, server, job, root):
        """Add a relative path to the given job.

        The `root` path segment is to be stored in a .links file in the root of the job folder.

        Args:
            server (str): `server` path segment.
            job (str): `job` path segment.
            root (str): `root` path segment.

        """
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
        """Remove the given root item from the job.

        Args:
            server (str): `server` path segment.
            job (str): `job` path segment.
            root (str): `root` path segment.

        """
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
        """Clear all root folders from the user settings file.

        This method removes all bookmarked job folders from the user settings file.

        """
        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        common.settings.setValue(cls.bookmark_settings_key, {})
        common.bookmarks = {}
        common.signals.bookmarksChanged.emit()

    @classmethod
    def bookmark_job_folder(cls, server, job, root):
        """Add the given bookmark item and save it in the user settings file.

        Args:
            server (str): `server` path segment.
            job (str): `job` path segment.
            root (str): `root` path segment.

        """
        if not os.path.exists(server):
            raise FileNotFoundError(f'Server path {server} does not exist')

        if not isinstance(server, str) or not isinstance(job, str) or not isinstance(root, str):
            raise TypeError('Expected three strings')

        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        k = common.bookmark_key(server, job, root)
        if k in common.bookmarks:
            raise FileExistsError('Folder has already been bookmarked!')

        data = common.bookmarks.copy()

        data[k] = {
            'server': server,
            'job': job,
            'root': root
        }
        common.bookmarks = data
        common.settings.setValue(cls.bookmark_settings_key, data)
        common.signals.bookmarkAdded.emit(server, job, root)

    @classmethod
    def unbookmark_job_folder(cls, server, job, root):
        """Remove the given bookmark from the user settings file.

        Removing a bookmark item will close and delete the item's database controller
        instances.

        Args:
            server (str): `server` path segment.
            job (str): `job` path segment.
            root (str): A path segment.

        """
        if not os.path.exists(server):
            raise FileNotFoundError(f'Server path {server} does not exist')

        if not isinstance(server, str) or not isinstance(job, str) or not isinstance(root, str):
            raise TypeError('Expected three strings')

        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        k = common.bookmark_key(server, job, root)
        if k not in common.bookmarks:
            raise FileNotFoundError('Bookmark item does not exist')

        data = common.bookmarks.copy()

        # If the bookmark removed is currently active, reset the active
        if (
                common.active('server') == server and
                common.active('job') == job and
                common.active('root') == root
        ):
            common.set_active('server', None)
            actions.change_tab(common.BookmarkTab)

        del data[k]

        common.settings.setValue(cls.bookmark_settings_key, data)
        common.signals.bookmarkRemoved.emit(server, job, root)

    @classmethod
    def save_bookmarks(cls, data):
        """Set the saved bookmarks to the user settings file.

        Args:
            data (dict): A dictionary of bookmark items.

        """
        if not isinstance(data, dict):
            raise TypeError('Expected a dictionary')

        if common.settings is None:
            raise ValueError('The user settings object is not initialized.')

        for v in data.values():
            if not all(k in v for k in ['server', 'job', 'root']):
                raise ValueError('Invalid bookmark item')

        common.settings.setValue(cls.bookmark_settings_key, data.copy())
        common.bookmarks = data.copy()
        common.signals.bookmarksChanged.emit()

    @staticmethod
    def get_env_bookmarks():
        """Check the current environment for any predefined bookmark items.

        If the environment contains any Bookmarks_ENV_ITEM# variables, they will be
        parsed and returned as a dictionary.

        The format of the variables should be set as follows using either a comma or
        semicolon as a delimiter:

        - "Bookmarks_ENV_ITEM0=server;job;root"
        - "Bookmarks_ENV_ITEM1=server,job,root"

        Don't use spaces as delimiters, this won't be parsed correctly:
        - "Bookmarks_ENV_ITEM2=server job root"

        Only the first three items are considered, so
        - "Bookmarks_ENV_ITEM3=server;job;root;asset;asset_path"
        is valid, but `asset` and `asset_path` are ignored.

        Returns:
            dict: The parsed data.

        """
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

    @classmethod
    def load_bookmarks(cls):
        """Loads all available bookmarks into memory.

        The bookmark items are made up of root items saved by the user to the user settings and
        items defined in the current environment. The environment bookmarks
        are "static", and can't be removed.

        """
        _current = common.bookmarks.copy()

        _static = cls.get_env_bookmarks()
        _static = _static if _static else {}

        # Save default items to cache
        common.env_bookmark_items = _static

        _user = common.settings.value(cls.bookmark_settings_key)
        _user = _user if _user else {}

        # Merge the static and custom bookmarks
        v = _static.copy()
        v.update(_user)

        # Remove invalid values before adding
        for k in list(v.keys()):
            if (
                    'server' not in v[k]
                    or 'job' not in v[k]
                    or 'root' not in v[k]
            ):
                del v[k]
                continue

            # Add servers defined in the bookmark items:
            common.servers[v[k]['server']] = v[k]['server']

        common.bookmarks = v

        if _current != common.bookmarks:
            common.signals.bookmarksChanged.emit()
