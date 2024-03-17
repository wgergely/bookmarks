"""
This is a utility script to send image sequences to After Effects rendered with the Maya.

The script expects the images sequences to use the Maya specified render template format.
Any valid image sequences will be included in an ExtendScript script that will be sent to
After Effects.

"""
import os
import re

try:
    from PySide6 import QtWidgets, QtGui, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtGui, QtCore

from .. import actions
from .. import common
from .. import database
from ..tokens import tokens

#: The render name template used by Maya
RENDER_NAME_TEMPLATE = '<RenderLayer>/<Version>/<RenderPass>/<RenderLayer>_<RenderPass>_<Version>'
#: The pattern used to match the render name template
pattern = r'{source_dir}/(.+)/(.+)/(.+)/.+\.[a-z]{{2,4}}$'


def items_it():
    """Yield a list of paths of the currently visible file items.

    """
    if not common.widget():
        return

    if not common.active('task'):
        raise RuntimeError('An active task folder must be set to export items.')

    model = common.model(common.FileTab)
    for idx in range(model.rowCount()):
        index = model.index(idx, 0)
        if not index.isValid():
            continue

        # Skip broken render images (RoyalRender)
        if '_broken__' in index.data(QtCore.Qt.DisplayRole):
            continue

        path = index.data(common.PathRole)
        if not path:
            continue
        yield index


def get_footage_sources():
    """Traverse over the active task folder's subdirectories and return a dictionary of image sequences.

    """
    source_dir = common.active('task', path=True)
    if not source_dir:
        raise RuntimeError('Must have an active task folder selected!')

    db = database.get(*common.active('root', args=True))
    framerate = db.value(db.source(), 'framerate', database.BookmarkTable)

    data = {}
    _pattern = pattern.format(source_dir=source_dir)

    for index in items_it():
        seq = index.data(common.SequenceRole)
        path = index.data(common.PathRole)

        if not seq:
            print(f'Skipping non-sequence item:\n{path}')
            continue

        match = re.match(_pattern, path, re.IGNORECASE)
        if not match:
            print(f'Skipping malformed sequence:\n{path}')
            continue

        k = f'{seq.group(1).strip("/_-.")}{seq.group(3).strip("/_-.")}'.split('/')[-1]
        if k not in data:
            print(f'Found sequence:\n{path}')
            data[k] = {
                'name': f'{match.group(1)}  ->  {match.group(3)}  ({match.group(2)})',
                'files': [],
                'layer': match.group(1),
                'version': match.group(2),
                'pass': match.group(3),
                'framerate': framerate,
            }

        data[k]['files'].append(common.get_sequence_start_path(path))

    return data


def generate_jsx_script(footage_sources):
    db = database.get(*common.active('root', args=True))

    # Look for framerate and resolution in the bookmark...
    bookmark_framerate = db.value(db.source(), 'framerate', database.BookmarkTable)
    bookmark_width = db.value(db.source(), 'width', database.BookmarkTable)
    bookmark_height = db.value(db.source(), 'height', database.BookmarkTable)

    # ...and if not found, look for it in the asset
    asset_framerate = db.value(common.active('asset', path=True), 'asset_framerate', database.AssetTable)
    asset_width = db.value(common.active('asset', path=True), 'asset_width', database.AssetTable)
    asset_height = db.value(common.active('asset', path=True), 'asset_height', database.AssetTable)

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
    var existingFootageItem = null;

    // Check if the footage item already exists
    for (var i = 1; i <= app.project.numItems; i++) {
        var currentItem = app.project.item(i);
        if (currentItem instanceof FootageItem && currentItem.name == name) {
            existingFootageItem = currentItem;
            break;
        }
    }

    var io = new ImportOptions();
    io.file = File(path);
    io.sequence = true;
    
    if (io.canImportAs(ImportAsType.FOOTAGE)) {
        io.importAs = ImportAsType.FOOTAGE;
    } else {
        alert('Could not import footage as a sequence. Please check the file path and try again.');
        return;
    }

    // If the footage exists and its source differs from the intended source
    if (existingFootageItem && existingFootageItem.mainSource.file.path != path) {
        var newFootage = app.project.importFile(io);
        
        existingFootageItem.replaceWithSequence(newFootage.mainSource.file, true);
        existingFootageItem.mainSource.conformFrameRate = framerate;
        
        // Clean up by removing the temporarily imported footage
        newFootage.remove();

    } else if (!existingFootageItem) {  // If footage doesn't exist
        
        var footageItem = app.project.importFile(io);
        footageItem.name = name;
        footageItem.mainSource.conformFrameRate = framerate;
        footageItem.parentFolder = cgi_folder;
        return footageItem;
    }
}

app.beginUndoGroup('Import Footage');"""

    # Create new composition if it doesn't exist yet
    jsx_script += f"""
var comp = null;
for (var i = 1; i <= project.numItems; i++) {{
    if (project.item(i) instanceof CompItem && project.item(i).name == '{comp_name}') {{
        comp = project.item(i);
        // Apply the cut_out and cut_in values to the composition
        break;
    }}
}}
if (!comp) {{
    comp = project.items.addComp('{comp_name}', {width}, {height}, 1, ({cut_out}-{cut_in})/{framerate}, {framerate});
}}

// Apply the cut out and cut in values to the composition
comp.duration = ({cut_out}-{cut_in}+1)/{framerate};
comp.displayStartFrame = {cut_in};
comp.workAreaStart = 0;
comp.workAreaDuration = comp.duration;

"""

    # Iterate over footage sources and add to the ExtendScript
    for name, data in footage_sources.items():
        # Sort the files to get the first one
        files = sorted(data['files'])
        first_file = files[0]
        jsx_script += f'var footageItem = importFootage("{first_file}", {data["framerate"]}, "{data["name"]}");\n'

    # Close the undo group
    jsx_script += "app.endUndoGroup();\n"

    return jsx_script, footage_sources


def send_to_after_effects(script_path):
    """Send the generated script to After Effects.

    Args:
        script_path (str): The path to the generated script.

    """

    if not common.active('root', args=True):
        raise RuntimeError('Must have an active bookmark')

    # Get the path to the executable
    possible_names = ['afterfx', 'aftereffects', 'afx']
    for name in possible_names:
        executable = common.get_binary(name)
        if executable:
            break
    else:
        raise RuntimeError(f'Could not find After Effects. Tried: {possible_names}')

    # Call after effects using with the generated script as an argument:
    actions.execute_detached(executable, ['-r', os.path.normpath(script_path)])

    return True


def run():
    """Run the script.

    """
    data = get_footage_sources()
    if not data:
        common.show_message(
            'No sequences found.',
            body='No sequences were found in the current task folder.',
        )
        return

    script_path = f'{common.active("task", path=True)}/import_footage.jsx'
    jsx_script, footage_sources = generate_jsx_script(data)
    with open(script_path, 'w') as f:
        f.write(jsx_script)

    if not send_to_after_effects(script_path):
        print('Could not find After Effects. Footage was not sent.')

    common.show_message(
        'Success.',
        body=f'Found {len(footage_sources)} items. An import script was saved to:\n'
             f'{common.active("task", path=True)}/import_footage.jsx',
        message_type='success',
    )
