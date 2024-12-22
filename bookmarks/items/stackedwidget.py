import functools

from PySide2 import QtWidgets, QtCore

from .. import common


class StackedWidget(QtWidgets.QStackedWidget):
    """This stacked widget contains the main :class:`~bookmarks.items.bookmark_items.BookmarkItemView`,
    :class:`~bookmarks.items.asset_items.AssetItemView`, :class:`~bookmarks.items.file_items.FileItemView` and
    :class:`~bookmarks.items.favourite_items.FavouriteItemView`.
    widgets.

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('BrowserStackedWidget')

        self.animation_in_progress = False

        common.signals.tabChanged.connect(self.setCurrentIndex)

    def setCurrentIndex(self, idx):
        """Sets the current index of the ``StackedWidget``.

        Args:
            idx (int): The index of the widget to set.

        """
        idx = common.BookmarkTab if idx is None or idx is False else idx
        idx = idx if idx >= common.BookmarkTab else common.BookmarkTab

        if (
                not common.active_index(common.BookmarkTab).isValid()
                and idx in (common.BookmarkTab, common.AssetTab, common.FileTab)
        ):
            idx = common.BookmarkTab

        if (
                common.active_index(common.BookmarkTab).isValid()
                and not common.active_index(common.AssetTab).isValid()
                and idx in (common.AssetTab, common.FileTab)
        ):
            idx = common.AssetTab

        if idx > common.FavouriteTab:
            idx = common.FavouriteTab

        # Save tab to user settings
        common.settings.setValue('selection/current_tab', idx)

        current_index = self.currentIndex()
        if current_index == idx:
            return

        @QtCore.Slot()
        def animation_finished(a):
            anim = a.animationAt(1)
            if not anim:
                return
            if isinstance(anim.targetObject(), QtWidgets.QWidget):
                _idx = self.indexOf(anim.targetObject())
                super().setCurrentIndex(_idx)
                common.signals.tabChanged.emit(_idx)

        @QtCore.Slot()
        def animation_state_changed(state, old_state):
            if state == QtCore.QAbstractAnimation.Running:
                self.animation_in_progress = True
            if state == QtCore.QAbstractAnimation.Stopped:
                self.animation_in_progress = False

        animation = QtCore.QParallelAnimationGroup()
        animation.finished.connect(functools.partial(animation_finished, animation))
        animation.stateChanged.connect(animation_state_changed)

        duration = 200

        # Create animation for outgoing widget
        out_anim = QtCore.QPropertyAnimation(self.widget(current_index), b"geometry")
        out_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        out_anim.setDuration(duration)

        out_rect = self.currentWidget().geometry()
        if current_index > idx:
            out_rect.moveLeft(self.width())
        else:
            out_rect.moveLeft(-self.width())
        out_anim.setStartValue(self.currentWidget().geometry())
        out_anim.setEndValue(out_rect)

        # Create animation for incoming widget
        in_anim = QtCore.QPropertyAnimation(self.widget(idx), b"geometry")
        in_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        in_anim.setDuration(duration)

        in_rect = self.currentWidget().geometry()
        if current_index > idx:
            in_rect.moveLeft(-in_rect.width())
        else:
            in_rect.moveLeft(in_rect.width())
        in_anim.setStartValue(in_rect)
        in_anim.setEndValue(self.currentWidget().geometry())

        out_op = QtCore.QPropertyAnimation(self.widget(current_index).graphicsEffect(), b"opacity")
        out_op.setStartValue(1.0)
        out_op.setEndValue(0.0)
        in_op = QtCore.QPropertyAnimation(self.widget(idx).graphicsEffect(), b"opacity")
        in_op.setStartValue(0.0)
        in_op.setEndValue(1.0)

        animation.addAnimation(out_anim)
        animation.addAnimation(in_anim)
        animation.addAnimation(out_op)
        animation.addAnimation(in_op)

        animation.start(QtCore.QPropertyAnimation.DeleteWhenStopped)
        self.widget(idx).show()

    def showEvent(self, event):
        """Event handler.

        """
        if self.currentWidget():
            self.currentWidget().setFocus()
