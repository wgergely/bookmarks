import datetime
import io
import json
import os
import tempfile
import zipfile
from enum import Enum

import bookmarks_openimageio
from PySide2 import QtGui, QtCore

from .. import common
from .. import database
from .. import images
from ..tokens import tokens


class TemplateType(Enum):
    USER = 0
    DATABASE = 1


template_blacklist = (
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
)


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
        self._original_data = data

        self._path = None
        self._data = None
        self._type = None

        if not any([path, data]):
            data = self.get_empty_template(binary=True)
            self._type = TemplateType.DATABASE

        self._metadata = None
        self._qimage = None
        self._template = None
        self._zip_file = None

        if path:
            self._type = TemplateType.USER
            self._path = os.path.normpath(path).replace('\\', '/')
        if data:
            self._type = TemplateType.DATABASE
            self._data = data

        self._load_zip_file()

    def _load_zip_file(self):
        if self.type == TemplateType.DATABASE:
            zf = zipfile.ZipFile(io.BytesIO(self._data), 'r')
        elif self.type == TemplateType.USER:
            zf = zipfile.ZipFile(self._path, 'r')
        else:
            raise ValueError('Invalid template type')

        with zf as z:
            nl = z.namelist()

            if 'metadata.json' not in nl:
                raise ValueError('metadata.json not found in zip file')
            if 'thumbnail.png' not in nl:
                raise ValueError('thumbnail.png not found in zip file')
            if 'template.zip' not in nl:
                raise ValueError('template.zip not found in zip file')

            with z.open('metadata.json') as m:
                self._metadata = json.load(m)
                for key in self.metadata_keys:
                    if key not in self._metadata:
                        raise ValueError(f'Missing key in metadata.json: {key}')

            with z.open('thumbnail.png') as t:
                data = t.read()
                self._qimage = QtGui.QImage.fromData(data)
                if self._qimage.isNull():
                    self._qimage = QtGui.QImage()

            with z.open('template.zip') as t:
                self._template = t.read()

    def _default_qimage(self, binary=True):
        """Get the default thumbnail.

        Returns:
            QtGui.QImage: Default thumbnail.

        """
        _q_path = images.rsc_pixmap(
            'asset',
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
        """Update the template data.

        """
        if not self._qimage or self._qimage.isNull():
            self._qimage = self._default_qimage(binary=False)

        zp = io.BytesIO(self._data)
        with zipfile.ZipFile(
                zp,
                'w',
                compression=self.compression
        ) as z:
            json_data = json.dumps(self._metadata)
            z.writestr('metadata.json', json_data)
            z.writestr('thumbnail.png', self.get_thumbnail(binary=True))
            z.writestr('template.zip', io.BytesIO(self._template).getvalue())

        self._data = zp.getvalue()

    def _save_to_database(self, force):
        if self.type != TemplateType.DATABASE:
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
            self._data,
            database.TemplateDataTable
        )

    def _save_to_disk(self, force):
        if self.type != TemplateType.USER:
            raise ValueError('Can\'t save a database template to disk')

        if not os.path.exists(self.default_user_folder):
            os.makedirs(self.default_user_folder, exist_ok=True)

        p = f'{self.default_user_folder}/{self._metadata["name"]}.{self.default_extension}'
        if os.path.exists(p) and not force:
            raise FileExistsError(f'Template already exists: {p}')

        with open(p, 'wb') as f:
            f.write(self._data)

        return p

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
            int: TemplateType.USER or TemplateType.DATABASE.

        """
        return self._type

    def set_type(self, value):
        """Set the type of template.

        Args:
            value (int): TemplateType.USER or TemplateType.DATABASE.

        """
        if value not in (TemplateType.USER, TemplateType.DATABASE):
            raise ValueError('Invalid template type')
        self._type = value

    def get_empty_template(self, binary=False):
        """Create an empty template.

        Returns:
            str or bytes: Path to the template file or binary data.

        """
        metadata = {
            'name': 'New',
            'description': '',
            'author': common.get_username(),
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        json_data = json.dumps(metadata)

        # Populate template with the default token config
        _template_io = io.BytesIO()
        with zipfile.ZipFile(
                _template_io,
                'w',
                compression=self.compression
        ) as z:
            for v in tokens.DEFAULT_TOKEN_CONFIG[tokens.AssetFolderConfig].values():
                p = f'{v["value"]}/'
                if p not in z.namelist():
                    z.writestr(p, '')

                if 'subfolders' not in v:
                    continue

                for _v in v['subfolders'].values():
                    p = f'{v["value"]}/{_v["value"]}/'
                    if p not in z.namelist():
                        z.writestr(p, '')

        # Create a template file
        if binary:
            zp = io.BytesIO()
        else:
            zp = tempfile.NamedTemporaryFile(suffix=f'.{self.default_extension}', delete=False).name

        with zipfile.ZipFile(
                zp,
                'w',
                compression=self.compression
        ) as z:
            z.writestr('metadata.json', json_data)
            z.writestr('thumbnail.png', self._default_qimage(binary=True))
            z.writestr('template.zip', _template_io.getvalue())

        if not binary:
            return zp

        return zp.getvalue()

    def set_metadata(self, key, value):
        """Set metadata key.

        Args:
            key (str): Metadata key.
            value (str): Metadata value.

        """
        if key not in self.metadata_keys:
            raise KeyError(f'Invalid metadata key: {key}, expected one of {self.metadata_keys}')
        self._metadata[key] = value
        self._update_data()

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
        self._update_data()

    def set_thumbnail(self, source):
        """Set thumbnail image.

        Args:
            source (str): Path to an image.

        """
        if not os.path.exists(source):
            raise FileNotFoundError(f'File not found: {source}')

        destination = tempfile.NamedTemporaryFile(suffix='.png', delete=False).name

        error = bookmarks_openimageio.convert_image(
            source,
            destination,
            source_color_space='',
            target_color_space='sRGB',
            size=int(common.size_thumbnail)
        )
        if error == 1:
            raise RuntimeError('Failed to convert the thumbnail')

        qimage = QtGui.QImage(destination)
        os.remove(destination)

        if qimage.isNull():
            qimage = self._default_qimage(binary=False)

        self._qimage = qimage
        self._update_data()

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
        self._qimage.save(_buffer, 'PNG')
        _buffer.close()

        return _buffer.data()

    def reset_thumbnail(self):
        """Reset thumbnail to the default.

        """
        self._qimage = self._default_qimage(binary=False)
        self._update_data()

    def create_template_from_folder(self, source_folder, skip_system_files=True, max_size_mb=50):
        """
        Creates a template from the specified folder, ensuring the total size does not exceed max_size_mb.

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
            raise NotADirectoryError(f"The source must be a directory: {source_folder}")

        if not os.access(source_folder, os.R_OK):
            raise PermissionError(f"No read access to the folder: {source_folder}")

        max_size_bytes = max_size_mb * 1024 * 1024
        total_size = 0

        blacklist = {f.lower() for f in template_blacklist}

        def _it(path):
            if not os.access(path, os.R_OK):
                return

            for entry in os.scandir(path):
                if entry.is_symlink():
                    continue

                if skip_system_files and entry.name.lower() in blacklist:
                    continue

                if entry.is_file():
                    yield entry.path.replace('\\', '/')
                elif entry.is_dir():
                    yield from _it(entry.path)

        files = []
        folders = []

        zp = io.BytesIO()
        with zipfile.ZipFile(zp, 'w', compression=self.compression) as z:
            for abs_path in _it(source_folder):
                if os.path.isdir(abs_path):
                    folders.append(abs_path)
                elif os.path.isfile(abs_path):
                    file_size = os.path.getsize(abs_path)
                    if total_size + file_size > max_size_bytes:
                        raise RuntimeError(f'Template size exceeds the maximum allowed size of {max_size_mb} MB.')
                    total_size += file_size
                    files.append(abs_path)

                    rel_path = os.path.relpath(abs_path, source_folder)
                    z.write(abs_path, rel_path)

        self._template = zp.getvalue()
        return files, folders

    def save(self, force=False):
        """Save the template.

        Args:
            force (bool, Optional): Override existing data if True, defaults to False.

        """
        if not self._metadata['name']:
            raise ValueError('Name must be set')

        self._update_data()

        if self.type == TemplateType.DATABASE:
            self._save_to_database(force)
        elif self.type == TemplateType.USER:
            self._save_to_disk(force)

    def delete(self):
        """Delete the template.

        """
        if not self._metadata['name']:
            raise ValueError('Name must be set')

        if self.type == TemplateType.DATABASE:
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

        if self.type == TemplateType.USER:
            p = f'{self.default_user_folder}/{self._metadata["name"]}.{self.default_extension}'

            if not os.path.exists(p):
                raise FileNotFoundError(f'Template not found: {p}')

            os.remove(p)

    @classmethod
    def get_all_templates(cls, _type):
        if _type == TemplateType.DATABASE:
            args = common.active('root', args=True)
            if not args:
                raise RuntimeError('A root item must be active to get the database templates')

            db = database.get(*args)
            _values = db.get_column('data', database.TemplateDataTable)
            if not _values:
                return

            for _value in _values:
                yield cls(data=_value)

        if _type == TemplateType.USER:
            if not os.path.exists(cls.default_user_folder):
                return

            for entry in os.scandir(cls.default_user_folder):
                if not entry.name.endswith(f'.{cls.default_extension}'):
                    continue

                yield cls(path=f'{cls.default_user_folder}/{entry.name}')