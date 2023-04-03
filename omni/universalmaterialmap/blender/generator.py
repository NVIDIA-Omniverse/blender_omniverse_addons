# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.

import typing
import sys
import json
import os

import bpy
import bpy_types

from ..core.generator.core import IGenerator
from ..core.generator import util
from ..core.service import store
from ..core.data import Library, Target, AssemblyMetadata, Client, Node, Plug
from . import get_library, show_message, CORE_MATERIAL_PROPERTIES, get_template_data_by_shader_node

__initialized: bool = False


def _create_target(display_name, class_name):
    target = Target()
    target.display_name = display_name
    target.store_id = '{0}.json'.format(display_name)
    target.metadata.category = AssemblyMetadata.CATEGORY_CONNECTOR
    target.metadata.supported_clients.append(Client.Blender())
    target.metadata.keywords.extend(
        [
            'Blender',
            class_name,
            display_name
        ]
    )
    return target


def _do_plug(
        node: Node,
        name: str,
        attribute_display_name: str,
        value_type: str,
        internal_value_type: str,
        default_value: typing.Any
) -> typing.Tuple[Plug, Plug]:
    if internal_value_type == 'STRING':
        default_value = str(default_value)
    if internal_value_type == 'INT':
        default_value = int(default_value)
    if internal_value_type == 'VALUE':
        default_value = float(default_value)
    if internal_value_type == 'VECTOR':
        default_value = list(default_value)
    if internal_value_type == 'RGBA':
        default_value = list(default_value)
    try:
        json.dumps(default_value)
    except TypeError as error:
        print('Warning: Universal Material Map: Unable to parse for a default value for property "{0}". Using "None" as default value. Error: {1}'.format(name, error))
        default_value = None

    input_plug = None
    for existing_plug in node.inputs:
        if existing_plug.name == name:
            input_plug = existing_plug
            input_plug.display_name = attribute_display_name
            input_plug.value_type = value_type
            input_plug.default_value = default_value
            input_plug.value = default_value
            break
    if not input_plug:
        input_plug = Plug.Create(
            parent=node,
            name=name,
            display_name=attribute_display_name,
            value_type=value_type
        )
        input_plug.default_value = default_value
        input_plug.value = default_value
        node.inputs.append(input_plug)

    input_plug.internal_value_type = internal_value_type

    output_plug = None
    for existing_plug in node.outputs:
        if existing_plug.name == name:
            output_plug = existing_plug
            output_plug.display_name = attribute_display_name
            output_plug.value_type = value_type
            output_plug.default_value = default_value
            output_plug.value = default_value
            output_plug.is_editable = True
            break
    if not output_plug:
        output_plug = Plug.Create(
            parent=node,
            name=name,
            display_name=attribute_display_name,
            value_type=value_type
        )
        output_plug.default_value = default_value
        output_plug.value = default_value
        output_plug.is_editable = True
        node.outputs.append(output_plug)

    output_plug.internal_value_type = internal_value_type
    output_plug.is_editable = True

    return input_plug, output_plug


class Generator(IGenerator):
    
    def __init__(self):
        super(Generator, self).__init__()

    def _to_value_type(self, internal_value_type):
        if internal_value_type == 'BOOLEAN':
            return Plug.VALUE_TYPE_BOOLEAN
        if internal_value_type == 'STRING':
            return Plug.VALUE_TYPE_STRING
        if internal_value_type == 'INT':
            return Plug.VALUE_TYPE_INTEGER
        if internal_value_type == 'VECTOR':
            return Plug.VALUE_TYPE_VECTOR3
        if internal_value_type == 'RGBA':
            return Plug.VALUE_TYPE_VECTOR4
        if internal_value_type == 'VALUE':
            return Plug.VALUE_TYPE_FLOAT
        if internal_value_type == 'CUSTOM':
            return Plug.VALUE_TYPE_ANY
        if internal_value_type == 'SHADER':
            return Plug.VALUE_TYPE_ANY
        if internal_value_type == 'OBJECT':
            return Plug.VALUE_TYPE_ANY
        if internal_value_type == 'IMAGE':
            return Plug.VALUE_TYPE_ANY
        if internal_value_type == 'GEOMETRY':
            return Plug.VALUE_TYPE_ANY
        if internal_value_type == 'COLLECTION':
            return Plug.VALUE_TYPE_ANY
        return Plug.VALUE_TYPE_ANY

    def can_generate_target(self, class_name: str) -> bool:
        """ """
        return False

    def generate_target(self, class_name: str) -> typing.Tuple[Library, Target]:
        """ """
        raise NotImplementedError()

    def can_generate_targets(self) -> bool:
        """ """
        return False

    def generate_targets(self) -> typing.List[typing.Tuple[Library, Target]]:
        """ """
        raise NotImplementedError()

    def can_generate_target_from_instance(self, instance: object) -> bool:
        """ """
        print('can_generate_target_from_instance', instance)
        print('can_generate_target_from_instance', instance.__class__.__bases__)
        try:
            if isinstance(instance, bpy.types.Material) and not instance.node_tree:
                return True
            return bpy_types.ShaderNode in instance.__class__.__bases__
        except Exception as error:
            print('WARNING: Universal Material Mapper experienced an error checking an instance ({0}) for base classes. Detail: {1}'.format(instance, error))
        return False

    def generate_target_from_instance(self, instance: object) -> typing.Tuple[Library, Target]:
        """ """
        display_name = '{0}'.format(instance.__class__.__name__)
        class_name = '{0}.{1}'.format(instance.__class__.__module__, instance.__class__.__name__)
        library = get_library()

        template, template_map, template_shader_name, material = get_template_data_by_shader_node(shader_node=instance)

        if template is None:
            existing_targets = store.find_assembly(assembly_class=class_name, library=library)

            if len(existing_targets) > 1:
                raise NotImplementedError('Found many existing assemblies for class name "{0}"'.format(class_name))
            if len(existing_targets) == 0:
                target = _create_target(display_name=display_name, class_name=class_name)
            else:
                target = existing_targets[0]

            node = None
            for existing_node in target.nodes:
                if existing_node.class_name == class_name:
                    node = existing_node
                    break
            if not node:
                node = Node.Create(class_name=class_name)
                target.nodes.append(node)

            target.root_node = node

            if isinstance(instance, bpy.types.Material) and not instance.node_tree:

                for o in CORE_MATERIAL_PROPERTIES:
                    name = o[0]

                    if not hasattr(instance, name):
                        continue

                    attribute_display_name = o[0]

                    internal_value_type = o[1]
                    value_type = self._to_value_type(internal_value_type=internal_value_type)

                    default_value = getattr(instance, name)

                    _do_plug(
                        node=node,
                        name=name,
                        attribute_display_name=attribute_display_name,
                        value_type=value_type,
                        internal_value_type=internal_value_type,
                        default_value=default_value
                    )

            elif isinstance(instance, bpy_types.ShaderNode):
                o: bpy.types.NodeSocketStandard
                for o in instance.inputs:
                    name = o.name
                    attribute_display_name = o.name

                    internal_value_type = str(o.type)
                    value_type = self._to_value_type(internal_value_type=internal_value_type)

                    default_value = o.default_value

                    _do_plug(
                        node=node,
                        name=name,
                        attribute_display_name=attribute_display_name,
                        value_type=value_type,
                        internal_value_type=internal_value_type,
                        default_value=default_value
                    )
        else:

            existing_targets = store.find_assembly(assembly_class=template_shader_name, library=library)

            if len(existing_targets) > 1:
                raise NotImplementedError('Found many existing assemblies for class name "{0}"'.format(template_shader_name))
            if len(existing_targets) == 0:
                target = _create_target(display_name=template_shader_name, class_name=template_shader_name)
            else:
                target = existing_targets[0]

            # set target.root_node
            target_node: Node = None
            for o in target.nodes:
                if o.class_name == template['name']:
                    target_node = o
                    break

            if target_node is None:
                target_node = Node.Create(class_name=template['name'])
                target.nodes.append(target_node)

            target.root_node = target_node

            # process node_definitions - only adds and updates - does not delete nodes
            for node_definition in template['nodes']:
                shader_node = None
                for o in material.node_tree.nodes:
                    if o.name == node_definition['name']:
                        shader_node = o
                        break
                target_node: Node = None
                for o in target.nodes:
                    if o.id == node_definition['name']:
                        target_node = o
                        break

                if target_node is None:
                    target_node = Node.Create(class_name=node_definition['class'])
                    target_node._id = node_definition['name']
                    target.nodes.append(target_node)

                for map_definition in template_map['maps']:
                    if not map_definition['blender_node'] == node_definition['name']:
                        continue

                    if isinstance(shader_node, bpy.types.ShaderNodeTexImage):
                        if map_definition['blender_socket'] == 'image':
                            _do_plug(
                                node=target_node,
                                name=map_definition['blender_socket'],
                                attribute_display_name=map_definition['umm_display_name'],
                                value_type=Plug.VALUE_TYPE_STRING,
                                internal_value_type='STRING',
                                default_value=['', 'raw']
                            )

                            continue

                        raise NotImplementedError(f"{type(shader_node)} {map_definition['blender_socket']}")

                    if isinstance(shader_node, bpy.types.ShaderNodeGroup):
                        socket: bpy.types.NodeSocketStandard = shader_node.inputs[map_definition['blender_socket']]

                        internal_value_type = str(socket.type)
                        value_type = self._to_value_type(internal_value_type=internal_value_type)

                        default_value = socket.default_value

                        _do_plug(
                            node=target_node,
                            name=map_definition['blender_socket'],
                            attribute_display_name=map_definition['umm_display_name'],
                            value_type=value_type,
                            internal_value_type=internal_value_type,
                            default_value=default_value
                        )

                        continue

                    if isinstance(shader_node, bpy.types.ShaderNodeBsdfPrincipled):
                        socket: bpy.types.NodeSocketStandard = shader_node.inputs[map_definition['blender_socket']]

                        internal_value_type = str(socket.type)
                        value_type = self._to_value_type(internal_value_type=internal_value_type)

                        default_value = socket.default_value

                        _do_plug(
                            node=target_node,
                            name=map_definition['blender_socket'],
                            attribute_display_name=map_definition['umm_display_name'],
                            value_type=value_type,
                            internal_value_type=internal_value_type,
                            default_value=default_value
                        )

                        continue

                    if isinstance(shader_node, bpy.types.ShaderNodeMapping):
                        socket: bpy.types.NodeSocketStandard = shader_node.inputs[map_definition['blender_socket']]

                        internal_value_type = str(socket.type)
                        value_type = self._to_value_type(internal_value_type=internal_value_type)

                        if value_type == Plug.VALUE_TYPE_VECTOR3:
                            if 'scale' in map_definition['blender_socket'].lower():
                                value_type = Plug.VALUE_TYPE_LIST
                            elif 'location' in map_definition['blender_socket'].lower():
                                value_type = Plug.VALUE_TYPE_LIST
                            elif 'rotation' in map_definition['blender_socket'].lower():
                                value_type = Plug.VALUE_TYPE_LIST

                        default_value = socket.default_value

                        _do_plug(
                            node=target_node,
                            name=map_definition['blender_socket'],
                            attribute_display_name=map_definition['umm_display_name'],
                            value_type=value_type,
                            internal_value_type=internal_value_type,
                            default_value=default_value
                        )

                        continue

                    raise NotImplementedError(map_definition['blender_node'])

        return library, target


class OT_Generator(bpy.types.Operator):
    bl_idname = 'universalmaterialmap.generator'
    bl_label = 'Universal Material Map Generator Operator'
    bl_description = 'Universal Material Map Generator'

    def execute(self, context):
        if not bpy.context or not bpy.context.active_object or not bpy.context.active_object.active_material:
            show_message(
                message='Please select one shader node and try again.',
                title='Universal Material Map',
                icon='ERROR'
            )
            return {'FINISHED'}
        instance = bpy.context.active_object.active_material
        if bpy.context.active_object.active_material.node_tree:
            selected_nodes = [o for o in bpy.context.active_object.active_material.node_tree.nodes if o.select]
            if not len(selected_nodes) == 1:
                show_message(
                    message='Please select one shader node and try again.',
                    title='Universal Material Map',
                    icon='ERROR'
                )
                # TODO: Show warning: https://blender.stackexchange.com/questions/109711/how-to-popup-simple-message-box-from-python-console
                return {'FINISHED'}
            instance = selected_nodes[0]

        if util.can_generate_target_from_instance(instance=instance):
            library, target = util.generate_target_from_instance(instance=instance)
            target.revision += 1
            print('Universal Material Map: Writing Target "{0}" to library "{1}".'.format(target.display_name, library.name))
            print('Universal Material Map: Target ID = "{0}".'.format(target.id))
            store.write(
                filename=target.display_name,
                instance=target,
                library=library,
                overwrite=True
            )

            message = 'The node "{0}" has been written as Target "{1}" in the UMM "{2}" library.'.format(
                instance.name,
                target.display_name,
                library.name
            )
            show_message(
                message=message,
                title='Universal Material Map',
                icon='INFO'
            )
        else:
            show_message(
                message='Not able to generate data from "{0}".'.format(instance.name),
                title='Universal Material Map',
                icon='ERROR'
            )
        return {'FINISHED'}


def initialize():
    if getattr(sys.modules[__name__], '__initialized'):
        return
    setattr(sys.modules[__name__], '__initialized', True)

    util.register(generator=Generator())
    print('Universal Material Map: Registered Target Generator classes.')


initialize()

"""
'NONE', 'QUESTION',
'ERROR', 'CANCEL',
'TRIA_RIGHT', 'TRIA_DOWN', 'TRIA_LEFT', 'TRIA_UP',
'ARROW_LEFTRIGHT', 'PLUS', 'DISCLOSURE_TRI_RIGHT', 'DISCLOSURE_TRI_DOWN', 'RADIOBUT_OFF', 'RADIOBUT_ON', 'MENU_PANEL', 'BLENDER', 'GRIP', 'DOT', 'COLLAPSEMENU', 'X',
'DUPLICATE', 'TRASH', 'COLLECTION_NEW', 'OPTIONS', 'NODE', 'NODE_SEL', 'WINDOW', 'WORKSPACE', 'RIGHTARROW_THIN', 'BORDERMOVE', 'VIEWZOOM', 'ADD', 'REMOVE',
'PANEL_CLOSE', 'COPY_ID', 'EYEDROPPER', 'CHECKMARK', 'AUTO', 'CHECKBOX_DEHLT', 'CHECKBOX_HLT', 'UNLOCKED', 'LOCKED', 'UNPINNED', 'PINNED', 'SCREEN_BACK',
'RIGHTARROW', 'DOWNARROW_HLT', 'FCURVE_SNAPSHOT', 'OBJECT_HIDDEN', 'TOPBAR', 'STATUSBAR', 'PLUGIN', 'HELP', 'GHOST_ENABLED', 'COLOR', 'UNLINKED', 'LINKED',
'HAND', 'ZOOM_ALL', 'ZOOM_SELECTED', 'ZOOM_PREVIOUS', 'ZOOM_IN', 'ZOOM_OUT', 'DRIVER_DISTANCE', 'DRIVER_ROTATIONAL_DIFFERENCE', 'DRIVER_TRANSFORM', 'FREEZE',
'STYLUS_PRESSURE', 'GHOST_DISABLED', 'FILE_NEW', 'FILE_TICK', 'QUIT', 'URL', 'RECOVER_LAST', 'THREE_DOTS', 'FULLSCREEN_ENTER', 'FULLSCREEN_EXIT',
'BRUSHES_ALL', 'LIGHT', 'MATERIAL', 'TEXTURE', 'ANIM', 'WORLD', 'SCENE', 'OUTPUT', 'SCRIPT', 'PARTICLES', 'PHYSICS', 'SPEAKER', 'TOOL_SETTINGS', 'SHADERFX',
'MODIFIER', 'BLANK1', 'FAKE_USER_OFF', 'FAKE_USER_ON', 'VIEW3D', 'GRAPH', 'OUTLINER', 'PROPERTIES', 'FILEBROWSER', 'IMAGE', 'INFO', 'SEQUENCE', 'TEXT',
'SOUND', 'ACTION', 'NLA', 'PREFERENCES', 'TIME', 'NODETREE', 'CONSOLE', 'TRACKER', 'ASSET_MANAGER', 'NODE_COMPOSITING', 'NODE_TEXTURE', 'NODE_MATERIAL',
'UV', 'OBJECT_DATAMODE', 'EDITMODE_HLT', 'UV_DATA', 'VPAINT_HLT', 'TPAINT_HLT', 'WPAINT_HLT', 'SCULPTMODE_HLT', 'POSE_HLT', 'PARTICLEMODE', 'TRACKING',
'TRACKING_BACKWARDS', 'TRACKING_FORWARDS', 'TRACKING_BACKWARDS_SINGLE', 'TRACKING_FORWARDS_SINGLE', 'TRACKING_CLEAR_BACKWARDS', 'TRACKING_CLEAR_FORWARDS',
'TRACKING_REFINE_BACKWARDS', 'TRACKING_REFINE_FORWARDS', 'SCENE_DATA', 'RENDERLAYERS', 'WORLD_DATA', 'OBJECT_DATA', 'MESH_DATA', 'CURVE_DATA', 'META_DATA',
'LATTICE_DATA', 'LIGHT_DATA', 'MATERIAL_DATA', 'TEXTURE_DATA', 'ANIM_DATA', 'CAMERA_DATA', 'PARTICLE_DATA', 'LIBRARY_DATA_DIRECT', 'GROUP', 'ARMATURE_DATA', 'COMMUNITY', 'BONE_DATA', 'CONSTRAINT', 'SHAPEKEY_DATA', 'CONSTRAINT_BONE', 'CAMERA_STEREO', 'PACKAGE', 'UGLYPACKAGE', 'EXPERIMENTAL', 'BRUSH_DATA', 'IMAGE_DATA', 'FILE', 'FCURVE', 'FONT_DATA', 'RENDER_RESULT', 'SURFACE_DATA', 'EMPTY_DATA', 'PRESET', 'RENDER_ANIMATION', 'RENDER_STILL', 'LIBRARY_DATA_BROKEN', 'BOIDS', 'STRANDS', 'LIBRARY_DATA_INDIRECT', 'GREASEPENCIL', 'LINE_DATA', 'LIBRARY_DATA_OVERRIDE', 'GROUP_BONE', 'GROUP_VERTEX', 'GROUP_VCOL', 'GROUP_UVS', 'FACE_MAPS', 'RNA', 'RNA_ADD', 'MOUSE_LMB', 'MOUSE_MMB', 'MOUSE_RMB', 'MOUSE_MOVE', 'MOUSE_LMB_DRAG', 'MOUSE_MMB_DRAG', 'MOUSE_RMB_DRAG', 'MEMORY', 'PRESET_NEW', 'DECORATE', 'DECORATE_KEYFRAME', 'DECORATE_ANIMATE', 'DECORATE_DRIVER', 'DECORATE_LINKED', 'DECORATE_LIBRARY_OVERRIDE', 'DECORATE_UNLOCKED', 'DECORATE_LOCKED', 'DECORATE_OVERRIDE', 'FUND', 'TRACKER_DATA', 'HEART', 'ORPHAN_DATA', 'USER', 'SYSTEM', 'SETTINGS', 'OUTLINER_OB_EMPTY', 'OUTLINER_OB_MESH', 'OUTLINER_OB_CURVE', 'OUTLINER_OB_LATTICE', 'OUTLINER_OB_META', 'OUTLINER_OB_LIGHT', 'OUTLINER_OB_CAMERA', 'OUTLINER_OB_ARMATURE', 'OUTLINER_OB_FONT', 'OUTLINER_OB_SURFACE', 'OUTLINER_OB_SPEAKER', 'OUTLINER_OB_FORCE_FIELD', 'OUTLINER_OB_GROUP_INSTANCE', 'OUTLINER_OB_GREASEPENCIL', 'OUTLINER_OB_LIGHTPROBE', 'OUTLINER_OB_IMAGE', 'OUTLINER_COLLECTION', 'RESTRICT_COLOR_OFF', 'RESTRICT_COLOR_ON', 'HIDE_ON', 'HIDE_OFF', 'RESTRICT_SELECT_ON', 'RESTRICT_SELECT_OFF', 'RESTRICT_RENDER_ON', 'RESTRICT_RENDER_OFF', 'RESTRICT_INSTANCED_OFF', 'OUTLINER_DATA_EMPTY', 'OUTLINER_DATA_MESH', 'OUTLINER_DATA_CURVE', 'OUTLINER_DATA_LATTICE', 'OUTLINER_DATA_META', 'OUTLINER_DATA_LIGHT', 'OUTLINER_DATA_CAMERA', 'OUTLINER_DATA_ARMATURE', 'OUTLINER_DATA_FONT', 'OUTLINER_DATA_SURFACE', 'OUTLINER_DATA_SPEAKER', 'OUTLINER_DATA_LIGHTPROBE', 'OUTLINER_DATA_GP_LAYER', 'OUTLINER_DATA_GREASEPENCIL', 'GP_SELECT_POINTS', 'GP_SELECT_STROKES', 'GP_MULTIFRAME_EDITING', 'GP_ONLY_SELECTED', 'GP_SELECT_BETWEEN_STROKES', 'MODIFIER_OFF', 'MODIFIER_ON', 'ONIONSKIN_OFF', 'ONIONSKIN_ON', 'RESTRICT_VIEW_ON', 'RESTRICT_VIEW_OFF', 'RESTRICT_INSTANCED_ON', 'MESH_PLANE', 'MESH_CUBE', 'MESH_CIRCLE', 'MESH_UVSPHERE', 'MESH_ICOSPHERE', 'MESH_GRID', 'MESH_MONKEY', 'MESH_CYLINDER', 'MESH_TORUS', 'MESH_CONE', 'MESH_CAPSULE', 'EMPTY_SINGLE_ARROW', 'LIGHT_POINT', 'LIGHT_SUN', 'LIGHT_SPOT', 'LIGHT_HEMI', 'LIGHT_AREA', 'CUBE', 'SPHERE', 'CONE', 'META_PLANE', 'META_CUBE', 'META_BALL', 'META_ELLIPSOID', 'META_CAPSULE', 'SURFACE_NCURVE', 'SURFACE_NCIRCLE', 'SURFACE_NSURFACE', 'SURFACE_NCYLINDER', 'SURFACE_NSPHERE', 'SURFACE_NTORUS', 'EMPTY_AXIS', 'STROKE', 'EMPTY_ARROWS', 'CURVE_BEZCURVE', 'CURVE_BEZCIRCLE', 'CURVE_NCURVE', 'CURVE_NCIRCLE', 'CURVE_PATH', 'LIGHTPROBE_CUBEMAP', 'LIGHTPROBE_PLANAR', 'LIGHTPROBE_GRID', 'COLOR_RED', 'COLOR_GREEN', 'COLOR_BLUE', 'TRIA_RIGHT_BAR', 'TRIA_DOWN_BAR', 'TRIA_LEFT_BAR', 'TRIA_UP_BAR', 'FORCE_FORCE', 'FORCE_WIND', 'FORCE_VORTEX', 'FORCE_MAGNETIC', 'FORCE_HARMONIC', 'FORCE_CHARGE', 'FORCE_LENNARDJONES', 'FORCE_TEXTURE', 'FORCE_CURVE', 'FORCE_BOID', 'FORCE_TURBULENCE', 'FORCE_DRAG', 'FORCE_FLUIDFLOW', 'RIGID_BODY', 'RIGID_BODY_CONSTRAINT', 'IMAGE_PLANE', 'IMAGE_BACKGROUND', 'IMAGE_REFERENCE', 'NODE_INSERT_ON', 'NODE_INSERT_OFF', 'NODE_TOP', 'NODE_SIDE', 'NODE_CORNER', 'ANCHOR_TOP', 'ANCHOR_BOTTOM', 'ANCHOR_LEFT', 'ANCHOR_RIGHT', 'ANCHOR_CENTER', 'SELECT_SET', 'SELECT_EXTEND', 'SELECT_SUBTRACT', 'SELECT_INTERSECT', 'SELECT_DIFFERENCE', 'ALIGN_LEFT', 'ALIGN_CENTER', 'ALIGN_RIGHT', 'ALIGN_JUSTIFY', 'ALIGN_FLUSH', 'ALIGN_TOP', 'ALIGN_MIDDLE', 'ALIGN_BOTTOM', 'BOLD', 'ITALIC', 'UNDERLINE', 'SMALL_CAPS', 'CON_ACTION', 'HOLDOUT_OFF', 'HOLDOUT_ON', 'INDIRECT_ONLY_OFF', 'INDIRECT_ONLY_ON', 'CON_CAMERASOLVER', 'CON_FOLLOWTRACK', 'CON_OBJECTSOLVER', 'CON_LOCLIKE', 'CON_ROTLIKE', 'CON_SIZELIKE', 'CON_TRANSLIKE', 'CON_DISTLIMIT', 'CON_LOCLIMIT', 'CON_ROTLIMIT', 'CON_SIZELIMIT', 'CON_SAMEVOL', 'CON_TRANSFORM', 'CON_TRANSFORM_CACHE', 'CON_CLAMPTO', 'CON_KINEMATIC', 'CON_LOCKTRACK', 'CON_SPLINEIK', 'CON_STRETCHTO', 'CON_TRACKTO', 'CON_ARMATURE', 'CON_CHILDOF', 'CON_FLOOR', 'CON_FOLLOWPATH', 'CON_PIVOT', 'CON_SHRINKWRAP', 'MODIFIER_DATA', 'MOD_WAVE', 'MOD_BUILD', 'MOD_DECIM', 'MOD_MIRROR', 'MOD_SOFT', 'MOD_SUBSURF', 'HOOK', 'MOD_PHYSICS', 'MOD_PARTICLES', 'MOD_BOOLEAN', 'MOD_EDGESPLIT', 'MOD_ARRAY', 'MOD_UVPROJECT', 'MOD_DISPLACE', 'MOD_CURVE', 'MOD_LATTICE', 'MOD_TINT', 'MOD_ARMATURE', 'MOD_SHRINKWRAP', 'MOD_CAST', 'MOD_MESHDEFORM', 'MOD_BEVEL', 'MOD_SMOOTH', 'MOD_SIMPLEDEFORM', 'MOD_MASK', 'MOD_CLOTH', 'MOD_EXPLODE', 'MOD_FLUIDSIM', 'MOD_MULTIRES', 'MOD_FLUID', 'MOD_SOLIDIFY', 'MOD_SCREW', 'MOD_VERTEX_WEIGHT', 'MOD_DYNAMICPAINT', 'MOD_REMESH', 'MOD_OCEAN', 'MOD_WARP', 'MOD_SKIN', 'MOD_TRIANGULATE', 'MOD_WIREFRAME', 'MOD_DATA_TRANSFER', 'MOD_NORMALEDIT', 'MOD_PARTICLE_INSTANCE', 'MOD_HUE_SATURATION', 'MOD_NOISE', 'MOD_OFFSET', 'MOD_SIMPLIFY', 'MOD_THICKNESS', 'MOD_INSTANCE', 'MOD_TIME', 'MOD_OPACITY', 'REC', 'PLAY', 'FF', 'REW', 'PAUSE', 'PREV_KEYFRAME', 'NEXT_KEYFRAME', 'PLAY_SOUND', 'PLAY_REVERSE', 'PREVIEW_RANGE', 'ACTION_TWEAK', 'PMARKER_ACT', 'PMARKER_SEL', 'PMARKER', 'MARKER_HLT', 'MARKER', 'KEYFRAME_HLT', 'KEYFRAME', 'KEYINGSET', 'KEY_DEHLT', 'KEY_HLT', 'MUTE_IPO_OFF', 'MUTE_IPO_ON', 'DRIVER', 'SOLO_OFF', 'SOLO_ON', 'FRAME_PREV', 'FRAME_NEXT', 'NLA_PUSHDOWN', 'IPO_CONSTANT', 'IPO_LINEAR', 'IPO_BEZIER', 'IPO_SINE', 'IPO_QUAD', 'IPO_CUBIC', 'IPO_QUART', 'IPO_QUINT', 'IPO_EXPO', 'IPO_CIRC', 'IPO_BOUNCE', 'IPO_ELASTIC', 'IPO_BACK', 'IPO_EASE_IN', 'IPO_EASE_OUT', 'IPO_EASE_IN_OUT', 'NORMALIZE_FCURVES', 'VERTEXSEL', 'EDGESEL', 'FACESEL', 'CURSOR', 'PIVOT_BOUNDBOX', 'PIVOT_CURSOR', 'PIVOT_INDIVIDUAL', 'PIVOT_MEDIAN', 'PIVOT_ACTIVE', 'CENTER_ONLY', 'ROOTCURVE', 'SMOOTHCURVE', 'SPHERECURVE', 'INVERSESQUARECURVE', 'SHARPCURVE', 'LINCURVE', 'NOCURVE', 'RNDCURVE', 'PROP_OFF', 'PROP_ON', 'PROP_CON', 'PROP_PROJECTED', 'PARTICLE_POINT', 'PARTICLE_TIP', 'PARTICLE_PATH', 'SNAP_FACE_CENTER', 'SNAP_PERPENDICULAR', 'SNAP_MIDPOINT', 'SNAP_OFF', 'SNAP_ON', 'SNAP_NORMAL', 'SNAP_GRID', 'SNAP_VERTEX', 'SNAP_EDGE', 'SNAP_FACE', 'SNAP_VOLUME', 'SNAP_INCREMENT', 'STICKY_UVS_LOC', 'STICKY_UVS_DISABLE', 'STICKY_UVS_VERT', 'CLIPUV_DEHLT', 'CLIPUV_HLT', 'SNAP_PEEL_OBJECT', 'GRID', 'OBJECT_ORIGIN', 'ORIENTATION_GLOBAL', 'ORIENTATION_GIMBAL', 'ORIENTATION_LOCAL', 'ORIENTATION_NORMAL', 'ORIENTATION_VIEW', 'COPYDOWN', 'PASTEDOWN', 'PASTEFLIPUP', 'PASTEFLIPDOWN', 'VIS_SEL_11', 'VIS_SEL_10', 'VIS_SEL_01', 'VIS_SEL_00', 'AUTOMERGE_OFF', 'AUTOMERGE_ON', 'UV_VERTEXSEL', 'UV_EDGESEL', 'UV_FACESEL', 'UV_ISLANDSEL', 'UV_SYNC_SELECT', 'TRANSFORM_ORIGINS', 'GIZMO', 'ORIENTATION_CURSOR', 'NORMALS_VERTEX', 'NORMALS_FACE', 'NORMALS_VERTEX_FACE', 'SHADING_BBOX', 'SHADING_WIRE', 'SHADING_SOLID', 'SHADING_RENDERED', 'SHADING_TEXTURE', 'OVERLAY', 'XRAY', 'LOCKVIEW_OFF', 'LOCKVIEW_ON', 'AXIS_SIDE', 'AXIS_FRONT', 'AXIS_TOP', 'LAYER_USED', 'LAYER_ACTIVE', 'OUTLINER_OB_HAIR', 'OUTLINER_DATA_HAIR', 'HAIR_DATA', 'OUTLINER_OB_POINTCLOUD', 'OUTLINER_DATA_POINTCLOUD', 'POINTCLOUD_DATA', 'OUTLINER_OB_VOLUME', 'OUTLINER_DATA_VOLUME', 'VOLUME_DATA', 'HOME', 'DOCUMENTS', 'TEMP', 'SORTALPHA', 'SORTBYEXT', 'SORTTIME', 'SORTSIZE', 'SHORTDISPLAY', 'LONGDISPLAY', 'IMGDISPLAY', 'BOOKMARKS', 'FONTPREVIEW', 'FILTER', 'NEWFOLDER', 'FOLDER_REDIRECT', 'FILE_PARENT', 'FILE_REFRESH', 'FILE_FOLDER', 'FILE_BLANK', 'FILE_BLEND', 'FILE_IMAGE', 'FILE_MOVIE', 'FILE_SCRIPT', 'FILE_SOUND', 'FILE_FONT', 'FILE_TEXT', 'SORT_DESC', 'SORT_ASC', 'LINK_BLEND', 'APPEND_BLEND', 'IMPORT', 'EXPORT', 'LOOP_BACK', 'LOOP_FORWARDS', 'BACK', 'FORWARD', 'FILE_ARCHIVE', 'FILE_CACHE', 'FILE_VOLUME', 'FILE_3D', 'FILE_HIDDEN', 'FILE_BACKUP', 'DISK_DRIVE', 'MATPLANE', 'MATSPHERE', 'MATCUBE', 'MONKEY', 'HAIR', 'ALIASED', 'ANTIALIASED', 'MAT_SPHERE_SKY', 'MATSHADERBALL', 'MATCLOTH', 'MATFLUID', 'WORDWRAP_OFF', 'WORDWRAP_ON', 'SYNTAX_OFF', 'SYNTAX_ON', 'LINENUMBERS_OFF', 'LINENUMBERS_ON', 'SCRIPTPLUGINS', 'DISC', 'DESKTOP', 'EXTERNAL_DRIVE', 'NETWORK_DRIVE', 'SEQ_SEQUENCER', 'SEQ_PREVIEW', 'SEQ_LUMA_WAVEFORM', 'SEQ_CHROMA_SCOPE', 'SEQ_HISTOGRAM', 'SEQ_SPLITVIEW', 'SEQ_STRIP_META', 'SEQ_STRIP_DUPLICATE', 'IMAGE_RGB', 'IMAGE_RGB_ALPHA', 'IMAGE_ALPHA', 'IMAGE_ZDEPTH', 'HANDLE_AUTOCLAMPED', 'HANDLE_AUTO', 'HANDLE_ALIGNED', 'HANDLE_VECTOR', 'HANDLE_FREE', 'VIEW_PERSPECTIVE', 'VIEW_ORTHO', 'VIEW_CAMERA', 'VIEW_PAN', 'VIEW_ZOOM', 'BRUSH_BLOB', 'BRUSH_BLUR', 'BRUSH_CLAY', 'BRUSH_CLAY_STRIPS', 'BRUSH_CLONE', 'BRUSH_CREASE', 'BRUSH_FILL', 'BRUSH_FLATTEN', 'BRUSH_GRAB', 'BRUSH_INFLATE', 'BRUSH_LAYER', 'BRUSH_MASK', 'BRUSH_MIX', 'BRUSH_NUDGE', 'BRUSH_PINCH', 'BRUSH_SCRAPE', 'BRUSH_SCULPT_DRAW', 'BRUSH_SMEAR', 'BRUSH_SMOOTH', 'BRUSH_SNAKE_HOOK', 'BRUSH_SOFTEN', 'BRUSH_TEXDRAW', 'BRUSH_TEXFILL', 'BRUSH_TEXMASK', 'BRUSH_THUMB', 'BRUSH_ROTATE', 'GPBRUSH_SMOOTH', 'GPBRUSH_THICKNESS', 'GPBRUSH_STRENGTH', 'GPBRUSH_GRAB', 'GPBRUSH_PUSH', 'GPBRUSH_TWIST', 'GPBRUSH_PINCH', 'GPBRUSH_RANDOMIZE', 'GPBRUSH_CLONE', 'GPBRUSH_WEIGHT', 'GPBRUSH_PENCIL', 'GPBRUSH_PEN', 'GPBRUSH_INK', 'GPBRUSH_INKNOISE', 'GPBRUSH_BLOCK', 'GPBRUSH_MARKER', 'GPBRUSH_FILL', 'GPBRUSH_AIRBRUSH', 'GPBRUSH_CHISEL', 'GPBRUSH_ERASE_SOFT', 'GPBRUSH_ERASE_HARD', 'GPBRUSH_ERASE_STROKE', 'SMALL_TRI_RIGHT_VEC', 'KEYTYPE_KEYFRAME_VEC', 'KEYTYPE_BREAKDOWN_VEC', 'KEYTYPE_EXTREME_VEC', 'KEYTYPE_JITTER_VEC', 'KEYTYPE_MOVING_HOLD_VEC', 'HANDLETYPE_FREE_VEC', 'HANDLETYPE_ALIGNED_VEC', 'HANDLETYPE_VECTOR_VEC', 'HANDLETYPE_AUTO_VEC', 'HANDLETYPE_AUTO_CLAMP_VEC', 'COLORSET_01_VEC', 'COLORSET_02_VEC', 'COLORSET_03_VEC', 'COLORSET_04_VEC', 'COLORSET_05_VEC', 'COLORSET_06_VEC', 'COLORSET_07_VEC', 'COLORSET_08_VEC', 'COLORSET_09_VEC', 'COLORSET_10_VEC', 'COLORSET_11_VEC', 'COLORSET_12_VEC', 'COLORSET_13_VEC', 'COLORSET_14_VEC', 'COLORSET_15_VEC', 'COLORSET_16_VEC', 'COLORSET_17_VEC', 'COLORSET_18_VEC', 'COLORSET_19_VEC', 'COLORSET_20_VEC', 'COLLECTION_COLOR_01', 'COLLECTION_COLOR_02', 'COLLECTION_COLOR_03', 'COLLECTION_COLOR_04', 'COLLECTION_COLOR_05', 'COLLECTION_COLOR_06', 'COLLECTION_COLOR_07', 'COLLECTION_COLOR_08', 'EVENT_A', 'EVENT_B', 'EVENT_C', 'EVENT_D', 'EVENT_E', 'EVENT_F', 'EVENT_G', 'EVENT_H', 'EVENT_I', 'EVENT_J', 'EVENT_K', 'EVENT_L', 'EVENT_M', 'EVENT_N', 'EVENT_O', 'EVENT_P', 'EVENT_Q', 'EVENT_R', 'EVENT_S', 'EVENT_T', 'EVENT_U', 'EVENT_V', 'EVENT_W', 'EVENT_X', 'EVENT_Y', 'EVENT_Z', 'EVENT_SHIFT', 'EVENT_CTRL', 'EVENT_ALT', 'EVENT_OS', 'EVENT_F1', 'EVENT_F2', 'EVENT_F3', 'EVENT_F4', 'EVENT_F5', 'EVENT_F6', 'EVENT_F7', 'EVENT_F8', 'EVENT_F9', 'EVENT_F10', 'EVENT_F11', 'EVENT_F12', 'EVENT_ESC', 'EVENT_TAB', 'EVENT_PAGEUP', 'EVENT_PAGEDOWN', 'EVENT_RETURN', 'EVENT_SPACEKEY'
"""