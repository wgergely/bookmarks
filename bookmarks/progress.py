"""Task progress tracker for asset items.

This module provides the basic definitions needed to implement task status tracking.
The progress data is stored in the asset table under the 'progress' column.

:attr:`STATES` defines the user selectable progress states.
:attr:`STAGES` define the production steps we're able to set states for. Each asset item
has their own STAGES data stored in the bookmark database, editable by user interactions
via the :class:`ProgressDelegate`.

"""
import copy

from PySide2 import QtWidgets, QtCore, QtGui

from . import common
from . import database
from . import images
from . import ui
from .items import delegate

n = (f for f in range(9999))
DesignStage = next(n)
LayoutStage = next(n)
ModelStage = next(n)
RigStage = next(n)
AnimationStage = next(n)
RenderStage = next(n)
FXStage = next(n)
CompStage = next(n)
GradeStage = next(n)

n = (f for f in range(9999))
OmittedState = next(n)
InProgressState = next(n)
PendingState = next(n)
CompletedState = next(n)
PriorityState = next(n)

#: The selectable progress states
STATES = {
    OmittedState: {
        'name': 'Skip',
        'icon': 'progress-dot-24',
        'color': common.color(common.color_opaque),
    },
    InProgressState: {
        'name': 'In\nProgress',
        'icon': 'progress-hourglass-24',
        'color': common.color(common.color_yellow),
    },
    PendingState: {
        'name': 'Pending',
        'icon': 'progress-task-planning-24',
        'color': common.color(common.color_background),
    },
    CompletedState: {
        'name': 'Done',
        'icon': 'progress-task-completed-24',
        'color': common.color(common.color_green),
    },
    PriorityState: {
        'name': 'Priority',
        'icon': 'progress-task-important-24',
        'color': common.color(common.color_dark_red),
    },
}

#: The production stages to be configured with a :attr:`STATES` value.
STAGES = {
    ModelStage: {
        'name': 'Model',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    RigStage: {
        'name': 'Rig',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    DesignStage: {
        'name': 'Design',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    LayoutStage: {
        'name': 'Layout',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    AnimationStage: {
        'name': 'Anim',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    RenderStage: {
        'name': 'Render',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    FXStage: {
        'name': 'FX',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    CompStage: {
        'name': 'Comp',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
    GradeStage: {
        'name': 'Grade',
        'states': (OmittedState, InProgressState, PendingState, CompletedState,
                   PriorityState),
        'value': 0,
        'visible': True,
    },
}


class ProgressDelegate(QtWidgets.QItemDelegate):
    """The delegate used to display task progress information.

    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        """Paints the extra columns of
        :class:`~bookmarks.items.asset_items.AssetItemView`.

        """
        source_model = index.model().sourceModel()
        source_index = index.model().mapToSource(index)

        p = source_model.source_path()
        k = source_model.task()
        t = common.FileItem

        _data = common.get_data(p, k, t)
        data = _data[source_index.row()][common.AssetProgressRole][index.column() - 1]

        right_edge = self._draw_background(painter, option, data)
        self._draw_text(painter, option, data, right_edge)
        self._draw_shadow(painter, option, index)

    @delegate.save_painter
    def _draw_shadow(self, painter, option, index):
        if index.column() != 1:
            return

        rect = QtCore.QRect(option.rect)
        o = common.size(common.size_margin) * 3.0
        rect.setWidth(o)

        painter.setOpacity(0.5)
        pixmap = images.rsc_pixmap(
            'gradient', None, rect.height()
        )
        painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(o * 0.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @delegate.save_painter
    def _draw_background(self, painter, option, data):
        selected = option.state & QtWidgets.QStyle.State_Selected
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        rect = QtCore.QRect(option.rect)
        rect.setBottom(rect.bottom() - common.size(common.size_separator))

        # Draw background
        color = STATES[data['value']]['color']
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.NoPen)
        if hover:
            painter.setOpacity(1.0)
        else:
            painter.setOpacity(0.85)
        painter.drawRect(rect)

        if selected:
            _color = common.color(common.color_light_background)
            painter.setBrush(_color)
            painter.setOpacity(0.15)
            painter.drawRect(rect)

        rect.setWidth(rect.height())
        center = rect.center()

        r = common.size(common.size_margin)
        rect.setSize(QtCore.QSize(r, r))
        rect.moveCenter(center)
        rect.moveLeft(option.rect.left() + common.size(common.size_indicator) * 2)

        if data['value'] == OmittedState:
            if hover:
                painter.setOpacity(1.0)
            else:
                painter.setOpacity(0.1)
        else:
            painter.setOpacity(0.5)

        pixmap = images.rsc_pixmap(
            STATES[data['value']]['icon'],
            color=None,
            size=r
        )

        painter.drawPixmap(rect, pixmap, pixmap.rect())
        return rect.right()

    @delegate.save_painter
    def _draw_text(self, painter, option, data, right_edge):
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        text = STATES[data['value']]['name']

        if data['value'] == OmittedState:
            text = f'Edit\n{data["name"]}' if hover else ''
            painter.setOpacity(0.25)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 255)))
        _rect = QtCore.QRect(option.rect)

        _o = common.size(common.size_indicator) * 2
        _rect.setLeft(right_edge + _o)

        font, metrics = common.font_db.light_font(common.size(common.size_font_small))
        painter.setFont(font)
        painter.drawText(
            _rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, text
        )

    def createEditor(self, parent, option, index):
        """Creates a combobox editor used to change a state value.

        """
        editor = QtWidgets.QComboBox(parent=parent)
        editor.setStyleSheet(
            f'border-radius:0px;'
            f'selection-background-color:rgba(180,180,180,255);'
            f'margin:0px;'
            f'padding:0px;'
            f'min-width:{common.size(common.size_width) * 0.33}px;'
            f'height:{option.rect.height()}px;'
        )
        editor.currentIndexChanged.connect(
            lambda _: self.commitData.emit(editor)
        )
        editor.currentIndexChanged.connect(
            lambda _: self.closeEditor.emit(editor)
        )
        QtCore.QTimer.singleShot(100, editor.showPopup)
        return editor

    def setEditorData(self, editor, index):
        """Loads the state values from the current index into the editor.

        """
        source_model = index.model().sourceModel()
        source_index = index.model().mapToSource(index)

        p = source_model.source_path()
        k = source_model.task()
        t = common.FileItem

        _data = common.get_data(p, k, t)
        data = _data[source_index.row()][common.AssetProgressRole][index.column() - 1]

        for state in sorted(data['states']):
            editor.addItem(
                STATES[state]['name'],
                userData=state
            )
            icon = STATES[state]['icon']

            editor.setItemIcon(
                editor.count() - 1,
                ui.get_icon(icon),
            )
            editor.setItemData(
                editor.count() - 1,
                STATES[state]['color'],
                role=QtCore.Qt.BackgroundRole
            )
            editor.setItemData(
                editor.count() - 1,
                QtCore.QSize(200, 36),
                role=QtCore.Qt.SizeHintRole
            )
        editor.setCurrentText(
            STATES[data['value']]['name']
        )

    def setModelData(self, editor, model, index):
        """Saves the current state value to the bookmark database.

        """
        source_model = index.model().sourceModel()
        source_index = index.model().mapToSource(index)

        p = source_model.source_path()
        k = source_model.task()
        t = common.FileItem

        data = common.get_data(p, k, t)

        # We don't have to modify the internal data directly because
        # the db.set_value call will trigger an item refresh
        progress_data = copy.deepcopy(data[source_index.row()][common.AssetProgressRole])
        progress_data[index.column() - 1]['value'] = editor.currentData()

        # Write current data to the database
        pp = data[source_index.row()][common.ParentPathRole]
        db = database.get(*pp[0:3])
        db.set_value(
            data[source_index.row()][common.PathRole],
            'progress',
            progress_data,
            table=database.AssetTable
        )

    def updateEditorGeometry(self, editor, option, index):
        """Resizes the editor.

        """
        super().updateEditorGeometry(editor, option, index)
        editor.setGeometry(option.rect)
