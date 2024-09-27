import datetime
import io
import json
import os
import re
import tempfile
import zipfile
from enum import Enum

import bookmarks_openimageio
from PySide2 import QtGui, QtCore

from .error import *
from .. import common
from .. import database
from .. import images
from .. import log
from ..links.lib import LinksAPI
from ..tokens import tokens


class TemplateType(Enum):
    DatabaseTemplate = 0
    UserTemplate = 1


template_blacklist = {
    'Thumbs.db',
    '.DS_Store',
    'desktop.ini',
    'Icon\r',
    '.Spotlight-V100',
    '.Trashes',
    '.fseventsd',
    '.TemporaryItems',
    '$RECYCLE.BIN',
    'System Volume Information',
    '.AppleDouble',
    '.AppleDB',
    '.AppleDesktop',
    '.DocumentRevisions-V100',
    '.Trash',
    'hiberfil.sys',
    'pagefile.sys',
    'swapfile.sys',
    'RECYCLER',
    'lost+found',
    '.VolumeIcon.icns',
    '.com.apple.timemachine.donotpresent',
    '.apdisk',
}

filename_char_blacklist = {
    '<',
    '>',
    ':',
    '"',
    '/',
    '\\',
    '|',
    '?',
    '*',
}


class TemplateItem(object):
    """Interface for template files.

    The template file is a zip file that contains a JSON file with metadata, a thumbnail.png
    and a zip archive with the actual template.

    Example:

        template.zip
        ├── metadata.json
        ├── thumbnail.png
        └── template.zip
            └── <custom files and folders>

    """

    #: Default extension for the template file
    default_extension = 'template'
    #: Default storage folder for user templates
    default_user_folder = (
        f'{QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.GenericDataLocation)}/'
        f'{common.product}/templates'
    )

    #: Metadata keys
    metadata_keys = (
        'name',
        'description',
        'author',
        'date',
    )

    #: Default compression method
    compression = zipfile.ZIP_STORED

    def __getitem__(self, key):
        return self.get_metadata(key)

    def __setitem__(self, key, value):
        self.set_metadata(key, value)

    def __repr__(self):
        return f'<TemplateItem: {self._metadata["name"]}>'

    def __init__(self, path=None, data=None):
        if all([path, data]):
            raise ValueError('Cannot provide both path and data')

        self._original_path = path

        self._path = None
        self._type = None
        self._template = None
        self._has_links = False
        self._has_error = False

        self._metadata = None
        self._qimage = None
        self._size = 0

        if not any([path, data]):
            self._type = TemplateType.DatabaseTemplate
            self.new_template_from_tokens()
            return

        if path and not data:
            self._type = TemplateType.UserTemplate
            self._path = os.path.normpath(path).replace('\\', '/')
        elif data:
            self._type = TemplateType.DatabaseTemplate

        if not self._type:
            raise ValueError('Type must be set')

        self._load_zip_file(path, data)

    def _load_zip_file(self, path, data):
        """Load the template zip file.

        Args:
            path (str): Path to the template file.
            data (bytes): Binary data of the template file.

        Raises:
            TemplateError: If the template file could not be read.
            TemplateMetadataError: If the metadata file is missing or invalid.

        """
        try:
            if path and not data:
                self._path = os.path.normpath(path).replace('\\', '/')
                self._size = os.path.getsize(path)
                zf = zipfile.ZipFile(path, 'r')
            elif data:
                zf = zipfile.ZipFile(io.BytesIO(data), 'r')
                self._size = common.get_py_obj_size(data)
            else:
                raise ValueError('Path or data must be provided')
        except:
            self._has_error = True
            raise TemplateError(f'Could not read template')

        with zf as z:
            nl = z.namelist()

            if 'metadata.json' not in nl:
                self._has_error = True
                raise TemplateError('metadata.json not found in zip file')
            if 'thumbnail.png' not in nl:
                self._has_error = True
                raise TemplateError('thumbnail.png not found in zip file')
            if 'template.zip' not in nl:
                self._has_error = True
                raise TemplateError('template.zip not found in zip file')

            try:
                with z.open('metadata.json') as m:
                    self._metadata = json.load(m)
                    for key in self.metadata_keys:
                        if key not in self._metadata:
                            self._has_error = True
                            raise TemplateMetadataError(f'Missing key in metadata.json: {key}')
            except (TemplateMetadataError, json.JSONDecodeError, zipfile.BadZipFile):
                self._metadata = {
                    'name': 'Unknown',
                    'description': '',
                    'author': '',
                    'date': '',
                }
                self._has_error = True
                log.error(f'Failed to load metadata.json in {self._path}')

            try:
                with z.open('thumbnail.png') as t:
                    data = t.read()
                    self._qimage = QtGui.QImage.fromData(data)
                    if self._qimage.isNull():
                        self._qimage = QtGui.QImage()
            except (ValueError, zipfile.BadZipFile, RuntimeError):
                self._qimage = QtGui.QImage()
                log.debug(f'Failed to load thumbnail.png in {self._path}')

            try:
                with z.open('template.zip') as t:
                    self._template = t.read()
                    with zipfile.ZipFile(io.BytesIO(self._template), 'r') as tz:
                        if '.links' in tz.namelist():
                            self._has_links = True
            except (zipfile.BadZipFile, RuntimeError) as e:
                log.error(f'Failed to read embedded template.zip: {e}')

                # Write empty template
                zp = io.BytesIO()
                with zipfile.ZipFile(zp, 'w') as _:
                    pass

                zp.seek(0)
                self._template = zp.getvalue()
                self._has_error = True

    @staticmethod
    def _default_qimage(binary=True):
        """Get the default thumbnail.

        Returns:
            QtGui.QImage: Default thumbnail.

        """
        _q_path = images.rsc_pixmap(
            'folder_sm',
            None,
            None,
            get_path=True
        )

        _qimage = QtGui.QImage(_q_path)
        if _qimage.isNull():
            raise RuntimeError('Failed to load the default thumbnail')

        if not binary:
            return _qimage

        _array = QtCore.QByteArray()
        _buffer = QtCore.QBuffer(_array)
        _buffer.open(QtCore.QIODevice.WriteOnly)
        _qimage.save(_buffer, 'PNG')
        _buffer.close()

        data = _buffer.data()

        if not data:
            raise RuntimeError('Failed to get binary data from the default thumbnail')

        return data

    def _update_data(self):
        """Update the template data."""
        if not self._qimage or self._qimage.isNull():
            self._qimage = self._default_qimage(binary=False)

        zp = io.BytesIO()

        with zipfile.ZipFile(zp, 'w', compression=self.compression) as z:
            json_data = json.dumps(self._metadata)
            z.writestr('metadata.json', json_data)
            z.writestr('thumbnail.png', self.get_thumbnail(binary=True))
            z.writestr('template.zip', self._template)

        # Reset the pointer to the beginning of the BytesIO object
        zp.seek(0)
        return zp.getvalue()

    def _save_to_database(self, force, data):
        if self.type != TemplateType.DatabaseTemplate:
            raise ValueError('Can\'t save a user template to the database')

        args = common.active('root', args=True)
        if not args:
            raise RuntimeError('A root item must be active to save the template to the database')

        db = database.get(*args)

        # Let's make sure the template name is unique
        _hashes = db.get_column('id', database.TemplateDataTable)
        _hash = common.get_hash(self._metadata['name'])

        if not force and _hash in _hashes:
            raise ValueError(f'Template already exists: {self._metadata["name"]}')

        db.set_value(
            self._metadata['name'],
            'data',
            data,
            database.TemplateDataTable
        )

    def _save_to_disk(self, force, data):
        if self.type != TemplateType.UserTemplate:
            raise ValueError('Can\'t save a database template to disk')

        if not os.path.exists(self.default_user_folder):
            os.makedirs(self.default_user_folder, exist_ok=True)

        sanitized_name = re.sub(
            fr'[{"".join(filename_char_blacklist)}]',
            '_', self._metadata['name']
        )
        current_name = self._metadata['name']
        self._metadata['name'] = sanitized_name

        if sanitized_name != current_name:
            self._update_data()

        p = f'{self.default_user_folder}/{sanitized_name}.{self.default_extension}'
        if os.path.exists(p) and not force:
            raise FileExistsError(f'Template already exists: {p}')

        with open(p, 'wb') as f:
            f.write(data)

        return p

    def _safe_extract(self, z, exclude_files=None):
        """
        Safely extract files from a zip archive into memory.

        Args:
            z (zipfile.ZipFile): The zip file object to extract from.
            exclude_files (set or None): Filenames to exclude from extraction.

        Returns:
            List[Tuple[str, bytes]]: A list of tuples containing sanitized filenames and
            their corresponding data.

        """
        if exclude_files is None:
            exclude_files = set()

        # Add template_blacklist to exclude_files
        exclude_files.update(template_blacklist)

        extracted_files = []

        for item in z.infolist():
            if item.filename in exclude_files:
                continue
            sanitized_filename = self._sanitize_filename(item.filename)
            if not sanitized_filename:
                continue

            # Read the file data into memory
            with z.open(item) as source:
                file_data = source.read()
                extracted_files.append((sanitized_filename, file_data))

        return extracted_files

    @staticmethod
    def _sanitize_filename(filename):
        """
        Sanitize a filename to prevent directory traversal attacks.

        Args:
            filename (str): The original filename from the zip archive.

        Returns:
            str or None: The sanitized filename, or None if it's unsafe.

        """
        is_dir = filename.endswith('/')
        filename = filename.lstrip('/\\').split(':')[-1]
        filename = os.path.normpath(filename).replace('\\', '/')
        if '..' in filename.split('/'):
            log.error(f'Skipping potentially unsafe file: {filename}')
            return None

        if is_dir:
            filename = f'{filename}/'

        return filename

    @property
    def path(self):
        """Path to the template file.

        Returns:
            str: Path to the template file.

        """
        return self._path

    @property
    def type(self):
        """Type of template.

        Returns:
            int: TemplateType.UserTemplate or TemplateType.DatabaseTemplate.

        """
        return self._type

    @type.setter
    def type(self, value):
        if value not in TemplateType:
            raise ValueError(f'Invalid template type: {value}, expected one of {TemplateType}')
        self._type = value

    @property
    def template(self):
        """Bytes of the template zip file."""
        return self._template

    @property
    def metadata(self):
        """Metadata.

        Returns:
            dict: Metadata.

        """
        return self._metadata

    @property
    def qimage(self):
        """Thumbnail image.

        Returns:
            QtGui.QImage: Thumbnail image.

        """
        return self._qimage

    @qimage.setter
    def qimage(self, value):
        if not isinstance(value, QtGui.QImage):
            raise ValueError(f'Invalid type: {value}, expected QtGui.QImage')
        self._qimage = value

    @property
    def size(self):
        """Size of the template file.

        Returns:
            int: Size of the template file.

        """
        return self._size

    @property
    def has_links(self):
        return self._has_links

    @property
    def has_error(self):
        """Whether the template has an error."""
        return self._has_error

    def set_metadata(self, key, value):
        """Set metadata key.

        Args:
            key (str): Metadata key.
            value (str): Metadata value.

        """
        if key not in self.metadata_keys:
            raise KeyError(f'Invalid metadata key: {key}, expected one of {self.metadata_keys}')
        self._metadata[key] = value

    def get_metadata(self, key):
        """Get metadata key.

        Args:
            key (str): Metadata key.

        Returns:
            str: Metadata value.

        """
        if key not in self.metadata_keys:
            raise KeyError(f'Invalid metadata key: {key}, expected one of {self.metadata_keys}')
        return self._metadata[key]

    def clear_metadata(self):
        """Clear metadata.

        """
        self._metadata = {
            'name': '',
            'description': '',
            'author': '',
            'date': '',
        }

    def set_thumbnail(self, source):
        """Set thumbnail image.

        Args:
            source (str): Path to an image.

        """
        if not os.path.exists(source):
            raise FileNotFoundError(f'File not found: {source}')

        destination = tempfile.NamedTemporaryFile(suffix='.png', delete=False).name
        try:
            error = bookmarks_openimageio.convert_image(
                source,
                destination,
                source_color_space='',
                target_color_space='sRGB',
                size=int(common.Size.Thumbnail(apply_scale=False))
            )
            if error == 1:
                raise RuntimeError('Failed to convert the thumbnail')

            qimage = QtGui.QImage(destination)
            os.remove(destination)

            if qimage.isNull():
                qimage = self._default_qimage(binary=False)

            self._qimage = qimage
        finally:
            if os.path.exists(destination):
                os.remove(destination)

    def get_thumbnail(self, binary=False):
        """Get thumbnail image.

        Args:
            binary (bool, Optional): Return binary data, defaults to False.

        Returns:
            QtGui.QImage or bytes: Thumbnail image.

        """
        if not binary:
            return self._qimage

        _array = QtCore.QByteArray()
        _buffer = QtCore.QBuffer(_array)
        _buffer.open(QtCore.QIODevice.WriteOnly)
        _buffer.seek(0)
        self._qimage.save(_buffer, 'PNG')
        _buffer.close()

        return bytes(_buffer.data())

    def clear_thumbnail(self):
        """Reset thumbnail to the default.

        """
        self._qimage = self._default_qimage(binary=False)

    def save(self, force=False):
        """Save the template.

        Args:
            force (bool, Optional): Override existing data if True, defaults to False.

        """
        if not self._metadata['name']:
            raise ValueError('Name must be set')

        data = self._update_data()

        if self.type == TemplateType.DatabaseTemplate:
            self._save_to_database(force, data)
        elif self.type == TemplateType.UserTemplate:
            self._save_to_disk(force, data)

    def delete(self):
        """Delete the template.

        If the template is a database template, the associate row will be removed from the database.
        If the template is a user template, the file will be removed from the disk.

        """
        if not self._metadata['name']:
            raise ValueError('Name must be set')

        if self.type == TemplateType.DatabaseTemplate:
            args = common.active('root', args=True)
            if not args:
                raise RuntimeError('A root item must be active to delete the template from the database')

            db = database.get(*args)
            _hashes = db.get_column('id', database.TemplateDataTable)
            _hash = common.get_hash(self._metadata['name'])

            if _hash not in _hashes:
                raise ValueError(f'Template not found: {self._metadata["name"]}')

            db.delete_row(self._metadata['name'], database.TemplateDataTable)
            return

        if self.type == TemplateType.UserTemplate:
            p = f'{self.default_user_folder}/{self._metadata["name"]}.{self.default_extension}'

            if not os.path.exists(p):
                raise FileNotFoundError(f'Template not found: {p}')

            os.remove(p)

    def rename(self, name):
        """Rename the template.

        Args:
            name (str): New name.

        """
        if not name:
            raise ValueError('Name must be set')

        current_name = self._metadata['name']

        if self.type == TemplateType.DatabaseTemplate:
            args = common.active('root', args=True)
            if not args:
                raise RuntimeError('A root item must be active to rename the template in the database')

            db = database.get(*args)
            _hashes = db.get_column('id', database.TemplateDataTable)
            _hash = common.get_hash(name)

            if _hash in _hashes:
                raise ValueError(f'Template already exists: {name}')

            self._metadata['name'] = name
            data = self._update_data()
            self._save_to_database(True, data)

            # Delete old db row
            db.delete_row(current_name, database.TemplateDataTable)
            return

        if self.type == TemplateType.UserTemplate:
            self._metadata['name'] = name
            data = self._update_data()
            self._save_to_disk(True, data)

            # Delete old file
            p = f'{self.default_user_folder}/{current_name}.{self.default_extension}'
            if not os.path.exists(p):
                raise FileNotFoundError(f'Template not found: {p}')
            os.remove(p)

    def contains_file(self, rel_path):
        """Check if the template contains a file.

        Args:
            rel_path (str): Relative path to the file.

        Returns:
            bool: True if the file exists in the template.

        """
        if not self._template:
            return False

        zp = io.BytesIO(self._template)
        with zipfile.ZipFile(zp, 'r') as z:
            return rel_path in z.namelist()

    def set_link_preset(self, preset, force=False):
        """Add a .links file to the template.

        Args:
            preset (str): Name of the preset.

        """
        presets = LinksAPI.presets()
        if preset not in presets:
            raise ValueError(f'Invalid preset: {preset}')

        v = presets[preset]
        if not v:
            raise ValueError(f'Invalid preset: {preset}')

        if not self._template:
            raise ValueError('Template is empty')

        # Make sure the .links file doesn't already exist and/or that it is unique
        if not force and self.contains_file('.links'):
            raise TemplateLinkExistsError('Template already contains a .links file!')
        if force and self.contains_file('.links'):
            self.remove_link_preset()

        if isinstance(v, (list, tuple)):
            v = '\n'.join(v)

        # add a .links file to the root of self._template
        try:
            zp = io.BytesIO(self._template)

            with zipfile.ZipFile(zp, 'a', compression=self.compression) as z:
                nl = z.namelist()
                if '.links' in nl:
                    raise TemplateLinkExistsError('Template already contains a .links file!')
                z.writestr('.links', v)

            zp.seek(0)
            self._template = zp.getvalue()
            self._has_links = True

        except zipfile.BadZipFile:
            self._has_links = False
            raise

    def remove_link_preset(self):
        """Remove the .links file from the template."""
        if not self._has_links:
            return

        old_zp = io.BytesIO(self._template)
        new_zp = io.BytesIO()

        with zipfile.ZipFile(old_zp, 'r') as old_zip, \
                zipfile.ZipFile(new_zp, 'w', compression=self.compression) as new_zip:

            # Safely extract files into memory, excluding '.links'
            extracted_files = self._safe_extract(old_zip, exclude_files={'.links'})

            # Write the sanitized files into the new zip archive
            for filename, data in extracted_files:
                new_zip.writestr(filename, data)

        new_zp.seek(0)
        self._template = new_zp.getvalue()
        self._has_links = False

    def get_links(self):
        try:
            zp = io.BytesIO(self._template)
            with zipfile.ZipFile(zp, 'r') as zf:
                with zf.open('.links') as f:
                    v = f.read()
            return v.decode('utf-8').strip().splitlines()
        except (zipfile.BadZipFile, KeyError) as e:
            log.error(f'Failed to read .links file: {e}')
            link_paths = []

        return link_paths

    def extract_template(self, destination_path, extract_contents_to_links=True):
        """
        Extracts the template to the specified destination directory.

        By default, if present, the .links file is placed in the root of the destination directory.
        However, if `extract_contents_to_links=True`, the contents of the template will be extracted into
        each subfolder specified in the .links file, leaving the root of the destination directory empty.

        Args:
            destination_path (str): The path where the template should be extracted.
            extract_contents_to_links (bool): Whether to extract the contents
                to the links specified in the .links file.

        """
        if not os.path.exists(destination_path):
            parent_dir = os.path.dirname(destination_path)
            if not os.path.exists(parent_dir):
                raise FileNotFoundError(f'Parent directory does not exist: {parent_dir}')

        if not self._template:
            raise ValueError('Template is empty')

        if self._has_error:
            raise TemplateError('Template has errors')

        _paths = []

        if not self._has_links and extract_contents_to_links:
            raise TemplateError('Cannot extract contents to links without a .links file!')
        elif extract_contents_to_links:
            links = self.get_links()
            if not links:
                raise TemplateError('Empty .links file!')

            for link in links:
                p = os.path.join(destination_path, link)
                p = os.path.normpath(p).replace('\\', '/')
                _paths.append(p)
        else:
            _paths.append(destination_path)

        zp = io.BytesIO(self._template)
        with zipfile.ZipFile(zp, 'r') as zf:
            extracted_files = self._safe_extract(zf)

        for root_dir in _paths:
            for rel_path, data in extracted_files:

                # Make folders
                is_dir = rel_path.endswith('/')
                if is_dir:
                    p = os.path.join(root_dir, rel_path.rstrip('/'))
                    p = os.path.normpath(p).replace('\\', '/')
                    if not os.path.exists(p):
                        os.makedirs(p, exist_ok=True)
                    continue

                if '.links' in rel_path:
                    if not os.path.exists(f'{root_dir}/.links'):
                        with open(f'{root_dir}/.links', 'wb') as f:
                            f.write(data)
                    continue

                # Write files
                p = os.path.join(root_dir, rel_path)
                p = os.path.normpath(p).replace('\\', '/')

                parent_dir = os.path.dirname(p)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)

                with open(p, 'wb') as f:
                    f.write(data)


    def folder_to_template(self, source_folder, skip_system_files=True, max_size_mb=100):
        """Adds a folder and its contents to the template replacing the current template.

        Args:
            source_folder (str): Path to the folder to be zipped.
            skip_system_files (bool): Whether to skip system files.
            max_size_mb (int): Maximum allowed size in megabytes.

        Returns:
            tuple: Lists of files and folders added to the template.

        Raises:
            TemplateSizeError: If the total size exceeds the maximum allowed size.

        """
        if not os.path.isdir(source_folder):
            raise NotADirectoryError(f'The source must be a directory: {source_folder}')

        if not os.access(source_folder, os.R_OK):
            raise PermissionError(f'No read access to the folder: {source_folder}')

        source_folder = os.path.normpath(source_folder).replace('\\', '/')

        max_size_bytes = max_size_mb * 1024 * 1024
        total_size = 0

        blacklist = {f.lower() for f in template_blacklist}

        files = []
        folders = []
        skipped = []

        zp = io.BytesIO()
        with zipfile.ZipFile(zp, 'w', compression=self.compression) as zf:

            def _it(path, _total_size, _files, _folders, _skipped):

                if not os.access(path, os.R_OK):
                    log.error(f'No read access to the folder: {path}')
                    return

                for entry in os.scandir(path):
                    if entry.is_symlink():
                        continue

                    p = entry.path.replace('\\', '/').rstrip('/')
                    rp = p[len(source_folder) + 1:]

                    if skip_system_files and entry.name.lower() in blacklist:
                        log.debug(f'Skipping system file: {p}')
                        _skipped.append(entry.path)
                        continue

                    if entry.is_file():
                        file_size = os.path.getsize(p)
                        if _total_size + file_size > max_size_bytes:
                            raise TemplateSizeError(
                                f'Template size exceeds the maximum allowed size of {max_size_mb} MB.')
                        _total_size += file_size

                        if rp == '.links':
                            self._has_links = True

                        _files.append(rp)
                        zf.write(p, rp)
                    elif entry.is_dir():
                        rp = f'{rp}/'
                        _folders.append(rp)
                        zf.writestr(rp, '')
                        _it(p, _total_size, _files, _folders, _skipped)

            _it(source_folder, total_size, files, folders, skipped)

        zp.seek(0)
        self._template = zp.getvalue()
        print(f'Files: {files}')
        print(f'Folders: {folders}')
        return files, folders


    def new_template_from_tokens(self):
        """Create a default template based on the current token config.

        Returns:
            str or bytes: Path to the template file or binary data.

        """

        self.clear_metadata()
        self._metadata['name'] = '!Default Template!'
        self._metadata['description'] = 'The default template generated based on the current asset folder settings.'
        self._metadata['author'] = common.get_username()
        self._metadata['date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        p = images.rsc_pixmap('icon_bw_sm', None, None, get_path=True)
        self.set_thumbnail(p)

        config = tokens.get(*common.active('root', args=True))
        if not config:
            raise RuntimeError('A root item must be active to get the default template!')

        # Populate template with the default token config
        zp = io.BytesIO()
        with zipfile.ZipFile(zp, 'w', compression=self.compression) as zf:
            for v in config.data(force=True)[tokens.AssetFolderConfig].values():
                p = f'{v["value"]}/'
                if p not in zf.namelist():
                    zf.writestr(p, '')

                if 'subfolders' not in v:
                    continue

                for _v in v['subfolders'].values():
                    p = f'{v["value"]}/{_v["value"]}/'
                    if p not in zf.namelist():
                        zf.writestr(p, '')

        zp.seek(0)
        self._template = zp.getvalue()


    @classmethod
    def get_saved_templates(cls, _type):
        """Yields :class:`TemplateItem` instances saved in the database or on disk."""

        if _type == TemplateType.DatabaseTemplate:
            args = common.active('root', args=True)
            if not args:
                raise RuntimeError('A root item must be active to get the database templates')

            db = database.get(*args)
            _values = db.get_column('data', database.TemplateDataTable)
            if not _values:
                return

            for _value in _values:
                yield cls(data=_value)

        if _type == TemplateType.UserTemplate:
            if not os.path.exists(cls.default_user_folder):
                return

            for entry in os.scandir(cls.default_user_folder):
                if not entry.name.endswith(f'.{cls.default_extension}'):
                    continue

                yield cls(path=f'{cls.default_user_folder}/{entry.name}')
