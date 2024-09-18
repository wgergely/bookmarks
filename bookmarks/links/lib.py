import os


class Links:
    """
    A class to manage links in a .links file.

    Attributes:
        path (str): The directory containing the .links file.
        links_file (str): The full path to the .links file.
        _cache (list): An in-memory cache of the links.
    """

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

    def _normalize_link(self, link):
        """
        Normalize a link to ensure consistent format.

        Args:
            link (str): The link to normalize.

        Returns:
            str: The normalized link.
        """
        return os.path.normpath(link).replace('\\', '/')

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
            ValueError: If the provided path is not under the base path.
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
            links = self._cache
        else:
            links = self._read_links_from_file()
            self._cache = links

        if absolute:
            return [self.to_absolute(link) for link in links]
        else:
            return links

    def add(self, link, force=False):
        """
        Add a link to the .links file.

        Args:
            link (str): Relative or absolute path to add to the .links file.
            force (bool): If True, skip the existence check for the link's path.

        Returns:
            bool: True if the link was added, False if it already exists.
        """
        if os.path.isabs(link):
            link = self.to_relative(link)

        link = self._normalize_link(link)
        full_link_path = self.to_absolute(link)
        if not force and not os.path.exists(full_link_path):
            raise RuntimeError(f'Link "{full_link_path}" does not exist')

        links = self.get()
        if link not in links:
            links.append(link)
            self._cache = sorted(set(links))
            self._write_links_to_file(self._cache)
            return True
        else:
            return False

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
        links = self.get()
        if link in links:
            links.remove(link)
            self._cache = sorted(set(links))
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
        links = self.get()
        valid_links = []
        for link in links:
            full_link_path = self.to_absolute(link)
            if os.path.exists(full_link_path):
                valid_links.append(link)

        valid_links = sorted(set(valid_links))
        self._write_links_to_file(valid_links)
        self._cache = valid_links
        return sorted(set(links) - set(valid_links))

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
            return sorted(set(links))
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
                for link in sorted(set(links)):
                    f.write(f'{link}\n')
        except IOError as e:
            raise RuntimeError(f'Failed to write to {self.links_file}: {e}')
