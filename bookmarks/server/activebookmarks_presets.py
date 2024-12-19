"""This module implements a simple API for managing active bookmarks presets.

Each preset is saved as a single JSON file with the following structure:

.. code-block:: json

    {
        "name": "PresetName",
        "data": [
            {
                "server": "//my-server.local/jobs",
                "job": "my-client/my-job",
                "root": "data/shots"
            },
            {
                "server": "//my-server.local/jobs",
                "job": "my-client/my-job",
                "root": "data/assets"
            },
            ...
        ]
    }

Internally, the presets are stored as a dictionary of the form:

.. code-block:: python

    self._presets = {
        "PresetName": [
            {
                "server": "//my-server.local/jobs",
                "job": "my-client/my-job",
                "root": "data/shots"
            },
            {
                "server": "//my-server.local/jobs",
                "job": "my-client/my-job",
                "root": "data/assets"
            }
        ]
    }

When saving a preset, we snapshot the current `common.bookmarks` dictionary. The `common.bookmarks`
dict is keyed by a unique bookmark path, and values are dicts containing 'server', 'job', and 'root'.

See also:
    :class:`.ServerAPI`

"""
import json
import os
import re

from PySide2 import QtCore

from . import lib
from .lib import ServerAPI
from .. import common
from .. import log

__all__ = [
    'ActiveBookmarksPresetsAPI',
    'get_presets_dir',
    'sanitize_filename',
    'init_active_bookmark_presets',
    'get_api',
]

PRESETS_DIR = f'{QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.GenericDataLocation)}/{common.product}/bookmark_presets'
api = None


def get_api():
    """Get the active bookmarks presets API instance.

    Returns:
        ActiveBookmarksPresetsAPI: The API instance.
    """
    global api
    if api is None:
        init_active_bookmark_presets()

    if not isinstance(api, ActiveBookmarksPresetsAPI):
        raise TypeError('API must be an instance of ActiveBookmarksPresetsAPI')

    return api


def init_active_bookmark_presets():
    global api

    if api is not None:
        raise RuntimeError('API already initialized')

    _dir = get_presets_dir()
    if not os.path.exists(_dir):
        os.makedirs(_dir)
        log.debug(__name__, f'Created directory: {_dir}')

    api = ActiveBookmarksPresetsAPI()

    if not isinstance(api, ActiveBookmarksPresetsAPI):
        raise TypeError('API must be an instance of ActiveBookmarksPresetsAPI')

    return api


def teardown_active_bookmark_presets():
    global api

    if api is None:
        log.warning(__name__, 'API already torn down')

    api = None


def get_presets_dir():
    """Return the directory where presets are stored.

    Returns:
        str: The directory path.
    """
    if not os.path.exists(PRESETS_DIR):
        os.makedirs(PRESETS_DIR, exist_ok=True)
    return PRESETS_DIR


def sanitize_filename(name):
    """Sanitize a given string for use as a filename.

    This removes or replaces characters that are invalid or unsafe for filenames
    across common operating systems. It also trims whitespace and replaces empty
    names with a default name.

    Args:
        name (str): The original filename string.

    Returns:
        str: A sanitized version safe for use as a filename.
    """
    if not isinstance(name, str):
        raise TypeError('Filename must be a string')

    # Trim whitespace
    name = name.strip()

    # Define a set of invalid characters:
    # On Windows: < > : " / \ | ? *
    # We'll also exclude control characters and ensure no null bytes, etc.
    invalid_pattern = r'[<>:"/\\|?*\x00-\x1F]'

    # Replace invalid characters with underscore
    name = re.sub(invalid_pattern, '_', name)

    # If the name becomes empty, use a default name
    if not name:
        name = 'untitled'

    return name


class ActiveBookmarksPresetsAPI(QtCore.QObject):
    """API for managing bookmarks presets.

    Attributes:
        _presets (dict): Dictionary mapping preset_name to a list of bookmark dicts.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._presets = {}
        self._connect_signals()

    def _connect_signals(self):
        common.signals.activeBookmarksPresetsChanged.connect(lambda: self.get_presets(force=True))
        common.signals.bookmarksChanged.connect(lambda: self.get_presets(force=True))

    @classmethod
    def _verify_preset(cls, preset_data):
        """Verify that a preset dictionary is valid.

        Args:
            preset_data (dict): The preset data with 'name' (str) and 'data' (list of dicts).

        Raises:
            TypeError: If preset_data isn't a dict, or data isn't a list.
            ValueError: If required keys are missing or invalid.
        """
        if not isinstance(preset_data, dict):
            raise TypeError('Preset must be a dictionary')
        if 'name' not in preset_data or 'data' not in preset_data:
            raise ValueError('Preset must contain "name" and "data" keys')

        if not isinstance(preset_data['name'], str) or not preset_data['name'].strip():
            raise ValueError('Key "name" must be a non-empty string')

        data = preset_data['data']
        if not isinstance(data, list):
            raise TypeError('Key "data" must be a list')

        for item in data:
            if not isinstance(item, dict):
                raise TypeError('Each item in "data" must be a dictionary')
            for key in ('server', 'job', 'root'):
                if key not in item:
                    raise ValueError(f'Missing required key in data item: {key}')
                if not isinstance(item[key], str) or not item[key].strip():
                    raise ValueError(f'Key {key} in data item must be a non-empty string')

    def exists(self, preset_name):
        """Check if a preset exists.

        Args:
            preset_name (str): The preset name.

        Returns:
            bool: True if exists, else False.
        """
        preset_name = sanitize_filename(preset_name)
        return preset_name in self._presets

    def _get_preset_by_name(self, preset_name):
        """Get a preset's data by name.

        Args:
            preset_name (str): The preset name.

        Returns:
            list: The preset's list of bookmark items, or None if not found.
        """
        preset_name = sanitize_filename(preset_name)
        return self._presets.get(preset_name)

    def get_paths_from_preset(self, preset_name):
        """Returns the paths saved in a preset.

        Args:
            preset_name (str): The preset name.

        Returns:
            list: A list of paths this preset contains.
        """
        data = self._get_preset_by_name(preset_name)
        if not data or not data:
            return []

        paths = []
        for item in data:
            paths.append(f"{item['server'].rstrip('/')}/{item['job'].strip('/')}/{item['root'].strip('/')}")

        paths = sorted(set(paths))
        return paths

    def get_presets(self, force=False):
        """Return the list of presets.

        Args:
            force (bool): If True, reload from disk.

        Returns:
            dict: A dict mapping preset_name to its data (list of items).

        """
        if not force and self._presets:
            return self._presets

        self._presets.clear()
        self._presets = {}

        _dir = get_presets_dir()
        if not os.path.exists(_dir):
            log.warning(__name__, f'Presets directory not found: {_dir}')
            return {}

        for fname in os.listdir(_dir):
            if not fname.endswith('.json'):
                log.warning(__name__, f'Skipping non-json file: {fname}')
                continue

            path = os.path.join(_dir, fname)
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                self._verify_preset(data)
                preset_name = sanitize_filename(data['name'])
                self._presets[preset_name] = data['data']
            except (ValueError, TypeError) as e:
                log.error(__name__, f'Invalid preset in {fname}: {e}')
            except Exception as e:
                log.error(__name__, f'Error loading preset from {path}: {e}')

        return self._presets.copy()

    def import_preset(self, preset_name, source_file, force=False):
        """Import a preset from a file.

        Args:
            preset_name (str): The desired preset name.
            source_file (str): Path to the source json file.
            force (bool): If True, overwrite existing preset.

        Raises:
            FileNotFoundError: If source_file does not exist.
            ValueError/TypeError: If the imported preset is invalid.
            FileExistsError: If preset exists and force=False.
        """
        preset_name = sanitize_filename(preset_name)
        if not os.path.exists(source_file):
            raise FileNotFoundError(f'Source file {source_file} does not exist')

        if self.exists(preset_name) and not force:
            raise FileExistsError(f'Preset {preset_name} already exists')

        with open(source_file, 'r') as f:
            data = json.load(f)
        self._verify_preset(data)
        data['name'] = preset_name

        self._save_preset_data(preset_name, data, force)

    def export_preset(self, preset_name, destination_file):
        """Export a preset to a file.

        Args:
            preset_name (str): The preset name.
            destination_file (str): Path to the destination json file.

        Raises:
            FileNotFoundError: If the preset does not exist.
        """
        preset_name = sanitize_filename(preset_name)
        preset_data = self._get_preset_by_name(preset_name)
        if not preset_data:
            raise FileNotFoundError(f'Preset {preset_name} not found')
        out_data = {
            'name': preset_name,
            'data': preset_data
        }
        self._verify_preset(out_data)
        with open(destination_file, 'w') as f:
            json.dump(out_data, f, indent=4)

    def _save_preset_data(self, preset_name, data, force):
        """Save given preset data to disk and update internal structure.

        Args:
            preset_name (str): The preset name.
            data (dict): The full preset structure with 'name' and 'data'.
            force (bool): If True, overwrite existing preset.

        Raises:
            ValueError/TypeError: If data is invalid.
            FileExistsError: If preset exists and force=False.

        """
        preset_name = sanitize_filename(preset_name)
        self._verify_preset(data)
        if data['name'] != preset_name:
            data['name'] = preset_name
        _dir = get_presets_dir()
        if not os.path.exists(_dir):
            os.makedirs(_dir, exist_ok=True)
        path = os.path.join(_dir, f'{preset_name}.json')

        if os.path.exists(path) and not force:
            raise FileExistsError(f'Preset {preset_name} already exists')

        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        self._presets[preset_name] = data['data']

    def save_preset(self, preset_name, force=False):
        """Save a preset to disk by snapshotting the current bookmarks.

        Args:
            preset_name (str): The preset name.
            force (bool): If True, overwrite existing preset.

        Raises:
            ValueError/TypeError: If data is invalid.
        """
        preset_name = sanitize_filename(preset_name)
        bookmarks = ServerAPI.bookmarks(force=True)
        data_items = list(bookmarks.values())
        data = {
            'name': preset_name,
            'data': data_items
        }
        self._save_preset_data(preset_name, data, force)

        common.signals.activeBookmarksPresetsChanged.emit()

    def delete_preset(self, preset_name):
        """Delete a preset from disk.

        Args:
            preset_name (str): The preset name.
        """
        preset_name = sanitize_filename(preset_name)
        if preset_name not in self._presets:
            log.warning(__name__, f'Preset {preset_name} not found')
            return
        _dir = get_presets_dir()
        path = os.path.join(_dir, f'{preset_name}.json')
        if os.path.exists(path):
            os.remove(path)
        del self._presets[preset_name]

        common.signals.activeBookmarksPresetsChanged.emit()

    def activate_preset(self, preset_name):
        """Set the contents of the preset as the current bookmark selection.

        Args:
            preset_name (str): The preset name.

        Raises:
            FileNotFoundError: If the preset does not exist.
        """
        preset_name = sanitize_filename(preset_name)
        preset_data = self._get_preset_by_name(preset_name)
        if not preset_data:
            raise FileNotFoundError(f'Preset {preset_name} not found')

        # Convert this data back into bookmarks and save them
        # The keys in common.bookmarks are 'server/job/root'
        bookmarks = {}
        for item in preset_data:
            key = ServerAPI.bookmark_key(item)
            bookmarks[key] = {
                'server': item['server'],
                'job': item['job'],
                'root': item['root']
            }

        lib.ServerAPI.save_bookmarks(bookmarks)

        # Verify the current active items against the new preset values
        # Set the first bookmark as active, if any
        if not preset_data:
            return

        if not common.active('root'):
            # We can bail early if there's no active root
            return

        paths = list(bookmarks.keys())
        active_path = common.active('root', path=True)
        if active_path not in paths:
            log.warning(__name__, f'Active path {active_path} not in preset paths')
            common.set_active('root', None)
            common.set_active('job', None)
            common.set_active('server', None)

    def clear_presets(self):
        """Delete all presets from disk."""
        _dir = get_presets_dir()
        if os.path.exists(_dir):
            for fname in os.listdir(_dir):
                if fname.endswith('.json'):
                    os.remove(os.path.join(_dir, fname))
        self._presets.clear()

    def is_valid(self, preset_name):
        """Check if a preset is valid.

        Args:
            preset_name (str): The preset name.

        Returns:
            bool: True if valid, False otherwise.
        """
        preset_name = sanitize_filename(preset_name)
        preset_data = self._get_preset_by_name(preset_name)
        if not preset_data:
            return False
        try:
            data = {
                'name': preset_name,
                'data': preset_data
            }
            self._verify_preset(data)
            return True
        except (ValueError, TypeError):
            return False

    def rename_preset(self, old_name, new_name, force=False):
        """Rename a preset.

        Args:
            old_name (str): The old preset name.
            new_name (str): The new preset name.
            force (bool): If True, overwrite existing preset with new_name if it exists.

        Raises:
            FileNotFoundError: If the old preset is not found.
            FileExistsError: If the new_name preset exists and force=False.
        """
        old_name = sanitize_filename(old_name)
        new_name = sanitize_filename(new_name)

        if old_name not in self._presets:
            raise FileNotFoundError(f'Preset {old_name} not found')

        if self.exists(new_name) and not force:
            raise FileExistsError(f'Preset {new_name} already exists')

        _dir = get_presets_dir()
        old_path = os.path.join(_dir, f'{old_name}.json')
        new_path = os.path.join(_dir, f'{new_name}.json')
        if os.path.exists(old_path):
            if os.path.exists(new_path) and force:
                os.remove(new_path)
            os.rename(old_path, new_path)
        # Update in-memory
        self._presets[new_name] = self._presets[old_name]
        del self._presets[old_name]

        data = {
            'name': new_name,
            'data': self._presets[new_name]
        }
        self._verify_preset(data)
        with open(new_path, 'w') as f:
            json.dump(data, f, indent=4)

        common.signals.activeBookmarksPresetsChanged.emit()
