import copy
import functools
import os

from PySide2 import QtWidgets, QtCore, QtGui

from . import common
# from akapipe.core import db, database, signals



n = (f for f in range(9999))
DesignStage = next(n)
LayoutStage = next(n)
AnimationStage = next(n)
RenderStage = next(n)
FXStage = next(n)
CompStage = next(n)
GradeStage = next(n)

n = (f for f in range(9999))
ModelStage = next(n)
RigStage = next(n)

n = (f for f in range(9999))
OmittedState = next(n)
InProgressState = next(n)
PendingState = next(n)
CompletedState = next(n)
PriorityState = next(n)

#: The selectable progress states
STATES = {
    OmittedState: {
        'name': 'Omitted',
        'icon': 'icons8-line-24',
        'color': (0, 0, 0, 0),
    },
    InProgressState: {
        'name': 'In Progress',
        'icon': 'icons8-hourglass-24',
        'color': (253, 166, 1, 255),
    },
    PendingState: {
        'name': 'Pending',
        'icon': 'icons8-task-planning-24',
        'color': (15, 74, 130, 255),
    },
    CompletedState: {
        'name': 'Completed',
        'icon': 'icons8-task-completed-24',
        'color': (85, 198, 170, 255),
    },
    PriorityState: {
        'name': 'Priority',
        'icon': 'icons8-task-important-24',
        'color': (214, 28, 42, 255),
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

CELL_WIDTH = 64
CELL_HEIGHT = 32


#
# class ProgressModel(QtCore.QAbstractTableModel):
#     def __init__(self, table):
#         super().__init__()
#
#     def index(self, row, column, parent=QtCore.QModelIndex()):
#         return self.createIndex(row, column, parent=QtCore.QModelIndex())
#
#     def rowCount(self, parent=QtCore.QModelIndex()):
#         return len(db.cache[self.table])
#
#     def columnCount(self, parent=QtCore.QModelIndex()):
#         return len(STAGES[self.table])
#
#     def flags(self, index, parent=QtCore.QModelIndex()):
#         return (
#                 QtCore.Qt.ItemIsEnabled |
#                 QtCore.Qt.ItemIsSelectable |
#                 QtCore.Qt.ItemIsEditable
#         )
#
#     def headerData(self, column, orientation, role=QtCore.Qt.DisplayRole):
#         if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
#             return STAGES[self.table][column]['name']
#         if role == QtCore.Qt.TextAlignmentRole:
#             return QtCore.Qt.AlignCenter
#         if role == QtCore.Qt.SizeHintRole and orientation == QtCore.Qt.Horizontal:
#             return QtCore.QSize(CELL_WIDTH, CELL_HEIGHT)
#         if role == QtCore.Qt.SizeHintRole and orientation == QtCore.Qt.Vertical:
#             return QtCore.QSize(CELL_HEIGHT, CELL_HEIGHT * 2)
#
#     def data(self, index, role=QtCore.Qt.DisplayRole, parent=QtCore.QModelIndex()):
#         if role == QtCore.Qt.DisplayRole:
#             return self.internal_data[index.row()][index.column()]['value']
#         if role == QtCore.Qt.SizeHintRole:
#             return QtCore.QSize(CELL_WIDTH, CELL_HEIGHT)
#
#     def setData(self, index, value, role=QtCore.Qt.DisplayRole):
#         columns = db.tables[self.table]['columns']
#         column = next(
#             v['column'] for v in columns.values() if v['role'] == db.ProgressRole
#         )
#         idx = next(
#             f for f in columns if columns[f]['role'] == db.IdRole
#         )
#         self.internal_data[index.row()][index.column()]['value'] = value
#         database.set_value(
#             self.table,
#             column,
#             db.cache[self.table][index.row()][idx],
#             self.internal_data[index.row()]
#         )
#         idx = next(
#             f for f in columns if columns[f]['role'] == db.ProgressRole
#         )
#         db.cache[self.table][index.row()][idx] = self.internal_data[index.row()]
#         return True


# @functools.lru_cache(maxsize=128)
# def get_icon(name):
#     s = os.path.normpath(__file__ + f'/../../rsc/gui/{name}.png')
#     pixmap = QtGui.QPixmap(s)
#     return QtGui.QIcon(pixmap)

#
class ProgressDelegate(QtWidgets.QItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        painter.save()

        row, column, data = self.get_row_column_data(index)

        color = QtGui.QColor(*STATES[data['value']]['color'])
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(option.rect)

        icon = STATES[data['value']]['icon']
        icon = get_icon(icon)
        rect = QtCore.QRect(option.rect)
        rect.setWidth(rect.height())
        center = rect.center()
        rect.setSize(QtCore.QSize(18, 18))
        rect.moveCenter(center)
        rect.moveLeft(option.rect.left() + 6)
        text = STATES[data['value']]['name']
        if data['value'] == OmittedState:
            painter.setOpacity(0.3)
        icon.paint(painter, rect)

        painter.restore()

        painter.save()
        if data['value'] == OmittedState:
            painter.setOpacity(0.25)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 255)))
        _rect = QtCore.QRect(option.rect)
        _rect.setLeft(rect.right() + 6)
        painter.drawText(
            _rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, text
        )
        painter.restore()

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent=parent)
        editor.setStyleSheet(
            f'border-radius:0px;'
            f'selection-background-color:rgba(180,180,180,255);'
            f'margin:0px;'
            f'padding:0px;'
            f'height:{option.rect.height()}px;'
        )
        editor.currentIndexChanged.connect(
            lambda _: self.commitData.emit(editor)
        )
        return editor

    def setEditorData(self, editor, index):
        pass

    def setModelData(self, editor, model, index):
        pass

    def updateEditorGeometry(self, editor, option, index):
        super().updateEditorGeometry(editor, option, index)
        editor.setGeometry(option.rect)
