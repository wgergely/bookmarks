"""
This module provides the interface for managing asset and job template files.

Templates are zip files containing a folder structure of an asset. :arg:`TemplateType.DatabaseTemplate` items are
stored in the active root item database, while :arg:`TemplateType.UserTemplate` items are stored in the user template
folder.

The templates internally contain a thumbnail image, a metadata file, and a zip file that contains the asset hierarchy.
Use the :class:`TemplateItem` class to create, edit, and save templates. The class takes a `path` or a `data` kwarg,
depending on the template type:

.. code-block:: python

    # To construct a new template from raw data:
    data = b'...'  # Binary data stored in the database
    template = TemplateItem(data=data)
    template['name'] = 'My Raw Data Template'
    template.save()  # saves the template to the database


    # To wrap an existing template file:
    path = 'path/to/template.template'  # Path to the template file on disk
    template = TemplateItem(path=path)
    template['name'] = 'My File Template'
    template.save()  # saves the template to the user template folder


    # To create template from a folder hierarchy:
    path = 'path/to/template.template'  # Template save path
    thumbnail_image = 'path/to/thumbnail.png'  # Path to the thumbnail image
    source_folder = 'path/to/folder'  # Path to the folder to be zipped
    template = TemplateItem(path=path)
    template['name'] = 'Template from a source folder'
    template.set_thumbnail(thumbnail_image)
    template.template_from_folder(source_folder)  # zip the given folder and save it to the template internally
    template.save()  # saves the template to the user template folder


Extracting the contents of a template to disk is done using the :meth:`TemplateItem.template_to_folder` method:

.. code-block:: python

    template = TemplateItem(path='path/to/template.template')
    template.template_to_folder('path/to/destination/folder')


.. note:

    Extracting templates might introduce path traversal vulnerabilities if the template uses links that define
    paths outside the destination directory. This can be desired in certain pipeline environments, but it's important
    to verify the contents of the template before extracting.


Links
-----

Importantly, templates support the :mod:`bookmarks.links` API. See :mod:`bookmarks.links` for more information on how to

"""
import datetime
import io
import json
import os
import tempfile
import zipfile
from enum import Enum, StrEnum

import bookmarks_openimageio
from PySide2 import QtGui, QtCore

from .error import *
from .. import common, tokens
from .. import database
from .. import images
from .. import log
from ..links.lib import LinksAPI

__all__ = [
    'TemplateType',
    'TemplateItem',
    'BuiltInTemplate',
    'builtin_template_exists',
    'get_saved_templates',
    'default_user_folder',  # Add for tests
]


class TemplateType(StrEnum):
    DatabaseTemplate = 'Shared Templates'
    UserTemplate = 'User Templates'


template_file_blacklist = {
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


default_extension = 'template'
default_user_folder = (
    f'{QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.GenericDataLocation)}/'
    f'{common.product}/templates'
)

metadata_keys = (
    'name',
    'description',
    'author',
    'date',
)


class BuiltInTemplate(Enum):
    TokenConfig = 'Default Template'
    Empty = 'Empty Template'


compression = zipfile.ZIP_STORED


@common.debug
@common.error(show_error=False)
def get_saved_templates(_type, create_builtin_if_missing=True):
    if not isinstance(_type, TemplateType):
        raise ValueError(f'Invalid template type: {_type}, expected one of {list(TemplateType)}')

    if _type == TemplateType.DatabaseTemplate:
        args = common.active('root', args=True)
        if not args:
            log.debug(__name__, 'Attempted to get database templates but no root item is active')
            return

        if create_builtin_if_missing and not builtin_template_exists(_type):
            log.debug(__name__, 'Creating built-in token config template...')
            token_template = TemplateItem()
            token_template.save(force=True)

            log.debug(__name__, 'Creating empty template...')
            empty_template = TemplateItem(empty=True)
            empty_template.save(force=True)

        db = database.get(*args)
        _values = db.get_column('data', database.TemplateDataTable)
        if not _values:
            log.debug(__name__, 'No templates found in the database')
            return

        for _value in _values:
            item = TemplateItem(data=_value)
            log.debug(__name__, f'Found template: {item["name"]}')
            yield item

    elif _type == TemplateType.UserTemplate:
        if not os.path.exists(default_user_folder):
            log.debug(__name__, f'Creating user template folder: {default_user_folder}')
            os.makedirs(default_user_folder, exist_ok=True)

        if create_builtin_if_missing and not builtin_template_exists(_type):
            log.debug(__name__, 'Default built-in template was not found, creating...')
            path = TemplateItem.get_save_path(BuiltInTemplate.Empty.value)
            if os.path.exists(path):
                log.debug(__name__, f'Empty template already exists: {path}, removing...')
                os.remove(path)
            template = TemplateItem(path=path, empty=True)
            template.save(force=True)

        with os.scandir(default_user_folder) as it:
            for entry in it:
                if not entry.name.endswith(f'.{default_extension}'):
                    continue
                yield TemplateItem(path=f'{default_user_folder}/{entry.name}')


def builtin_template_exists(_type=TemplateType.DatabaseTemplate):
    if not isinstance(_type, TemplateType):
        raise ValueError(f'Invalid template type: {_type}, expected one of {list(TemplateType)}')

    if _type == TemplateType.DatabaseTemplate:
        args = common.active('root', args=True)
        if not args:
            log.debug(__name__, 'Attempted to check for database templates but no root item is active')
            return False

        db = database.get(*args)
        ids = db.get_column('id', database.TemplateDataTable)
        return (
                common.get_hash(BuiltInTemplate.TokenConfig.value) in ids and
                common.get_hash(BuiltInTemplate.Empty.value) in ids
        )

    if _type == TemplateType.UserTemplate:
        if not os.path.exists(default_user_folder):
            log.debug(__name__, f'User template folder not found: {default_user_folder}')
            return False

        with os.scandir(default_user_folder) as it:
            for entry in it:
                if entry.name == f'{BuiltInTemplate.Empty.value}.{default_extension}':
                    return True

    return False


class TemplateItem(object):
    def __getitem__(self, key):
        return self.get_metadata(key)

    def __setitem__(self, key, value):
        self.set_metadata(key, value)

    def __repr__(self):
        return f'<TemplateItem: {self._metadata["name"]}>'

    def __init__(self, path=None, data=None, empty=False):
        if path and data:
            raise ValueError('Provide either raw template data, or a path to a valid template file')

        if empty and data:
            raise ValueError('Requested an empty template, but provided raw data')

        self._path = None
        self._original_path = None
        self._template = None
        self._has_links = False
        self._has_error = False
        self._metadata = None
        self._qimage = None
        self._size = 0

        # If we're given a path (user template), store it and normalize
        if path:
            self._path = os.path.normpath(path).replace('\\', '/')
            self._original_path = self._path

        if empty:
            self.new_empty_template()
            # If user template and path is given, set metadata name from filename
            if self.type == TemplateType.UserTemplate and self._path:
                base_name = os.path.splitext(os.path.basename(self._path))[0]
                self._metadata['name'] = base_name
            return

        if not path and not empty and not data:
            self.new_template_from_tokens()
            # If user template and path is given, set metadata name from filename
            if self.type == TemplateType.UserTemplate and self._path:
                base_name = os.path.splitext(os.path.basename(self._path))[0]
                self._metadata['name'] = base_name
            return

        self._load_zip_file(path, data)
        # If user template and path is given, ensure metadata['name'] matches filename if not set
        if self.type == TemplateType.UserTemplate and self._path:
            base_name = os.path.splitext(os.path.basename(self._path))[0]
            self._metadata['name'] = base_name

    @staticmethod
    def get_save_path(name):
        return f'{default_user_folder}/{name}.{default_extension}'

    @common.debug
    def _load_zip_file(self, path, data):
        if not path and not data:
            log.error(__name__, 'No path or data provided, skipping.')
            return

        try:
            if path and os.path.exists(path):
                self._size = os.path.getsize(path)
                zf = zipfile.ZipFile(path, 'r')
            elif data:
                zf = zipfile.ZipFile(io.BytesIO(data), 'r')
                self._size = common.get_py_obj_size(data)
            else:
                raise ValueError('No path or data provided')
        except (zipfile.BadZipFile, FileNotFoundError, ValueError):
            self._has_error = True
            log.error(__name__, f'Failed to read template: {path}')
            raise TemplateError('Could not read template')

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
                    for key in metadata_keys:
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
                log.error(__name__, f'Failed to load metadata.json in {self._path}')

            try:
                with z.open('thumbnail.png') as t:
                    d = t.read()
                    self._qimage = QtGui.QImage.fromData(d)
                    if self._qimage.isNull():
                        self._qimage = QtGui.QImage()
            except (ValueError, zipfile.BadZipFile, RuntimeError):
                self._qimage = QtGui.QImage()
                log.error(__name__, f'Failed to load thumbnail.png in {self._path}')

            try:
                with z.open('template.zip') as t:
                    self._template = t.read()
                    with zipfile.ZipFile(io.BytesIO(self._template), 'r') as tz:
                        if '.links' in tz.namelist():
                            self._has_links = True
            except (zipfile.BadZipFile, RuntimeError) as e:
                log.error(__name__, f'Failed to read embedded template.zip: {e}')
                zp = io.BytesIO()
                with zipfile.ZipFile(zp, 'w') as _:
                    pass
                zp.seek(0)
                self._template = zp.getvalue()
                self._has_error = True

    @staticmethod
    def _default_qimage(binary=True):
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

    def _get_save_data(self):
        if not self._qimage or self._qimage.isNull():
            self._qimage = self._default_qimage(binary=False)

        zp = io.BytesIO()
        with zipfile.ZipFile(zp, 'w', compression=compression) as z:
            json_data = json.dumps(self._metadata)
            z.writestr('metadata.json', json_data)
            z.writestr('thumbnail.png', self.get_thumbnail(binary=True))
            z.writestr('template.zip', self._template)
        zp.seek(0)
        return zp.getvalue()

    def _save_to_database(self, force, data):
        if self.type != TemplateType.DatabaseTemplate:
            raise ValueError('Can\'t save a user template to the database')

        args = common.active('root', args=True)
        if not args:
            raise RuntimeError('A root item must be active to save the template to the database')

        db = database.get(*args)

        _hash = common.get_hash(self._metadata['name'])
        _hashes = db.get_column('id', database.TemplateDataTable)

        if not force and _hash in _hashes:
            raise ValueError(f'Template already exists: {self._metadata["name"]}')

        db.set_value(self._metadata['name'], 'data', data, database.TemplateDataTable)
        common.signals.templatesChanged.emit()

    def _save_to_disk(self, force, data):
        if self.type != TemplateType.UserTemplate:
            raise ValueError('Can\'t save a database template to disk')

        # If _path not set yet (user template created without a path), derive from metadata['name']
        if not self._path:
            self._path = self.get_save_path(self._metadata['name'])

        if os.path.exists(self._path) and not force:
            raise FileExistsError(f'Template already exists: {self._path}')

        folder = os.path.dirname(self._path)
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        with open(self._path, 'wb') as f:
            f.write(data)

        common.signals.templatesChanged.emit()

    def _safe_extract(self, z, exclude_files=None):
        if exclude_files is None:
            exclude_files = set()
        exclude_files.update(template_file_blacklist)
        extracted_files = []

        for item in z.infolist():
            if item.filename in exclude_files:
                continue

            sanitized_filename = self._sanitize_filename(item.filename)

            if not sanitized_filename:
                continue

            with z.open(item) as source:
                file_data = source.read()
                log.debug(__name__, f'Extracting: {sanitized_filename} ({len(file_data)} bytes)')
                extracted_files.append((sanitized_filename, file_data))

        log.debug(__name__, f'Extracted files: {extracted_files}')
        return extracted_files

    @staticmethod
    def _sanitize_filename(filename):
        is_dir = filename.endswith('/')
        filename = filename.lstrip('/\\').split(':')[-1]
        filename = os.path.normpath(filename).replace('\\', '/')
        if is_dir:
            filename = f'{filename}/'
        return filename

    @property
    def path(self):
        return self._path

    @property
    def type(self):
        if self._path is not None:
            return TemplateType.UserTemplate
        else:
            return TemplateType.DatabaseTemplate

    @property
    def template(self):
        return self._template

    @property
    def metadata(self):
        return self._metadata

    @property
    def qimage(self):
        return self._qimage

    @qimage.setter
    def qimage(self, value):
        if not isinstance(value, QtGui.QImage):
            raise ValueError(f'Invalid type: {value}, expected QtGui.QImage')
        self._qimage = value

    @property
    def size(self):
        return self._size

    @property
    def has_links(self):
        return self._has_links

    @common.debug
    def get_links(self):
        link_paths = []
        try:
            zp = io.BytesIO(self._template)
            with zipfile.ZipFile(zp, 'r') as zf:
                with zf.open('.links') as f:
                    v = f.read()
            link_paths = v.decode('utf-8').strip().splitlines()
        except (zipfile.BadZipFile, KeyError):
            log.debug(__name__, f'No .links file found.')
        return link_paths

    @common.debug
    def set_link_preset(self, preset, force=False):
        presets = LinksAPI.presets()
        if preset not in presets:
            raise ValueError(f'Invalid preset: {preset}')

        v = presets[preset]
        if not v:
            raise ValueError(f'Invalid preset: {preset}')

        if not self._template:
            raise ValueError('Template is empty')

        if not force and self.contains_file('.links'):
            raise TemplateLinkExistsError('Template already contains a .links file!')
        if force and self.contains_file('.links'):
            self.remove_link_preset()

        if isinstance(v, (list, tuple)):
            v = '\n'.join(v)

        try:
            zp = io.BytesIO(self._template)
            with zipfile.ZipFile(zp, 'a', compression=compression) as z:
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
        if not self._has_links:
            return

        old_zp = io.BytesIO(self._template)
        new_zp = io.BytesIO()

        with zipfile.ZipFile(old_zp, 'r') as old_zip, \
                zipfile.ZipFile(new_zp, 'w', compression=compression) as new_zip:
            extracted_files = self._safe_extract(old_zip, exclude_files={'.links'})
            for filename, data in extracted_files:
                new_zip.writestr(filename, data)

        new_zp.seek(0)
        self._template = new_zp.getvalue()
        self._has_links = False

    @property
    def has_error(self):
        return self._has_error

    def set_metadata(self, key, value):
        if key not in metadata_keys:
            raise KeyError(f'Invalid metadata key: {key}, expected one of {metadata_keys}')
        self._metadata[key] = value

    def get_metadata(self, key):
        if key not in metadata_keys:
            raise KeyError(f'Invalid metadata key: {key}, expected one of {metadata_keys}')
        return self._metadata[key]

    def clear_metadata(self):
        self._metadata = {
            'name': '',
            'description': '',
            'author': '',
            'date': '',
        }

    @common.debug
    @common.error(show_error=False)
    def set_thumbnail(self, source):
        if not os.path.exists(source):
            raise FileNotFoundError(f'File not found: {source}')

        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        destination = tmp.name
        tmp.close()

        try:
            error = bookmarks_openimageio.convert_image(
                source,
                destination,
                source_color_space='',
                target_color_space='sRGB',
                size=int(common.Size.Thumbnail(apply_scale=False))
            )
            if error == 1:
                log.error(__name__, 'Failed to convert the thumbnail, using default thumbnail')
                qimage = self._default_qimage(binary=False)
            else:
                qimage = QtGui.QImage(destination)
                if qimage.isNull():
                    qimage = self._default_qimage(binary=False)

            self._qimage = qimage
        finally:
            if os.path.exists(destination):
                os.remove(destination)

    def get_thumbnail(self, binary=False):
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
        self._qimage = self._default_qimage(binary=False)

    @common.debug
    @common.error(show_error=False)
    def save(self, force=False):
        if not self._metadata['name']:
            raise ValueError('Cannot save a template without a name')
        if self._has_error:
            raise TemplateError('Cannot save a template with errors')
        if self.type == TemplateType.DatabaseTemplate and not common.active('root', args=True):
            raise RuntimeError('A root item must be active to save the template to the database')

        data = self._get_save_data()
        if self.type == TemplateType.DatabaseTemplate:
            self._save_to_database(force, data)
        elif self.type == TemplateType.UserTemplate:
            self._save_to_disk(force, data)


    @common.debug
    @common.error(show_error=False)
    def delete(self):
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

        p = f'{default_user_folder}/{self._metadata["name"]}.{default_extension}'
        if not os.path.exists(p):
            raise FileNotFoundError(f'Template not found: {p}')
        os.remove(p)

    def rename(self, name):
        if not name:
            raise ValueError('Name must be set')

        current_name = self._metadata['name']
        if self.type == TemplateType.DatabaseTemplate:
            # Database template rename logic unchanged...
            args = common.active('root', args=True)
            if not args:
                raise RuntimeError('A root item must be active to rename the template in the database')
            db = database.get(*args)
            _hashes = db.get_column('id', database.TemplateDataTable)
            _hash = common.get_hash(name)
            if _hash in _hashes:
                raise ValueError(f'Template already exists: {name}')
            self._metadata['name'] = name
            data = self._get_save_data()
            self._save_to_database(True, data)
            db.delete_row(current_name, database.TemplateDataTable)
            return

        # User template rename logic
        new_path = self.get_save_path(name)

        # If the template file already exists under the old path, rename it on disk
        old_path = self._path
        if os.path.exists(old_path):
            if os.path.exists(new_path):
                raise FileExistsError(f'Template already exists: {new_path}')
            os.rename(old_path, new_path)

        self._metadata['name'] = name
        self._path = new_path

        # Save again to update metadata.json inside the template zip
        data = self._get_save_data()
        self._save_to_disk(force=True, data=data)

        # If old_path existed and differs from new_path, the file was already moved
        # No need to remove old_path as os.rename took care of that

    def contains_file(self, rel_path):
        if not self._template:
            return False
        zp = io.BytesIO(self._template)
        with zipfile.ZipFile(zp, 'r') as z:
            return rel_path in z.namelist()

    @common.debug
    @common.error(show_error=False)
    def template_to_folder(
            self,
            root_path,
            extract_contents_to_links=False,  # Changed default to False
            ignore_existing_folders=False,
            ignore_links=False,
    ):
        if extract_contents_to_links and ignore_links:
            raise RuntimeError('Cannot specify both `extract_contents_to_links` and `ignore_links`')

        # Ensure root_path exists
        if not os.path.exists(root_path):
            parent_dir = os.path.dirname(root_path)
            if not os.path.exists(parent_dir):
                log.error(__name__, f'Parent directory does not exist: {parent_dir}')
                raise FileNotFoundError(f'Parent directory does not exist: {parent_dir}')
            try:
                os.makedirs(root_path, exist_ok=True)
                log.debug(__name__, f'Created root path: {root_path}')
            except PermissionError:
                log.error(__name__, f'No permission to create directory: {root_path}')
                raise PermissionError(f'No permission to create directory: {root_path}')

        root_path = os.path.normpath(root_path).replace('\\', '/')

        if self._has_error:
            log.error(__name__, 'Template has errors and cannot be extracted')
            raise TemplateError('Template has errors')

        if not self._template:
            log.error(__name__, f'No template data found for template: {self._metadata["name"]}')
            raise ValueError(f'Template data not found: {self._metadata["name"]}')

        # If we need to extract contents to links but no links file exists, raise TemplateError
        if extract_contents_to_links and not ignore_links:
            if not self._has_links:
                raise TemplateError('No .links found in the template!')

        inner_zp = io.BytesIO(self._template)
        with zipfile.ZipFile(inner_zp, 'r') as inner_zf:
            abs_paths = []
            if self._has_links and extract_contents_to_links and not ignore_links:
                links = self.get_links()
                if not links:
                    raise TemplateError('No .links found in the template!')
                for rel_path in links:
                    abs_path = f'{root_path}/{rel_path}'
                    if os.path.exists(abs_path) and not ignore_existing_folders:
                        log.error(__name__, f'Path already exists: {abs_path}')
                        raise FileExistsError(f'Path already exists: {abs_path}')
                    try:
                        os.makedirs(abs_path, exist_ok=True)
                        log.debug(__name__, f'Created link path: {abs_path}')
                    except PermissionError:
                        log.error(__name__, f'No permission to create directory: {abs_path}')
                        raise PermissionError(f'No permission to create directory: {abs_path}')
                    abs_paths.append(abs_path)
            else:
                abs_paths = [root_path]

            extracted_files = self._safe_extract(inner_zf)
            links_data = None
            skipped_files = []
            log.info(__name__, f'Extracting {len(extracted_files)} files from template.zip to {len(abs_paths)} paths')

            for filename, data in extracted_files:
                is_dir = filename.endswith('/')
                if is_dir:
                    for abs_path in abs_paths:
                        dir_path = f'{abs_path}/{filename}'.rstrip('/')
                        try:
                            os.makedirs(dir_path, exist_ok=True)
                            log.debug(__name__, f'Created directory: {dir_path}')
                        except PermissionError:
                            log.error(__name__, f'No permission to create directory: {dir_path}')
                            raise PermissionError(f'No permission to create directory: {dir_path}')
                    continue

                if filename.endswith('.links'):
                    links_data = data
                    continue

                for abs_path in abs_paths:
                    file_path = f'{abs_path}/{filename}'
                    parent_dir = os.path.dirname(file_path)
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except PermissionError:
                        log.error(__name__, f'No permission to create directory: {parent_dir}')
                        raise PermissionError(f'No permission to create directory: {parent_dir}')

                    if os.path.exists(file_path):
                        log.warning(__name__, f'File already exists: {file_path}, skipping')
                        skipped_files.append(file_path)
                        continue

                    try:
                        with open(file_path, 'wb') as f:
                            f.write(data)
                        log.debug(__name__, f'Extracted file: {file_path}')
                    except PermissionError:
                        log.error(__name__, f'No permission to write file: {file_path}')
                        raise PermissionError(f'No permission to write file: {file_path}')

            if links_data and not ignore_links:
                links_path = f'{root_path}/.links'
                try:
                    with open(links_path, 'wb') as f:
                        f.write(links_data)
                    log.debug(__name__, f'Wrote .links file to {links_path}')
                except PermissionError:
                    log.error(__name__, f'No permission to write .links file: {links_path}')
                    raise PermissionError(f'No permission to write .links file: {links_path}')

        log.info(__name__, f'Successfully extracted template files to {root_path}')

    @common.debug
    @common.error(show_error=False)
    def template_from_folder(self, source_folder, skip_system_files=True, max_size_mb=100):
        if not os.path.isdir(source_folder):
            raise NotADirectoryError(f'The source must be a directory: {source_folder}')
        if not os.access(source_folder, os.R_OK):
            raise PermissionError(f'No read access to the folder: {source_folder}')

        source_folder = os.path.normpath(source_folder).replace('\\', '/')
        max_size_bytes = max_size_mb * 1024 * 1024

        blacklist = {f.lower() for f in template_file_blacklist}

        files = []
        folders = []
        skipped = []
        total_size = 0

        zp = io.BytesIO()
        with zipfile.ZipFile(zp, 'w', compression=compression) as zf:

            def _it(path, _total_size, _files, _folders, _skipped):
                if not os.access(path, os.R_OK):
                    log.error(__name__, f'No read access to the folder: {path}')
                    return _total_size
                with os.scandir(path) as it:
                    for entry in it:
                        if entry.is_symlink():
                            continue
                        p = entry.path.replace('\\', '/').rstrip('/')
                        rp = p[len(source_folder) + 1:]
                        if skip_system_files and entry.name.lower() in blacklist:
                            log.debug(__name__, f'Skipping system file: {p}')
                            _skipped.append(p)
                            continue
                        if entry.is_file():
                            file_size = os.path.getsize(p)
                            if _total_size + file_size > max_size_bytes:
                                raise TemplateSizeError(
                                    f'Template size exceeds the maximum allowed size of {max_size_mb} MB.'
                                )
                            _total_size += file_size
                            if rp == '.links':
                                self._has_links = True
                            _files.append(rp)
                            zf.write(p, rp)
                        elif entry.is_dir():
                            rp_dir = f'{rp}/'
                            _folders.append(rp_dir)
                            zf.writestr(rp_dir, '')
                            _total_size = _it(p, _total_size, _files, _folders, _skipped)
                return _total_size

            total_size = _it(source_folder, total_size, files, folders, skipped)

        zp.seek(0)
        self._template = zp.getvalue()
        return files, folders

    @common.debug
    def new_template_from_tokens(self):
        self.clear_metadata()
        # If no path, it's a built-in db template. If path is given, keep name from path?
        # The built-in token config template is always named Default Template.
        self._metadata['name'] = BuiltInTemplate.TokenConfig.value
        self._metadata['description'] = 'Built-in template generated based on the current asset folder settings'
        self._metadata['author'] = common.get_username()
        self._metadata['date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        p = images.rsc_pixmap('icon_bw_sm', None, None, get_path=True)
        self.set_thumbnail(p)

        args = common.active('root', args=True)
        if args:
            config = tokens.get(*args).data(force=True)
        else:
            log.error(__name__, 'No active root item found, using the default token config')
            config = tokens.DEFAULT_TOKEN_CONFIG.copy()

        zp = io.BytesIO()
        with zipfile.ZipFile(zp, 'w', compression=compression) as zf:
            for v in config[tokens.AssetFolderConfig].values():
                dir_path = f'{v["value"]}/'
                if dir_path not in zf.namelist():
                    zf.writestr(dir_path, '')
                if 'subfolders' in v:
                    for _v in v['subfolders'].values():
                        sub_path = f'{v["value"]}/{_v["value"]}/'
                        if sub_path not in zf.namelist():
                            zf.writestr(sub_path, '')

        zp.seek(0)
        self._template = zp.getvalue()

    @common.debug
    def new_empty_template(self):
        self.clear_metadata()

        self._metadata['name'] = BuiltInTemplate.Empty.value
        self._metadata['description'] = 'Built-in empty template'
        self._metadata['author'] = common.get_username()
        self._metadata['date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        p = images.rsc_pixmap('icon_bw_sm', None, None, get_path=True)
        self.set_thumbnail(p)

        zp = io.BytesIO()
        with zipfile.ZipFile(zp, 'w', compression=compression):
            pass
        zp.seek(0)
        self._template = zp.getvalue()

    def is_builtin(self):
        return self['name'] in (BuiltInTemplate.TokenConfig.value, BuiltInTemplate.Empty.value)
