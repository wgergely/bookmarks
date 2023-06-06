"""Contains various utility methods, and :func:`.convert()`, the main method used
to convert a source image sequence to a movie file using an external FFMPEG binary.

The FFMpeg ui elements are defined at
:class:`bookmarks.external.ffmpeg_widget.FFMpegWidget`.

"""
import os
import re
import string
import subprocess

from PySide2 import QtCore, QtWidgets

from .. import common
from .. import database
from .. import images
from .. import ui


class SafeDict(dict):
    """Utility class.

    """

    def __missing__(self, key):
        return '{' + key + '}'


def _safe_format(s, **kwargs):
    return string.Formatter().vformat(s, (), SafeDict(**kwargs))


H264HQ = 0
H264LQ = 1
DNxHD90 = 2

_preset_info = ', drawtext=fontfile={FONT}:text=\'{' \
               'LABEL}%{{frame_num}}\':start_number={' \
               'STARTFRAME}:x=lh:y=h-(lh*2.5):fontcolor=white:fontsize=ceil(' \
               'w/80):box=1:boxcolor=black:boxborderw=14'

_preset_x264 = '\
"{BIN}" \
-y \
-hwaccel auto \
-framerate {FRAMERATE} \
-start_number {STARTFRAME} \
-i "{INPUT}" \
-r {FRAMERATE} \
-c:v h264 \
-preset {PRESET} \
-tune animation \
-colorspace bt709 \
-color_primaries bt709 \
-color_trc gamma22 \
-threads 0 \
-movflags +faststart \
-vf "format=yuv420p, \
scale=ceil({WIDTH}/2)*2:ceil(({WIDTH}*(min(iw\,ih)/max(iw\,ih)))/2)*2, \
setsar=1/1, \
pad={WIDTH}:{HEIGHT}:0:(max({HEIGHT}\,oh)-min({HEIGHT}\,oh))/2:black\
{TIMECODE}" \
"{OUTPUT}"\
'

_preset_dnxhd = '\
"{BIN}" \
-y \
-hwaccel auto \
-framerate {FRAMERATE} \
-start_number {STARTFRAME} \
-i "{INPUT}" \
-r {FRAMERATE} \
-c:v dnxhd \
-b:v {BITRATE} \
-color_range 2 \
-colorspace bt709 \
-color_primaries bt709 \
-color_trc gamma22 \
-threads 0 \
-movflags +faststart \
-vf "format=yuv422p, \
fifo, \
colormatrix=bt601:bt709, \
scale=ceil({WIDTH}/2)*2:ceil(({WIDTH}*(min(iw\,ih)/max(iw\,ih)))/2)*2, \
setsar=1/1, \
pad={WIDTH}:{HEIGHT}:0:({HEIGHT}-(ceil(({WIDTH}*(min(iw\,ih)/max(iw\,' \
                'ih)))/2)*2))/2:black\
{TIMECODE}" \
"{OUTPUT}"\
'

SIZE_PRESETS = {
    0: {
        'name': 'Original',
        'value': (None, None)
    },
    1: {
        'name': '720p',
        'value': (1280, 720)
    },
    2: {
        'name': '1080p',
        'value': (1920, 1080)
    },
    3: {
        'name': f'{int(1080 * 1.5)}p',
        'value': (1920 * 1.5, 1080 * 1.5)
    },
    4: {
        'name': f'{int(1080 * 2)}p',
        'value': (1920 * 2, 1080 * 2)
    },
}

PRESETS = {
    H264HQ: {
        'name': 'H.264 | MP4 | HQ',
        'description': 'Creates a H.264 video, can be used to preview or publish '
                       'image sequence previews',
        'preset': _safe_format(
            _preset_x264,
            PRESET='slower'
        ),
        'output_extension': 'mp4',
    },
    H264LQ: {
        'name': 'H.264 | MP4 | LQ',
        'description': 'Creates a H.264 video, can be used to preview or publish '
                       'image sequence previews',
        'preset': _safe_format(
            _preset_x264,
            PRESET='medium'
        ),
        'output_extension': 'mp4'
    },
    DNxHD90: {
        'name': 'DNxHD | MOV | 1080p (90Mbps)',
        'description': 'DNxHD video for Avid - output size must be set to 1080p',
        'preset': _safe_format(
            _preset_dnxhd,
            BITRATE='90M'
        ),
        'output_extension': 'mov'
    },
}

SHOT = 0
ASSET = 1


def _get_font_path():
    """Return the path to the font used to label the generated files.
    The method also takes care of returning the path in a format that ffmpeg
    can consume.

    Returns:
        str: path to the font file used to label the generated files.

    """
    v = common.rsc(f'fonts/{common.medium_font}.ttf')
    v = v.replace(':', '\\:').replace('\\', '\\\\').replace('\\\\:', '\\:')
    return f'\'{v}\''


def _get_sequence_start_end(path):
    """Utility method for returning the first and last frames of a sequence.

    Args:
        path (str): Path to the sequence.

    Returns:
        tuple: The sequence, and first and last frames.

    """
    ext = path.split('.')[-1]
    path = path.replace('\\', '/')
    if common.is_collapsed(path):
        path = common.get_sequence_start_path(path)

    seq = common.get_sequence(path)
    if not seq:
        raise RuntimeError(f'{path} is not a sequence.')

    _dir = QtCore.QFileInfo(path).dir()
    if not _dir.exists():
        raise RuntimeError(f'{_dir} does not exists.')

    f = []
    for entry in os.scandir(_dir.path()):
        _path = entry.path.replace('\\', '/')
        if not _path.endswith(ext):
            continue
        if not seq.group(1) in _path:
            continue
        _seq = common.get_sequence(_path)
        if not _seq:
            continue
        f.append(int(_seq.group(2)))
    if not f:
        raise RuntimeError(
            'Could not find the first frame of the sequence.'
        )

    return seq, min(f), max(f)


def _input_path_from_seq(seq):
    """Returns an input path from a sequence that ffmpeg can recognize.

    TODO: Currently does not work with non-sequential images.

    Returns:
        str: Path to an image file.

    """
    return os.path.normpath(
        f'{seq.group(1)}%0{len(seq.group(2))}d{seq.group(3)}.{seq.group(4)}'
    )


def _output_path_from_seq(seq, ext):
    """Return preformatted output path for ffmpeg.

    """
    return f'{seq.group(1).rstrip(".").rstrip("_").rstrip()}.{ext}'


def _get_framerate(server, job, root, fallback_framerate=24.0):
    """Get the currently set frame-rate from the bookmark item database.

    Returns:
        float: The current framerate.

    """
    db = database.get_db(server, job, root)
    v = db.value(
        db.source(),
        'framerate',
        database.BookmarkTable
    )

    if not v:  # use the fallback value when not set
        return fallback_framerate
    return v


def _get_info_label(timecode_preset, output_path, in_frame, out_frame):
    """Construct an informative label when converting using the information label.

    This is the text the gets stamped onto the generated movie file.

    Returns:
        str: An informative label describing the movie file.

    """
    if not timecode_preset:
        raise RuntimeError('No timecode preset set.')

    version = re.search(r'v\d{1,4}', output_path)
    version = version.group(0) if version else 'No version'
    sequence, shot = common.get_sequence_and_shot(output_path)

    sequence = sequence if sequence else '###'
    shot = shot if shot else '####'

    ext = QtCore.QFileInfo(output_path).suffix()

    from ..tokens import tokens
    config = tokens.get(*common.active('root', args=True))

    v = config.expand_tokens(
        timecode_preset,
        asset=common.active('asset'),
        version=version,
        task=common.active('task'),
        sh=shot,
        shot=shot,
        sq=sequence,
        seq=sequence,
        sequence=sequence,
        ext=ext,
        in_frame=in_frame,
        out_frame=out_frame,
    )

    # replace any non-alphanumeric characters in timecode_preset with the character prefixed by '\\'
    # this is to prevent ffmpeg from interpreting the characters as special characters
    v = re.sub(r'([^\w])', r'\\\1', v)

    return f'{v} \\| '


@common.error
@common.debug
def convert(
        path, preset, server=None, job=None, root=None, asset=None, task=None,
        size=(None, None), timecode=False, timecode_preset=None, output_path=None, parent=None
):
    """Start a convert process using ffmpeg.

    Args:
        path (str): Path to image file to convert.
        preset (str): An ffmpeg preset.
        server (str): `server` path segment.
        job (str): `job` path segment.
        root (str): `root` path segment.
        asset (str): `asset` path segment.
        task (str): `task` path segment.
        size (tuple(int, int)): The output video width in pixels.
        timecode (bool): Add an informative timecode stamp when `True`.
        output_path (str): Video output path.

    Returns:
        str: The path to the generated movie file or `None` when the process fails.

    Raises:
        RuntimeError: If the input path is not a sequence or not found.

    """
    common.check_type(path, str)
    common.check_type(preset, str)
    common.check_type(server, (str, None))
    common.check_type(job, (str, None))
    common.check_type(root, (str, None))
    common.check_type(asset, (str, None))
    common.check_type(task, (str, None))
    common.check_type(size, (tuple, None))
    common.check_type(output_path, (str, None))

    # First, let's check if FFMPEG is available.
    ffmpeg_bin = common.get_binary('ffmpeg')
    if not ffmpeg_bin:
        raise RuntimeError('Could not find FFMpeg binary.')
    if not QtCore.QFileInfo(ffmpeg_bin).exists():
        raise RuntimeError('FFMpeg is set but the file does not exist.')
    ffmpeg_bin = os.path.normpath(ffmpeg_bin)

    server = server if server else common.active('server')
    job = job if job else common.active('job')
    root = root if root else common.active('root')
    asset = asset if asset else common.active('asset')
    task = task if task else common.active('task')

    if not all((server, job, root, asset, task)):
        raise RuntimeError('Not all required active items are set.')

    seq, startframe, endframe = _get_sequence_start_end(path)
    ext = next(
        PRESETS[f]['output_extension'] for f in PRESETS
        if PRESETS[f]['preset'] == preset
    )
    output_path = output_path if output_path else _output_path_from_seq(seq, ext)

    # Let's use the input image size if not specified directly
    if not all(size):
        buf = images.ImageCache.get_buf(common.get_sequence_start_path(path))
        spec = buf.spec()
        width = spec.width
        height = spec.height
    else:
        width, height = size

    if timecode and not timecode_preset:
        raise RuntimeError('Timecode preset not specified.')

    if timecode:
        tc = _preset_info.format(
            FONT=_get_font_path(),
            LABEL=_get_info_label(timecode_preset, output_path, startframe, endframe),
            STARTFRAME=startframe
        )
    else:
        tc = ''

    # Get all properties and construct the ffmpeg command
    cmd = preset.format(
        BIN=ffmpeg_bin,
        FRAMERATE=_get_framerate(server, job, root),
        STARTFRAME=startframe,
        INPUT=_input_path_from_seq(seq),
        OUTPUT=output_path,
        WIDTH=width,
        HEIGHT=height,
        TIMECODE=tc
    )

    with subprocess.Popen(
            cmd,
            bufsize=1,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
    ) as proc:

        pbar = ui.get_progress_bar(
            'Making Video',
            'Processing images...',
            startframe,
            endframe,
            parent=parent
        )

        pbar.open()
        QtWidgets.QApplication.instance().processEvents()

        lines = []

        while proc.poll() is None:
            if pbar.wasCanceled():
                proc.kill()
                pbar.close()
                return None

            line = proc.stdout.readline()
            if not line:
                continue
            lines.append(line)

            match = re.search(
                r'.*frame=.*?([0-9]+)', line.strip(), flags=re.IGNORECASE
            )
            if not match:
                continue

            pbar.setValue(int(match.group(1)))
            QtWidgets.QApplication.instance().processEvents()

        pbar.close()
        # Verify the output
        if proc.returncode == 1:
            with open(f'{output_path}.log', 'w', encoding='utf-8') as f:
                f.write(cmd)
                f.write('\n\n')
                f.write('\n'.join(lines))

            ui.ErrorBox(
                'An error occurred converting.',
                '\n'.join(lines[-5:])
            ).open()
            return None

    return output_path
