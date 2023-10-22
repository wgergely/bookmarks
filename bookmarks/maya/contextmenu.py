"""Maya-specific context menus.

"""
import collections
import functools
import importlib
import json
import os

from PySide2 import QtCore

try:
    from maya import cmds
except ImportError:
    raise ImportError('Could not find the Maya modules.')

from .. import common
from .. import ui
from .. import contextmenu
from .. import database
from . import actions
from . import export


class PluginContextMenu(contextmenu.BaseContextMenu):
    """Maya plugin context menu.

    """

    def setup(self):
        """Creates the context menu.

        """
        self.scripts_menu()
        self.separator()
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
        self.separator()
        self.hud_menu()

    def apply_bookmark_settings_menu(self):
        """Apply settings action.

        """
        server = common.active('server')
        job = common.active('job')
        root = common.active('root')
        asset = common.active('asset')

        if not all((server, job, root, asset)):
            return

        self.menu[contextmenu.key()] = {
            'text': 'Apply scene settings...',
            'icon': ui.get_icon('check', color=common.color(common.color_green)),
            'action': actions.apply_settings
        }

    def save_menu(self):
        """Save scene action.

        """
        if not all(common.active('asset', args=True)):
            return

        scene = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

        self.menu[contextmenu.key()] = {
            'text': 'Save Scene...',
            'icon': ui.get_icon('add_file', color=common.color(common.color_green)),
            'action': lambda: actions.save_scene(increment=False)
        }
        if common.get_sequence(scene.fileName()):
            self.menu[contextmenu.key()] = {
                'text': 'Incremental Save...',
                'icon': ui.get_icon('add_file'),
                'action': lambda: actions.save_scene(increment=True)
            }

    def open_import_scene_menu(self):
        """Scene open actions.

        """
        if not self.index.isValid():
            return

        path = self.index.data(common.PathRole)
        path = common.get_sequence_end_path(path)
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
        """Cache export actions.

        """
        k = contextmenu.key()
        self.menu[k] = {
            'text': 'Export...',
            'icon': ui.get_icon('set', color=None),
            'action': export.show
        }

    def import_camera_menu(self):
        """Import camera template action.

        """
        k = contextmenu.key()
        self.menu[k] = {
            'text': 'Import Camera Template',
            'action': actions.import_camera_preset
        }

    def viewport_presets_menu(self):
        """Viewport display preset action.
        """
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
        """Capture viewport action.

        """
        k = 'Capture Viewport'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('capture_thumbnail')

        width = cmds.getAttr("defaultResolution.width")
        height = cmds.getAttr("defaultResolution.height")

        def _size(n):
            return int(int(width) * n), int(int(height) * n)

        for n in (1.0, 0.5, 0.25, 1.5, 2.0):
            w, h = _size(n)
            self.menu[k][f'capture{n}'] = {
                'text': f'Capture  ｜  @{n}  |  {w}x{h}px',
                'action': functools.partial(actions.capture_viewport, size=n),
                'icon': ui.get_icon('capture_thumbnail'),
            }

    def show_window_menu(self):
        """Show plugin window action.

        """
        if not hasattr(self.parent(), 'clicked'):
            return
        self.menu['show'] = {
            'icon': ui.get_icon('icon_bw', color=None),
            'text': f'Toggle {common.product.title()}',
            'action': self.parent().clicked.emit
        }

    def scripts_menu(self):
        """Custom scripts deployed with the Maya module.

        """
        k = 'Scripts'
        self.menu[k] = collections.OrderedDict()
        self.menu[f'{k}:icon'] = ui.get_icon('icon')

        p = os.path.normpath(f'{__file__}/../scripts/scripts.json')
        if not os.path.isfile(p):
            raise RuntimeError(f'File not found: {p}')

        with open(p, 'r') as f:
            data = json.load(f)

        @common.debug
        @common.error
        def _run(name):
            module = importlib.import_module(f'.scripts.{name}', package=__package__)

            if not hasattr(module, 'run'):
                raise RuntimeError(f'Failed to run module: {name} - Missing run() function in {module}!')

            module.run()

        for v in data.values():
            if v['name'] == 'separator':
                self.separator(menu=self.menu[k])
                continue

            # Check if the script needs_active
            if 'needs_active' in v and v['needs_active']:
                if not common.active(v['needs_active'], args=True):
                    continue
            # Check if the script needs_active
            if 'needs_application' in v and v['needs_application']:
                if not common.active('root', args=True):
                    continue
                # Get the bookmark database
                db = database.get(*common.active('root', args=True))
                applications = db.value(db.source(), 'applications', database.BookmarkTable)
                if not applications:
                    continue
                if not [app for app in applications.values() if v['needs_application'].lower() in app['name'].lower()]:
                    continue
            if 'icon' in v and v['icon']:
                icon = ui.get_icon(v['icon'])
            else:
                icon = ui.get_icon('icon')

            self.menu[k][contextmenu.key()] = {
                'text': v['name'],
                'action': functools.partial(_run, v['module']),
                'icon': icon,
            }

    def hud_menu(self):
        k = contextmenu.key()
        self.menu[k] = {
            'text': 'Toggle HUD',
            'action': actions.toggle_hud
        }


class MayaButtonWidgetContextMenu(PluginContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, parent=None):
        super().__init__(
            QtCore.QModelIndex(), parent=parent
        )


class MayaWidgetContextMenu(PluginContextMenu):
    """Context menu associated with :class:`MayaWidget`.

    """

    @common.error
    @common.debug
    def setup(self):
        """Creates the context menu.

        """
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
        self.separator()
        self.hud_menu()
