"""
"""
import functools
import os

import opentimelineio as otio
try:
    from PySide6 import QtWidgets, QtGui, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtGui, QtCore

from .. import actions
from .. import common
from .. import database
from .. import log
from .. import ui
from ..editor import base
from ..external import rv

instance = None

n = iter(range(QtCore.Qt.UserRole + 1024, QtCore.Qt.UserRole + 2048))

#: Item data roles used by the :class:`MediaView` model.
DescriptionRole = QtCore.Qt.ItemDataRole(next(n))
CutInRole = QtCore.Qt.ItemDataRole(next(n))
CutOutRole = QtCore.Qt.ItemDataRole(next(n))
EditInRole = QtCore.Qt.ItemDataRole(next(n))
EditOutRole = QtCore.Qt.ItemDataRole(next(n))
FramerateRole = QtCore.Qt.ItemDataRole(next(n))
WidthRole = QtCore.Qt.ItemDataRole(next(n))
HeightRole = QtCore.Qt.ItemDataRole(next(n))
CreatedRole = QtCore.Qt.ItemDataRole(next(n))
FileSizeRole = QtCore.Qt.ItemDataRole(next(n))
VersionRole = QtCore.Qt.ItemDataRole(next(n))
FormatRole = QtCore.Qt.ItemDataRole(next(n))
FilePathRole = QtCore.Qt.ItemDataRole(next(n))
AssetRole = QtCore.Qt.ItemDataRole(next(n))
TaskRole = QtCore.Qt.ItemDataRole(next(n))

SETTINGS_SECTIONS = {
    'edl': (
        'edl/source1',
        'edl/source2',
        'edl/source3',
        'edl/output_path',
        'edl/gaps',
        'edl/adapter',
        'edl/push_to_rv',
        'edl/reveal',
    )
}

DEFAULT_SOURCES = {
    'edl/source1': '{asset}/capture/*.mp4',
    'edl/source2': '{asset}/images/*.mp4',
    'edl/source3': '',
}

OTIO_ADAPTERS = {
    'otio_json': {
        'name': 'OpenTimelineIO JSON',
        'description': 'Exports an OpenTimelineIO .otio JSON file',
        'extension': 'otio',
    },
    'otioz': {
        'name': 'OpenTimelineIO Zip',
        'description': 'Exports an OpenTimelineIO .otioz zip archive',
        'extension': 'otioz',
    },
    'otiod': {
        'name': 'OpenTimelineIO Directory',
        'description': 'Exports an OpenTimelineIO .otiod directory',
        'extension': 'otiod',
    },
    'cmx_3600': {
        'name': 'Avid EDL',
        'description': 'Exports an EDL (Edit Decision List) file',
        'extension': 'edl',
    },
    'AAF': {
        'name': 'Avid AAF',
        'description': 'Exports an Avid AAF (Advanced Authoring Format) file',
        'extension': 'aaf',
    },
    'fcp_xml': {
        'name': 'Final Cut Pro 7 XML',
        'description': 'Exports a Final Cut Pro 7 XML file',
        'extension': 'xml',
    },
    'fcpx_xml': {
        'name': 'Final Cut Pro X XML',
        'description': 'Exports a Final Cut Pro X XML file',
        'extension': 'fcpxml',
    },
    'rv_session': {
        'name': 'RV Session',
        'description': 'Exports an RV Session file',
        'extension': 'rv',
    },
}


def close():
    """Closes the :class:`PreferenceEditor` widget.

    """
    global instance
    if instance is None:
        return
    try:
        instance.close()
        instance.deleteLater()
    except:
        pass
    instance = None


def show():
    """Shows the :class:`PreferenceEditor` widget.

    """
    close()
    global instance
    instance = EdlWidget()
    common.restore_window_geometry(instance)
    common.restore_window_state(instance)
    return instance


class StatusLabel(ui.PaintedLabel):
    """Status label.

    """

    def __init__(self, parent=None):
        super().__init__('No source selected', parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Fixed
        )
        self.setMinimumWidth(common.size(common.size_width * 0.33))


class AdaptersModel(ui.AbstractListModel):
    """Format item picker model.

    """

    def init_data(self):
        """Initializes data.

        """
        adapter_names = otio.adapters.available_adapter_names()

        for k, v in OTIO_ADAPTERS.items():
            icon = ui.get_icon('file')

            # Skip adapters that are not available.
            if k not in adapter_names:
                continue

            self._data[len(self._data)] = {
                QtCore.Qt.DisplayRole: v['name'],
                QtCore.Qt.DecorationRole: icon,
                QtCore.Qt.SizeHintRole: self.row_size,
                QtCore.Qt.StatusTipRole: v['description'],
                QtCore.Qt.AccessibleDescriptionRole: v['description'],
                QtCore.Qt.WhatsThisRole: v['description'],
                QtCore.Qt.ToolTipRole: v['description'],
                QtCore.Qt.UserRole: k,
            }


class AdaptersComboBox(QtWidgets.QComboBox):
    """Format item picker.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setView(QtWidgets.QListView())
        model = AdaptersModel()
        self.setModel(model)


class Node(object):
    def __init__(self, data, parent=None):
        self._data = data
        self._children = []
        self._parent = parent
        if parent:
            parent.addChild(self)

    def data(self, role):
        return self._data.get(role, None)

    def setData(self, role, value):
        self._data[role] = value

    def row(self):
        if self._parent:
            return self._parent._children.index(self)
        return 0

    def child(self, row):
        return self._children[row]

    def addChild(self, child):
        self._children.append(child)

    def childCount(self):
        return len(self._children)

    def parent(self):
        return self._parent

    def columnCount(self):
        return len(self._data)


class MediaModel(QtCore.QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_node = Node({})

    def init_data(self, data):
        self.beginResetModel()

        self._root_node = Node({})

        for asset, medias in data.items():
            asset_node = Node(
                {
                    QtCore.Qt.DisplayRole: asset,
                    AssetRole: asset
                }, self._root_node
            )
            for media in medias:
                Node(media, asset_node)
        self.endResetModel()

    def rowCount(self, parent):
        if not parent.isValid():
            parent_node = self._root_node
        else:
            parent_node = parent.internalPointer()
        return parent_node.childCount()

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        if not index.isValid():
            return None
        node = index.internalPointer()

        is_media_node = node.parent() != self._root_node

        if role == QtCore.Qt.ForegroundRole and is_media_node:
            return common.color(common.color_text)
        if role == QtCore.Qt.ForegroundRole and not is_media_node:
            return common.color(common.color_blue)
        if role == QtCore.Qt.FontRole:
            font, _ = common.font_db.medium_font(
                common.size(common.size_font_small)
            )
            return font
        if role == QtCore.Qt.SizeHintRole and is_media_node:
            o = common.size(common.size_margin * 1.2)
            return QtCore.QSize(o, o)
        if role == QtCore.Qt.SizeHintRole and not is_media_node:
            o = common.size(common.size_margin)
            return QtCore.QSize(o, o)
        if role == QtCore.Qt.DecorationRole and is_media_node:
            return ui.get_icon('file')
        if role == QtCore.Qt.DecorationRole and not is_media_node:
            return ui.get_icon('asset')
        if role == QtCore.Qt.DisplayRole and is_media_node:
            return node.data(FilePathRole).split('/')[-1]
        if role == QtCore.Qt.DisplayRole and not is_media_node:
            bookmark = common.active('root', path=True)
            return node.data(QtCore.Qt.DisplayRole).replace(bookmark, '').strip('/')

        return node.data(role)

    def headerData(self, section, orientation, role):
        return None

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def parent(self, index):
        node = self.get_node(index)
        parent_node = node.parent()
        if parent_node == self._root_node:
            return QtCore.QModelIndex()
        return self.createIndex(parent_node.row(), 0, parent_node)

    def index(self, row, column, parent):
        parent_node = self.get_node(parent)
        child_node = parent_node.child(row)
        if child_node:
            return self.createIndex(row, column, child_node)
        else:
            return QtCore.QModelIndex()

    def get_node(self, index):
        if index.isValid():
            node = index.internalPointer()
            if node:
                return node
        return self._root_node


class MediaView(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setModel(MediaModel())
        self.setMinimumHeight(common.size(common.size_height * 1.2))
        self.setRootIsDecorated(True)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # Hide the top header
        self.header().hide()

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

    def sizeHint(self):
        return QtCore.QSize(
            common.size(common.size_width * 1),
            common.size(common.size_height * 1),
        )


class EdlWidget(base.BasePropertyEditor):
    sourceDataReady = QtCore.Signal(dict)

    #: UI layout
    sections = {
        0: {
            'name': 'Sources',
            'icon': 'asset',
            'color': common.color(common.color_yellow),
            'groups': {
                0: {
                    0: {
                        'name': None,
                        'key': None,
                        'validator': None,
                        'widget': None,
                        'placeholder': None,
                        'description': None,
                        'help': 'Generate EDLs from the media sources of the currently visible assets.',
                    },
                    1: {
                        'name': 'Source #1',
                        'key': 'edl/source1',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': None,
                        'description': 'Footage source #1',
                    },
                    2: {
                        'name': 'Source #2',
                        'key': 'edl/source2',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': None,
                        'description': 'Footage source #1',
                    },
                    3: {
                        'name': 'Source #3',
                        'key': 'edl/source3',
                        'validator': None,
                        'widget': ui.LineEdit,
                        'placeholder': None,
                        'description': 'Footage source #1',
                    },
                },
            },
        },
        1: {
            'name': 'Options',
            'icon': 'settings',
            'color': common.color(common.color_green),
            'groups': {
                0: {
                    0: {
                        'name': 'Export format',
                        'key': 'edl/adapter',
                        'validator': None,
                        'widget': AdaptersComboBox,
                        'placeholder': None,
                        'description': 'Default output directory for generated files.',
                    },
                },
                1: {
                    0: {
                        'name': 'Add gaps',
                        'key': 'edl/gaps',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                        'placeholder': None,
                        'description': 'Add gaps between each source.',
                        'help': 'Tick to add any potential gaps between sources. If left disabled the source'
                                ' clips will be laid out back to back, disregarding the edit information.',
                    },
                    1: {
                        'name': 'Push to RV',
                        'key': 'edl/push_to_rv',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                        'placeholder': None,
                        'description': 'Push to RV instead of saving a file',
                        'help': 'Click enabled to push directly to RV instead of saving a file when RV Session is '
                                'selected.',
                    },
                    2: {
                        'name': 'Reveal Output',
                        'key': 'edl/reveal',
                        'validator': None,
                        'widget': functools.partial(QtWidgets.QCheckBox, 'Enable'),
                        'placeholder': None,
                        'description': 'Reveal the output file in the file browser.',
                        'help': 'Enable reveal the output file in the file browser after export.',
                    },
                },
            },
        },
        2: {
            'name': 'Media',
            'icon': 'image',
            'color': common.color(common.color_blue),
            'groups': {
                0: {
                    0: {
                        'name': None,
                        'key': 'selection_status',
                        'validator': None,
                        'widget': StatusLabel,
                        'placeholder': None,
                        'description': None,
                        'button': 'Update Media Sources',
                    },
                },
                1: {
                    0: {
                        'name': None,
                        'key': 'parse_media',
                        'validator': None,
                        'widget': None,
                        'placeholder': None,
                        'description': 'Parse assets and generate a list of source media candidates for the EDL.',
                    },
                    1: {
                        'name': None,
                        'key': 'media_view',
                        'validator': None,
                        'widget': MediaView,
                        'placeholder': None,
                        'description': None,
                    },
                },
            },
        },
    }

    def __init__(self, parent=None):
        if not common.active('root', args=True):
            raise ValueError('A root item must be active before continuing.')

        super().__init__(
            *common.active('root', args=True),
            db_table=database.BookmarkTable,
            fallback_thumb='sg',
            buttons=('Export', 'cancel'),
            parent=parent
        )

        self.selection_status_timer = common.Timer()
        self.selection_status_timer.timeout.connect(self.update_selection_status)
        self.selection_status_timer.setInterval(500)
        self.selection_status_timer.setSingleShot(False)

        self.sourceDataReady.connect(self.media_view_editor.model().init_data)
        self.sourceDataReady.connect(self.media_view_editor.expandAll)

        common.widget(common.AssetTab).model().invalidated.connect(self.parse_media)
        common.widget(common.AssetTab).model().invalidated.connect(self.select_latest_sources)

        self.edl_push_to_rv_editor.stateChanged.connect(
            lambda x: self.save_button.setText('Push to RV' if x else 'Export')
        )

    @QtCore.Slot()
    def update_selection_status(self):
        """Updates the selection status.

        """
        selected_sources = self.get_selected_sources()
        selected_sources = selected_sources if selected_sources else []
        count = len(selected_sources)

        if not hasattr(self, 'selection_status_editor'):
            return

        self.selection_status_editor.setText(
            f'{count} source{"" if count == 1 else "s"} selected.'
        )

    def hideEvent(self, event):
        super().hideEvent(event)
        self.selection_status_timer.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self.selection_status_timer.start()

    def db_source(self):
        """A file path to use as the source of database values.

        Returns:
            str: The database source file.

        """
        return common.active('root', path=True)

    @common.error
    @common.debug
    def save_changes(self):
        """Saves changes.

        """
        selected_sources = self.get_selected_sources()
        if not selected_sources:
            common.show_message(
                'No Sources Selected',
                body='Please select at least one source to generate an EDL.',
                message_type='error'
            )
            return False

        # Get oito timeline
        selected_sources = self.get_selected_sources()
        if not selected_sources:
            common.show_message(
                'Make sure to select at least one source to continue',
                message_type='error'
            )
            return False

        timeline = self.get_otio_timeline(selected_sources)
        if not timeline:
            return False

        # Get the selected adapter
        if not self.edl_adapter_editor.currentData():
            common.show_message(
                'Select an output format before continuing.',
                message_type='error'
            )
            return False

        adapter = self.edl_adapter_editor.currentData()
        if adapter not in OTIO_ADAPTERS:
            raise ValueError(f'Adapter "{adapter}" not found.')

        # Check that the required environment values are set
        if adapter == 'rv_session':
            if 'OTIO_RV_PYTHON_BIN' not in os.environ or 'OTIO_RV_PYTHON_LIB' not in os.environ:
                bin_path = common.get_binary('rv')
                if not bin_path:
                    raise RuntimeError('RV not found.')

                rv_bin_dir = QtCore.QFileInfo(bin_path).dir().path()

                if not common.get_platform() == common.PlatformWindows:
                    raise RuntimeError('Unsupported platform.')

                rv_py_interp = f'{rv_bin_dir}/py-interp.exe'
                if not QtCore.QFileInfo(rv_py_interp).exists():
                    rv_py_interp = common.get_binary('py-interp')
                    rv_bin_dir = QtCore.QFileInfo(rv_py_interp).dir().path()
                    if not rv_py_interp:
                        raise RuntimeError('Could not find py-interp.exe')

                os.environ['OTIO_RV_PYTHON_BIN'] = QtCore.QFileInfo(rv_py_interp).absoluteFilePath()

                rv_session_dir = f'{rv_bin_dir}/../src/python'
                if not QtCore.QFileInfo(rv_session_dir).exists():
                    raise RuntimeError('Could not find rvSession')
                else:
                    os.environ['OTIO_RV_PYTHON_LIB'] = QtCore.QFileInfo(rv_session_dir).absoluteFilePath()

        extension = OTIO_ADAPTERS[adapter]['extension']

        # Get default save folder
        previous_file = common.settings.value('edl/output_path', None)
        previous_file = previous_file if isinstance(previous_file, str) else None

        default_parent_dir = self.db_source()
        if previous_file and QtCore.QFileInfo(previous_file).isFile():
            default_parent_dir = QtCore.QFileInfo(previous_file).dir().path()
        if previous_file and not QtCore.QFileInfo(previous_file).isFile():
            default_parent_dir = previous_file

        if not self.edl_push_to_rv_editor.isChecked():
            # Get output filenamee
            output_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                f'Save {OTIO_ADAPTERS[adapter]["name"]}',
                default_parent_dir,
                f'{OTIO_ADAPTERS[adapter]["name"]} (*.{extension});;',
            )
        else:
            output_path = f'{common.temp_path()}/rv_push_temp.{extension}'

        if not output_path:
            return False

        common.settings.setValue('edl/output_path', output_path)
        otio.adapters.write_to_file(timeline, output_path, adapter_name=adapter)

        if self.edl_reveal_editor.isChecked():
            actions.reveal(output_path)

        if adapter == 'rv_session' and self.edl_push_to_rv_editor.isChecked():
            rv.execute_rvpush_command(output_path, rv.PushAndClear)

        if not self.edl_push_to_rv_editor.isChecked():
            common.show_message(
                f'{QtCore.QFileInfo(output_path).fileName()} was exported successfully.',
                message_type='success'
            )

    @common.error
    @common.debug
    def init_data(self, *args, **kwargs):
        """Initializes data.

        """
        self.init_db_data()
        self.thumbnail_editor.setDisabled(True)
        for k in SETTINGS_SECTIONS:
            self.load_saved_user_settings(SETTINGS_SECTIONS[k])
            self._connect_settings_save_signals(SETTINGS_SECTIONS[k])

        for k in DEFAULT_SOURCES:
            if not hasattr(self, f'{k.replace("/", "_")}_editor'):
                return
            editor = getattr(self, f'{k.replace("/", "_")}_editor')
            if not editor.text():
                editor.setText(DEFAULT_SOURCES[k])

        self.parse_media()
        self.select_latest_sources()

        if self.edl_push_to_rv_editor.isChecked():
            self.save_button.setText('Push to RV')

    @QtCore.Slot()
    def selection_status_button_clicked(self, *args, **kwargs):
        """Parse assets button clicked.

        """
        self.parse_media()
        self.select_latest_sources()

    @QtCore.Slot()
    def parse_media(self, *args, **kwargs):
        """Parse the visible asset items and return a list of source media data items.

        """
        model = common.model(common.AssetTab)
        if not model:
            raise ValueError('')

        def _get_sources(path, ext):
            for entry in os.scandir(path):
                if entry.is_dir():
                    yield from _get_sources(entry.path, ext)
                elif entry.is_file() and entry.name.endswith(ext):
                    yield entry.path.replace('\\', '/')

        data = {}

        common.show_message(
            'Looking for sources...',
            body='Please wait...',
            disable_animation=True,
            message_type=None,
            buttons=[]
        )

        for idx in range(model.rowCount()):
            index = model.index(idx, 0)
            if not index.isValid():
                continue
            asset = index.data(common.PathRole)
            if not asset:
                continue

            if asset not in data:
                data[asset] = []

            # Get database values
            asset_data = {}
            db = database.get(*common.active('root', args=True))
            with db.connection():
                for k in ('cut_in', 'cut_out', 'edit_in', 'edit_out', 'description', 'sg_task_name'):
                    asset_data[k] = db.value(asset, k, database.AssetTable)
                for k in ('width', 'height', 'framerate'):
                    asset_data[k] = db.value(db.source(), k, database.BookmarkTable)

            common.message_widget.title_label.setText(f'Processing {asset}...')
            QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

            for k in DEFAULT_SOURCES:
                if not hasattr(self, f'{k.replace("/", "_")}_editor'):
                    log.debug(f'No editor found for {k}, skipping.')
                    continue

                editor = getattr(self, f'{k.replace("/", "_")}_editor')

                if not editor.text():
                    continue

                source = editor.text().format(asset=asset)
                source_info = QtCore.QFileInfo(source)
                source_dir = source_info.dir().path()
                source_ext = source_info.suffix()

                if not QtCore.QFileInfo(source_dir).exists():
                    log.debug(f'{source_dir} does not exist, skipping.')
                    continue

                common.message_widget.body_label.setText(f'Found source dir:\n{source_dir}')
                QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)

                # Get the source files
                for source in _get_sources(source_dir, source_ext):
                    source_info = QtCore.QFileInfo(source)

                    source_data_item = {
                        QtCore.Qt.DisplayRole: source_info.fileName(),
                        QtCore.Qt.UserRole: source_info.filePath(),
                        QtCore.Qt.ToolTipRole: source_info.filePath(),
                        AssetRole: asset,
                        CutInRole: asset_data['cut_in'],
                        CutOutRole: asset_data['cut_out'],
                        EditInRole: asset_data['edit_in'],
                        EditOutRole: asset_data['edit_out'],
                        DescriptionRole: asset_data['description'],
                        WidthRole: asset_data['width'],
                        HeightRole: asset_data['height'],
                        FramerateRole: asset_data['framerate'],
                        CreatedRole: source_info.birthTime().toMSecsSinceEpoch(),
                        FileSizeRole: source_info.size(),
                        FormatRole: source_info.suffix(),
                        FilePathRole: source_info.filePath(),
                        TaskRole: asset_data['sg_task_name']
                    }

                    data[asset].append(source_data_item)

        self.sourceDataReady.emit(data)
        common.close_message()

    def get_latest_sources(self):
        """Iterate over the model data and return a dictionary mapping
        each asset to its latest media source.

        If all sources for an asset have a version number, the latest source is
        determined by the highest version number. If any source does not have a
        version number, the latest source is determined by the latest modified time.

        """
        latest_sources = {}
        model = self.media_view_editor.model()

        def visit(node):
            asset = node.data(QtCore.Qt.DisplayRole)

            children = [node.child(i) for i in range(node.childCount())]
            if node.columnCount() == 2 and children:
                last_modified_child = max(children, key=lambda x: x.data(CreatedRole))
                latest_sources[asset] = last_modified_child.data(FilePathRole)

            for i in range(node.childCount()):
                visit(node.child(i))

        visit(model._root_node)

        return latest_sources

    def select_latest_sources(self):
        """Select each asset's latest source in the given view.

        'view' is a QTreeView displaying the media sources.
        'latest_sources' is a dictionary mapping each asset to its latest source,
        as returned by get_latest_sources.

        """
        latest_sources = self.get_latest_sources()

        view = self.media_view_editor
        model = view.model()

        selection_model = view.selectionModel()
        selection_model.clear()  # Clear the current selection

        def visit(node):
            if node.columnCount() == 2:
                asset = node.data(QtCore.Qt.DisplayRole)
                latest_source = latest_sources.get(asset)
                if not latest_source:
                    return
                for i in range(node.childCount()):
                    child = node.child(i)
                    if child.data(FilePathRole) == latest_source:
                        index = self.media_view_editor.model().createIndex(child.row(), 0, child)
                        selection_model.select(index, QtCore.QItemSelectionModel.Select)
                        return

            for i in range(node.childCount()):
                visit(node.child(i))

        visit(model._root_node)

    def get_selected_sources(self):
        """Return a list of the selected sources in the given view.

        'view' is a QTreeView displaying the media sources.

        """
        view = self.media_view_editor
        selected_indexes = view.selectionModel().selectedIndexes()
        selected_sources = []

        for index in selected_indexes:
            node = index.internalPointer()
            if node.childCount():  # This is an asset node, so skip it
                continue
            selected_sources.append(node)

        return selected_sources

    def get_otio_timeline(self, selected_sources):
        if not selected_sources:
            return None

        def sort_key(node):
            if node.data(EditInRole) is not None:
                return node.data(EditInRole)
            return f'0{node.data(QtCore.Qt.DisplayRole)}'

        # sort the sources by their edit_in values
        sorted_sources = sorted(selected_sources, key=sort_key)

        # create a new timeline
        timeline = otio.schema.Timeline()
        timeline.name = 'Imported Timeline'

        # create a default track
        track = otio.schema.Track()
        track.name = 'Imported Media Sources'
        timeline.tracks.append(track)

        last_edit_out = None

        for i, node in enumerate(sorted_sources):
            # check if any of the required data is None, and if so, skip this node
            if any(
                    node.data(role) is None for role in
                    [QtCore.Qt.DisplayRole, QtCore.Qt.UserRole, CutInRole, CutOutRole, EditInRole, EditOutRole,
                     FramerateRole]
            ):
                print(f'Skipping {node.data(QtCore.Qt.DisplayRole)} because it is missing required data.')
                continue

            edit_in = node.data(EditInRole)
            edit_out = node.data(EditOutRole)

            # create a new clip
            clip = otio.schema.Clip()

            # set the name of the clip
            clip.name = node.data(QtCore.Qt.DisplayRole)

            # set the source file path for the clip
            media_ref = otio.schema.ExternalReference(
                target_url=node.data(QtCore.Qt.UserRole),
            )
            clip.media_reference = media_ref

            # set the range for the clip
            clip.source_range = otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(node.data(CutInRole), node.data(FramerateRole)),
                duration=otio.opentime.RationalTime(
                    node.data(CutOutRole) - node.data(CutInRole), node.data(
                        FramerateRole
                    )
                    )
            )

            # add metadata to the clip
            clip.metadata.update(
                {
                    'description': node.data(DescriptionRole),
                    'width': node.data(WidthRole),
                    'height': node.data(HeightRole),
                    'last_modified': node.data(CreatedRole),
                    'file_size': node.data(FileSizeRole),
                    'format': node.data(FormatRole),
                    'file_path': node.data(FilePathRole),
                    'task': node.data(TaskRole)
                }
            )

            # add a gap if necessary, if checkbox is checked, if it's not the first clip, and if gap is at least one
            # frame long
            if i > 0 and self.edl_gaps_editor.isChecked() and last_edit_out is not None:
                gap_duration = edit_in - last_edit_out
                if gap_duration >= node.data(FramerateRole):  # Ensure gap is at least one frame long
                    gap = otio.schema.Gap(
                        source_range=otio.opentime.TimeRange(
                            duration=otio.opentime.RationalTime(gap_duration, node.data(FramerateRole))
                        )
                    )
                    track.append(gap)

            # add the clip to the track
            track.append(clip)

            last_edit_out = edit_out  # update the last_edit_out after adding the clip

        return timeline


def run():
    w = EdlWidget()
    w.show()


if __name__ == '__main__':
    run()
