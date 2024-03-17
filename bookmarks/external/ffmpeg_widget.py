"""FFMpeg control widget used to convert a source image sequence to a movie.

"""
import functools
import os
import subprocess

import bookmarks_openimageio
try:
    from PySide6 import QtWidgets, QtGui, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtGui, QtCore

from . import ffmpeg
from .. import common
from .. import database
from .. import images
from .. import log
from .. import ui
from ..editor import base
from ..external import rv
from ..tokens import tokens


def close():
    """Closes the :class:`FFMpegWidget` editor.

    """
    if common.ffmpeg_export_widget is None:
        return
    try:
        common.ffmpeg_export_widget.close()
        common.ffmpeg_export_widget.deleteLater()
    except:
        pass
    common.ffmpeg_export_widget = None


def show(index):
    """Opens the :class:`FFMpegWidget` editor.

    Args:
        index (QModelIndex): The source image sequence index.

    Returns:
        QWidget: The FFMpegWidget instance.

    """
    close()
    common.ffmpeg_export_widget = FFMpegWidget(index)
    common.ffmpeg_export_widget.open()
    return common.ffmpeg_export_widget


class TimecodeModel(ui.AbstractListModel):
    """Template item picker model.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def init_data(self):
        """Initializes data.

        """
        config = tokens.get(*common.active('root', args=True))
        data = config.data()
        if not isinstance(data, dict):
            return

        # Add no-timecode option
        self._data[len(self._data)] = {
            QtCore.Qt.DisplayRole: 'No timecode',
            QtCore.Qt.DecorationRole: None,
            QtCore.Qt.SizeHintRole: self.row_size,
            QtCore.Qt.StatusTipRole: 'No timecode',
            QtCore.Qt.AccessibleDescriptionRole: 'No timecode',
            QtCore.Qt.WhatsThisRole: 'No timecode',
            QtCore.Qt.ToolTipRole: 'No timecode',
            QtCore.Qt.UserRole: None,
        }

        template = common.settings.value('ffmpeg/timecode_preset')
        for v in data[tokens.FFMpegTCConfig].values():
            if template == v['name']:
                icon = ui.get_icon(
                    'check', color=common.color(common.color_green), size=common.size(common.size_margin) * 2
                )
            else:
                icon = ui.get_icon(
                    'branch_closed', size=common.size(common.size_margin) * 2
                )

            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: v['name'],
                QtCore.Qt.DecorationRole: icon,
                QtCore.Qt.SizeHintRole: self.row_size,
                QtCore.Qt.StatusTipRole: v['description'],
                QtCore.Qt.AccessibleDescriptionRole: v['description'],
                QtCore.Qt.WhatsThisRole: v['description'],
                QtCore.Qt.ToolTipRole: v['description'],
                QtCore.Qt.UserRole: v['value'],
            }


class TimecodeComboBox(QtWidgets.QComboBox):
    """Timecode preset picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.setModel(TimecodeModel())


class PresetComboBox(QtWidgets.QComboBox):
    """FFMpeg preset picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        """Initializes data.

        """
        self.blockSignals(True)
        for v in ffmpeg.PRESETS.values():
            self.addItem(v['name'], userData=v['preset'])
        self.blockSignals(False)


class SizeComboBox(QtWidgets.QComboBox):
    """FFMpeg output size picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        self.init_data()

    def init_data(self):
        """Initializes data.

        """
        db = database.get(*common.active('root', args=True))
        bookmark_width = db.value(db.source(), 'width', database.BookmarkTable)
        bookmark_height = db.value(db.source(), 'height', database.BookmarkTable)
        asset_width = db.value(common.active('asset', path=True), 'asset_width', database.AssetTable)
        asset_height = db.value(common.active('asset', path=True), 'asset_height', database.AssetTable)

        width = asset_width or bookmark_width or None
        height = asset_height or bookmark_height or None

        if all((width, height)):
            self.addItem(f'Project | {int(height)}p', userData=(width, height))
            self.addItem(f'Project | {int(height * 0.5)}p', userData=(int(width * 0.5), int(height * 0.5)))

        self.blockSignals(True)
        for v in ffmpeg.SIZE_PRESETS.values():
            self.addItem(v['name'], userData=v['value'])

        self.blockSignals(False)


class FFMpegWidget(base.BasePropertyEditor):
    """Widget used to convert an image sequence to a video.

    """
    #: UI layout definition
    sections = {
        0: {
            'name': 'Convert Image Sequence to Video',
            'icon': 'convert',
            'color': common.color(common.color_dark_background),
            'groups': {
                0: {
                    0: {
                        'name': 'Preset',
                        'key': 'ffmpeg_preset',
                        'validator': None,
                        'widget': PresetComboBox,
                        'placeholder': None,
                        'description': 'Select the preset to use.',
                    },
                    1: {
                        'name': 'Size',
                        'key': 'ffmpeg_size',
                        'validator': None,
                        'widget': SizeComboBox,
                        'placeholder': None,
                        'description': 'Set the output video size.',
                    },
                    3: {
                        'name': 'Timecode preset',
                        'key': 'ffmpeg_timecode_preset',
                        'validator': None,
                        'widget': TimecodeComboBox,
                        'placeholder': None,
                        'description': 'Select the timecode preset to use.',
                    },
                    4: {
                        'name': 'Push to RV',
                        'key': 'ffmpeg_pushtorv',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Push to RV'),
                        'placeholder': None,
                        'description': 'Open the converted clip with RV.',
                    },
                },
            },
        },
    }

    def __init__(self, index, parent=None):
        super().__init__(
            None, None, None, fallback_thumb='convert', hide_thumbnail_editor=True, buttons=(
                'Convert', 'Cancel'), parent=parent
        )
        self._index = index
        self._connect_settings_save_signals(common.SECTIONS['ffmpeg'])

        self.setFixedWidth(common.size(common.size_width))
        self.setFixedHeight(common.size(common.size_height * 0.80))
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.FramelessWindowHint
        )

    @common.error
    @common.debug
    def init_data(self):
        """Initializes data.

        """
        self.load_saved_user_settings(common.SECTIONS['ffmpeg'])

    @common.debug
    @common.error
    def save_changes(self):
        """Saves changes.

        """
        index = self._index
        if not index.isValid():
            return False

        path = index.data(common.PathRole)
        if not path:
            return False

        is_collapsed = common.is_collapsed(path)
        if not is_collapsed:
            raise RuntimeError(f'{index.data(QtCore.Qt.DisplayRole)} is not a sequence.')

        frames = index.data(common.FramesRole)
        if not frames:
            raise RuntimeError(
                f'{index.data(QtCore.Qt.DisplayRole)} does not seem to have any frames.'
            )

        if len(frames) < 4:
            raise RuntimeError(
                f'{index.data(QtCore.Qt.DisplayRole)} is too short.'
            )

        # Check output video file
        seq = index.data(common.SequenceRole)
        preset = self.ffmpeg_preset_editor.currentData()
        ext = next(
            v['output_extension'] for v in ffmpeg.PRESETS.values() if v['preset'] == preset
        )

        if self.ffmpeg_timecode_preset_editor.currentData():
            destination = f'{seq.group(1).strip().strip("_").strip(".")}' \
                          f'{seq.group(3).strip().strip("_").strip(".")}_tc.' \
                          f'{ext}'
        else:
            destination = f'{seq.group(1).strip().strip("_")}' \
                          f'{seq.group(3).strip().strip("_")}' \
                          f'{ext}'

        _f = QtCore.QFile(destination)
        if _f.exists():
            if common.show_message(
                    'File already exists', f'{destination} already exists.\nDo you want to replace it with a new '
                                           f'version?', buttons=[common.YesButton,
                                                                 common.NoButton], message_type='error', modal=True,
            ) == QtWidgets.QDialog.Rejected:
                return False
            if not _f.remove():
                raise RuntimeError(f'Could not remove {destination}')

        common.show_message(
            'Preparing images...', body='Please wait while the frames are being converted. This might take a '
                                        'while...', message_type=None, disable_animation=True, buttons=[], )

        source_image_paths = self.preprocess_sequence()
        if not common.message_widget or common.message_widget.isHidden():
            return

        timecode_preset = self.ffmpeg_timecode_preset_editor.currentData()

        mov = ffmpeg.convert(
            source_image_paths[
                0], self.ffmpeg_preset_editor.currentData(), size=self.ffmpeg_size_editor.currentData(),
            timecode=bool(timecode_preset), timecode_preset=timecode_preset, output_path=destination, parent=self
        )

        for f in source_image_paths:
            images.ImageCache.flush(f)

        if not mov:
            common.close_message()
            raise RuntimeError('No movie file was saved.')

        if not QtCore.QFileInfo(mov).exists():
            common.close_message()
            raise RuntimeError(f'Could not find {mov}')

        common.widget(common.FileTab).show_item(
            destination, role=common.PathRole, update=True
        )

        if self.ffmpeg_pushtorv_editor.isChecked():
            try:
                rv.execute_rvpush_command(destination, rv.PushAndClear)
            except:
                log.error('Failed to push to RV.')

        common.show_message('Success', f'Movie saved to {destination}', message_type='success')
        log.success(f'Movie saved to {destination}')
        return True

    def preprocess_sequence(self, preconversion_format='jpg'):
        """Preprocesses the source image sequence.

        FFMpeg can't handle missing frames, so we'll check and fill in the gaps and convert the source images
        to jpeg images using OpenImageIO if they're not already supported by FFMpeg.

        Args:
            preconversion_format (str): The format to convert the source images to.

        Returns:
            tuple: A tuple of jpeg file paths to be used as input for ffmpeg.

        """
        index = self._index
        seq = index.data(common.SequenceRole)

        # The sequence element of the sequence members as padded strings
        frames = index.data(common.FramesRole)
        frames_it = (f for f in frames)

        # The full sequence of frame numbers
        all_frames = [str(f).zfill(len(frames[0])) for f in range(int(frames[0]), int(frames[-1]) + 1)]

        # FFMpeg can't handle missing frames, so we'll check for them and fill in the gaps
        has_missing_frames = len(all_frames) != len(frames)

        # Set up the temp directory
        _dir = QtCore.QDir(f'{common.temp_path()}/ffmpeg')
        if not _dir.exists():
            if not _dir.mkpath('.'):
                raise RuntimeError('Could not create ffmpeg temp dir')

        # Remove any previously created temp image frames
        for entry in os.scandir(_dir.path()):
            if entry.is_dir():
                continue
            if not entry.name.startswith('ffmpeg_'):
                continue
            _f = QtCore.QFile(entry.path)
            if not _f.remove():
                log.error(f'Could not remove {_f.filePath()}')

        ext = QtCore.QFileInfo(index.data(common.PathRole)).suffix().strip('.').lower()

        # Get the supported ffmpeg image extensions from the current binary
        # Run the command and capture the output
        ffmpeg_bin = common.get_binary('ffmpeg')

        if not ffmpeg_bin:
            raise RuntimeError('FFMpeg binary not found.')

        if not QtCore.QFileInfo(ffmpeg_bin).exists():
            raise RuntimeError(f'FFMpeg binary {ffmpeg_bin} does not exist.')

        result = subprocess.run([os.path.normpath(ffmpeg_bin), '-decoders'], capture_output=True, text=True)
        extensions = ffmpeg.get_supported_formats(result.stdout)

        if not extensions:
            raise RuntimeError('FFMpeg doesn\'t seem to support any image formats.')

        needs_conversion = ext not in extensions

        source_images = []
        ffmpeg_source_images = []

        # If the source images are already supported by ffmpeg and there are no missing frames, we'll just use the
        # source images as input for ffmpeg.
        if not has_missing_frames and not needs_conversion:
            return [f'{seq.group(1)}{f}{seq.group(3)}.{seq.group(4)}' for f in frames]

        # We'll build a full sequence filling in any missing frames with the closest available frame. This allows us
        # to correctly create videos of sequences with missing images.
        source_frame = all_frames[0]
        for frame in all_frames:
            if frame in frames:
                source_frame = next(frames_it)

            source_path = f'{seq.group(1)}{source_frame}{seq.group(3)}.{seq.group(4)}'
            source_images.append(source_path)

            destination_path = f'{_dir.path()}/ffmpeg_{frame}.{preconversion_format if needs_conversion else ext}'
            ffmpeg_source_images.append(destination_path)

        # We'll copy the source files to the temp directory instead of converting them to create a full sequence
        # of images. This allows us to correctly create videos of sequences with missing images.
        if not needs_conversion and has_missing_frames:
            for idx, items in enumerate(zip(source_images, ffmpeg_source_images)):
                source_path, destination_path = items

                common.message_widget.body_label.setText(f'Copying image {idx} of {len(source_images)}...')
                QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

                if not QtCore.QFile.copy(source_path, destination_path):
                    raise RuntimeError(f'Could not copy {source_path} to {destination_path}')

        # Convert the source images to jpeg images using OpenImageIO
        if needs_conversion:
            common.message_widget.body_label.setText(
                f'The sequence needs pre-converting:\nConverting {len(source_images)} images, please wait...'
            )
            QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

            if not bookmarks_openimageio.convert_images(source_images, ffmpeg_source_images, max_size=-1, release_gil=True):
                raise RuntimeError('Failed to convert an image using OpenImageIO.')

        # Sanity check to make sure all the destination paths exist
        for f in ffmpeg_source_images:
            if not QtCore.QFileInfo(f).exists():
                raise RuntimeError(f'{f} does not exist')

        return ffmpeg_source_images

    def sizeHint(self):
        """Returns a size hint.

        """
        return QtCore.QSize(
            common.size(common.size_width) * 0.66, common.size(common.size_height) * 0.66
        )

    def showEvent(self, event):
        super().showEvent(event)

        if not self._index:
            return

        item_rect = common.widget().visualRect(self._index)
        corner = common.widget().mapToGlobal(item_rect.bottomLeft())

        self.move(corner)
        self.setGeometry(
            self.geometry().x() + (item_rect.width() / 2) - (
                    self.geometry().width() / 2), self.geometry().y(), self.geometry().width(), self.geometry(

            ).height()
        )
        common.move_widget_to_available_geo(self)
