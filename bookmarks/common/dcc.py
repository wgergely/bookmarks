import functools
import re

DCC_FILE_FORMATS = {
    # 3D Scene Layout and World Building
    'city_engine': ('cej',),
    'marmoset': ('mtb',),

    # 2D Image Editors
    'corel_draw': ('cdr',),
    'photoshop': ('psd', 'psb', 'psq'),
    'illustrator': ('ai', 'eps'),
    'indesign': ('indd',),

    # Vector Graphics
    'inkscape': ('svg', 'svgz'),

    # Video Editing Software
    'premiere': ('prproj', 'ppj'),
    'fcp': ('fcp', 'fcpx'),
    'final_cut': ('fcp', 'fcpx'),
    'avid': ('avp', 'avb'),
    'resolve': ('drp', 'drt'),
    'davince': ('drp', 'drt'),

    # Playback
    'rv': ('rv',),
    'godot': ('tscn', 'gd'),

    # Compositing Apps
    'nuke': ('nk', 'nk~'),
    'after_effects': ('aep', 'aepx'),
    'afx': ('aep', 'aepx'),
    'fusion': ('comp',),
    'flame': ('clip', 'batch'),

    # 2D Animation
    'moho': ('moho',),
    'tv_paint': ('tvpp',),
    'animate': ('fla', 'xfl'),
    'flash': ('fla', 'xfl'),
    'toon_boom': ('xstage', 'tpl'),
    'krita': ('kra',),

    # 3D Apps
    'houdini': ('hip', 'hiplc', 'hipnc', 'hud'),
    'maya': ('ma', 'mb'),
    'blender': ('blend',),
    '3ds_max': ('max',),
    'cinema_4d': ('c4d',),
    'katana': ('katana',),
    'unreal': ('umap', 'uasset'),
    'unity': ('unity', 'prefab'),
    'clarisse': ('project',),
    'modo': ('lxo',),
    'bifrost': ('bif',),

    # Sculpting & Texturing
    'mudbox': ('mud',),
    '3dcoat': ('3b',),
    'substance_painter': ('spp',),
    'substance_designer': ('sbs', 'sbsar'),
    'substance': ('sbs', 'sbsar', 'spp'),
    'zbrush': ('zpr', 'ztl', 'zbr', 'zpac'),
    'mari': ('mra', 'ptx'),

    # Simulation
    'marvelous': ('zprj',),
    'speed_tree': ('spm', 'sts'),
    'character_creator': ('ccProject', 'ccAvatar'),
    'real_flow': ('flw', 'fld', 'rcproj'),
    'gaea': ('tor',),

    # Matchmoving
    'mocha': ('mocha',),
    'synth_eyes': ('sni', 'sni.gz'),
}

DCC_ALIASES = {
    # 3D Scene Layout and World Building
    'city_engine': ['CityEngine', 'CEJ'],

    # 2D Image Editors
    'corel_draw': ['CorelDraw', 'Corel'],
    'photoshop': ['Photoshop', 'PS', 'Adobe PS', 'Adobe Photoshop'],
    'illustrator': ['Illustrator', 'Adobe Illustrator', 'AI'],
    'indesign': ['InDesign', 'ID', 'Adobe InDesign'],

    # Vector Graphics
    'inkscape': ['Inkscape', 'SVG Editor'],

    # Video Editing Software
    'premiere': ['Premiere', 'Adobe Premiere', 'Premiere Pro', 'PPRO'],
    'fcp': ['Final Cut Pro', 'FCP', 'FCPX'],
    'avid': ['Avid', 'Avid Media Composer'],
    'resolve': ['DaVinci Resolve', 'Resolve', 'Davinci'],

    # Playback
    'rv': ['RV', 'Tweak Software RV', 'ShotGrid RV', 'Shotgun RV', 'ShotgunRV', 'ShotGridRV'],
    'godot': ['Godot Engine', 'Godot'],

    # Compositing Apps
    'nuke': ['Nuke', 'The Foundry Nuke'],
    'after_effects': ['After Effects', 'AFX', 'AE', 'Adobe After Effects', 'AfterFX'],
    'fusion': ['Fusion', 'Blackmagic Fusion'],
    'flame': ['Flame', 'Autodesk Flame'],

    # 2D Animation
    'moho': ['Moho', 'Anime Studio'],
    'tv_paint': ['TVPaint', 'TV Paint'],
    'animate': ['Animate', 'Adobe Animate', 'Adobe Animate', 'Flash'],
    'toon_boom': ['Toon Boom', 'Toon Boom Harmony'],
    'krita': ['Krita'],

    # 3D Apps
    'houdini': ['Houdini', 'SideFX Houdini', 'Houdini FX', 'Houdini Core', 'Hou'],
    'maya': ['Maya', 'Autodesk Maya'],
    'blender': ['Blender'],
    '3ds_max': ['3ds Max', 'Autodesk 3ds Max'],
    'cinema_4d': ['Cinema 4D', 'C4D'],
    'katana': ['Katana'],
    'unreal': ['UnrealEngine', 'Unreal Engine', 'UE', 'Unreal', 'UE4', 'UE5'],
    'unity': ['Unity', 'Unity3D'],
    'clarisse': ['Clarisse'],
    'modo': ['Modo'],
    'bifrost': ['Bifrost'],

    # Sculpting & Texturing
    'mudbox': ['Mudbox', 'Autodesk Mudbox'],
    '3dcoat': ['3DCoat'],
    'substance_painter': ['Substance Painter', 'SP'],
    'substance_designer': ['Substance Designer', 'SD'],
    'substance': ['Substance', 'Allegorithmic Substance', 'Adobe Substance'],
    'zbrush': ['ZBrush'],
    'mari': ['Mari'],

    # Simulation
    'marvelous': ['Marvelous Designer', 'MD'],
    'speed_tree': ['SpeedTree'],
    'character_creator': ['Character Creator', 'CC'],
    'real_flow': ['RealFlow'],
    'gaea': ['Gaea'],

    # Matchmoving
    'mocha': ['Mocha', 'Mocha Pro'],
    'synth_eyes': ['SynthEyes', 'Syntheyes'],
}

CACHE_FORMATS = {
    'abc'
    'hda',
    'ass',
    'bgeo',
    'fbx',
    'geo',
    'ifd',
    'obj',
    'rs',
    'sc',
    'sim',
    'vdb',
    'usd',
    'usda',
    'usdc'
    'usdz',
    'vrscene',
    'mi',
    'prt',
    'bin',
    'gltf',
    'glb',
    'ply',
    'stl',
    '3ds',
    'dae',
    'vrmesh'
    'rib',
    'orbx',
    'ocs',
    'uasset',
    'umap',
    'ma',
    'mb',
    'blend',
    'hip',
    'hiplc',
    'c4d',
    'max',
}


@functools.cache
def normalize_dcc_name(dcc_name):
    """
    Normalize the given DCC name by removing years, versions, non-essential words,
    and non-alphanumeric characters.

    Args:
        dcc_name (str): The original DCC name.

    Returns:
        str: The normalized DCC name.
    """
    # Convert to lowercase for consistency
    dcc_name = dcc_name.lower()

    # Replace non-word characters (excluding underscores and hyphens) with spaces
    dcc_name = re.sub(r'[_\-]', ' ', dcc_name).strip()

    # Split into words
    words = dcc_name.split()

    # Words to keep
    kept_words = []

    # Patterns to identify version indicators and years
    version_patterns = [
        r'v\d+(\.\d+)*[a-z]*',  # v1, v1.2, v1.2.3a
        r'version\d+(\.\d+)*[a-z]*',  # version1, version1.2b
        r'release\d+(\.\d+)*[a-z]*',  # release1, release1.2c
        r'\d{4}',  # Years like 2020
        r'\d+(\.\d+)*[a-z]*',  # Numbers with optional letters at the end
        r'\d{1}r\d{1,2}',  # Numbers followed by letters (e.g., '4r8')
        r'r\d{2}',  # Letters followed by numbers (e.g., 'r23')
    ]

    # Compile regex patterns
    version_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in version_patterns]

    # Words to exclude (non-essential descriptors)
    exclude_words = {
        'adobe', 'sidefx', 'update', 'beta', 'indie', 'LT', 'core', 'alpha', 'lite', 'demo', 'trial', 'personal',
        'enterprise',
        'studio', 'pro', 'cc', 'cs', 'fx', 'x', 'r', 'edition'
    }

    # Known words that include numbers and should be kept

    known_number_words = {
        '3ds', '3dcoat', '3d', '4d', 'cinema'
    }

    for word in words:
        # Remove leading/trailing underscores or hyphens
        word_clean = word.strip('_- ')

        # Skip empty words
        if not word_clean:
            continue

        # Skip excluded words
        if word_clean in exclude_words:
            continue

        # Check if the word matches any version pattern
        is_version = False
        for regex in version_regexes:
            if regex.match(word_clean):
                is_version = True
                break

        # Keep the word if it's not a version indicator or excluded word
        if not is_version or word_clean in known_number_words:
            kept_words.append(word_clean)

    # Join the kept words without spaces
    normalized_name = ''.join(kept_words)

    # Remove any remaining non-alphanumeric characters
    normalized_name = re.sub(r'[^\w]', '', normalized_name, re.IGNORECASE)

    # Normalize to lowercase and trim extra underscores or hyphens
    normalized_name = normalized_name.strip('_- ').lower()

    return normalized_name


@functools.cache
def get_dcc_icon_name(dcc_name):
    """
    Retrieve the canonical DCC name for a given DCC name or alias.

    Args:
        dcc_name (str): The name or variation of the DCC tool.

    Returns:
        str: The associated canonical DCC name, or None if not found.
    """
    # Normalize the input name
    dcc_name_normalized = normalize_dcc_name(dcc_name)

    # First check in the DCC_FILE_FORMATS
    if dcc_name_normalized in DCC_FILE_FORMATS:
        return dcc_name_normalized

    # Check aliases and return the associated DCC
    for dcc, aliases in DCC_ALIASES.items():
        for alias in aliases:
            alias_normalized = normalize_dcc_name(alias)
            if dcc_name_normalized == alias_normalized:
                return dcc

    # Split by space and check for aliases of individual words
    for name in dcc_name.split():
        name_normalized = normalize_dcc_name(name)
        if name_normalized in DCC_FILE_FORMATS:
            return name_normalized
        for dcc, aliases in DCC_ALIASES.items():
            for alias in aliases:
                alias_normalized = normalize_dcc_name(alias)
                if name_normalized == alias_normalized:
                    return dcc

    # Try rejoining split words with underscores and check again
    dcc_name_underscored = '_'.join(dcc_name.split())
    dcc_name_underscored_normalized = normalize_dcc_name(dcc_name_underscored)
    if dcc_name_underscored_normalized in DCC_FILE_FORMATS:
        return dcc_name_underscored_normalized
    for dcc, aliases in DCC_ALIASES.items():
        for alias in aliases:
            alias_normalized = normalize_dcc_name(alias)
            if dcc_name_underscored_normalized == alias_normalized:
                return dcc

    # Return None if nothing matches
    return None


@functools.cache
def get_all_known_dcc_formats():
    """
    Retrieve all known DCC formats.

    Returns:
        dict: A dictionary mapping DCC names to their associated file formats.
    """
    return {f for v in DCC_FILE_FORMATS.values() for f in v}
