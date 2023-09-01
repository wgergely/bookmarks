import maya.cmds as cmds


# Function to find object with variable namespace
def find_object_with_namespace(base_object):
    objects = cmds.ls('*:' + base_object)  # Find objects with any namespace
    return objects or None  # Return None if no object found


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
        "IbogaineDJ_body_export": ["head_geo", "body_geo", "shoes_geo"],
        "IbogaineDJ_extra_export": ["hair_geo", "eye_l_geo", "eye_r_geo", "hat_geo"],
        "IbogaineDJ_cloth_export": ["cloth_geo",],
        "camera_export": ["camera:camera"],
    }

    # Create each set and add its objects
    created_sets = []

    for set_name, base_objects in set_object_mapping.items():
        created_set = create_set(set_name)
        created_sets.append(created_set)

        for base_object in base_objects:
            found_objects = None
            # For camera, no need to find objects with namespace
            if base_object == "camera:camera":
                found_objects = cmds.ls(base_object)
            else:
                found_objects = find_object_with_namespace(base_object)

            if found_objects:
                for found_object in found_objects:
                    cmds.sets(found_object, add=created_set)

    # Create master set and add all other sets to it
    master_set = create_set("EXPORTS")
    cmds.sets(created_sets, add=master_set)
