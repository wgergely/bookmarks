# -*- coding: utf-8 -*-
"""Common FFMpeg functionality."""
import os
import re
from datetime import datetime
import subprocess
import string


from PySide2 import QtCore, QtWidgets

from .. import images
from .. import ui
from .. import common

from .. import database


PROGRESS_MATCH = re.compile(r'frame=.+?([0-9]+).+?fps.*')


class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


def _safe_format(s, **kwargs):
    return string.Formatter().vformat(s, (), SafeDict(**kwargs))


_preset_info = ', pad=ceil(iw/2)*2:ceil(ih/2)*2, drawtext=fontfile={FONT}:text=\'{LABEL}%{{frame_num}}\':start_number={STARTFRAME}:x=10:y=h-lh-10:fontcolor=white:fontsize=ceil(w/50):box=1:boxcolor=black:boxborderw=10'
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
-vf "format=yuv420p, scale={WIDTH}:{HEIGHT}{TIMECODE}" \
"{OUTPUT}"\
'


SIZE_PRESETS = {
    0: {
        'name': 'Original',
        'value': (None, None)
    },
    1: {
        'name': '1080p',
        'value': (1920, 1080)
    },
    2: {
        'name': '1620p',
        'value': (1920 * 1.5, 1080 * 1.5)
    },
    3: {
        'name': '2160p',
        'value': (1920 * 2, 1080 * 2)
    },
}


PRESETS = {
    0: {
        'name': 'H.264 | MP4 | HQ',
        'description': 'Creates a H.264 video, can be used to preview or publish image sequence previews',
        'preset': _safe_format(
            _preset_x264,
            PRESET='slower'
        ),
        'output_extension': 'mp4',
    },
    1: {
        'name': 'H.264 | MP4 | LQ',
        'description': 'Creates a H.264 video, can be used to preview or publish image sequence previews',
        'preset': _safe_format(
            _preset_x264,
            PRESET='medium'
        ),
        'output_extension': 'mp4'
    }
}


def _get_font_path():
    """Return the path to the font used to label the generated files.
    The method also takes care of returning the path in a format that ffmpeg
    can consume.

    """
    v = os.path.sep.join((__file__, os.path.pardir, os.path.pardir, 'rsc', 'fonts',
                          f'{common.medium_font}.ttf'))
    v = os.path.normpath(os.path.abspath(v))
    if not os.path.isfile(v):
        raise RuntimeError('Font could not be found.')

    v = v.replace(':', '\\:').replace('\\', '\\\\').replace('\\\\:', '\\:')
    return '\'{}\''.format(v)


def _get_sequence_start_end(path):
    """Utility method for returning the first and last frames of a sequence.

    Args:
        path (str): Path to the sequence.

    Returns:
        tuple: The sequence, and first and last frames.

    """
    path = path.replace('\\', '/')
    if common.is_collapsed(path):
        path = common.get_sequence_startpath(path)

    seq = common.get_sequence(path)
    if not seq:
        raise RuntimeError('{} is not a sequence.'.format(path))

    _dir = QtCore.QFileInfo(path).dir()
    if not _dir.exists():
        raise RuntimeError('{} does not exists.'.format(_dir))

    f = []
    for entry in os.scandir(_dir.path()):
        _path = entry.path.replace('\\', '/')
        if not seq.group(1) in _path:
            continue
        _seq = common.get_sequence(_path)
        if not _seq:
            continue
        f.append(int(_seq.group(2)))
    if not f:
        raise RuntimeError(
            'Could not find the first frame of the sequence.')

    return seq, min(f), max(f)


def _input_path_from_seq(seq):
    """Returns an input path from a sequence that ffmpeg can recognize.
    """
    return os.path.normpath(
        seq.group(1) +
        '%0{}d'.format(len(seq.group(2))) +
        seq.group(3) +
        '.' +
        seq.group(4)
    )


def _output_path_from_seq(seq, ext):
    """Return preformatted output path for ffmpeg.
    """
    return os.path.normpath(
        seq.group(1).rstrip('.').rstrip('_').rstrip() + '.' + ext
    )


def _get_framerate(server, job, root):
    """Get the currently set framerate from the bookmark database.
    """
    db = database.get_db(server, job, root)
    v = db.value(
        db.source(),
        'framerate',
        table=database.BookmarkTable
    )

    if not v:  # default framerate when not set
        return 24
    return v


def _get_info_label(job, asset, task, output_path, startframe, endframe):
    """Construct an informative label when converting using the information label.

    """
    v = ''
    if job:
        v += job
        v += ' \\| '
    if asset:
        v += asset
        v += ' \\| '
    if task:
        v += task
        v += ' \\| '
    vseq = common.get_sequence(output_path)
    if vseq:
        v += 'v' + vseq.group(2) + ' \\| '
        v += datetime.now().strftime('%a %d/%m/%Y %H\\:%M \\| ')
    v += '{}-{} '.format(startframe, endframe)
    return v


def _get_progress_bar(startframe, endframe):
    v = QtWidgets.QProgressDialog()
    common.set_custom_stylesheet(v)
    v.setFixedWidth(common.size(common.DefaultWidth))
    v.setLabelText('FFMpeg is converting, please wait...')
    v.setMinimum(int(startframe))
    v.setMaximum(int(endframe))
    v.setRange(int(startframe), int(endframe))
    v.setWindowTitle('Convert Progress')
    return v


@common.error
@common.debug
def convert(path, preset, server=None, job=None, root=None, asset=None, task=None, size=(None, None), ext='mp4', timecode=False):
    """Start a convert process using ffmpeg.

    Args:
        path (str): Path to image file to convert.
        preset (str): An ffmpeg preset.
        server (str): A path segment.
        job (str): A path segment.
        root (str): A path segment.
        asset (str): A path segment.
        task (str): A path segment.
        size (tuple(int, int)): The output video width in pixels.

    Raises:
        RuntimeError: If the path is not a sequence or not found.

    """
    common.check_type(path, str)
    common.check_type(preset, str)
    common.check_type(server, (str, None))
    common.check_type(job, (str, None))
    common.check_type(root, (str, None))
    common.check_type(asset, (str, None))
    common.check_type(task, (str, None))
    common.check_type(size, (tuple, None))

    # First, let's check if FFMPEG is available.
    FFMPEG_BIN = common.get_path_to_executable(common.FFMpegKey)
    if not FFMPEG_BIN:
        raise RuntimeError('Could not find FFMpeg binary.')
    if not QtCore.QFileInfo(FFMPEG_BIN).exists():
        raise RuntimeError('FFMpeg is set but the file does not exist.')
    FFMPEG_BIN = os.path.normpath(os.path.abspath(FFMPEG_BIN))

    server = server if server else common.active(common.ServerKey)
    job = job if job else common.active(common.JobKey)
    root = root if root else common.active(common.RootKey)
    asset = asset if asset else common.active(common.AssetKey)
    task = task if task else common.active(common.TaskKey)

    if not all((server, job, root, asset, task)):
        raise RuntimeError('Not all required active items are set.')

    seq, startframe, endframe = _get_sequence_start_end(path)
    output_path = _output_path_from_seq(seq, ext)

    # Let's use the input image size if not specified directly
    if not all(size):
        buf = images.oiio_get_buf(common.get_sequence_startpath(path))
        spec = buf.spec()
        width = spec.width
        height = spec.height
    else:
        width, height = size

    if timecode:
        tc = _preset_info.format(
            FONT=_get_font_path(),
            LABEL=_get_info_label(
                job, asset, task, output_path, startframe, endframe
            ),
            STARTFRAME=startframe
        )
    else:
        tc = ''

    # Get all properties and construct the ffmpeg command
    cmd = preset.format(
        BIN=FFMPEG_BIN,
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
        pbar = _get_progress_bar(startframe, endframe)
        pbar.open()

        lines = []

        while proc.poll() is None:
            QtWidgets.QApplication.instance().processEvents()

            if pbar.wasCanceled():
                proc.kill()
                pbar.close()
                break

            line = proc.stdout.readline()
            if not line:
                continue
            lines.append(line)

            match = PROGRESS_MATCH.match(line)
            if not match:
                continue

            pbar.setValue(int(match.group(1)))

        pbar.close()
        # Verify the output
        if proc.returncode == 1:
            with open(f'{output_path}.log', 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            ui.ErrorBox(
                'An error occured converting.',
                '\n'.join(lines[-5:])
            ).open()
            return False
        return True
