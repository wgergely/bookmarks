"""
Module: Reset Rotation
Author: Gergely Wootsch (hello@gergely-wootsch.com)
Assisted by: ChatGPT-4, OpenAI
Description:
    This module provides a function to reset the rotation attributes of joints in Maya to zero
    while preserving their current orientations by adjusting their jointOrient attributes accordingly.
Usage:
    1. Select a joint in Maya.
    2. Run this script.
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds


def it(node):
    """Generator to traverse joint hierarchy.

    Args:
        node: str, name of the root joint.
    Yields:
        str, name of the current joint.
    """
    yield node
    children = cmds.listRelatives(node, children=True)
    for child in children:
        _children = cmds.listRelatives(child, children=True)
        if not _children:
            yield child
            continue
        yield from it(child)


def get_world_matrix(node):
    """Return the world matrix of a node in Maya.

    Args:
        node: str, name of the node.
    Returns:
        MMatrix, world matrix of the node.
    """
    m = cmds.xform(node, query=True, matrix=True, worldSpace=True)
    return om.MMatrix([m[i:i + 4] for i in range(0, len(m), 4)])


def get_inverse_world_matrix(node):
    """Return the inverse world matrix of a node in Maya.

    Args:
        node: str, name of the node.
    Returns:
        MMatrix, inverse world matrix of the node.
    """
    m = cmds.xform(node, query=True, matrix=True, worldSpace=True)
    return om.MMatrix([m[i:i + 4] for i in range(0, len(m), 4)]).inverse()


def get_rotational_order(joint):
    """Return the MEulerRotation rotation order of a joint.

    Args:
        joint: str, name of the joint.
    Returns:
        MEulerRotation constant, rotation order of the joint.
    """
    ro = cmds.getAttr(f'{joint}.rotateOrder')
    rotation_orders = [om.MEulerRotation.kXYZ, om.MEulerRotation.kYZX, om.MEulerRotation.kZXY, om.MEulerRotation.kXZY,
                       om.MEulerRotation.kYXZ, om.MEulerRotation.kZYX]
    return rotation_orders[ro]


def get_euler_rotation_from_matrix(matrix, rotation_order):
    """Return the Euler rotation from a transformation matrix.

    Args:
        matrix: MMatrix, transformation matrix.
        rotation_order: MEulerRotation constant, rotation order.
    Returns:
        list of float, Euler rotation in degrees.
    """
    transform = om.MTransformationMatrix(matrix)
    euler = transform.rotation(asQuaternion=False)
    euler.reorderIt(rotation_order)
    return [om.MAngle(euler[i]).asDegrees() for i in range(3)]


def adjust_joint_orient(joint):
    """Adjust jointOrient attribute based on current world matrix, then zero out rotation.

    Args:
        joint: str, name of the joint.
    """
    if not cmds.objExists(joint):
        print(f'Joint {joint} does not exist')
        return

    if cmds.getAttr(f'{joint}.rotate', lock=True) or cmds.listConnections(
            f'{joint}.rotate', source=True, destination=False
    ):
        print(f'Cannot modify rotate of {joint} because it is locked or has incoming connections')
        return

    for axis in ['X', 'Y', 'Z']:
        if cmds.getAttr(f'{joint}.rotate{axis}', lock=True) or cmds.listConnections(
                f'{joint}.rotate{axis}', source=True, destination=False
        ):
            print(f'Cannot modify rotate{axis} of {joint} because it is locked or has incoming connections')
            return

    joint_world_matrix = get_world_matrix(joint)

    parent = cmds.listRelatives(joint, parent=True)
    if parent:
        parent_inverse_world_matrix = get_inverse_world_matrix(parent[0])
    else:
        parent_inverse_world_matrix = om.MMatrix()

    joint_orient_matrix = joint_world_matrix * parent_inverse_world_matrix

    rotation_order = get_rotational_order(joint)
    new_joint_orient = get_euler_rotation_from_matrix(joint_orient_matrix, rotation_order)

    cmds.setAttr(f'{joint}.jointOrient', *new_joint_orient)
    cmds.setAttr(f'{joint}.rotate', 0, 0, 0)


def run():
    root = cmds.ls(selection=True)
    if not root:
        print('Please select a joint')
        raise RuntimeError('Please select a joint')
    root = root[0]
    if not cmds.nodeType(root) == 'joint':
        print('Please select a joint')
        raise RuntimeError('Please select a joint')

    for node in it(root):
        if not cmds.nodeType(node) == 'joint':
            continue
        adjust_joint_orient(node)

run()