import os

from PySide2 import QtCore, QtWidgets

from .. import common, ui
from ..editor import base
from ..editor.base_widgets import ThumbnailEditorWidget
from ..server.view import EditAssetTemplatesWrapper
from ..templates.lib import TemplateType, get_saved_templates


def show():
    """Show the :class:`AddJobDialog` window.

    """
    if common.add_job_widget is None:
        common.add_job_widget = AddJobDialog()
    common.add_job_widget.open()
    return common.add_job_widget


def close():
    """Closes the :class:`AddJobDialog` editor.

    """
    if common.add_job_widget is None:
        return
    try:
        common.add_job_widget.close()
        common.add_job_widget.deleteLater()
    except:
        pass
    common.add_job_widget = None


class AddJobDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Add Asset')

        if not parent:
            common.set_stylesheet(self)

        self.name_editor = None
        self._thumbnail_editor = None

        self.asset_template_combobox = None
        self.edit_asset_templates_button = None

        self.template_editor = None

        self.summary_label = None

        self.ok_button = None
        self.cancel_button = None

        self._create_ui()
        self._connect_signals()

        self._init_completers()

        self.update_timer = common.Timer(parent=self)
        self.update_timer.setInterval(300)
        self.update_timer.timeout.connect(self.update_summary)
        self.update_timer.start()

        QtCore.QTimer.singleShot(100, self._init_templates)

    def _create_ui(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(widget)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().setSpacing(0)
        widget.layout().setAlignment(QtCore.Qt.AlignCenter)
        widget.setStyleSheet(f'background-color: {common.Color.VeryDarkBackground(qss=True)};')
        widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        self._thumbnail_editor = ThumbnailEditorWidget(
            fallback_thumb='folder_sm',
            parent=self
        )
        widget.layout().addWidget(self._thumbnail_editor, 0)
        self.layout().addWidget(widget, 0)

        widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(widget)
        o = common.Size.Indicator(6.0)
        widget.layout().setContentsMargins(o, o, o, o)
        widget.layout().setSpacing(o * 0.5)

        row = ui.add_row(None, height=None, parent=widget)
        self.summary_label = QtWidgets.QLabel(parent=self)
        self.summary_label.setText('')
        self.summary_label.setTextFormat(QtCore.Qt.RichText)
        row.layout().addWidget(self.summary_label, 1)

        grp = ui.get_group(parent=widget)

        row = ui.add_row('Client', height=None, parent=grp)
        self.name_editor = ui.LineEdit(required=True, parent=self)
        self.name_editor.setPlaceholderText('Enter Asset name, for example: SHOT_0010')
        self.name_editor.setValidator(base.name_validator)
        row.layout().addWidget(self.name_editor)
        self.client_row = row

        grp = ui.get_group(parent=widget)

        row = ui.add_row('Asset Template', height=None, parent=grp)
        self.asset_template_combobox = QtWidgets.QComboBox(parent=self)
        self.asset_template_combobox.setView(QtWidgets.QListView(parent=self.asset_template_combobox))
        row.layout().addWidget(self.asset_template_combobox, 1)

        self.edit_asset_templates_button = ui.PaintedButton('Edit Templates', parent=self)
        row.layout().addWidget(self.edit_asset_templates_button)

        self.template_editor = EditAssetTemplatesWrapper(parent=self)
        row.layout().addWidget(self.template_editor)
        self.template_editor.hide()

        widget.layout().addStretch(10)

        row = ui.add_row(None, height=None, parent=widget)
        self.ok_button = ui.PaintedButton('Add', parent=self)
        row.layout().addWidget(self.ok_button, 1)

        self.cancel_button = ui.PaintedButton('Cancel', parent=self)
        row.layout().addWidget(self.cancel_button)

        self.layout().addWidget(widget, 1)

    def _init_templates(self):
        templates = get_saved_templates(TemplateType.UserTemplate)
        templates = [f for f in templates]
        if not templates:
            self.asset_template_combobox.addItem('No templates found.', userData=None)
            self.asset_template_combobox.setItemData(
                0,
                ui.get_icon('close', color=common.Color.VeryDarkBackground()),
                QtCore.Qt.DecorationRole
            )
            return

        for template in templates:
            self.asset_template_combobox.addItem(template['name'], userData=template)

    def _init_completers(self):

        def _it(path):
            with os.scandir(path) as it:
                for entry in it:
                    if not entry.is_dir():
                        continue
                    if entry.name.startswith('.'):
                        continue
                    if not os.access(entry.path, os.R_OK | os.W_OK):
                        continue
                    p = entry.path.replace('\\', '/')
                    _rel_path = p[len(common.active('root', path=True)) + 1:].strip('/')
                    yield _rel_path

        def _add_completer(editor, values):
            completer = QtWidgets.QCompleter(values, parent=editor)
            completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
            completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            completer.setFilterMode(QtCore.Qt.MatchContains)
            common.set_stylesheet(completer.popup())

            action = QtWidgets.QAction(editor)
            action.setIcon(ui.get_icon('preset', color=common.Color.Text()))
            action.triggered.connect(completer.complete)
            editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

            action = QtWidgets.QAction(editor)
            action.setIcon(ui.get_icon('uppercase', color=common.Color.SecondaryText()))
            action.triggered.connect(lambda: editor.setText(editor.text().upper()))
            editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

            action = QtWidgets.QAction(editor)
            action.setIcon(ui.get_icon('lowercase', color=common.Color.SecondaryText()))
            action.triggered.connect(lambda: editor.setText(editor.text().lower()))
            editor.addAction(action, QtWidgets.QLineEdit.TrailingPosition)

            editor.setCompleter(completer)

        values = sorted([f for f in _it(common.active('root', path=True))])
        _add_completer(self.name_editor, set(values))

    def _connect_signals(self):
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.edit_asset_templates_button.clicked.connect(self.edit_asset_templates)

    @QtCore.Slot()
    def update_summary(self):
        summary = (f'The job will be created at <span style="color: '
                   f'{common.Color.Green(qss=True)}">{common.active("root", path=True)}')
        invalid_label = (f'<span style="color: {common.Color.LightYellow(qss=True)}">'
                         f'Make sure to fill out all required fields.</span>')
        name = self.name_editor.text()
        if not name:
            self.summary_label.setText(invalid_label)
            return
        summary = f'{summary}/{name}'
        summary = f'{summary}</span>'

        if self.asset_template_combobox.currentData():
            template = self.asset_template_combobox.currentData()
            summary = f'{summary} using the template "{template["name"]}"'
        else:
            summary = f'{summary} without using a template.'

        self.summary_label.setText(summary)

    def sizeHint(self):
        return QtCore.QSize(
            common.Size.DefaultWidth(1.5),
            common.Size.DefaultHeight(0.1)
        )

    @common.error
    @common.debug
    @QtCore.Slot(int)
    def done(self, r):
        if r == QtWidgets.QDialog.Rejected:
            return super().done(r)

        name = self.name_editor.text()
        if not name:
            raise ValueError('Job name is required.')

        path = f'{common.active("root", path=True)}/{name}'
        if os.path.exists(path):
            raise FileExistsError(f'Path "{path}" already exists.')
        os.makedirs(path)

        if self.asset_template_combobox.currentData():
            template = self.asset_template_combobox.currentData()
            template.template_to_folder(
                path,
                extract_contents_to_links=False,
                ignore_existing_folders=False
            )

        common.signals.assetAdded.emit(path)

        return super().done(r)

    @common.error
    @common.debug
    @QtCore.Slot()
    def edit_asset_templates(self):
        self.template_editor.setVisible(self.template_editor.isHidden())
