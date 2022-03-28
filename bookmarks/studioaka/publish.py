import re
import time

from PySide2 import QtCore, QtWidgets
from akapipe.core import database as akadatabase
from akapipe.core import db as akadb
from akapipe.core import templates as akatemplates

from . import base
from .. import actions, log
from .. import common
from .. import database
from .. import images
from .. import ui
from ..external import ffmpeg

AnimPublish = 0
CompPublish = 1

PRESETS = {
    AnimPublish: {
        'name': 'Work in Progress',
        'token': akatemplates.AV_AnimationPublish,
        'formats': (
            'png',
            'jpg',
        ),
    },
    CompPublish: {
        'name': 'Comp & Final',
        'token': akatemplates.AV_CompPublish,
        'formats': (
            'png',
            'jpg',
            'exr',
            'tif',
        ),
    },
}


def get_stamp_text(publish_type, source=None):
    v = 'Published on {time} by {user} to {publish_type}'.format(
        time=time.strftime('%d/%m/%Y %H:%M:%S'),
        publish_type=publish_type,
        user=common.get_username(),
    )
    if source:
        v += '\n Source:\n{}'.format(source)

    return v


@common.error
@common.debug
def stamp_publish(server, job, root, stamp_path, source, publish_type):
    # Write stamp file to publish dir
    with open(stamp_path, 'w') as f:
        v = get_stamp_text(publish_type, source=source)
        f.write(v)

    # Save the stamp info in the bookmark database
    db = database.get_db(server, job, root)
    common.proxy_path(source)
    with db.connection():
        db.setValue(
            common.proxy_path(source),
            'description',
            get_stamp_text(publish_type),
            table=database.AssetTable
        )


def get_progress_bar(frames):
    pbar = QtWidgets.QProgressDialog()
    common.set_stylesheet(pbar)
    pbar.setFixedWidth(common.size(common.DefaultWidth))
    pbar.setLabelText('Publishing files...')
    pbar.setMinimum(1)
    pbar.setMaximum(len(frames))
    pbar.setRange(1, len(frames))
    return pbar


def publish_footage(
        preset,
        source,
        frames,
        seq=None,
        shot=None,
        server=None,
        job=None,
        root=None,
        asset=None,
        task=None,
        make_movie=True,
        add_timecode=None,
        video_size=None,
        ffmpeg_preset=None,
        copy_path=True,
        reveal_publish=True,
):
    """Our footage publish script.

    Args:
        ref (weakref):  A reference to an item's data.
        publish_type (unicode):  The publish type.
        reveal (bool):  Show the publish folder in the file explorer.

    """
    is_collapsed = common.is_collapsed(source)
    if not is_collapsed:
        raise RuntimeError('Item is not a sequence.')
    if not frames:
        raise RuntimeError('Sequence seems to be empty.')

    ext = source.split('.')[-1]
    if make_movie and ext.lower() not in images.oiio_image_extensions:
        raise RuntimeError(f'{ext} is not a accepted image format.')

    # Let's check if the template file exists
    if not all((seq, shot)):
        seq, shot = base.get_seq_shot(source)
    if not all((seq, shot)):
        raise RuntimeError(
            'The item cannot be published because it is not in a shot folder.'
        )

    if ext.lower() not in PRESETS[preset]['formats']:
        raise RuntimeError('Not a valid publish format.')

    client, project = base.get_client_project()
    if not all((client, project)):
        raise RuntimeError(
            'Could not get the client and project names from the the current job.'
        )

    destination = akatemplates.expand_token(
        PRESETS[preset]['token'],
        PR_NetworkPath=server,
        client=client,
        project=project,
        sequence=seq,
        shot=shot,
    )

    if not QtCore.QFileInfo(destination).exists():
        if not QtCore.QDir(destination).mkpath('.'):
            raise RuntimeError(f'Could not create {destination}.')

    # Get the publish type from the path
    regex = r'|'.join(akatemplates.tokens[f] for f in akatemplates.publish_types)
    publish_type = re.search(regex, destination).group(0)
    publish_type = re.sub(r'[0-9_-]+', '', publish_type)

    # Initialize the aka database and get the client and project prefixes
    akadatabase.init_table_data(akadb.CL)
    akadatabase.init_table_data(akadb.PR)
    cl_abbrev = akadatabase.get_value(akadb.CL, client, akadb.CL_Abbreviation)
    pr_abbrev = akadatabase.get_value(akadb.PR, project, akadb.PR_Abbreviation)

    padding = akatemplates.tokens[akatemplates.AV_PublishSequenceFile].count('#')

    frames = sorted(frames, key=lambda x: int(x))

    pbar = get_progress_bar(frames)
    pbar.open()
    for idx, frame in enumerate(frames, 1):
        if pbar.wasCanceled():
            break
        pbar.setValue(idx)
        QtWidgets.QApplication.instance().processEvents()

        source_frame = f'{is_collapsed.group(1)}{frame}{is_collapsed.group(3)}'

        _framename = akatemplates.expand_token(
            akatemplates.AV_PublishSequenceFile,
            CL_Abbreviation=cl_abbrev,
            PR_Abbreviation=pr_abbrev,
            publish_type=publish_type,
            sequence=seq,
            shot=shot,
            ext=ext,
        )
        _framename = re.sub(r'[#]+', str(int(idx)).zfill(padding), _framename)
        destination_frame = f'{destination}/{_framename}'

        # Make thumbnail
        try:
            if idx == 1:
                # Now let's create a thumbnail for this publish
                images.ImageCache.oiio_make_thumbnail(
                    source_frame,
                    f'{destination}/thumbnail.png',
                    common.thumbnail_size
                )
        except:
            log.error('Could not make thumbnail.')

        # Create a movie
        if make_movie and idx == 1:
            try:
                movie_path = ffmpeg.convert(
                    source_frame,
                    ffmpeg_preset,
                    server=server,
                    job=job,
                    root=root,
                    asset=asset,
                    task=task,
                    size=video_size,
                    timecode=add_timecode
                )

                _moviename = akatemplates.expand_token(
                    akatemplates.AV_PublishFile,
                    CL_Abbreviation=cl_abbrev,
                    PR_Abbreviation=pr_abbrev,
                    publish_type=publish_type,
                    sequence=seq,
                    shot=shot,
                    ext=next(
                        v['output_extension'] for v in ffmpeg.PRESETS.values()
                        if v['preset'] == ffmpeg_preset
                    ),
                )

                destination_movie = f'{destination}/{_moviename}'
                destination_movie_file = QtCore.QFile(destination_movie)
                if destination_movie_file.exists():
                    if not destination_movie_file.remove():
                        raise RuntimeError('Could not remove movie file')
                if movie_path and not QtCore.QFile.copy(movie_path, destination_movie):
                    log.error(f'Could copy {movie_path}')

                if copy_path:
                    actions.copy_path(
                        destination_movie,
                        mode=common.WindowsPath
                    )
            except Exception as e:
                log.error('Failed to make movie.')

        destination_file = QtCore.QFile(destination_frame)
        # The actual copy operation
        if destination_file.exists():
            if not destination_file.remove():
                log.error(f'Could not remove {destination_frame}')

        QtCore.QFile.copy(source_frame, destination_frame)

    # Stamp the publish so we can backtrace if needed
    try:
        stampname = akatemplates.expand_token(
            akatemplates.AV_PublishFile,
            CL_Abbreviation=cl_abbrev,
            PR_Abbreviation=pr_abbrev,
            publish_type=publish_type,
            sequence=seq,
            shot=shot,
            ext='txt',
        )
        stamp_publish(
            server, job, root,
            f'{destination}/{stampname}',
            source,
            publish_type
        )
    except Exception as e:
        log.error(e)


    try:
        from ..teams import message

        db = database.get_db(server, job, root)
        webhook = db.value(db.source(), 'teamstoken', database.BookmarkTable)

        if webhook:
            payload = message.get_payload(
                message.PUBLISH_MESSAGE,
                thumbnail=f'{destination}/thumbnail.png',
                seq=seq,
                shot=shot,
                path=destination,
                date=time.strftime('%d/%m/%Y %H:%M:%S'),
                user=common.get_username(),
                publish_type=publish_type,
            )
            message.send(webhook, payload)

    except Exception as e:
        log.error(e)

    if copy_path:
        ui.OkBox(
            'Item published successfully.',
            'The path to the published movie file has been copied to the clipboard.'
        ).open()
    else:
        ui.OkBox(
            'Item published successfully.'
        ).open()

    if reveal_publish:
        actions.reveal(destination)
