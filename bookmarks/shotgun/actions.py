"""A list of ShotGrid specific actions.

"""
import os

from PySide2 import QtCore

from . import shotgun
from .. import common
from .. import database


@common.debug
@common.error
def link_bookmark_entity(server, job, root):
    from ..shotgun import link_bookmark as editor
    widget = editor.show(server, job, root)
    return widget


@common.debug
@common.error
def link_asset_entity(server, job, root, asset, entity_type):
    from ..shotgun import link_asset as editor
    widget = editor.show(server, job, root, asset, entity_type)
    return widget


@common.debug
@common.error
def show_task_picker():
    from ..shotgun import tasks as editor
    widget = editor.show()
    widget.sgEntitySelected.connect(common.signals.sgEntitySelected)
    return widget


@common.debug
@common.error
def link_assets():
    from ..shotgun import link_assets as editor
    widget = editor.show()
    widget.sgAssetsLinked.connect(common.signals.sgAssetsLinked)
    return widget


@common.debug
@common.error
def publish(formats=('mp4', 'mov')):
    from . import sg_publish_clip as editor
    widget = editor.show(formats=formats)
    return widget


@common.error
@common.debug
def upload_thumbnail(sg_properties, thumbnail_path):
    """Uploads an item thumbnail to shotgun.

    """
    if not sg_properties.verify():
        return

    asset = sg_properties.asset

    if asset is None:
        entity_type = sg_properties.bookmark_type
        entity_id = sg_properties.bookmark_id
    else:
        entity_type = sg_properties.asset_type
        entity_id = sg_properties.asset_id

    with sg_properties.connection() as sg:
        sg.upload_thumbnail(
            entity_type,
            entity_id,
            thumbnail_path
        )

    common.show_message(
        'Successfully uploaded thumbnail.',
        body=f'Uploaded thumbnail to {entity_type} {entity_id}.',
        message_type='success'
    )


@common.debug
@common.error
def test_sg_connection(sg_properties):
    if not sg_properties.verify(connection=True):
        if not sg_properties.domain:
            raise ValueError('ShotGrid Domain not set.')
        if not sg_properties.script:
            raise ValueError('ShotGrid API Script Name not set.')
        if not sg_properties.key:
            raise ValueError('ShotGrid API Script Key not set.')

    with sg_properties.connection() as sg:
        if not sg.find('Project', []):
            raise ValueError(
                'Could not find any projects. Are you sure the script'
                'has all the needed permissions to run?'
            )

        info = ''
        for k, v in sg.info().items():
            info += f'{k}: {v}'
            info += '\n'

    common.show_message(
        'Successfully connected to ShotGrid.',
        body=info
    )


@common.error
@common.debug
def create_entity(
        entity_type, entity_name, request_data=None, create_data=None,
        verify_bookmark=True, verify_all=False
):
    """Creates a new ShotGrid entity linked to the currently active  project.

    """
    sg_properties = shotgun.SGProperties(active=True)
    sg_properties.init()

    if not sg_properties.verify(connection=True):
        raise RuntimeError('Bookmark not configured.')

    if verify_bookmark:
        if not sg_properties.verify(bookmark=True):
            raise RuntimeError('Bookmark not configured.')
    if verify_all:
        if not sg_properties.verify():
            raise RuntimeError('Bookmark not configured.')

    if request_data is None:
        request_data = [
            ['project', 'is', {
                'type': 'Project',
                'id': sg_properties.bookmark_id
            }],
        ]
    if create_data is None:
        create_data = {
            'project': {
                'type': 'Project',
                'id': sg_properties.bookmark_id
            },
            'code': entity_name,
        }

    with sg_properties.connection() as sg:
        # We won't allow creating duplicate entites. So. Let's
        # check for before we move on:
        entities = sg.find(entity_type, request_data, fields=shotgun.entity_fields[entity_type])

        for entity in entities:
            def has(k):
                return k in entity and entity[k].lower() == entity_name.lower()

            # Check for duplicates
            if has('name') or has('code') or has('contents'):
                raise ValueError(f'{entity_name} exists already.')

        # We're in the clear, let's create the entity
        entity = sg.create(
            entity_type,
            create_data,
            return_fields=shotgun.entity_fields[entity_type]
        )

    if not entity:
        raise RuntimeError('Unknown error creating entity.')

    return entity


@common.error
@common.debug
def create_project(server, job, root, entity_name):
    """Creates a new ShotGrid entity linked to the currently active  project.

    """
    sg_properties = shotgun.SGProperties(server, job, root)
    sg_properties.init()
    if not sg_properties.verify(connection=True):
        raise ValueError('Bookmark not configured.')

    with sg_properties.connection() as sg:
        # We won't allow creating duplicate entities. So. Let's
        # check for before we move on:
        entities = sg.find(
            'Project', [
                ['is_demo', 'is', False],
                ['is_template', 'is', False],
                ['is_template_project', 'is', False],
                ['archived', 'is', False],
            ], fields=shotgun.entity_fields['Project']
        )

        for entity in entities:
            def has(k):
                return k in entity and entity[k].lower() == entity_name.lower()

            # Check for duplicates
            if has('name'):
                raise ValueError(f'{entity_name} exists already.')

        # We're in the clear, let's create the entity
        entity = sg.create(
            'Project',
            {
                'name': entity_name,
            },
            return_fields=shotgun.entity_fields['Project']
        )

    if not entity:
        raise RuntimeError('Unknown error creating entity.')

    return entity


@common.error
@common.debug
def save_entity_data_to_db(server, job, root, source, table, entity, value_map):
    """Save the selected entity data to the Bookmark Database.

    """
    if not entity:
        raise ValueError('Invalid entity value')

    s = source
    t = table
    db = database.get(server, job, root)
    with db.connection():

        # Let's iterate over the value map dictionary to extract data from the
        # entity and save it into our bookmark database
        for k, v in value_map.items():
            # Just in case the value map describes a column the entity is
            # missing, let's skip it alltogether
            if v['column'] not in entity:
                continue

            _v = entity[v['column']]
            if not isinstance(_v, v['type']) and _v is not None:
                try:
                    _v = v['type'](_v)
                except:
                    from .. import log
                    log.error(__name__, 'Type conversion failed.')
                    continue

            # If 'overwrite' is `True`, no matter what, we'll overwrite the
            # current database value
            if v['overwrite']:
                db.set_value(s, k, _v, t)
                continue

            # Nothing to do if there's overwrite is False, and the entity does
            # not contain data
            if not _v:
                continue

            # Entity has data, and we have nothing set currently in our database
            cval = db.value(s, k, t)
            if not cval and _v:
                db.set_value(s, k, _v, t)


def get_status_codes(sg):
    """Returns a list of status codes available in the current context.

    """
    sg_properties = shotgun.SGProperties(active=True)
    sg_properties.init()
    if not sg_properties.verify():
        return []

    schema = sg.schema_field_read('Version')
    if not schema:
        return []

    # Check data integrity before proceeding
    k = 'sg_status_list'
    if k not in schema or not schema[k]:
        return []
    v = schema[k]

    k = 'properties'
    if k not in v or not v[k]:
        return []
    v = v[k]

    k = 'valid_values'
    if k not in v or not v[k]:
        return []
    v = v[k]

    k = 'value'
    if k not in v or not v[k]:
        return []
    v = v[k]

    entities = []
    for code in v:
        entity = sg.find_one(
            'Status',
            [
                ['code', 'is', code]
            ],
            fields=shotgun.entity_fields['Status']
        )
        if not entity:
            continue
        entities.append(entity)

    # Let's find out the default and mark the item as such
    v = schema['sg_status_list']['properties']['default_value']['value']
    for entity in entities:
        if entity['code'] == v:
            entity['default'] = True
        else:
            entity['default'] = False

    return entities


def create_published_file(
        sg,
        version_entity,
        name,
        file_name,
        file_path,
        version,
        description,
        project_entity,
        asset_entity,
        user_entity,
        task_entity,
        published_file_type_entity,
        local_storage_entity
):
    """Creates a new PublishedFile entity on ShotGrid.

    The data structure was taken from the ShotGrid API documentation
    https://developer.shotgunsoftware.com/tk-core/_modules/tank/util/shotgun/publish_creation.html#register_publish

    """
    create_data = {
        'name': name,  # name excluding version number
        'code': file_name,  # name including version number
        'version_number': version,
        'description': description,
        'project': project_entity,
        'entity': asset_entity,
        'created_by': user_entity,
        'task': task_entity,
        'published_file_type': published_file_type_entity,
        'version': version_entity,
        'path': {
            'content_type': None,
            'link_type': 'local',
            # OS native path separators
            'local_path': os.path.normpath(os.path.abspath(file_path)),
            'local_path_linux': shotgun.sanitize_path(file_path, '/'),
            'local_path_mac': shotgun.sanitize_path(file_path, '/'),
            'local_path_windows': shotgun.sanitize_path(file_path, '\\'),
            'local_storage': local_storage_entity,
            'name': file_name,
            'url': QtCore.QUrl.fromLocalFile(file_path).toString(
                options=QtCore.QUrl.FullyEncoded
            )
        },
        'path_cache': file_path.replace(common.active('server'), '').strip('/'),
    }

    entity = sg.create(
        'PublishedFile',
        create_data,
        return_fields=shotgun.entity_fields['PublishedFile']
    )
    return entity


def upload_movie(sg, version_entity, version_movie, num_tries=3):
    """Upload a movie file for the given version."""
    n = -1
    while True:
        n += 1
        try:
            return sg.upload(
                'Version',
                version_entity['id'],
                version_movie,
                field_name='sg_uploaded_movie',
                display_name=QtCore.QFileInfo(version_movie).fileName(),
            )
        except:
            if n == num_tries:
                raise


def create_version(
        sg,
        file_name,
        file_path,
        version_movie,
        version_sequence,
        version_cache,
        description,
        project_entity,
        asset_entity,
        task_entity,
        user_entity,
        status_entity,
):
    """Add a new Version entity to ShotGrid."""
    if not version_cache:
        version_cache = file_path

    # Check status
    k = 'code'
    if status_entity and k in status_entity and status_entity[k]:
        status = status_entity[k]
    else:
        status = None

    data = {
        'code': file_name,
        'project': project_entity,
        'entity': asset_entity,
        'sg_task': task_entity,
        'tasks': [task_entity, ],
        'user': user_entity,
        'description': description,
        'sg_status_list': status,
        'sg_path_to_movie': version_movie,
        'sg_path_to_frames': version_sequence,
        'sg_path_to_geometry': version_cache,
    }
    version_entity = sg.create(
        'Version',
        data,
        return_fields=shotgun.entity_fields['Version']
    )

    if not version_entity:
        return None

    return version_entity
