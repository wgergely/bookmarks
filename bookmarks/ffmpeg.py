# -*- coding: utf-8 -*-
"""Common FFMpeg functionality."""

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


VIDEOFILTER = '-vf "pad=ceil(iw/2)*2:ceil(ih/2)*2, drawtext=fontfile={FONT}: text=\'{LABEL}%{{frame_num}}\': start_number={STARTFRAME}: x=10: y=h-lh-10: fontcolor=white: fontsize=ceil(h/40): box=1: boxcolor=black: boxborderw=10" '

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
        'name': u'Image Sequence to mp4 with Timecode',
        'preset': _format(
                BASE_H264_PRESET,
                VIDEOFILTER=VIDEOFILTER,
                BITRATE=u'25000k',
            )
        },
    1: {
        'name': u'Image Sequence to mp4',
        'preset': _format(
                BASE_H264_PRESET,
                VIDEOFILTER='',
                BITRATE=u'25000k',
            )
    },
}



def convert_progress(func):
    """Decorator to create a menu set."""
    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):

        # Open progress popup
        w = ui.MessageBox(u'Converting...', u'Should not take too long, please wait.', no_buttons=True)
        w.open()
        QtWidgets.QApplication.instance().processEvents()

        try:
            output = func(*args, **kwargs)
            if output:
                log.success(u'Successfully saved {}'.format(output))
                ui.OkBox(u'Finished converting', u'Saved to {}'.format(output)).open()
                common.signals.fileAdded.emit(output)
                return output
        except:
            raise
        finally:
            w.close()

    return func_wrapper



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
@convert_progress
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
        label += datetime.now().strftime('(%a %d/%m/%Y %H:%M) \\| ')
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
    print cmd
    subprocess.check_output(cmd, shell=True)
    return os.path.normpath(output)
