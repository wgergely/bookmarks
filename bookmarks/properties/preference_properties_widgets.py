# -*- coding: utf-8 -*-
"""A list of widgets used by the `PreferencesWidget`.

"""
from PySide2 import QtWidgets, QtCore, QtGui
from .. import common
from .. import ui

_about_widget_instance = None


class ScaleWidget(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(ScaleWidget, self).__init__(parent=parent)
        self.init_data()

    def init_data(self):
        size = QtCore.QSize(1, common.ROW_HEIGHT() * 0.8)

        self.blockSignals(True)
        for n in common.SCALE_FACTORS:
            name = '{}%'.format(int(n * 100))
            self.addItem(name)

            self.setItemData(
                self.count() - 1,
                n,
                role=QtCore.Qt.UserRole
            )
            self.setItemData(
                self.count() - 1,
                size,
                role=QtCore.Qt.SizeHintRole
            )
        self.setCurrentText('100%')
        self.blockSignals(False)


class AboutLabel(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(AboutLabel, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet(
            'background-color:{bg};border: {bd}px solid {bc};border-radius:{r}px;color:{c};padding: {r}px {r}px {r}px {r}px;'.format(
                bg=common.rgb(common.DARK_BG),
                bd=common.ROW_SEPARATOR(),
                bc=common.rgb(common.SEPARATOR),
                r=common.MARGIN() * 0.5,
                c=common.rgb(common.DISABLED_TEXT)
            )
        )
        self.init_data()

    def init_data(self):
        import importlib
        mod = importlib.import_module(__name__.split('.')[0])
        self.setText(mod.get_info())

    def mouseReleaseEvent(self, event):
        QtGui.QDesktopServices.openUrl(common.ABOUT_URL)


class AboutWidget(QtWidgets.QDialog):
    def __init__(self, parent=None):
        global _about_widget_instance
        _about_widget_instance = self

        super(AboutWidget, self).__init__(parent=parent)
        if not self.parent():
            common.set_custom_stylesheet(self)

        self.label = None
        self.ok_button = None

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        self.label = AboutLabel(parent=self)
        self.ok_button = ui.PaintedButton('Close', parent=self)

        self.layout().addWidget(self.label, 1)
        self.layout().addWidget(self.ok_button, 0)

    def _connect_signals(self):
        self.ok_button.clicked.connect(self.close)
