import os
import re

from .. import common
from .. import database


class LinksAPI:
    """
    A class to manage interface with `.links` files.

    Attributes:
        path (str): The directory containing the .links file.
        links_file (str): The full path to the .links file.

    """

    #: Cache to store api instances
    _instances = {}

    def __new__(cls, path, *args, **kwargs):
        if not path or not isinstance(path, str):
            raise RuntimeError('Path cannot be empty')

        if path in cls._instances:
            return cls._instances[path]

        cls._instances[path] = super(LinksAPI, cls).__new__(cls)
        return cls._instances[path]

    def __init__(self, path):
        """
        Initialize the Links object.

        Args:
            path (str): Path to the folder where the .links file resides.

        """
        if not os.path.exists(path):
            raise RuntimeError(f'Path "{path}" does not exist')

        self.path = path.replace('\\', '/')
        self.links_file = os.path.join(self.path, '.links').replace('\\', '/')
        self._cache = None

    @classmethod
    def update_cached_data(cls):
        """
        Update all current instances' cached data from disk.

        """
        for k in cls._instances.keys():
            cls._instances[k].get(force=True)

    @classmethod
    def clear_cache(cls):
        """
        Clear the cache of instances.

        """
        for key in list(cls._instances.keys()):
            del cls._instances[key]
        cls._instances = {}

    @staticmethod
    def _normalize_link(link):
        """
        Normalize path.

        Args:
            link (str): The link to normalize.

        Returns:
            str: The normalized link.

        """
        link = os.path.normpath(link)
        link = link.replace('\\', '/')
        link = link.strip('/')
        link = re.sub(r'[/]+', '/', link)  # Remove multiple slashes
        return link

    @classmethod
    def verify_link(cls, link):
        """Check the characters of the given link against forbidden characters.

        """
        if not link:
            raise ValueError('Link cannot be empty')
        if not isinstance(link, str):
            raise ValueError('Link must be a string')

        link = cls._normalize_link(link)

        invalid_chars = {' ', '.', '-', '_'}
        if link[-1] in invalid_chars:
            raise ValueError(f'"{link}" cannot end with these characters: {", ".join(invalid_chars)}')
        if link[0] in invalid_chars:
            raise ValueError(f'"{link}" cannot start with these characters: {", ".join(invalid_chars)}')

        forbidden_chars = {':', '*', '?', '"', '<', '>', '|'}
        if any(char in link for char in forbidden_chars):
            raise ValueError(f'"{link}" contains forbidden characters: {", ".join(forbidden_chars)}')

        reserved_names = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
                          'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4',
                          'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}

        for folder_name in link.split('/'):
            if folder_name.upper() in reserved_names:
                raise ValueError(f'"{folder_name}" contains a reserved name ({" ,".join(reserved_names)})')

        return True

    def _read_links_from_file(self):
        """
        Internal method to read links from the .links file.

        Returns:
            list: A list of links read from the file.
        """
        if not os.path.exists(self.links_file):
            return []
        try:
            with open(self.links_file, 'r') as f:
                lines = f.readlines()
            links = [self._normalize_link(line.strip()) for line in lines if line.strip()]
            return sorted(set(links), key=str.lower)
        except IOError as e:
            raise RuntimeError(f'Failed to read from {self.links_file}: {e}')

    def _write_links_to_file(self, links):
        """
        Internal method to write links to the .links file.

        Args:
            links (list): The list of links to write to the file.
        """
        try:
            with open(self.links_file, 'w') as f:
                for link in sorted(set(links), key=str.lower):
                    f.write(f'{link}\n')
        except IOError as e:
            raise RuntimeError(f'Failed to write to {self.links_file}: {e}')

    def to_absolute(self, link):
        """
        Convert a relative link to an absolute path.

        Args:
            link (str): The relative link.

        Returns:
            str: The absolute path.
        """
        link = self._normalize_link(link)
        return os.path.abspath(os.path.join(self.path, link)).replace('\\', '/')

    def to_relative(self, path):
        """
        Convert an absolute path to a relative link with respect to the base path.

        Args:
            path (str): The absolute path.

        Returns:
            str: The relative link.

        Raises:
            ValueError: If the provided path isn't under the base path.
        """
        path = os.path.abspath(path).replace('\\', '/')
        base_path = os.path.abspath(self.path).replace('\\', '/')
        if not path.startswith(base_path):
            raise ValueError(f'Path "{path}" is not under base path "{base_path}"')
        relative_link = os.path.relpath(path, self.path).replace('\\', '/')
        return self._normalize_link(relative_link)

    def get(self, force=False, absolute=False):
        """
        Return a list of links from the .links file.

        Args:
            force (bool): If True, force reading from disk even if cache exists.
            absolute (bool): If True, return absolute paths instead of relative links.

        Returns:
            list: A list of file paths.
        """
        if self._cache is not None and not force:
            return self._cache

        links = []
        if self._cache is None:
            links = self._read_links_from_file()

        _links = []
        for l in links:
            l = self._normalize_link(l)
            if absolute:
                l = self.to_absolute(l)

            try:
                self.verify_link(l)
            except:
                continue

            _links.append(l)

        v = sorted(_links, key=str.lower)
        self._cache = v

        return v

    def add(self, link, force=False):
        """
        Add a link to the .links file.

        Args:
            link (str): Relative or absolute path to add to the .links file.
            force (bool): If True, skip the existence check for the link's path.

        Returns:
            bool: True if the link was added, False if it already exists.
        """
        link = self._normalize_link(link)
        self.verify_link(link)

        if os.path.isabs(link):
            link = self.to_relative(link)

        link = self._normalize_link(link)
        self.verify_link(link)

        full_link_path = self.to_absolute(link)
        if not force and not os.path.exists(full_link_path):
            raise RuntimeError(f'Link "{full_link_path}" does not exist')

        links = self.get(force=True)

        if link in links:
            raise RuntimeError(f'Link "{link}" already exists')

        links.append(link)
        self._write_links_to_file(sorted(set(links), key=str.lower))
        self.get(force=True)

    def remove(self, link):
        """
        Remove a link from the .links file.

        Args:
            link (str): Relative or absolute path to remove from the .links file.

        Returns:
            bool: True if the link was removed, False if it wasn't found.
        """
        if os.path.isabs(link):
            link = self.to_relative(link)

        link = self._normalize_link(link)
        links = self.get(force=True)
        if link in links:
            links.remove(link)
            self._cache = sorted(set(links), key=str.lower)
            self._write_links_to_file(self._cache)
            return True
        else:
            return False

    def clear(self):
        """
        Clear all links from the .links file.

        Returns:
            bool: True after clearing the links.
        """
        self._cache = []
        self._write_links_to_file(self._cache)
        return True

    def prune(self):
        """
        Remove links from the .links file that don't exist on the disk.

        Returns:
            int: The number of links removed.
        """
        links = self.get(force=True)
        valid_links = []
        for link in links:
            full_link_path = self.to_absolute(link)
            if os.path.exists(full_link_path):
                valid_links.append(link)

        valid_links = sorted(set(valid_links), key=str.lower)
        self._write_links_to_file(valid_links)
        self._cache = valid_links
        return sorted(set(links) - set(valid_links))

    @staticmethod
    def presets():
        """
        Get the list of presets from the active bookmark item's database.

        Returns:
            dict: A dictionary of presets.

        """
        args = common.active('root', args=True)
        if not args:
            raise RuntimeError('Getting presets requires a root item to be active')

        db = database.get(*args)
        v = db.value(db.source(), 'asset_link_presets', database.BookmarkTable)

        if not v:
            return {}

        return {k: v[k] for k in sorted(v.keys(), key=str.lower)}

    @staticmethod
    def clear_preset(preset):
        """Clear a preset from the active bookmark item's database."""
        args = common.active('root', args=True)
        if not args:
            raise RuntimeError('Clearing a preset requires a root item to be active')

        if not preset or not isinstance(preset, str):
            raise RuntimeError('Preset name cannot be empty')

        db = database.get(*args)
        v = db.value(db.source(), 'asset_link_presets', database.BookmarkTable)

        if not v or preset not in v:
            raise RuntimeError(f'Preset "{preset}" does not exist')

        del v[preset]
        db.set_value(db.source(), 'asset_link_presets', v, database.BookmarkTable)

        # Verify
        v = db.value(db.source(), 'asset_link_presets', database.BookmarkTable)
        if preset in v:
            raise RuntimeError(f'Failed to remove preset "{preset}"')

    @staticmethod
    def clear_presets():
        """
        Clear all presets from the active bookmark item's database.

        """
        args = common.active('root', args=True)
        if not args:
            raise RuntimeError('Clearing presets requires a root item to be active')

        db = database.get(*args)
        db.set_value(db.source(), 'asset_link_presets', {}, database.BookmarkTable)

    @staticmethod
    def _save_data_to_database(name, data, force=True):
        """ Save a preset to the active bookmark item's database.

        Args:
            name (str): The name of the preset.
            data (list): The data to save.
            force (bool): If True, overwrite an existing preset with the same name.

        """
        if not data or not isinstance(data, (list, tuple)):
            raise RuntimeError('No links to save as a preset')

        args = common.active('root', args=True)
        if not args:
            raise RuntimeError('Saving a preset requires a root item to be active')

        if not name or not isinstance(name, str):
            raise RuntimeError('Preset name cannot be empty')

        db = database.get(*args)
        v = db.value(db.source(), 'asset_link_presets', database.BookmarkTable)
        v = v if v else {}

        if not force and name in v:
            raise RuntimeError(f'Preset "{name}" already exists')

        v[name] = data

        db.set_value(db.source(), 'asset_link_presets', v, database.BookmarkTable)

        # Verify
        v = db.value(db.source(), 'asset_link_presets', database.BookmarkTable)
        if name not in v:
            raise RuntimeError(f'Failed to save preset "{name}"')

    def save_preset_to_database(self, name, force=True):
        """
        Save the current links as a preset in the active bookmark item's database.

        Args:
            name (str): The name of the preset to save.
            force (bool): If True, overwrite an existing preset with the same name.

        """
        links = self.get(force=True)
        self._save_data_to_database(name, links, force=force)

    def apply_preset(self, preset):
        """
        Apply a preset to the current links.

        Args:
            preset (str): The name of the preset to apply.

        """
        if not preset or not isinstance(preset, str):
            raise RuntimeError('Preset name cannot be empty')

        presets = self.presets()
        if preset not in presets:
            raise RuntimeError(f'Preset "{preset}" does not exist')

        links = presets[preset]
        self.clear()
        for link in links:
            self.add(link, force=True)

    @staticmethod
    def remove_preset(name):
        """
        Remove a preset from the active bookmark item's database.

        Args:
            name (str): The name of the preset to remove.

        """
        args = common.active('root', args=True)
        if not args:
            raise RuntimeError('Removing a preset requires a root item to be active')

        if not name or not isinstance(name, str):
            raise RuntimeError('Preset name cannot be empty')

        db = database.get(*args)
        v = db.value(db.source(), 'asset_link_presets', database.BookmarkTable)
        v = v if v else {}

        if name not in v:
            raise RuntimeError(f'Preset "{name}" does not exist')

        del v[name]

        db.set_value(db.source(), 'asset_link_presets', v, database.BookmarkTable)

        # Verify
        v = db.value(db.source(), 'asset_link_presets', database.BookmarkTable)
        if name in v:
            raise RuntimeError(f'Failed to remove preset "{name}"')

    def copy_to_clipboard(self, links=None):
        """
        Copy the current links to the clipboard.

        """
        if links is None:
            v = self.get(force=True)
        elif links and isinstance(links, (list, tuple)):
            v = links
        else:
            v = []

        if not v:
            raise RuntimeError('No links to copy to the clipboard')

        common.set_clipboard(common.AssetLinksClipboard, v)

    def paste_from_clipboard(self):
        """
        Paste the links from the clipboard.

        Returns:
            list: A list of links that were skipped.

        """
        v = common.get_clipboard(common.AssetLinksClipboard)
        if not v:
            raise RuntimeError('Clipboard is empty')

        links = self.get(force=True)
        links = links if links else []

        skipped = []

        for link in v:
            if link in links:
                skipped.append(link)
                continue
            self.add(link, force=True)

        return skipped
