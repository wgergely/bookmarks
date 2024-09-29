import enum
import os
import re
import subprocess

from .. import common, log, actions
from ..links.lib import LinksAPI
from ..templates.lib import TemplateItem, TemplateType


class JobStyle(enum.IntEnum):
    NoSubdirectories = 0 # no subdirectories
    JobHasClient = 1 # 1 subdirectory
    JobHasClientAndDepartment = 2 # 2 subdirectories



class ServerAPI:
    server_settings_key = 'user/servers'
    job_style_settings_key = 'servers/jobstyle'

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

        if not cls.check_permissions(path):
            raise PermissionError(f'Access denied to {path}')

        path = path.replace('\\', '/')

        common.settings.sync()
        values = common.settings.value(cls.server_settings_key, {})
        values = {k.rstrip('/'): v for k, v in sorted(values.items(), key=lambda x: x[0].lower())}

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

        path = path.replace('\\', '/')

        common.settings.sync()
        values = common.settings.value(cls.server_settings_key, {})

        if path not in values:
            raise ValueError('Server does not exist in the list of user specified servers.')

        values = {k.rstrip('/'): v for k, v in sorted(values.items(), key=lambda x: x[0].lower())}
        del values[path]

        common.settings.setValue(cls.server_settings_key, values)
        common.servers = values

        # Emit signals
        common.signals.serverRemoved.emit(path)
        common.signals.serversChanged.emit()
        common.signals.bookmarksChanged.emit()

    @classmethod
    def clear_servers(cls):
        """Clears the list of user specified servers."""
        common.settings.sync()
        values = common.settings.value(cls.server_settings_key, {})

        for k in list(values.keys()):
            del values[k]
            del common.servers[k]
            common.signals.serverRemoved.emit(k)

        common.settings.setValue(cls.server_settings_key, {})
        common.servers = {}

        common.signals.serversChanged.emit()
        common.signals.bookmarksChanged.emit()

    @classmethod
    def get_servers(cls, force=False):
        """Returns a list of available network servers.

        Args:
            force (bool): If True, the list of servers is reloaded from the user settings file.

        """
        if not force and common.servers is not None:
            return common.servers

        common.settings.sync()

        values = common.settings.value(cls.server_settings_key, {})
        values = {k.rstrip('/'): v for k, v in sorted(values.items(), key=lambda x: x[0].lower())}

        common.servers = values.copy()
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
        for m in (os.R_OK, os.W_OK, os.X_OK):
            if not os.access(path, m):
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
                drive = f'{drive_letter}:'
                if os.path.exists(drive):
                    try:
                        unc_path = cls.drive_to_unc(drive)
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
                print(f"Error running 'net use': {e}")
                return None

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
    def add_root_item_to_job(cls, server, job, root):
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
    def remove_root_item_from_job(cls, server, job, root):
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

        job_path = os.path.join(server, job)
        if not os.path.exists(job_path):
            raise FileNotFoundError(f'Job path {job_path} does not exist')

        root_path = os.path.join(job, root)
        if not os.path.exists(root_path):
            raise FileNotFoundError(f'Root path {root_path} does not exist')

        job_path = job_path.replace('\\', '/')

        api = LinksAPI(job_path)
        api.remove(root)

        return root_path

    @classmethod
    def add_root_folder_to_saved_bookmarks(cls, server, job, root):
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
            raise FileExistsError('Bookmark item already exists')

        common.bookmarks[k] = {
            'server': server,
            'job': job,
            'root': root
        }
        common.settings.set_bookmarks(common.bookmarks)
        common.signals.bookmarkAdded.emit(server, job, root)

    @classmethod
    def remove_root_folder_from_saved_bookmarks(cls, server, job, root):
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

        # If the bookmark removed is currently active, reset the active
        if (
                common.active('server') == server and
                common.active('job') == job and
                common.active('root') == root
        ):
            actions.set_active('server', None)
            actions.change_tab(common.BookmarkTab)

        del common.bookmarks[k]
        common.settings.set_bookmarks(common.bookmarks)
        common.signals.bookmarkRemoved.emit(server, job, root)
