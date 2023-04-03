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
import traceback
import os
import re
import json
import math

import bpy
import bpy_types

from . import get_library, get_value, CORE_MATERIAL_PROPERTIES, create_template, developer_mode, get_template_data_by_shader_node, get_template_data_by_class_name, create_from_template
from ..core.converter.core import ICoreConverter, IObjectConverter, IDataConverter
from ..core.converter import util
from ..core.service import store
from ..core.data import Plug, ConversionManifest, DagNode, ConversionGraph, TargetInstance
from ..core.util import get_extension_from_image_file_format


__initialized: bool = False
__manifest: ConversionManifest = None


def _get_manifest() -> ConversionManifest:
    if not getattr(sys.modules[__name__], '__manifest'):
        setattr(sys.modules[__name__], '__manifest', store.get_conversion_manifest(library=get_library()))
        if developer_mode:
            manifest: ConversionManifest = getattr(sys.modules[__name__], '__manifest')
            print('UMM DEBUG: blender.converter._get_manifest(): num entries = "{0}"'.format(len(manifest.conversion_maps)))
            for conversion_map in manifest.conversion_maps:
                print('UMM DEBUG: blender.converter._get_manifest(): Entry: graph_id = "{0}", render_context = "{1}"'.format(conversion_map.conversion_graph_id, conversion_map.render_context))
    return getattr(sys.modules[__name__], '__manifest')


def _get_conversion_graph_impl(source_class: str, render_context: str) -> typing.Union[ConversionGraph, typing.NoReturn]:
    if developer_mode:
        print('UMM DEBUG: blender.converter._get_conversion_graph_impl(source_class="{0}", render_context="{1}")'.format(source_class, render_context))
    for conversion_map in _get_manifest().conversion_maps:
        if not conversion_map.render_context == render_context:
            if developer_mode:
                print('UMM DEBUG: blender.converter._get_conversion_graph_impl: conversion_map.render_context "{0}" != "{1}")'.format(conversion_map.render_context, render_context))
            continue
        if not conversion_map.conversion_graph:
            if developer_mode:
                print('UMM DEBUG: blender.converter._get_conversion_graph_impl: conversion_map.conversion_graph "{0}")'.format(conversion_map.conversion_graph))
            continue
        if not conversion_map.conversion_graph.source_node:
            if developer_mode:
                print('UMM DEBUG: blender.converter._get_conversion_graph_impl: conversion_map.source_node "{0}")'.format(conversion_map.conversion_graph.source_node))
            continue
        if not conversion_map.conversion_graph.source_node.target.root_node.class_name == source_class:
            if developer_mode:
                print('UMM DEBUG: blender.converter._get_conversion_graph_impl: conversion_map.conversion_graph.source_node.target.root_node.class_name "{0}" != "{1}")'.format(conversion_map.conversion_graph.source_node.target.root_node.class_name, source_class))
            continue
        if developer_mode:
            print('UMM DEBUG: blender.converter._get_conversion_graph_impl: found match "{0}")'.format(conversion_map.conversion_graph.filename))
        return conversion_map.conversion_graph
    if developer_mode:
        print('UMM DEBUG: blender.converter._get_conversion_graph_impl: found no match!)')
    return None


def _instance_to_output_entity(graph: ConversionGraph, instance: object) -> TargetInstance:
    if developer_mode:
        print('_instance_to_output_entity')
    for output in graph.source_node.outputs:
        if output.name == 'node_id_output':
            continue
        if util.can_set_plug_value(instance=instance, plug=output):
            util.set_plug_value(instance=instance, plug=output)
        else:
            print('UMM Warning: Unable to set output plug "{0}"... using default value of "{1}"'.format(output.name, output.default_value))
            output.value = output.default_value
    return graph.get_output_entity()


def _data_to_output_entity(graph: ConversionGraph, data: typing.List[typing.Tuple[str, typing.Any]]) -> TargetInstance:
    for output in graph.source_node.outputs:
        if output.name == 'node_id_output':
            continue
        o = [o for o in data if o[0] == output.name]
        if len(o):
            output.value = o[0][1]
        else:
            output.value = output.default_value
    return graph.get_output_entity()


def _instance_to_data(instance: object, graph: ConversionGraph) -> typing.List[typing.Tuple[str, typing.Any]]:
    target_instance = _instance_to_output_entity(graph=graph, instance=instance)
    if developer_mode:
        print('_instance_to_data')
        print('\ttarget_instance.target.store_id', target_instance.target.store_id)

    # Compute target attribute values
    attribute_data = [(util.TARGET_CLASS_IDENTIFIER, target_instance.target.root_node.class_name)]
    for plug in target_instance.inputs:
        if not plug.input:
            continue
        if developer_mode:
            print('\t{} is invalid: {}'.format(plug.name, plug.is_invalid))
        if plug.is_invalid and isinstance(plug.parent, DagNode):
            plug.parent.compute()
        if developer_mode:
            print('\t{} computed value = {}'.format(plug.name, plug.computed_value))
        attribute_data.append((plug.name, plug.computed_value))
    return attribute_data


def _to_convertible_instance(instance: object, material: bpy.types.Material = None) -> object:
    if developer_mode:
        print('_to_convertible_instance', type(instance))

    if material is None:
        if isinstance(instance, bpy.types.Material):
            material = instance
        else:
            for m in bpy.data.materials:
                if not m.use_nodes:
                    continue
                if not len([o for o in m.node_tree.nodes if o == instance]):
                    continue
                material = m
                break

    if material is None:
        return instance

    if not material.use_nodes:
        return material

    if instance == material:
        # Find the Surface Shader.
        for link in material.node_tree.links:
            if not isinstance(link, bpy.types.NodeLink):
                continue
            if not isinstance(link.to_node, bpy.types.ShaderNodeOutputMaterial):
                continue
            if not link.to_socket.name == 'Surface':
                continue
            result = _to_convertible_instance(instance=link.from_node, material=material)
            if result is not None:
                return result
        # No surface shader found - return instance
        return instance

    if isinstance(instance, bpy.types.ShaderNodeAddShader):
        for link in material.node_tree.links:
            if not isinstance(link, bpy.types.NodeLink):
                continue
            if not link.to_node == instance:
                continue
            # if not link.to_socket.name == 'Shader':
            #     continue
            result = _to_convertible_instance(instance=link.from_node, material=material)
            if result is not None:
                return result

    # if isinstance(instance, bpy.types.ShaderNodeBsdfGlass):
    #     return instance
    # if isinstance(instance, bpy.types.ShaderNodeBsdfGlossy):
    #     return instance
    if isinstance(instance, bpy.types.ShaderNodeBsdfPrincipled):
        return instance
    # if isinstance(instance, bpy.types.ShaderNodeBsdfRefraction):
    #     return instance
    # if isinstance(instance, bpy.types.ShaderNodeBsdfTranslucent):
    #     return instance
    # if isinstance(instance, bpy.types.ShaderNodeBsdfTransparent):
    #     return instance
    # if isinstance(instance, bpy.types.ShaderNodeEeveeSpecular):
    #     return instance
    # if isinstance(instance, bpy.types.ShaderNodeEmission):
    #     return instance
    # if isinstance(instance, bpy.types.ShaderNodeSubsurfaceScattering):
    #     return instance
    return None


class CoreConverter(ICoreConverter):

    def __init__(self):
        super(CoreConverter, self).__init__()

    def get_conversion_manifest(self) -> typing.List[typing.Tuple[str, str]]:
        """
        Returns data indicating what source class can be converted to a render context.

        Example: [('lambert', 'MDL'), ('blinn', 'MDL'),]
        """
        output = []
        for conversion_map in _get_manifest().conversion_maps:
            if not conversion_map.render_context:
                continue
            if not conversion_map.conversion_graph:
                continue
            if not conversion_map.conversion_graph.source_node:
                continue
            output.append((conversion_map.conversion_graph.source_node.target.root_node.class_name, conversion_map.render_context))
        return output


class ObjectConverter(CoreConverter, IObjectConverter):
    """ """

    MATERIAL_CLASS = 'bpy.types.Material'

    SHADER_NODES = [
        'bpy.types.ShaderNodeBsdfGlass',
        'bpy.types.ShaderNodeBsdfGlossy',
        'bpy.types.ShaderNodeBsdfPrincipled',
        'bpy.types.ShaderNodeBsdfRefraction',
        'bpy.types.ShaderNodeBsdfTranslucent',
        'bpy.types.ShaderNodeBsdfTransparent',
        'bpy.types.ShaderNodeEeveeSpecular',
        'bpy.types.ShaderNodeEmission',
        'bpy.types.ShaderNodeSubsurfaceScattering',
    ]

    def can_create_instance(self, class_name: str) -> bool:
        """ Returns true if worker can generate an object of the given class name. """
        if class_name == ObjectConverter.MATERIAL_CLASS:
            return True
        return class_name in ObjectConverter.SHADER_NODES

    def create_instance(self, class_name: str, name: str = 'material') -> object:
        """ Creates an object of the given class name. """
        material = bpy.data.materials.new(name=name)
        if class_name in ObjectConverter.SHADER_NODES:
            material.use_nodes = True
        return material

    def can_set_plug_value(self, instance: object, plug: Plug) -> bool:
        """ Returns true if worker can set the plug's value given the instance and its attributes. """
        if plug.input:
            return False

        if isinstance(instance, bpy.types.Material):
            for o in CORE_MATERIAL_PROPERTIES:
                if o[0] == plug.name:
                    return hasattr(instance, plug.name)
            return False

        if isinstance(instance, bpy_types.ShaderNode):
            return len([o for o in instance.inputs if o.name == plug.name]) == 1

        return False

    def set_plug_value(self, instance: object, plug: Plug) -> typing.NoReturn:
        """ Sets the plug's value given the value of the instance's attribute named the same as the plug. """
        if isinstance(instance, bpy.types.Material):
            plug.value = getattr(instance, plug.name)
            if developer_mode:
                print('set_plug_value')
                print('\tinstance', type(instance))
                print('\tname', plug.name)
                print('\tvalue', plug.value)
            return

        inputs = [o for o in instance.inputs if o.name == plug.name]
        if not len(inputs) == 1:
            return
        plug.value = get_value(socket=inputs[0])
        if developer_mode:
            # print('set_plug_value')
            # print('\tinstance', type(instance))
            # print('\tname', plug.name)
            # print('\tvalue', plug.value)
            print('\tset_plug_value: {} = {}'.format(plug.name, plug.value))

    def can_set_instance_attribute(self, instance: object, name: str):
        """ Resolves if worker can set an attribute by the given name on the instance. """
        return False

    def set_instance_attribute(self, instance: object, name: str, value: typing.Any) -> typing.NoReturn:
        """ Sets the named attribute on the instance to the value. """
        raise NotImplementedError()

    def can_convert_instance(self, instance: object, render_context: str) -> bool:
        """ Resolves if worker can convert the instance to another object given the render_context. """
        return False

    def convert_instance_to_instance(self, instance: object, render_context: str) -> typing.Any:
        """ Converts the instance to another object given the render_context. """
        raise NotImplementedError()

    def can_convert_instance_to_data(self, instance: object, render_context: str) -> bool:
        """ Resolves if worker can convert the instance to another object given the render_context. """
        node = _to_convertible_instance(instance=instance)
        if node is not None and not node == instance:
            if developer_mode:
                print('Found graph node to use instead of bpy.types.Material: {0}'.format(type(node)))
            instance = node

        template, template_map, template_shader_name, material = get_template_data_by_shader_node(shader_node=instance)

        if template is None:
            class_name = '{0}.{1}'.format(instance.__class__.__module__, instance.__class__.__name__)
            conversion_graph = _get_conversion_graph_impl(source_class=class_name, render_context=render_context)
            if not conversion_graph:
                return False
            try:
                destination_target_instance = _instance_to_output_entity(graph=conversion_graph, instance=instance)
            except Exception as error:
                print('Warning: Unable to get destination assembly using document "{0}".\nDetails: {1}'.format(conversion_graph.filename, error))
                return False
            return destination_target_instance is not None
        else:
            conversion_graph = _get_conversion_graph_impl(source_class=template_shader_name, render_context=render_context)
            return conversion_graph is not None

    def convert_instance_to_data(self, instance: object, render_context: str) -> typing.List[typing.Tuple[str, typing.Any]]:
        """
        Returns a list of key value pairs in tuples.
        The first pair is ("umm_target_class", "the_class_name") indicating the conversion target class.
        """
        node = _to_convertible_instance(instance=instance)
        if node is not None and not node == instance:
            if developer_mode:
                print('Found graph node to use instead of bpy.types.Material: {0}'.format(type(node)))
            instance = node

        template, template_map, template_shader_name, material = get_template_data_by_shader_node(shader_node=instance)

        if template is None:
            class_name = '{0}.{1}'.format(instance.__class__.__module__, instance.__class__.__name__)
            conversion_graph = _get_conversion_graph_impl(source_class=class_name, render_context=render_context)
            return _instance_to_data(instance=instance, graph=conversion_graph)
        else:
            conversion_graph = _get_conversion_graph_impl(source_class=template_shader_name, render_context=render_context)
            if developer_mode:
                print('conversion_graph', conversion_graph.filename)
            # set plug values on conversion_graph.source_node.outputs
            for output in conversion_graph.source_node.outputs:
                if output.name == 'node_id_output':
                    continue
                if developer_mode:
                    print('output', output.name)

                internal_node = None
                for a in conversion_graph.source_node.target.nodes:
                    for b in a.outputs:
                        if output.id == b.id:
                            internal_node = a
                            break
                    if internal_node is not None:
                        break

                if internal_node is None:
                    raise NotImplementedError(f"No internal node found for {output.name}")

                map_definition = None
                for o in template_map['maps']:
                    if o['blender_node'] == internal_node.id and o['blender_socket'] == output.name:
                        map_definition = o
                        break

                if map_definition is None:
                    raise NotImplementedError(f"No map definition found for {output.name}")

                if developer_mode:
                    print('map_definition', map_definition['blender_node'])
                if map_definition['blender_node'] == '':
                    output.value = output.default_value
                    if developer_mode:
                        print('output.value', output.value)
                    continue

                for shader_node in material.node_tree.nodes:
                    if not shader_node.name == map_definition['blender_node']:
                        continue

                    if isinstance(shader_node, bpy.types.ShaderNodeTexImage):
                        if map_definition['blender_socket'] == 'image':
                            if shader_node.image and (shader_node.image.source == 'FILE' or shader_node.image.source == 'TILED'):
                                print(f'UMM: image.filepath: "{shader_node.image.filepath}"')
                                print(f'UMM: image.source: "{shader_node.image.source}"')
                                print(f'UMM: image.file_format: "{shader_node.image.file_format}"')
                                value = shader_node.image.filepath
                                if (shader_node.image.source == 'TILED'):
                                    # Find all numbers in the path.
                                    numbers = re.findall('[0-9]+', value)
                                    if (len(numbers) > 0):
                                        # Get the string representation of the last number.
                                        num_str = str(numbers[-1])
                                        # Replace the number substring with '<UDIM>'.
                                        split_items = value.rsplit(num_str, 1)
                                        if (len(split_items) == 2):
                                            value = split_items[0] + '<UDIM>' + split_items[1]
                                try:
                                    if value is None or value == '':
                                        file_format = shader_node.image.file_format
                                        file_format = get_extension_from_image_file_format(file_format, shader_node.image.name)
                                        if not shader_node.image.name.endswith(file_format):
                                            value = f'{shader_node.image.name}.{file_format}'
                                        else:
                                            value = shader_node.image.name
                                        output.value = [value, shader_node.image.colorspace_settings.name]
                                    else:
                                        output.value = [os.path.abspath(bpy.path.abspath(value)), shader_node.image.colorspace_settings.name]
                                except Exception as error:
                                    print('Warning: Universal Material Map: Unable to evaluate absolute file path of texture "{0}". Detail: {1}'.format(shader_node.image.filepath, error))
                                    output.value = ['', 'raw']
                                print(f'UMM: output.value: "{output.value}"')
                            else:
                                if developer_mode:
                                    print('setting default value for output.value')
                                    if not shader_node.image:
                                        print('\tshader_node.image == None')
                                    else:
                                        print('\tshader_node.image.source == {}'.format(shader_node.image.source))
                                output.value = ['', 'raw']
                            if developer_mode:
                                print('output.value', output.value)
                            break

                        raise NotImplementedError(f"No support for bpy.types.ShaderNodeTexImage {map_definition['blender_socket']}")

                    if isinstance(shader_node, bpy.types.ShaderNodeBsdfPrincipled):
                        socket: bpy.types.NodeSocketStandard = shader_node.inputs[map_definition['blender_socket']]
                        output.value = socket.default_value
                        if developer_mode:
                            print('output.value', output.value)
                        break

                    if isinstance(shader_node, bpy.types.ShaderNodeGroup):
                        if map_definition['blender_socket'] not in shader_node.inputs.keys():
                            if developer_mode:
                                print(f'{map_definition["blender_socket"]} not in shader_node.inputs.keys()')
                            break
                        socket: bpy.types.NodeSocketStandard = shader_node.inputs[map_definition['blender_socket']]
                        output.value = socket.default_value
                        if developer_mode:
                            print('output.value', output.value)
                        break

                    if isinstance(shader_node, bpy.types.ShaderNodeMapping):
                        socket: bpy.types.NodeSocketStandard = shader_node.inputs[map_definition['blender_socket']]
                        value = socket.default_value
                        if output.name == 'Rotation':
                            value = [
                                math.degrees(value[0]),
                                math.degrees(value[1]),
                                math.degrees(value[2])
                            ]
                        output.value = value
                        if developer_mode:
                            print('output.value', output.value)
                        break

            # compute to target_instance for output
            target_instance = conversion_graph.get_output_entity()

            if developer_mode:
                print('_instance_to_data')
                print('\ttarget_instance.target.store_id', target_instance.target.store_id)

            # Compute target attribute values
            attribute_data = [(util.TARGET_CLASS_IDENTIFIER, target_instance.target.root_node.class_name)]
            for plug in target_instance.inputs:
                if not plug.input:
                    continue
                if developer_mode:
                    print('\t{} is invalid: {}'.format(plug.name, plug.is_invalid))
                if plug.is_invalid and isinstance(plug.parent, DagNode):
                    plug.parent.compute()
                if developer_mode:
                    print('\t{} computed value = {}'.format(plug.name, plug.computed_value))
                value = plug.computed_value
                if plug.internal_value_type == 'bool':
                    value = True if value else False
                attribute_data.append((plug.name, value))
            return attribute_data

    def can_convert_attribute_values(self, instance: object, render_context: str, destination: object) -> bool:
        """ Resolves if the instance's attribute values can be converted and set on the destination object's attributes. """
        raise NotImplementedError()

    def convert_attribute_values(self, instance: object, render_context: str, destination: object) -> typing.NoReturn:
        """ Attribute values are converted and set on the destination object's attributes. """
        raise NotImplementedError()

    def can_apply_data_to_instance(self, source_class_name: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]], instance: object) -> bool:
        """ Resolves if worker can convert the instance to another object given the render_context. """
        if developer_mode:
            print('can_apply_data_to_instance()')
        if not isinstance(instance, bpy.types.Material):
            if developer_mode:
                print('can_apply_data_to_instance: FALSE - instance not bpy.types.Material')
            return False
        if not render_context == 'Blender':
            if developer_mode:
                print('can_apply_data_to_instance: FALSE - render_context not "Blender"')
            return False
        conversion_graph = _get_conversion_graph_impl(source_class=source_class_name, render_context=render_context)
        if not conversion_graph:
            if developer_mode:
                print('can_apply_data_to_instance: FALSE - conversion_graph is None')
            return False
        if developer_mode:
            print(f'conversion_graph {conversion_graph.filename}')
        try:
            destination_target_instance = _data_to_output_entity(graph=conversion_graph, data=source_data)
        except Exception as error:
            print('Warning: Unable to get destination assembly using document "{0}".\nDetails: {1}'.format(conversion_graph.filename, error))
            return False
        if developer_mode:
            if destination_target_instance is None:
                print('destination_target_instance is None')
            elif destination_target_instance is None:
                print('destination_target_instance.target is None')
            else:
                print('destination_target_instance.target is not None')
        if destination_target_instance is None or destination_target_instance.target is None:
            return False
        if developer_mode:
            print(f'num destination_target_instance.target.nodes: {len(destination_target_instance.target.nodes)}')
        if len(destination_target_instance.target.nodes) < 2:
            return True
        template, template_map = get_template_data_by_class_name(class_name=destination_target_instance.target.root_node.class_name)
        if developer_mode:
            print(f'return {template is not None}')
        return template is not None

    def apply_data_to_instance(self, source_class_name: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]], instance: object) -> None:
        """
        Implementation requires that `instance` is type `bpy.types.Material`.
        """
        if developer_mode:
            print('apply_data_to_instance()')
        if not isinstance(instance, bpy.types.Material):
            raise Exception('instance type not supported', type(instance))

        if not render_context == 'Blender':
            raise Exception('render_context not supported', render_context)

        conversion_graph = _get_conversion_graph_impl(source_class=source_class_name, render_context=render_context)
        # This only works for Blender import of MDL/USDPreview. Blender export would need to use convert_instance_to_data().
        destination_target_instance = _data_to_output_entity(graph=conversion_graph, data=source_data)

        material: bpy.types.Material = instance

        # Make sure we're using nodes
        material.use_nodes = True

        # Remove existing nodes - we're starting from scratch - assuming Blender import
        to_delete = [o for o in material.node_tree.nodes]
        while len(to_delete):
            material.node_tree.nodes.remove(to_delete.pop())

        if len(destination_target_instance.target.nodes) < 2:
            # Create base graph
            output_node = material.node_tree.nodes.new('ShaderNodeOutputMaterial')
            output_node.location = [300.0, 300.0]
            bsdf_node = material.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
            bsdf_node.location = [0.0, 300.0]

            material.node_tree.links.new(bsdf_node.outputs[0], output_node.inputs[0])

            node_cache = dict()
            node_location = [-500, 300]

            # Create graph if texture value
            for plug in destination_target_instance.inputs:
                if not plug.input:
                    continue
                if isinstance(plug.computed_value, list) or isinstance(plug.computed_value, tuple):
                    if len(plug.computed_value) == 2 and isinstance(plug.computed_value[0], str) and isinstance(plug.computed_value[1], str):
                        key = '{0}|{1}'.format(plug.computed_value[0], plug.computed_value[1])
                        if key in node_cache.keys():
                            node = node_cache[key]
                        else:
                            try:
                                path = plug.computed_value[0]
                                if not path == '':
                                    node = material.node_tree.nodes.new('ShaderNodeTexImage')
                                    path = plug.computed_value[0]
                                    if '<UDIM>' in path:
                                        pattern = path.replace('\\', '/')
                                        pattern = pattern.replace('<UDIM>', '[0-9][0-9][0-9][0-9]')
                                        directory = pattern[:pattern.rfind('/') + 1]
                                        pattern = pattern.replace(directory, '')
                                        image_set = False
                                        for item in os.listdir(directory):
                                            if re.match(pattern, item):
                                                tile_path = '{}{}'.format(directory, item)
                                                if not os.path.isfile(tile_path):
                                                    continue
                                                if not image_set:
                                                    node.image = bpy.data.images.load(tile_path)
                                                    node.image.source = 'TILED'
                                                    image_set = True
                                                    continue
                                                tile_indexes = re.findall('[0-9][0-9][0-9][0-9]', item)
                                                node.image.tiles.new(int(tile_indexes[-1]))
                                    else:
                                        node.image = bpy.data.images.load(path)
                                    node.image.colorspace_settings.name = plug.computed_value[1]
                                else:
                                    continue
                            except Exception as error:
                                print('Warning: UMM failed to properly setup a ShaderNodeTexImage. Details: {0}\n{1}'.format(error, traceback.format_exc()))
                                continue
                            node_cache[key] = node
                            node.location = node_location
                            node_location[1] -= 300

                        bsdf_input = [o for o in bsdf_node.inputs if o.name == plug.name][0]

                        if plug.name == 'Metallic':
                            separate_node = None
                            for link in material.node_tree.links:
                                if link.from_node == node and link.to_node.__class__.__name__ == 'ShaderNodeSeparateRGB':
                                    separate_node = link.to_node
                                    break
                            if separate_node is None:
                                separate_node = material.node_tree.nodes.new('ShaderNodeSeparateRGB')
                                separate_node.location = [node.location[0] + 250, node.location[1]]

                            material.node_tree.links.new(node.outputs[0], separate_node.inputs[0])
                            material.node_tree.links.new(separate_node.outputs[2], bsdf_input)
                        elif plug.name == 'Roughness':
                            separate_node = None
                            for link in material.node_tree.links:
                                if link.from_node == node and link.to_node.__class__.__name__ == 'ShaderNodeSeparateRGB':
                                    separate_node = link.to_node
                                    break
                            if separate_node is None:
                                separate_node = material.node_tree.nodes.new('ShaderNodeSeparateRGB')
                                separate_node.location = [node.location[0] + 250, node.location[1]]

                            material.node_tree.links.new(node.outputs[0], separate_node.inputs[0])
                            material.node_tree.links.new(separate_node.outputs[1], bsdf_input)
                        elif plug.name == 'Normal':
                            normal_node = None
                            for link in material.node_tree.links:
                                if link.from_node == node and link.to_node.__class__.__name__ == 'ShaderNodeNormalMap':
                                    normal_node = link.to_node
                                    break
                            if normal_node is None:
                                normal_node = material.node_tree.nodes.new('ShaderNodeNormalMap')
                                normal_node.location = [node.location[0] + 250, node.location[1]]

                            material.node_tree.links.new(node.outputs[0], normal_node.inputs[1])
                            material.node_tree.links.new(normal_node.outputs[0], bsdf_input)
                        else:
                            material.node_tree.links.new(node.outputs[0], bsdf_input)
                        continue

                # Set Value
                blender_inputs = [o for o in bsdf_node.inputs if o.name == plug.name]
                if len(blender_inputs) == 0:
                    for property_name, property_object in bsdf_node.rna_type.properties.items():
                        if not property_name == plug.name:
                            continue
                        if property_object.is_readonly:
                            break
                        try:
                            setattr(bsdf_node, property_name, plug.computed_value)
                        except Exception as error:
                            print('Warning: Universal Material Map: Unexpected error when setting property "{0}" to value "{1}": "{2}"'.format(property_name, plug.computed_value, error))
                else:
                    if isinstance(blender_inputs[0], bpy.types.NodeSocketShader):
                        continue
                    try:
                        blender_inputs[0].default_value = plug.computed_value
                    except Exception as error:
                        print('Warning: Universal Material Map: Unexpected error when setting input "{0}" to value "{1}": "{2}"'.format(plug.name, plug.computed_value, error))
            return

        if developer_mode:
            print(f'TEMPLATE CREATION BASED ON {destination_target_instance.target.root_node.class_name}')

        # find template to use
        template, template_map = get_template_data_by_class_name(class_name=destination_target_instance.target.root_node.class_name)

        if developer_mode:
            print(f"TEMPLATE NAME {template['name']}")

        # create graph
        create_from_template(material=material, template=template)

        # set attributes
        use_albedo_map = False
        use_normal_map = False
        use_detail_normal_map = False
        use_emission_map = False
        for input_plug in destination_target_instance.inputs:
            # if developer_mode:
            #     print('input_plug', input_plug.name)

            internal_node = None
            for a in destination_target_instance.target.nodes:
                for b in a.inputs:
                    if input_plug.id == b.id:
                        internal_node = a
                        break
                if internal_node is not None:
                    break

            if internal_node is None:
                raise NotImplementedError(f"No internal node found for {input_plug.name}")

            map_definition = None
            for o in template_map['maps']:
                if o['blender_node'] == internal_node.id and o['blender_socket'] == input_plug.name:
                    map_definition = o
                    break

            if map_definition is None:
                raise NotImplementedError(f"No map definition found for {internal_node.id} {input_plug.name}")

            for shader_node in material.node_tree.nodes:
                if not shader_node.name == map_definition['blender_node']:
                    continue
                # if developer_mode:
                #     print(f'node: {shader_node.name}')

                if isinstance(shader_node, bpy.types.ShaderNodeTexImage):
                    if map_definition['blender_socket'] == 'image':
                        # if developer_mode:
                        #     print(f'\tbpy.types.ShaderNodeTexImage: path: {input_plug.computed_value[0]}')
                        #     print(f'\tbpy.types.ShaderNodeTexImage: colorspace: {input_plug.computed_value[1]}')
                        path = input_plug.computed_value[0]
                        if not path == '':
                            if '<UDIM>' in path:
                                pattern = path.replace('\\', '/')
                                pattern = pattern.replace('<UDIM>', '[0-9][0-9][0-9][0-9]')
                                directory = pattern[:pattern.rfind('/') + 1]
                                pattern = pattern.replace(directory, '')
                                image_set = False
                                for item in os.listdir(directory):
                                    if re.match(pattern, item):
                                        tile_path = '{}{}'.format(directory, item)
                                        if not os.path.isfile(tile_path):
                                            continue
                                        if not image_set:
                                            shader_node.image = bpy.data.images.load(tile_path)
                                            shader_node.image.source = 'TILED'
                                            image_set = True
                                            continue
                                        tile_indexes = re.findall('[0-9][0-9][0-9][0-9]', item)
                                        shader_node.image.tiles.new(int(tile_indexes[-1]))
                            else:
                                shader_node.image = bpy.data.images.load(path)

                            if map_definition['blender_node'] == 'Albedo Map':
                                use_albedo_map = True
                            if map_definition['blender_node'] == 'Normal Map':
                                use_normal_map = True
                            if map_definition['blender_node'] == 'Detail Normal Map':
                                use_detail_normal_map = True
                            if map_definition['blender_node'] == 'Emissive Map':
                                use_emission_map = True

                            shader_node.image.colorspace_settings.name = input_plug.computed_value[1]
                        continue

                    raise NotImplementedError(
                        f"No support for bpy.types.ShaderNodeTexImage {map_definition['blender_socket']}")

                if isinstance(shader_node, bpy.types.ShaderNodeBsdfPrincipled):
                    blender_inputs = [o for o in shader_node.inputs if o.name == input_plug.name]
                    if len(blender_inputs) == 0:
                        for property_name, property_object in shader_node.rna_type.properties.items():
                            if not property_name == input_plug.name:
                                continue
                            if property_object.is_readonly:
                                break
                            try:
                                setattr(shader_node, property_name, input_plug.computed_value)
                            except Exception as error:
                                print('Warning: Universal Material Map: Unexpected error when setting property "{0}" to value "{1}": "{2}"'.format(property_name, input_plug.computed_value, error))
                    else:
                        if isinstance(blender_inputs[0], bpy.types.NodeSocketShader):
                            continue
                        try:
                            blender_inputs[0].default_value = input_plug.computed_value
                        except Exception as error:
                            print('Warning: Universal Material Map: Unexpected error when setting input "{0}" to value "{1}": "{2}"'.format(input_plug.name, input_plug.computed_value, error))

                    continue

                if isinstance(shader_node, bpy.types.ShaderNodeGroup):
                    blender_inputs = [o for o in shader_node.inputs if o.name == input_plug.name]
                    if len(blender_inputs) == 0:
                        for property_name, property_object in shader_node.rna_type.properties.items():
                            if not property_name == input_plug.name:
                                continue
                            if property_object.is_readonly:
                                break
                            try:
                                setattr(shader_node, property_name, input_plug.computed_value)
                            except Exception as error:
                                print('Warning: Universal Material Map: Unexpected error when setting property "{0}" to value "{1}": "{2}"'.format(property_name, input_plug.computed_value, error))
                    else:
                        if isinstance(blender_inputs[0], bpy.types.NodeSocketShader):
                            continue
                        try:
                            blender_inputs[0].default_value = input_plug.computed_value
                        except Exception as error:
                            print('Warning: Universal Material Map: Unexpected error when setting input "{0}" to value "{1}": "{2}"'.format(input_plug.name, input_plug.computed_value, error))

                    continue

                if isinstance(shader_node, bpy.types.ShaderNodeMapping):
                    blender_inputs = [o for o in shader_node.inputs if o.name == input_plug.name]
                    value = input_plug.computed_value
                    if input_plug.name == 'Rotation':
                        value[0] = math.radians(value[0])
                        value[1] = math.radians(value[1])
                        value[2] = math.radians(value[2])

                    if len(blender_inputs) == 0:
                        for property_name, property_object in shader_node.rna_type.properties.items():
                            if not property_name == input_plug.name:
                                continue
                            if property_object.is_readonly:
                                break
                            try:
                                setattr(shader_node, property_name, value)
                            except Exception as error:
                                print('Warning: Universal Material Map: Unexpected error when setting property "{0}" to value "{1}": "{2}"'.format(property_name, input_plug.computed_value, error))
                    else:
                        if isinstance(blender_inputs[0], bpy.types.NodeSocketShader):
                            continue
                        try:
                            blender_inputs[0].default_value = value
                        except Exception as error:
                            print('Warning: Universal Material Map: Unexpected error when setting input "{0}" to value "{1}": "{2}"'.format(input_plug.name, input_plug.computed_value, error))

                    continue

        # UX assist with special attributes
        for shader_node in material.node_tree.nodes:
            if shader_node.name == 'OmniPBR Compute' and isinstance(shader_node, bpy.types.ShaderNodeGroup):
                shader_node.inputs['Use Albedo Map'].default_value = 1 if use_albedo_map else 0
                shader_node.inputs['Use Normal Map'].default_value = 1 if use_normal_map else 0
                shader_node.inputs['Use Detail Normal Map'].default_value = 1 if use_detail_normal_map else 0
                shader_node.inputs['Use Emission Map'].default_value = 1 if use_emission_map else 0
                break


class DataConverter(CoreConverter, IDataConverter):
    """ """

    def can_convert_data_to_data(self, class_name: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]]) -> bool:
        """ Resolves if worker can convert the given class and source_data to another class and target data. """
        conversion_graph = _get_conversion_graph_impl(source_class=class_name, render_context=render_context)
        if not conversion_graph:
            return False
        try:
            destination_target_instance = _data_to_output_entity(graph=conversion_graph, data=source_data)
        except Exception as error:
            print('Warning: Unable to get destination assembly using document "{0}".\nDetails: {1}'.format(conversion_graph.filename, error))
            return False
        return destination_target_instance is not None

    def convert_data_to_data(self, class_name: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]]) -> typing.List[typing.Tuple[str, typing.Any]]:
        """
        Returns a list of key value pairs in tuples.
        The first pair is ("umm_target_class", "the_class_name") indicating the conversion target class.
        """
        if developer_mode:
            print('UMM DEBUG: DataConverter.convert_data_to_data()')
            print('\tclass_name="{0}"'.format(class_name))
            print('\trender_context="{0}"'.format(render_context))
            print('\tsource_data=[')
            for o in source_data:
                if o[1] == '':
                    print('\t\t("{0}", ""),'.format(o[0]))
                    continue
                print('\t\t("{0}", {1}),'.format(o[0], o[1]))
            print('\t]')
        conversion_graph = _get_conversion_graph_impl(source_class=class_name, render_context=render_context)
        destination_target_instance = _data_to_output_entity(graph=conversion_graph, data=source_data)

        attribute_data = [(util.TARGET_CLASS_IDENTIFIER, destination_target_instance.target.root_node.class_name)]

        for plug in destination_target_instance.inputs:
            if not plug.input:
                continue
            if plug.is_invalid and isinstance(plug.parent, DagNode):
                plug.parent.compute()
            attribute_data.append((plug.name, plug.computed_value))

        return attribute_data


class OT_InstanceToDataConverter(bpy.types.Operator):
    bl_idname = 'universalmaterialmap.instance_to_data_converter'
    bl_label = 'Universal Material Map Converter Operator'
    bl_description = 'Universal Material Map Converter'

    def execute(self, context):
        print('Conversion Operator: execute')
        # Get object by name: bpy.data.objects['Cube']
        # Get material by name: bpy.data.materials['MyMaterial']
        # node = [o for o in bpy.context.active_object.active_material.node_tree.nodes if o.select][0]
        print('selected_node', bpy.context.active_object, type(bpy.context.active_object))
        # print('\n'.join(dir(bpy.context.active_object)))
        material_slot: bpy.types.MaterialSlot # https://docs.blender.org/api/current/bpy.types.MaterialSlot.html?highlight=materialslot#bpy.types.MaterialSlot
        for material_slot in bpy.context.active_object.material_slots:
            material: bpy.types.Material = material_slot.material
            if material.node_tree:
                for node in material.node_tree.nodes:
                    if isinstance(node, bpy.types.ShaderNodeOutputMaterial):
                        for input in node.inputs:
                            if not input.type == 'SHADER':
                                continue
                            if not input.is_linked:
                                continue
                            for link in input.links:
                                if not isinstance(link, bpy.types.NodeLink):
                                    continue
                                if not link.is_valid:
                                    continue
                                instance = link.from_node
                                for render_context in ['MDL', 'USDPreview']:
                                    if util.can_convert_instance_to_data(instance=instance, render_context=render_context):
                                        util.convert_instance_to_data(instance=instance, render_context=render_context)
                                    else:
                                        print('Information: Universal Material Map: Not able to convert instance "{0}" to data with render context "{1}"'.format(instance, render_context))
            else:
                instance = material
                for render_context in ['MDL', 'USDPreview']:
                    if util.can_convert_instance_to_data(instance=instance, render_context=render_context):
                        util.convert_instance_to_data(instance=instance, render_context=render_context)
                    else:
                        print('Information: Universal Material Map: Not able to convert instance "{0}" to data with render context "{1}"'.format(instance, render_context))
        return {'FINISHED'}


class OT_DataToInstanceConverter(bpy.types.Operator):
    bl_idname = 'universalmaterialmap.data_to_instance_converter'
    bl_label = 'Universal Material Map Converter Operator'
    bl_description = 'Universal Material Map Converter'

    def execute(self, context):
        render_context = 'Blender'
        source_class = 'OmniPBR.mdl|OmniPBR'
        sample_data = [
            ('diffuse_color_constant', (0.800000011920929, 0.800000011920929, 0.800000011920929)),
            ('diffuse_texture', ''),
            ('reflection_roughness_constant', 0.4000000059604645),
            ('reflectionroughness_texture', ''),
            ('metallic_constant', 0.0),
            ('metallic_texture', ''),
            ('specular_level', 0.5),
            ('enable_emission', True),
            ('emissive_color', (0.0, 0.0, 0.0)),
            ('emissive_color_texture', ''),
            ('emissive_intensity', 1.0),
            ('normalmap_texture', ''),
            ('enable_opacity', True),
            ('opacity_constant', 1.0),
        ]

        if util.can_convert_data_to_data(class_name=source_class, render_context=render_context, source_data=sample_data):
            converted_data = util.convert_data_to_data(class_name=source_class, render_context=render_context, source_data=sample_data)
            destination_class = converted_data[0][1]
            if util.can_create_instance(class_name=destination_class):
                instance = util.create_instance(class_name=destination_class)
                print('instance "{0}".'.format(instance))
                temp = converted_data[:]
                while len(temp):
                    item = temp.pop(0)
                    property_name = item[0]
                    property_value = item[1]
                    if util.can_set_instance_attribute(instance=instance, name=property_name):
                        util.set_instance_attribute(instance=instance, name=property_name, value=property_value)
            else:
                print('Cannot create instance from "{0}".'.format(source_class))
        return {'FINISHED'}


class OT_DataToDataConverter(bpy.types.Operator):
    bl_idname = 'universalmaterialmap.data_to_data_converter'
    bl_label = 'Universal Material Map Converter Operator'
    bl_description = 'Universal Material Map Converter'

    def execute(self, context):
        render_context = 'Blender'
        source_class = 'OmniPBR.mdl|OmniPBR'
        sample_data = [
            ('diffuse_color_constant', (0.800000011920929, 0.800000011920929, 0.800000011920929)),
            ('diffuse_texture', ''),
            ('reflection_roughness_constant', 0.4000000059604645),
            ('reflectionroughness_texture', ''),
            ('metallic_constant', 0.0),
            ('metallic_texture', ''),
            ('specular_level', 0.5),
            ('enable_emission', True),
            ('emissive_color', (0.0, 0.0, 0.0)),
            ('emissive_color_texture', ''),
            ('emissive_intensity', 1.0),
            ('normalmap_texture', ''),
            ('enable_opacity', True),
            ('opacity_constant', 1.0),
        ]

        if util.can_convert_data_to_data(class_name=source_class, render_context=render_context, source_data=sample_data):
            converted_data = util.convert_data_to_data(class_name=source_class, render_context=render_context, source_data=sample_data)
            print('converted_data:', converted_data)
        else:
            print('UMM Failed to convert data. util.can_convert_data_to_data() returned False')
        return {'FINISHED'}


class OT_ApplyDataToInstance(bpy.types.Operator):
    bl_idname = 'universalmaterialmap.apply_data_to_instance'
    bl_label = 'Universal Material Map Apply Data To Instance Operator'
    bl_description = 'Universal Material Map Converter'

    def execute(self, context):

        if not bpy.context:
            return {'FINISHED'}
        if not bpy.context.active_object:
            return {'FINISHED'}
        if not bpy.context.active_object.active_material:
            return {'FINISHED'}

        instance = bpy.context.active_object.active_material

        render_context = 'Blender'
        source_class = 'OmniPBR.mdl|OmniPBR'
        sample_data = [
            ('albedo_add', 0.02),  # Adds a constant value to the diffuse color
            ('albedo_desaturation', 0.19999999),  # Desaturates the diffuse color
            ('ao_texture', ('', 'raw')),
            ('ao_to_diffuse', 1),  # Controls the amount of ambient occlusion multiplied into the diffuse color channel
            ('bump_factor', 10),  # Strength of normal map
            ('diffuse_color_constant', (0.800000011920929, 0.800000011920929, 0.800000011920929)),
            ('diffuse_texture', ('D:/Blender_GTC_2021/Marbles/assets/standalone/A_bumper/textures/play_bumper/blue/play_bumperw_albedo.png', 'sRGB')),
            ('diffuse_tint', (0.96202534, 0.8118357, 0.8118357)),  # When enabled, this color value is multiplied over the final albedo color
            ('enable_emission', 0),
            ('enable_ORM_texture', 1),
            ('metallic_constant', 1),
            ('metallic_texture', ('', 'raw')),
            ('metallic_texture_influence', 1),
            ('normalmap_texture', ('D:/Blender_GTC_2021/Marbles/assets/standalone/A_bumper/textures/play_bumper/blue/play_bumperw_normal.png', 'raw')),
            ('ORM_texture', ('D:/Blender_GTC_2021/Marbles/assets/standalone/A_bumper/textures/play_bumper/blue/play_bumperw_orm.png', 'raw')),
            ('reflection_roughness_constant', 1),  # Higher roughness values lead to more blurry reflections
            ('reflection_roughness_texture_influence', 1),  # Blends between the constant value and the lookup of the roughness texture
            ('reflectionroughness_texture', ('', 'raw')),
            ('texture_rotate', 45),
            ('texture_scale', (2, 2)),
            ('texture_translate', (0.1, 0.9)),
        ]

        if util.can_apply_data_to_instance(source_class_name=source_class, render_context=render_context, source_data=sample_data, instance=instance):
            util.apply_data_to_instance(source_class_name=source_class, render_context=render_context, source_data=sample_data, instance=instance)
        else:
            print('UMM Failed to convert data. util.can_convert_data_to_data() returned False')
        return {'FINISHED'}


class OT_CreateTemplateOmniPBR(bpy.types.Operator):
    bl_idname = 'universalmaterialmap.create_template_omnipbr'
    bl_label = 'Convert to OmniPBR Graph'
    bl_description = 'Universal Material Map Converter'

    def execute(self, context):

        if not bpy.context:
            return {'FINISHED'}
        if not bpy.context.active_object:
            return {'FINISHED'}
        if not bpy.context.active_object.active_material:
            return {'FINISHED'}

        create_template(source_class='OmniPBR', material=bpy.context.active_object.active_material)
        return {'FINISHED'}


class OT_CreateTemplateOmniGlass(bpy.types.Operator):
    bl_idname = 'universalmaterialmap.create_template_omniglass'
    bl_label = 'Convert to OmniGlass Graph'
    bl_description = 'Universal Material Map Converter'

    def execute(self, context):

        if not bpy.context:
            return {'FINISHED'}
        if not bpy.context.active_object:
            return {'FINISHED'}
        if not bpy.context.active_object.active_material:
            return {'FINISHED'}

        create_template(source_class='OmniGlass', material=bpy.context.active_object.active_material)
        return {'FINISHED'}


class OT_DescribeShaderGraph(bpy.types.Operator):
    bl_idname = 'universalmaterialmap.describe_shader_graph'
    bl_label = 'Universal Material Map Describe Shader Graph Operator'
    bl_description = 'Universal Material Map'

    @staticmethod
    def describe_node(node) -> dict:
        node_definition = dict()
        node_definition['name'] = node.name
        node_definition['label'] = node.label
        node_definition['location'] = [node.location[0], node.location[1]]
        node_definition['width'] = node.width
        node_definition['height'] = node.height
        node_definition['parent'] = node.parent.name if node.parent else None
        node_definition['class'] = type(node).__name__
        node_definition['inputs'] = []
        node_definition['outputs'] = []
        node_definition['nodes'] = []
        node_definition['links'] = []
        node_definition['properties'] = []
        node_definition['texts'] = []

        if node_definition['class'] == 'NodeFrame':
            node_definition['properties'].append(
                {
                    'name': 'use_custom_color',
                    'value': node.use_custom_color,
                }
            )
            node_definition['properties'].append(
                {
                    'name': 'color',
                    'value': [node.color[0], node.color[1], node.color[2]],
                }
            )
            node_definition['properties'].append(
                {
                    'name': 'shrink',
                    'value': node.shrink,
                }
            )

            if node.text is not None:
                text_definition = dict()
                text_definition['name'] = node.text.name
                text_definition['contents'] = node.text.as_string()
                node_definition['texts'].append(text_definition)

        elif node_definition['class'] == 'ShaderNodeRGB':

            for index, output in enumerate(node.outputs):
                definition = dict()
                definition['index'] = index
                definition['name'] = output.name
                definition['class'] = type(output).__name__

                if definition['class'] == 'NodeSocketColor':
                    default_value = output.default_value
                    definition['default_value'] = [default_value[0], default_value[1], default_value[2], default_value[3]]
                else:
                    raise NotImplementedError()

                node_definition['outputs'].append(definition)

        elif node_definition['class'] == 'ShaderNodeMixRGB':

            node_definition['properties'].append(
                {
                    'name': 'blend_type',
                    'value': node.blend_type,
                }
            )

            node_definition['properties'].append(
                {
                    'name': 'use_clamp',
                    'value': node.use_clamp,
                }
            )

            for index, input in enumerate(node.inputs):
                definition = dict()
                definition['index'] = index
                definition['name'] = input.name
                definition['class'] = type(input).__name__

                if definition['class'] == 'NodeSocketFloatFactor':
                    definition['default_value'] = node.inputs[input.name].default_value
                elif definition['class'] == 'NodeSocketColor':
                    default_value = node.inputs[input.name].default_value
                    definition['default_value'] = [default_value[0], default_value[1], default_value[2], default_value[3]]
                else:
                    raise NotImplementedError()

                node_definition['inputs'].append(definition)

        elif node_definition['class'] == 'ShaderNodeGroup':
            for index, input in enumerate(node.inputs):
                definition = dict()
                definition['index'] = index
                definition['name'] = input.name
                definition['class'] = type(input).__name__

                if definition['class'] == 'NodeSocketFloatFactor':
                    definition['min_value'] = node.node_tree.inputs[input.name].min_value
                    definition['max_value'] = node.node_tree.inputs[input.name].max_value
                    definition['default_value'] = node.inputs[input.name].default_value
                elif definition['class'] == 'NodeSocketIntFactor':
                    definition['min_value'] = node.node_tree.inputs[input.name].min_value
                    definition['max_value'] = node.node_tree.inputs[input.name].max_value
                    definition['default_value'] = node.inputs[input.name].default_value
                elif definition['class'] == 'NodeSocketColor':
                    default_value = node.inputs[input.name].default_value
                    definition['default_value'] = [default_value[0], default_value[1], default_value[2], default_value[3]]
                else:
                    raise NotImplementedError()

                node_definition['inputs'].append(definition)

            for index, output in enumerate(node.outputs):
                definition = dict()
                definition['index'] = index
                definition['name'] = output.name
                definition['class'] = type(output).__name__
                node_definition['outputs'].append(definition)

            for child in node.node_tree.nodes:
                node_definition['nodes'].append(OT_DescribeShaderGraph.describe_node(child))

            for link in node.node_tree.links:
                if not isinstance(link, bpy.types.NodeLink):
                    continue
                if not link.is_valid:
                    continue
                link_definition = dict()
                link_definition['from_node'] = link.from_node.name
                link_definition['from_socket'] = link.from_socket.name
                link_definition['to_node'] = link.to_node.name
                link_definition['to_socket'] = link.to_socket.name
                node_definition['links'].append(link_definition)
        elif node_definition['class'] == 'ShaderNodeUVMap':
            pass
        elif node_definition['class'] == 'ShaderNodeTexImage':
            pass
        elif node_definition['class'] == 'ShaderNodeOutputMaterial':
            pass
        elif node_definition['class'] == 'ShaderNodeBsdfPrincipled':
            pass
        elif node_definition['class'] == 'ShaderNodeMapping':
            pass
        elif node_definition['class'] == 'ShaderNodeNormalMap':
            pass
        elif node_definition['class'] == 'ShaderNodeHueSaturation':
            pass
        elif node_definition['class'] == 'ShaderNodeSeparateRGB':
            pass
        elif node_definition['class'] == 'NodeGroupInput':
            pass
        elif node_definition['class'] == 'NodeGroupOutput':
            pass
        elif node_definition['class'] == 'ShaderNodeMath':
            node_definition['properties'].append(
                {
                    'name': 'operation',
                    'value': node.operation,
                }
            )

            node_definition['properties'].append(
                {
                    'name': 'use_clamp',
                    'value': node.use_clamp,
                }
            )
        elif node_definition['class'] == 'ShaderNodeVectorMath':
            node_definition['properties'].append(
                {
                    'name': 'operation',
                    'value': node.operation,
                }
            )
        else:
            raise NotImplementedError(node_definition['class'])

        return node_definition

    def execute(self, context):
        material = bpy.context.active_object.active_material
        output = dict()
        output['name'] = 'Principled Omni Glass'
        output['nodes'] = []
        output['links'] = []
        for node in material.node_tree.nodes:
            output['nodes'].append(OT_DescribeShaderGraph.describe_node(node))

        for link in material.node_tree.links:
            if not isinstance(link, bpy.types.NodeLink):
                continue
            if not link.is_valid:
                continue
            link_definition = dict()
            link_definition['from_node'] = link.from_node.name
            link_definition['from_socket'] = link.from_socket.name
            link_definition['to_node'] = link.to_node.name
            link_definition['to_socket'] = link.to_socket.name
            output['links'].append(link_definition)

        print(json.dumps(output, indent=4))
        return {'FINISHED'}


def initialize():
    if getattr(sys.modules[__name__], '__initialized'):
        return
    setattr(sys.modules[__name__], '__initialized', True)

    util.register(converter=DataConverter())
    util.register(converter=ObjectConverter())
    print('Universal Material Map: Registered Converter classes.')


initialize()
