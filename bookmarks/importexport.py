"""Property export and import functions.

This module can export bookmark and asset item properties to external files. The files
themselves are zip files made up of a manifest.json, bookmark_table_properties.json
asset_table_properties.json and a thumbnail file. See the main export function
:func:`export_item_properties`, and the main import function
:func:`import_item_properties` for details.


"""
import json
import os
import shutil
import time
import uuid
import zipfile

from PySide2 import QtCore, QtWidgets

from . import common
from . import database
from . import images
from . import log
from . import ui

_last_directory = None


def get_properties_as_json(index):
    """Returns the item's bookmark and asset table properties as a JSON strings.

    Args:
        index (QtCore.QModelIndex): An item index.

    Returns:
        tuple (str, str): The bookmark and asset table properties of the item.

    """
    if not index.isValid():
        return
    if not index.data(common.FileInfoLoaded):
        raise ValueError('Index is not yet fully loaded.')

    pp = index.data(common.ParentPathRole)
    source = index.data(common.PathRole)
    item_type = index.data(common.ItemTabRole)

    db = database.get_db(*pp[0:3])

    asset_table_data = db.get_row(source, database.AssetTable)
    asset_table_data = {
        k: v for k, v in asset_table_data.items() if v is not None
    }

    if item_type == common.BookmarkTab:
        bookmark_table_data = db.get_row(source, database.BookmarkTable)
        bookmark_table_data = {
            k: v for k, v in bookmark_table_data.items() if v is not None
        }
    elif item_type == common.AssetTab:
        # Asset items *should* store all their values in the asset table only
        bookmark_table_data = {}
    else:
        raise ValueError(f'Invalid item type: {index.data(common.ItemTabRole)}')

    return (
        json.dumps(bookmark_table_data, sort_keys=False, indent=4),
        json.dumps(asset_table_data, sort_keys=False, indent=4),
    )


def get_save_path(name):
    """Prompts the user to pick a file-save path.

    Args:
        name (str): The item's display name.

    Returns:
        str: The path to save the item.

    """
    global _last_directory

    d = _last_directory if _last_directory else ''
    v, _ = QtWidgets.QFileDialog.getSaveFileName(
        caption='Export item properties...',
        filter='*.preset',
        dir=f'{d}/{name.replace("/", "_").strip("_").strip()}.preset'
    )

    if not v:
        return None
    _last_directory = QtCore.QFileInfo(v).dir().path()
    return v


def get_load_path(extension='preset'):
    """Prompts the user to pick a file-load path.

    Returns:
        str: Path to the file to load.

    """
    global _last_directory

    d = _last_directory if _last_directory else ''
    v, _ = QtWidgets.QFileDialog.getOpenFileName(
        caption='Import properties...',
        filter=f'*.{extension}',
        dir=d
    )

    if not v:
        return None
    _last_directory = QtCore.QFileInfo(v).dir().path()
    return v


def get_manifest_data(index):
    """Get an informative json string to stamp a properties file.

    Args:
        index (QtCore.QModelIndex): An item index.

    Returns:
        str: Manifest data as a JSON string.

    """
    data = {
        'item_type': index.data(common.ItemTabRole),
        'user': common.get_username(),
        'date': time.strftime('%d/%m/%Y %H:%M:%S'),
        'source': index.data(common.PathRole)
    }
    return json.dumps(data, sort_keys=False, indent=4)


def verify_zip_file(path, item_type):
    """Verifies the given preset file against the given item type.

    """
    if item_type not in (common.BookmarkTab, common.AssetTab):
        raise ValueError(f'Invalid item type: {item_type}')

    # Verify temp file
    if not QtCore.QFileInfo(path).exists():
        raise RuntimeError(f'{path} does not exist')

    if not zipfile.is_zipfile(path):
        raise RuntimeError(f'{path} is not a valid zip file')

    with zipfile.ZipFile(path, 'r', compression=zipfile.ZIP_STORED) as f:
        corrupt = f.testzip()
        if corrupt:
            raise RuntimeError(f'The zip archive seems corrupt: {corrupt}')

        # Check the zip file integrity
        for _f in (
                'manifest.json',
                'bookmark_table_properties.json',
                'asset_table_properties.json',
        ):
            if _f not in f.namelist():
                raise RuntimeError(f'Invalid preset file: {_f} is missing from {path}')

        # Check property file type
        manifest_data = json.loads(
            f.read('manifest.json'),
            parse_int=int,
            parse_float=float,
            object_hook=common.int_key
        )
        f.close()

    if 'item_type' not in manifest_data:
        raise RuntimeError(f'Invalid manifest file.')

    if manifest_data['item_type'] != item_type:
        a = '[unknown]'
        a = 'asset' if manifest_data['item_type'] == common.AssetTab else a
        a = 'bookmark' if manifest_data['item_type'] == common.BookmarkTab else a

        b = '[unknown]'
        b = 'bookmark' if item_type == common.BookmarkTab else b
        b = 'asset' if item_type == common.AssetTab else b
        raise RuntimeError(
            f'This is a {a} property file, and it isn\'t compatible with {b} items.'
        )


def export_item_properties(index, destination=None):
    """The principal function used to export an item's properties to an external file.

    Args:
        index (QtCore.QModelIndex): An item index.
        destination (str):
            Optional path to a file. If not provided, the user will be prompted to
            select a destination a file.

    """
    bookmark_table_data, asset_table_data = get_properties_as_json(index)
    manifest_data = get_manifest_data(index)

    # Get thumbnail
    # w = common.widget(index.data(common.ItemTabRole))
    # fallback_thumb = w.itemDelegate().fallback_thumb
    thumbnail_path = images.get_thumbnail(
        index.data(common.ParentPathRole)[0],
        index.data(common.ParentPathRole)[1],
        index.data(common.ParentPathRole)[2],
        index.data(common.PathRole),
        fallback_thumb=None,
        get_path=True,
    )
    if f'placeholder.{common.thumbnail_format}' in thumbnail_path:
        thumbnail_path = None

    temp_file = f'{common.temp_path()}/{uuid.uuid1().hex}.preset'
    with zipfile.ZipFile(temp_file, 'w', compression=zipfile.ZIP_STORED) as f:
        if thumbnail_path:
            f.write(thumbnail_path, f'thumbnail.{common.thumbnail_format}')
        f.writestr('manifest.json', manifest_data)
        f.writestr('bookmark_table_properties.json', bookmark_table_data)
        f.writestr('asset_table_properties.json', asset_table_data)
        f.close()

    verify_zip_file(temp_file, index.data(common.ItemTabRole))

    if destination is None:
        name = index.data(QtCore.Qt.DisplayRole)
        destination = get_save_path(name)
    if not destination:
        return

    f = QtCore.QFile(destination)
    if f.exists() and not f.remove():
        raise RuntimeError(f'Failed to remove {destination}')

    if not QtCore.QFile.copy(temp_file, destination):
        raise RuntimeError(f'Failed to copy {temp_file} to {destination}')

    if not QtCore.QFile(temp_file).remove():
        log.error(f'Failed to remove {temp_file}')

    if QtCore.QFileInfo(destination).exists():
        log.success(f'Properties saved to {destination}')


def import_item_properties(index, source=None, prompt=True):
    """The principal function used to import an item's properties from an external file.

    Args:
        index (QtCore.QModelIndex): An item index.
        source (str): Path to a preset file. Optional.
        prompt (bool): Show prompt before overriding.

    """
    if prompt:
        mbox = ui.MessageBox(
            'Are you sure you want to import the preset file?',
            'This will override current item property values.',
            buttons=[ui.YesButton, ui.CancelButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return None

    if source is None:
        source = get_load_path()
        if not source:
            return

    item_type = index.data(common.ItemTabRole)
    verify_zip_file(source, item_type)

    with zipfile.ZipFile(source, 'r', compression=zipfile.ZIP_STORED) as f:
        bookmark_table_data = json.loads(
            f.read('bookmark_table_properties.json'),
            parse_int=int,
            parse_float=float,
            object_hook=common.int_key
        )
        asset_table_data = json.loads(
            f.read('asset_table_properties.json'),
            parse_int=int,
            parse_float=float,
            object_hook=common.int_key
        )

        # Check if there's a thumbnail image available to read
        # And extract it to the item's thumbnail image path
        if f'thumbnail.{common.thumbnail_format}' in f.namelist():
            p = images.get_cached_thumbnail_path(
                index.data(common.ParentPathRole)[0],
                index.data(common.ParentPathRole)[1],
                index.data(common.ParentPathRole)[2],
                index.data(common.PathRole),
                proxy=False
            )

            # Write thumbnail image
            images.ImageCache.flush(index.data(common.PathRole))
            _p = QtCore.QFile(p)
            if _p.exists():
                _p.remove()
            with f.open(f'thumbnail.{common.thumbnail_format}') as t, open(p, 'wb') as _t:
                shutil.copyfileobj(t, _t)
            images.ImageCache.flush(index.data(common.PathRole))
            images.ImageCache.flush(p)

        f.close()

    db = database.get_db(*index.data(common.ParentPathRole)[0:3])
    source = index.data(common.PathRole)
    with db.connection():
        for k, v in bookmark_table_data.items():
            db.set_value(source, k, v, table=database.BookmarkTable)
        for k, v in asset_table_data.items():
            db.set_value(source, k, v, table=database.AssetTable)


def import_json_asset_properties(indexes, prompt=True):
    """Import properties for multiple items from a JSON file.

    Args:
        indexes (list[QtCore.QModelIndex]): A list of item indexes.
        prompt (bool): Show prompt before overriding.
    """
    json_file_path = get_load_path(extension='json')
    if not json_file_path:
        return

    # Load JSON data from file
    if not os.path.exists(json_file_path):
        raise ValueError(f"File does not exist: {json_file_path}")

    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        raise ValueError(f"File is not a valid JSON file: {json_file_path}")

    if prompt:
        from . import ui
        mbox = ui.MessageBox(
            'Are you sure you want override the properties of the visible items?',
            buttons=[ui.YesButton, ui.NoButton]
        )
        if mbox.exec_() == QtWidgets.QDialog.Rejected:
            return

    # Loop through all visible indexes
    for index in indexes:

        path = index.data(common.PathRole)
        db = database.get_db(*index.data(common.ParentPathRole)[0:3])

        for item in data:

            # Skip invalid items
            if 'name' not in data[item]:
                continue

            # Match a corresponding item by name
            if item.lower() not in path.lower():
                continue

            # Set valid database values
            with db.connection():
                for k, v in data[item].items():
                    if k not in database.TABLES[database.AssetTable]:
                        continue
                    db.set_value(path, k, v, table=database.AssetTable)

            if 'thumbnail' in data[item] and os.path.isfile(data[item]['thumbnail']):
                images.create_thumbnail_from_image(
                    index.data(common.ParentPathRole)[0],
                    index.data(common.ParentPathRole)[1],
                    index.data(common.ParentPathRole)[2],
                    index.data(common.PathRole),
                    data[item]['thumbnail'],
                    proxy=False
                )
