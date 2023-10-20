"""
This script creates sets for each export group in the scene.
Used in conjunction with Bookmarks to export character meshes for Houdini cloth simulation.

Author:
    Studio AKA, 2023 (c) All rights reserved.
    https://www.studioaka.co.uk/
    Gergely Wootsch,
    hello@gergely-wootsch.com

"""
import maya.cmds as cmds


# Function to find object with variable namespace
def find_object_with_namespace(base_object):
    objects = cmds.ls(f'*{base_object}')
    namespace_dict = {}

    for obj in objects:
        if ':' in obj:
            namespace = obj.rsplit(':', 1)[0]
        else:
            namespace = ''

        if namespace not in namespace_dict:
            namespace_dict[namespace] = []
        namespace_dict[namespace].append(obj)

    return namespace_dict


# Function to create and color object set
def create_set(set_name):
    # Create the set
    if not cmds.objExists(set_name):
        new_set = cmds.sets(name=set_name)
    else:
        print(f"Set {set_name} already exists.")
        new_set = set_name

    return new_set


def run():
    # Mapping of set names and their corresponding objects
    set_object_mapping = {
        'IbogaineDJ_body_export': ['*DJ*:head_geo', '*DJ*:body_geo', '*DJ*:shoes_geo'],
        'IbogaineDJ_extra_export': ['*DJ*:hair_geo', '*DJ*:eye_l_geo', '*DJ*:eye_r_geo', '*DJ*:hat_geo'],
        'IbogaineDJ_cloth_export': ['*DJ*:cloth_geo', ],
        'IbogaineMatty_body_export': ['*Matty*:head_geo', '*Matty*:body_geo', '*Matty*:shoes_geo'],
        'IbogaineMatty_cloth_export': ['*Matty*:cloth_geo', ],
        'IbogaineMarcus_body_export': ['*Marcus*:head_geo', '*Marcus*:body_geo', '*Marcus*:shoes_geo'],
        'IbogaineMarcus_cloth_export': ['*Marcus*:tshirt_geo', '*Marcus*:trousers_geo'],
        'IbogaineMarcus_extra_export': ['*Marcus*:eye_L', '*Marcus*:eye_R'],
        'IbogaineMarcus_body_mirrored_export': ['*Marcus*:head_geo_mirrored', '*Marcus*:body_geo_mirrored', '*Marcus*:shoes_geo_mirrored'],
        'IbogaineMarcus_cloth_mirrored_export': ['*Marcus*:tshirt_geo_mirrored', '*Marcus*:trousers_geo_mirrored'],
        'IbogaineMarcus_extra_mirrored_export': ['*Marcus*:eye_L_mirrored', '*Marcus*:eye_R_mirrored'],
        'set_ground_export': ['set_ground_geo', ],
        'set_background_export': ['set_background_geo', ],
        'set_floor_export': ['set_floor_geo', ],
        'camera_export': ['camera:camera'],
    }

    cmds.undoInfo(openChunk=True)

    try:
        # Create each set and add its objects
        created_sets = []
        sel = cmds.ls(sl=True)
        cmds.select(clear=True)

        for set_name, base_objects in set_object_mapping.items():
            for base_object in base_objects:
                if 'camera:camera' in base_object:
                    found_objects = {
                        '': cmds.ls(base_object)
                    }
                else:
                    found_objects = find_object_with_namespace(base_object)

                if not found_objects:
                    continue

                suffix_count = 0
                for namespace, objs in found_objects.items():
                    suffix_count += 1

                    final_set_name = set_name
                    if len(found_objects) > 1 and suffix_count > 1:
                        final_set_name = set_name.replace('_export', f'_{suffix_count:02}_export')

                    created_set = create_set(final_set_name)
                    created_sets.append(created_set)

                    for found_object in objs:
                        cmds.sets(found_object, add=created_set)

        master_set = create_set('EXPORTS')
        cmds.sets(created_sets, add=master_set)
        cmds.select(sel, replace=True)
    except Exception as e:
        print(f"Error: {str(e)}")
        raise
    finally:
        # Ensure the undo chunk is always closed, regardless of success or error
        cmds.undoInfo(closeChunk=True)
