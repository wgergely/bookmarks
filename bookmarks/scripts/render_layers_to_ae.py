import os
import re

from PySide2 import QtCore

from .. import common
from .. import database
from ..tokens import tokens

RENDER_NAME_TEMPLATE = '<RenderLayer>/<Version>/<RenderPass>/<RenderLayer>_<RenderPass>_<Version>'
pattern = r'{source_dir}/(.+)/(.+)/(.+)/.+\_\d+.exr$'


def recursive_parse(path):

    for entry in os.scandir(path):
        if entry.is_dir():
            yield from recursive_parse(entry.path)
            continue

        if '_broken' in entry.name:
            continue
        if os.path.splitext(entry.name)[-1] != '.exr':
            continue

        yield entry.path.replace('\\', '/')


def get_footage_sources():
    source_dir = common.active('task', path=True)
    if not source_dir:
        raise RuntimeError('No active task')
    if not QtCore.QFileInfo(source_dir).isDir():
        raise RuntimeError('Active task is not a directory')

    db = database.get(*common.active('root', args=True))
    framerate = db.value(db.source(), 'framerate', database.BookmarkTable)

    data = {}
    for path in recursive_parse(source_dir):
        seq = common.get_sequence(path)
        if not seq:
            continue

        match = re.match(pattern.format(source_dir=source_dir), path, re.IGNORECASE)
        if not match:
            continue

        k = f'{seq.group(1).strip("/_-.")}{seq.group(3).strip("/_-.")}'.split('/')[-1]
        if k not in data:
            data[k] = {
                'name': f'{match.group(1)}  ->  {match.group(3)}  ({match.group(2)})',
                'files': [],
                'layer': match.group(1),
                'version': match.group(2),
                'pass': match.group(3),
                'framerate': framerate,
            }

        data[k]['files'].append(path)

    return data


def generate_jsx_script(footage_sources):
    db = database.get(*common.active('root', args=True))

    # Look for framerate and resolution in the bookmark...
    bookmark_framerate = db.value(db.source(), 'framerate', database.BookmarkTable)
    bookmark_width = db.value(db.source(), 'width', database.BookmarkTable)
    bookmark_height = db.value(db.source(), 'height', database.BookmarkTable)

    # ...and if not found, look for it in the asset
    asset_framerate = db.value(common.active('asset', path=True), 'framerate', database.AssetTable)
    asset_width = db.value(common.active('asset', path=True), 'width', database.AssetTable)
    asset_height = db.value(common.active('asset', path=True), 'height', database.AssetTable)

    # If still not found, use default values
    framerate = asset_framerate or bookmark_framerate or 25
    width = asset_width or bookmark_width or 1920
    height = asset_height or bookmark_height or 1080

    cut_in = db.value(common.active('asset', path=True), 'cut_in', database.AssetTable)
    cut_out = db.value(common.active('asset', path=True), 'cut_out', database.AssetTable)

    config = tokens.get(*common.active('root', args=True), force=True)

    # TODO: 'asset1' is hardcoded here, but it should correspond to the asset name
    #  ({asset1} in the Studio Aka SG pipeline, for example)
    comp_name = config.expand_tokens('{asset1}_comp', asset=common.active('asset'))

    jsx_script = ""

    # Begin ExtendScript
    jsx_script += """
var project = app.project;

// Check if the "cgi" folder already exists
var cgi_folder = null;
for (var i = 1; i <= project.numItems; i++) {
    if (project.item(i) instanceof FolderItem && project.item(i).name == 'cgi') {
        cgi_folder = project.item(i);
        break;
    }
}
// If the "cgi" folder does not exist, create it
if (!cgi_folder) {
    cgi_folder = project.items.addFolder('cgi');
}

function importFootage(path, framerate, name) {
    // Check if the footage item already exists
    for (var i = 1; i <= project.numItems; i++) {
        if (project.item(i) instanceof FootageItem && project.item(i).name == name) {
            return;  // Footage item already exists, skip importing
        }
    }
    var importOptions = new ImportOptions(File(path));
    importOptions.sequence = true;
    var footageItem = project.importFile(importOptions);
    footageItem.name = name;
    footageItem.mainSource.conformFrameRate = framerate;
    footageItem.parentFolder = cgi_folder;
    return footageItem;
}

app.beginUndoGroup('Import Footage');
    """

    # Iterate over footage sources and add to the ExtendScript
    for name, data in footage_sources.items():
        # Sort the files to get the first one
        files = sorted(data['files'])
        first_file = files[0]
        jsx_script += f'var footageItem = importFootage("{first_file}", {data["framerate"]}, "{data["name"]}");\n'

    # Create new composition if it doesn't exist yet
    jsx_script += f"""
var comp = null;
for (var i = 1; i <= project.numItems; i++) {{
    if (project.item(i) instanceof CompItem && project.item(i).name == '{comp_name}') {{
        comp = project.item(i);
        break;
    }}
}}
if (!comp) {{
    comp = project.items.addComp('{comp_name}', {width}, {height}, 1, ({cut_out}-{cut_in})/{framerate}, {framerate});
    comp.layers.add(footageItem);
}}
comp.workAreaStart = {cut_in}/{framerate};
    """

    # Close the undo group
    jsx_script += "app.endUndoGroup();\n"

    return jsx_script


def run():
    data = get_footage_sources()
    with open(f'{common.active("task", path=True)}/import_footage.jsx', 'w') as f:
        f.write(generate_jsx_script(data))
        common.show_message(
            'Render Layers to After Effects',
            body=f'Import script generated successfully and saved to:\n{common.active("task", path=True)}/import_footage.jsx',
            message_type='success',
        )