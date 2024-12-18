"""This module implements a simple API for managing active bookmarks presets.

Each preset is saved as a single JSON file with the following structure:

.. code-block:: json

    {
        "name": "PresetName",
        "server": "//my-server.local/jobs",
        "job": "my-client/my-job",
        "root": "data/shots"
    }

Internally, the presets are stored as a dictionary of the form:

.. code-block:: python

    self._presets = {
        "PresetName": {
            "server": "//my-server.local/jobs",
            "job": "my-client/my-job",
            "root": "data/shots"
        }
    }

See also:
    :class:`.ServerAPI`

"""
import os
import json
import re

from .. import common
from .. import log
from . import lib

PRESETS_DIR = f'{common.temp_path()}/bookmark_presets'
api = None


def _init_active_bookmark_presets():
    if not os.path.exists(PRESETS_DIR):
        os.makedirs(PRESETS_DIR)
        log.debug(__name__, f'Created directory: {PRESETS_DIR}')

    global api
    if api is None:
        api = ActiveBookmarksPresetsAPI()

    if not isinstance(api, ActiveBookmarksPresetsAPI):
        raise TypeError('API must be an instance of ActiveBookmarksPresetsAPI')

    return api


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


class ActiveBookmarksPresetsAPI:
    """API for managing bookmarks presets.

    Attributes:
        _presets (dict): Dictionary mapping preset_name to a dict with keys:
            'server', 'job', 'root'.
    """

    def __init__(self):
        self._presets = {}

    @classmethod
    def _verify_preset(cls, preset_data):
        """Verify that a preset dictionary is valid.

        Args:
            preset_data (dict): The preset data.

        Raises:
            TypeError: If preset_data is not a dict.
            ValueError: If the preset data is missing required keys or has invalid values.
        """
        if not isinstance(preset_data, dict):
            raise TypeError('Preset must be a dictionary')
        for key in ('name', 'server', 'job', 'root'):
            if key not in preset_data:
                raise ValueError(f'Missing required key: {key}')
            if not isinstance(preset_data[key], str) or not preset_data[key].strip():
                raise ValueError(f'Key {key} must be a non-empty string')

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
            dict: The preset dictionary { 'server': ..., 'job': ..., 'root': ... } or None.
        """
        preset_name = sanitize_filename(preset_name)
        return self._presets.get(preset_name)

    def preset_to_path(self, preset_name):
        """Returns the bookmark's key (path) value for a given preset name.

        Args:
            preset_name (str): The preset name.

        Returns:
            str: 'server/job/root' or empty string if not found.
        """
        preset = self._get_preset_by_name(preset_name)
        if not preset:
            return ''
        return f"{preset['server'].rstrip('/')}/{preset['job'].strip('/')}/{preset['root'].strip('/')}"

    def get_presets(self, force=False):
        """Return the list of presets.

        Args:
            force (bool): If True, reload from disk.

        Returns:
            dict: A dict mapping preset_name to its data.
        """
        if not force and self._presets:
            return self._presets

        self._presets.clear()
        if os.path.exists(PRESETS_DIR):
            for fname in os.listdir(PRESETS_DIR):
                if fname.endswith('.json'):
                    path = os.path.join(PRESETS_DIR, fname)
                    try:
                        with open(path, 'r') as f:
                            data = json.load(f)
                        self._verify_preset(data)
                        preset_name = sanitize_filename(data['name'])
                        self._presets[preset_name] = {
                            'server': data['server'],
                            'job': data['job'],
                            'root': data['root']
                        }
                    except (ValueError, TypeError) as e:
                        log.error(__name__, f'Invalid preset in {fname}: {e}')
                    except Exception as e:
                        log.error(__name__, f'Error loading preset from {path}: {e}')
        return self._presets

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
        self.save_preset(preset_name, data)

    def export_preset(self, preset_name, destination_file):
        """Export a preset to a file.

        Args:
            preset_name (str): The preset name.
            destination_file (str): Path to the destination json file.

        Raises:
            FileNotFoundError: If the preset does not exist.
        """
        preset_name = sanitize_filename(preset_name)
        preset = self._get_preset_by_name(preset_name)
        if not preset:
            raise FileNotFoundError(f'Preset {preset_name} not found')
        data = {
            'name': preset_name,
            'server': preset['server'],
            'job': preset['job'],
            'root': preset['root']
        }
        with open(destination_file, 'w') as f:
            json.dump(data, f, indent=4)

    def save_preset(self, preset_name, data):
        """Save a preset to disk.

        Args:
            preset_name (str): The preset name.
            data (dict): A dict with keys 'name', 'server', 'job', 'root'.

        Raises:
            ValueError/TypeError: If data is invalid.
        """
        preset_name = sanitize_filename(preset_name)
        self._verify_preset(data)
        if data['name'] != preset_name:
            data['name'] = preset_name
        if not os.path.exists(PRESETS_DIR):
            os.makedirs(PRESETS_DIR)
        path = os.path.join(PRESETS_DIR, f'{preset_name}.json')
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        self._presets[preset_name] = {
            'server': data['server'],
            'job': data['job'],
            'root': data['root']
        }

    def delete_preset(self, preset_name):
        """Delete a preset from disk.

        Args:
            preset_name (str): The preset name.
        """
        preset_name = sanitize_filename(preset_name)
        if preset_name not in self._presets:
            return
        path = os.path.join(PRESETS_DIR, f'{preset_name}.json')
        if os.path.exists(path):
            os.remove(path)
        del self._presets[preset_name]

    def activate_preset(self, preset_name):
        """Set the contents of the preset as the current active bookmarks.

        Args:
            preset_name (str): The preset name.

        Raises:
            FileNotFoundError: If the preset does not exist.
        """
        preset_name = sanitize_filename(preset_name)
        preset = self._get_preset_by_name(preset_name)
        if not preset:
            raise FileNotFoundError(f'Preset {preset_name} not found')
        bookmarks = {}
        key = f"{preset['server'].rstrip('/')}/{preset['job'].strip('/')}/{preset['root'].strip('/')}"
        bookmarks[key] = {
            'server': preset['server'],
            'job': preset['job'],
            'root': preset['root']
        }
        lib.ServerAPI.clear_bookmarks()
        lib.ServerAPI.save_bookmarks(bookmarks)
        common.set_active('server', preset['server'])
        common.set_active('job', preset['job'])
        common.set_active('root', preset['root'])

    def clear_presets(self):
        """Delete all presets from disk."""
        if os.path.exists(PRESETS_DIR):
            for fname in os.listdir(PRESETS_DIR):
                if fname.endswith('.json'):
                    os.remove(os.path.join(PRESETS_DIR, fname))
        self._presets.clear()

    def is_valid(self, preset_name):
        """Check if a preset is valid.

        Args:
            preset_name (str): The preset name.

        Returns:
            bool: True if valid, False otherwise.
        """
        preset_name = sanitize_filename(preset_name)
        preset = self._get_preset_by_name(preset_name)
        if not preset:
            return False
        try:
            data = {
                'name': preset_name,
                'server': preset['server'],
                'job': preset['job'],
                'root': preset['root']
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

        old_path = os.path.join(PRESETS_DIR, f'{old_name}.json')
        new_path = os.path.join(PRESETS_DIR, f'{new_name}.json')
        if os.path.exists(old_path):
            if os.path.exists(new_path) and force:
                os.remove(new_path)
            os.rename(old_path, new_path)
        # Update in-memory
        self._presets[new_name] = self._presets[old_name]
        del self._presets[old_name]

        data = {
            'name': new_name,
            'server': self._presets[new_name]['server'],
            'job': self._presets[new_name]['job'],
            'root': self._presets[new_name]['root']
        }
        with open(new_path, 'w') as f:
            json.dump(data, f, indent=4)
