import collections
import functools

from PySide2 import QtCore
from maya import cmds

from .. import common
from .. import ui
from .. import contextmenu
from . import actions
from . import export


class PluginContextMenu(contextmenu.BaseContextMenu):
    def setup(self):
        self.apply_bookmark_settings_menu()
        self.separator()
        self.save_menu()
        self.separator()
        self.open_import_scene_menu()
        self.separator()
        self.export_menu()
        self.separator()
        self.import_camera_menu()
        self.separator()
        self.viewport_presets_menu()
        self.capture_menu()

    def apply_bookmark_settings_menu(self):
        server = common.active(common.ServerKey)
        job = common.active(common.JobKey)
        root = common.active(common.RootKey)
        asset = common.active(common.AssetKey)

        if not all((server, job, root, asset)):
            return

        self.menu[contextmenu.key()] = {
            'text': 'Apply scene settings...',
            'icon': ui.get_icon('check', color=common.color(common.GreenColor)),
            'action': actions.apply_settings
        }

    def save_menu(self):
        if not all(common.active(common.AssetKey, args=True)):
            return

        scene = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

        self.menu[contextmenu.key()] = {
            'text': 'Save Scene...',
            'icon': ui.get_icon('add_file', color=common.color(common.GreenColor)),
            'action': lambda: actions.save_scene(increment=False)
        }
        if common.get_sequence(scene.fileName()):
            self.menu[contextmenu.key()] = {
                'text': 'Incremental Save...',
                'icon': ui.get_icon('add_file'),
                'action': lambda: actions.save_scene(increment=True)
            }

    def open_import_scene_menu(self):
        if not self.index.isValid():
            return

        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        _s = file_info.suffix().lower()
        if _s not in ('ma', 'mb', 'abc'):
            return

        maya_pixmap = ui.get_icon('maya', color=None)
        maya_reference_pixmap = ui.get_icon('maya_reference', color=None)

        self.menu[contextmenu.key()] = {
            'text': 'Open',
            'icon': maya_pixmap,
            'action': functools.partial(
                actions.open_scene,
                file_info.filePath()
            )
        }
        self.menu[contextmenu.key()] = {
            'text': 'Import',
            'icon': maya_pixmap,
            'action': functools.partial(
                actions.import_scene,
                file_info.filePath(),
                reference=False
            )
        }
        self.menu[contextmenu.key()] = {
            'text': 'Reference',
            'icon': maya_reference_pixmap,
            'action': functools.partial(
                actions.import_scene,
                file_info.filePath(),
                reference=True
            )
        }

    def export_menu(self):
        k = contextmenu.key()
        self.menu[k] = {
            'text': 'Export...',
            'icon': ui.get_icon('set', color=None),
            'action': export.show
        }

    def import_camera_menu(self):
        k = contextmenu.key()
        self.menu[k] = {
            'text': 'Import Camera Template',
            'action': actions.import_camera_preset
        }

    def viewport_presets_menu(self):
        from . import viewport
        k = 'Viewport Presets'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('image')

        for _k in viewport.presets:
            self.menu[k][contextmenu.key()] = {
                'icon': ui.get_icon('image'),
                'text': _k,
                'action': functools.partial(actions.apply_viewport_preset, _k)
            }

    def capture_menu(self):
        k = 'Capture Viewport'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('capture_thumbnail')

        width = cmds.getAttr("defaultResolution.width")
        height = cmds.getAttr("defaultResolution.height")

        def size(n):
            return (int(int(width) * n), int(int(height) * n))

        for n in (1.0, 0.5, 0.25, 1.5, 2.0):
            w, h = size(n)
            self.menu[k][f'capture{n}'] = {
                'text': f'Capture  |  @{n}  |  {w}x{h}px',
                'action': functools.partial(actions.capture_viewport, size=n),
                'icon': ui.get_icon('capture_thumbnail'),
            }

    def show_window_menu(self):
        if not hasattr(self.parent(), 'clicked'):
            return
        self.menu['show'] = {
            'icon': ui.get_icon('icon_bw', color=None),
            'text': f'Toggle {common.product.title()}',
            'action': self.parent().clicked.emit
        }


class MayaButtonWidgetContextMenu(PluginContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, parent=None):
        super(MayaButtonWidgetContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent
        )


class MayaWidgetContextMenu(PluginContextMenu):
    @common.error
    @common.debug
    def setup(self):
        self.apply_bookmark_settings_menu()
        self.separator()
        self.save_menu()
        self.separator()
        self.open_import_scene_menu()
        self.separator()
        self.export_menu()
        self.separator()
        self.import_camera_menu()
        self.separator()
        self.viewport_presets_menu()
        self.capture_menu()
