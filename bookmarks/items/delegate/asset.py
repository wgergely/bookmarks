import copy

from PySide2 import QtCore, QtGui, QtWidgets

from ... import common, ui
from ... import database
from ... import images
from ... import progress

from . import base


class AssetItemViewDelegate(base.ItemDelegate):
    """The delegate used to render
    :class:`bookmarks.items.asset_items.AssetItemView` items.

    """
    #: The item's default thumbnail image
    fallback_thumb = 'icon_bw_sm'

    def paint(self, painter, option, index):
        """Paints the extra columns of
        :class:`~bookmarks.items.asset_items.AssetItemView`.

        """
        ctx = super().paint(painter, option, index)

        if not ctx:
            return

        if index.column() < 4:
            return

        source_model = index.model().sourceModel()
        source_index = index.model().mapToSource(index)

        p = source_model.parent_path()
        k = source_model.task()
        t = common.FileItem

        _data = common.get_data(p, k, t)

        if not _data:
            return
        if source_index.row() not in _data:
            return
        if not _data[source_index.row()][common.AssetProgressRole]:
            return
        if index.column() - 4 not in _data[source_index.row()][common.AssetProgressRole]:
            return

        data = _data[source_index.row()][common.AssetProgressRole][index.column() - 4]

        right_edge = self.paint_progress_background(ctx, data)
        self.paint_progress_name(ctx, data, right_edge)
        self.paint_progress_leading_shadow(ctx)

        return ctx

    @base.save_painter
    def paint_progress_leading_shadow(self, ctx):
        if ctx.index.column() != 4:
            return

        rect = QtCore.QRect(ctx.rect)
        o = common.Size.Margin(3.0)
        rect.setWidth(o)

        ctx.painter.setOpacity(0.5)
        pixmap = images.rsc_pixmap(
            'gradient', None, rect.height()
        )
        ctx.painter.drawPixmap(rect, pixmap, pixmap.rect())
        rect.setWidth(o * 0.5)
        ctx.painter.drawPixmap(rect, pixmap, pixmap.rect())

    @base.save_painter
    def paint_progress_background(self, ctx, data):
        rect = QtCore.QRect(ctx.rect)
        rect.setBottom(rect.bottom() - common.Size.Separator())

        # Draw background
        color = progress.STATES[data['value']]['color']
        ctx.painter.setBrush(color)
        ctx.painter.setPen(QtCore.Qt.NoPen)
        if ctx.hover:
            ctx.painter.setOpacity(1.0)
        else:
            ctx.painter.setOpacity(0.85)
        ctx.painter.drawRect(rect)

        if ctx.selected:
            _color = common.Color.LightBackground()
            ctx.painter.setBrush(_color)
            ctx.painter.setOpacity(0.15)
            ctx.painter.drawRect(rect)

        rect.setWidth(rect.height())
        center = rect.center()

        r = common.Size.Margin()
        rect.setSize(QtCore.QSize(r, r))
        rect.moveCenter(center)
        rect.moveLeft(ctx.rect.left() + common.Size.Indicator(2.0))

        if data['value'] == progress.OmittedState:
            if ctx.hover:
                ctx.painter.setOpacity(1.0)
            else:
                ctx.painter.setOpacity(0.1)
        else:
            ctx.painter.setOpacity(0.5)

        pixmap = images.rsc_pixmap(
            progress.STATES[data['value']]['icon'],
            color=None,
            size=r
        )

        ctx.painter.drawPixmap(rect, pixmap, pixmap.rect())
        return rect.right()

    @base.save_painter
    def paint_progress_name(self, ctx, data, right_edge):

        text = progress.STATES[data['value']]['name']

        if data['value'] == progress.OmittedState:
            text = f'Edit\n{data["name"]}' if ctx.hover else ''
            ctx.painter.setOpacity(0.25)
        ctx.painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 255)))
        _rect = QtCore.QRect(ctx.rect)

        _o = common.Size.Indicator(2.0)
        _rect.setLeft(right_edge + _o)

        font, metrics = common.Font.LightFont(common.Size.SmallText())
        ctx.painter.setFont(font)
        ctx.painter.drawText(
            _rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, text
        )

    def createEditor(self, parent, option, index):
        """Creates a combobox editor used to change a state value.

        """
        if index.column() < 4:
            return super().createEditor(parent, option, index)

        editor = QtWidgets.QComboBox(parent=parent)
        editor.setStyleSheet(
            f'border-radius:0px;'
            f'selection-background-color:rgba(180,180,180,255);'
            f'margin:0px;'
            f'padding:0px;'
            f'min-width:{common.Size.DefaultWidth(0.33)}px;'
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
        if index.column() < 4:
            return super().setEditorData(editor, index)

        source_model = index.model().sourceModel()
        source_index = index.model().mapToSource(index)

        p = source_model.parent_path()
        k = source_model.task()
        t = common.FileItem

        _data = common.get_data(p, k, t)
        data = _data[source_index.row()][common.AssetProgressRole][index.column() - 4]

        for state in sorted(data['states']):
            editor.addItem(
                progress.STATES[state]['name'],
                userData=state
            )
            icon = progress.STATES[state]['icon']

            editor.setItemIcon(
                editor.count() - 1,
                ui.get_icon(icon, color=None),
            )
            editor.setItemData(
                editor.count() - 1,
                progress.STATES[state]['color'],
                role=QtCore.Qt.BackgroundRole
            )
            editor.setItemData(
                editor.count() - 1,
                QtCore.QSize(1, common.Size.RowHeight(1.0)),
                role=QtCore.Qt.SizeHintRole
            )
        editor.setCurrentText(
            progress.STATES[data['value']]['name']
        )

    def setModelData(self, editor, model, index):
        """Saves the current state value to the bookmark database.

        """
        if index.column() < 4:
            return super().setModelData(editor, model, index)

        source_model = index.model().sourceModel()
        source_index = index.model().mapToSource(index)

        p = source_model.parent_path()
        k = source_model.task()
        t = common.FileItem

        data = common.get_data(p, k, t)

        # We don't have to modify the internal data directly because
        # the db.set_value call will trigger an item refresh
        progress_data = copy.deepcopy(data[source_index.row()][common.AssetProgressRole])
        progress_data[index.column() - 4]['value'] = editor.currentData()

        # Write current data to the database
        pp = data[source_index.row()][common.ParentPathRole]
        db = database.get(*pp[0:3])
        db.set_value(
            data[source_index.row()][common.PathRole],
            'progress',
            progress_data,
            database.AssetTable
        )

    def updateEditorGeometry(self, editor, option, index):
        """Resizes the editor.

        """
        if index.column() < 4:
            super().updateEditorGeometry(editor, option, index)
            return

        super().updateEditorGeometry(editor, option, index)
        editor.setGeometry(option.rect)
