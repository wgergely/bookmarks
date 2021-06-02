# -*- coding: utf-8 -*-
"""Common FFMpeg functionality."""
import re
import os
from datetime import datetime
import subprocess
import functools
import string

import _scandir
from PySide2 import QtCore, QtWidgets

from . import log
from . import common
from . import ui
from . import settings
from . import bookmark_db


class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


def _format(s, **kwargs):
    return string.Formatter().vformat(s, (), SafeDict(**kwargs))


VIDEOFILTER = '-vf "pad=ceil(iw/2)*2:ceil(ih/2)*2, drawtext=fontfile={FONT}: text=\'{LABEL} %{{frame_num}}\': start_number={STARTFRAME}: x=10: y=h-lh-10: fontcolor=white: fontsize=ceil(h/40): box=1: boxcolor=black: boxborderw=10" '

BASE_H264_PRESET = '\
"{BIN}" \
-y \
-hwaccel auto \
-framerate {FRAMERATE} \
-start_number {STARTFRAME} \
-gamma 2.2 \
-i "{INPUT}" \
{VIDEOFILTER}\
-c:v libx264 \
-b:v {BITRATE} \
-maxrate {BITRATE} \
-minrate {BITRATE} \
-bufsize {BITRATE} \
-profile:v main \
-sc_threshold 0 \
-preset slow \
-tune animation \
-g 10 \
-x264-params colormatrix=bt709 \
-pix_fmt yuv420p \
-colorspace bt709 \
-color_primaries bt709 \
-color_trc gamma22 \
-map 0:v:0? \
-c:s mov_text \
-map 0:s? \
-an \
-map_metadata 0 \
-f mp4 \
-threads 0 \
-movflags +faststart \
"{OUTPUT}"\
'



PRESETS = {
    0: {
        'name': u'Image Sequence to MP4 (with timecode)',
        'preset': _format(
                BASE_H264_PRESET,
                VIDEOFILTER=VIDEOFILTER,
                BITRATE=u'25000k',
            )
        },
    1: {
        'name': u'Image Sequence to MP4',
        'preset': _format(
                BASE_H264_PRESET,
                VIDEOFILTER='',
                BITRATE=u'25000k',
            )
    },
}



def get_font_path(name='bmRobotoMedium'):
    """The font used to label the generated files."""
    font_file = __file__ + os.path.sep + os.path.pardir + os.path.sep + \
        'rsc' + os.path.sep + 'fonts' + os.path.sep + '{}.ttf'.format(name)
    font_file = os.path.abspath(os.path.normpath(font_file))
    # needed for ffmpeg
    font_file = font_file.replace(u':', u'\\:').replace(u'\\', u'\\\\').replace(u'\\\\:', u'\\:')
    return '\'{}\''.format(font_file)


@common.error
@common.debug
def launch_ffmpeg_command(input, preset, server=None, job=None, root=None, asset=None, task=None):
    """Calls FFMpeg to process an input using the given preset.

    """
    FFMPEG_BIN = common.get_path_to_executable(settings.FFMpegKey)
    if not FFMPEG_BIN:
        raise RuntimeError('FFMPEG not set or found.')
    if not QtCore.QFileInfo(FFMPEG_BIN).exists():
        raise RuntimeError('FFMPEG set but not found.')

    server = server if server else settings.active(settings.ServerKey)
    job = job if job else settings.active(settings.JobKey)
    root = root if root else settings.active(settings.RootKey)
    asset = asset if asset else settings.active(settings.AssetKey)
    task = task if task else settings.active(settings.TaskKey)

    input = input.replace(u'\\', u'/')

    # We want to get the first item  of any sequence
    if common.is_collapsed(input):
        input = common.get_sequence_startpath(input)
    else:
        seq = common.get_sequence(input)
        if not seq:
            raise RuntimeError(u'{} is not a sequence.'.format(input))
        _dir = QtCore.QFileInfo(input).dir()
        if not _dir.exists():
            raise RuntimeError(u'{} does not exists.'.format(_dir))

        f = []
        for entry in _scandir.scandir(_dir.path()):
            _path = entry.path.replace(u'\\', u'/')
            if not seq.group(1) in _path:
                continue
            _seq = common.get_sequence(_path)
            if not _seq:
                continue
            f.append(int(_seq.group(2)))
        if not f:
            raise RuntimeError(
                u'Could not find the first frame of the sequence.')

    startframe = min(f)
    endframe = max(f)

    # Framerate
    db = bookmark_db.get_db(server, job, root)
    framerate = db.value(
        db.source(),
        u'framerate',
        table=bookmark_db.BookmarkTable
    )

    if not framerate:
        framerate = 24

    input = (
        seq.group(1) +
        u'%0{}d'.format(len(seq.group(2))) +
        seq.group(3) +
        u'.' +
        seq.group(4)
    )
    output = seq.group(1).rstrip(u'.').rstrip(u'_').rstrip() + u'.mp4'

    # Add informative label
    label = u''
    if job:
        label += job
        label += u'_'
    if asset:
        label += asset
        label += u'_'
    if task:
        label += task
        label += u' \\| '
    vseq = common.get_sequence(output)
    if vseq:
        label += 'v' + vseq.group(2) + u' '
        label += datetime.now().strftime('(%a %d/%m/%Y %H\\:%M) \\| ')
    label += u'{}-{} \\| '.format(startframe, endframe)

    cmd = preset.format(
        BIN=FFMPEG_BIN,
        FRAMERATE=framerate,
        STARTFRAME=startframe,
        INPUT=os.path.normpath(input),
        OUTPUT=os.path.normpath(output),
        FONT=get_font_path(),
        LABEL=label,
    )

    pbar = QtWidgets.QProgressDialog()
    common.set_custom_stylesheet(pbar)
    pbar.setFixedWidth(common.WIDTH())
    pbar.setLabelText(u'FFMpeg is converting, please wait...')
    pbar.setMinimum(int(startframe))
    pbar.setMaximum(int(endframe))
    pbar.setRange(int(startframe), int(endframe))
    pbar.setWindowTitle('FFMpeg Convert Progress')
    pbar.open()

    cmatch = re.compile(r'frame=.+?([0-9]+).+?fps.*')
    proc = subprocess.Popen(
        cmd,
        bufsize=1,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    while proc.poll() is None:
        QtWidgets.QApplication.instance().processEvents()

        if pbar.wasCanceled():
            proc.kill()
            pbar.close()
            break

        line = proc.stdout.readline()
        if not line:
            continue

        match = cmatch.match(line)
        if not match:
            continue

        pbar.setValue(int(match.group(1)))

    return os.path.normpath(output)
