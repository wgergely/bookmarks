DCC_ICONS = {
    # Houdini
    'hou': 'hip',  # Houdini (Abbreviation)
    'houdini': 'hip',  # Houdini (Full name)
    'sidefx': 'hip',  # Houdini (Alternative abbreviation)

    # Maya
    'maya': 'ma',  # Maya (ASCII)

    # After Effects
    'after_effects': 'aep',  # After Effects (Snake case)
    'afx': 'aep',  # After Effects (Abbreviation)
    'aftereffects': 'aep',  # After Effects (No space)

    # Photoshop
    'photoshop': 'psd',  # Photoshop (Full name)

    # Cinema 4D
    'cinema4d': 'c4d',  # Cinema 4D (Full name)
    'c4d': 'c4d',  # Cinema 4D (Abbreviation)
    'cinema_4d': 'c4d',  # Cinema 4D (Snake case)

    # Blender
    'blender': 'blend',  # Blender (Full name)
    'blend': 'blend',  # Blender (File extension)

    # Nuke
    'nuke': 'nk',  # Nuke (Full name)

    # Katana
    'katana': 'katana',  # Katana (Full name)

    # 3ds Max
    '3dsmax': 'max',  # 3ds Max (Full name)
    'max': 'max',  # 3ds Max (Abbreviation)
    '3ds_max': 'max',  # 3ds Max (Snake case)

    # Mari
    'mari': 'mra',  # Mari (Full name)

    # Substance
    'substancepainter': 'spp',  # Substance Painter (Full name)
    'substance_painter': 'spp',  # Substance Painter (Snake case)
    'substance_designer': 'spp',  # Substance Designer (Snake case)
    'substancedesigner': 'spp',  # Substance Designer (Snake case)
    'substance': 'spp',  # Substance Designer (General)

    # Fusion
    'fusion': 'comp',  # Fusion (Full name)

    # SpeedTree
    'speedtree': 'sts',  # SpeedTree (Full name)

    # Clarisse
    'clarisse': 'project',  # Clarisse (Full name)

    # Modo
    'modo': 'lxo',  # Modo (Full name)

    # ZBrush
    'zbrush': 'zpr',  # ZBrush (Full name)

    # DaVinci Resolve
    'davinci': 'drp',  # DaVinci Resolve (Short name)

    # Silhouette
    'silhouette': 'sfx',  # Silhouette (Full name)

    # Arnold Renderer
    'arnold': 'ass',  # Arnold Renderer (ASCII)

    # V-Ray
    'vray': 'vrscene',  # V-Ray (Full name)

    # RealFlow
    'realflow': 'rfa',  # RealFlow (Full name)

    # Terragen
    'terragen': 'ter',  # Terragen (Full name)

    # LightWave 3D
    'lightwave': 'lws',  # LightWave 3D (Full name)

    # Autodesk Flame
    'flame': 'flame',  # Autodesk Flame (Full name)

    # Vue
    'vue': 'vue',  # Vue (Full name)
    'vue_project': 'vue',  # Vue Project
    'vue_scene': 'vue',  # Vue Scene

    # Marmoset Toolbag
    'marmoset': 'mtb',  # Marmoset Toolbag (Full name)

    # Gaea
    'gaea': 'gaea',  # Gaea (Full name)

    # Marvelous Designer
    'marvelousdesigner': 'zprj',  # Marvelous Designer (Full name)
    'marvelous_designer': 'zprj',  # Marvelous Designer (Snake case)
}


def get_scene_extension(dcc_name):
    """
    Retrieve the scene file extension for a given DCC name.

    Args:
        dcc_name (str): The name or variation of the DCC tool.

    Returns:
        str: The associated scene file extension, or None if not found.
    """
    dcc_name_normalized = dcc_name.lower()
    return DCC_ICONS.get(dcc_name_normalized)
