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

# Copyright (c) 2021-2024 NVIDIA CORPORATION.  All rights reserved.

import os
import json
from typing import *

import bpy

template_file_path = os.sep.join([
    os.path.dirname(os.path.abspath(__file__)),
    "template",
    "template.blend"
])


def get_pbr_shading_group(name:str) -> bpy.types.NodeGroup:
    assert name in {"OmniPBR", "OmniGlass"}, f"Invalid group type '{name}'!"

    if name not in bpy.data.node_groups:
        with bpy.data.libraries.load(template_file_path, link=False) as (data_source, data_target):
            present_groups = [x for x in data_source.node_groups if x == name]
            data_target.node_groups = present_groups

    return bpy.data.node_groups[name]


def get_extension_from_image_file_format(format:str, base_name:str) -> str:
    """
    For image formats that have multiple possible extensions,
    determine if we should stick with the current format specifier
    or use the one from the filename itself.
    """
    format = format.lower()
    split = base_name.rpartition(".")[-1]
    extension = split.lower() if len(split) else None

    if format == "open_exr":
        format = "exr"
    elif format == "jpeg":
        format = extension if extension in {"jpeg", "jpg"} else "jpg"
    elif format == "tiff":
        format = extension if extension in {"tiff", "tif"} else "tif"
    elif format == "targa_raw":
        format = "tga"
    return format


def __get_value_impl(socket: bpy.types.NodeSocketStandard, depth=0, max_depth=100) -> Any:

    # Local utility function which returns a file extension
    # corresponding to the given image file format string.
    # This mimics similar logic used in the Blender USD IO
    # C++ implementation.

    debug = False
    if debug:
        print('__get_value_impl: depth={0}'.format(depth))

    if depth > max_depth:
        if debug:
            print('\t reached max_depth ({0}). terminating recursion'.format(max_depth))
        return None

    if debug:
        print('\tsocket.is_linked'.format(socket.is_linked))
    if socket.is_linked:
        for link in socket.links:
            if not isinstance(link, bpy.types.NodeLink):
                if debug:
                    print('\t\tlink is not bpy.types.NodeLink: {0}'.format(type(link)))
                continue
            if not link.is_valid:
                if debug:
                    print('\t\tlink is not valid')
                continue
            instance = link.from_node
            if debug:
                print('\t\tlink.from_node: {0}'.format(type(instance)))
            if isinstance(instance, bpy.types.ShaderNodeTexImage):
                print(f'UMM: image.filepath: "{instance.image.filepath}"')
                print(f'UMM: image.source: "{instance.image.source}"')
                print(f'UMM: image.file_format: "{instance.image.file_format}"')
                if debug:
                    print('\t\tinstance.image: {0}'.format(instance.image))
                    if instance.image:
                        print('\t\tinstance.image.source: {0}'.format(instance.image.source))
                if instance.image and (instance.image.source == 'FILE' or instance.image.source == 'TILED'):
                    value = instance.image.filepath
                    if (instance.image.source == 'TILED'):
                        # Find all numbers in the path.
                        numbers = re.findall('[0-9]+', value)
                        if (len(numbers) > 0):
                            # Get the string representation of the last number.
                            num_str = str(numbers[-1])
                            # Replace the number substring with '<UDIM>'.
                            split_items = value.rsplit(num_str, 1)
                            if (len(split_items)==2):
                                value = split_items[0] + '<UDIM>' + split_items[1]
                    if debug:
                        print('\t\tinstance.image.filepath: {0}'.format(value))
                    try:
                        if value and instance.image.packed_file:
                            # The image is packed, so ignore the filepath, which is likely
                            # invalid, and return just the base name.
                            value = bpy.path.basename(value)
                            # Make sure the file has a valid extension for
                            # the expected format.
                            file_format = instance.image.file_format
                            file_format = get_extension_from_image_file_format(file_format, base_name=value)
                            value = bpy.path.ensure_ext(value, '.' + file_format)
                            print(f'UMM: packed image data: "{[value, instance.image.colorspace_settings.name]}"')
                            return [value, instance.image.colorspace_settings.name]
                        if value is None or value == '':
                            file_format = instance.image.file_format
                            file_format = get_extension_from_image_file_format(file_format)
                            value = f'{instance.image.name}.{file_format}'
                            if debug:
                                print(f'\t\tvalue: {value}')
                            print(f'UMM: image data: "{[value, instance.image.colorspace_settings.name]}"')
                            return [value, instance.image.colorspace_settings.name]
                        return [os.path.abspath(bpy.path.abspath(value)), instance.image.colorspace_settings.name]
                    except Exception as error:
                        print('Warning: Universal Material Map: Unable to evaluate absolute file path of texture "{0}". Detail: {1}'.format(instance.image.filepath, error))
                        return None
            if isinstance(instance, bpy.types.ShaderNodeNormalMap):
                for o in instance.inputs:
                    if o.name == 'Color':
                        value = __get_value_impl(socket=o, depth=depth + 1, max_depth=max_depth)
                        if value:
                            return value
            for o in instance.inputs:
                value = __get_value_impl(socket=o, depth=depth + 1, max_depth=max_depth)
                if debug:
                    print('\t\tre-entrant: input="{0}", value="{1}"'.format(o.name, value))
                if value:
                    return value
    return None


def get_value(socket: bpy.types.NodeSocketStandard) -> Any:
    debug = False
    value = __get_value_impl(socket=socket)
    if debug:
        print('get_value', value, socket.default_value)
    return socket.default_value if not value else value


def _create_node_from_template(node_tree: bpy.types.NodeTree, node_definition: dict, parent: object = None) -> object:
    node = node_tree.nodes.new(node_definition['class'])

    if parent:
        node.parent = parent

    node.name = node_definition['name']
    node.label = node_definition['label']
    node.location = node_definition['location']

    if node_definition['class'] == 'NodeFrame':
        node.width = node_definition['width']
        node.height = node_definition['height']

    for o in node_definition['properties']:
        setattr(node, o['name'], o['value'])

    if node_definition['class'] == 'NodeFrame':
        for text_definition in node_definition['texts']:
            existing = None
            for o in bpy.data.texts:
                if o.name == text_definition['name']:
                    existing = o
                    break

            if existing is None:
                existing = bpy.data.texts.new(text_definition['name'])
                existing.write(text_definition['contents'])

            node.text = existing
            node.location = node_definition['location']

    elif node_definition['class'] == 'ShaderNodeGroup':
        ## New version: use the pre-made node groups from the template file
        shader_type = node.name.partition(" ")[0]
        shader_group = get_pbr_shading_group(shader_type)
        material = bpy.context.active_object.active_material
        node_tree = material.node_tree
        node.node_tree = shader_group
        node.width = node_definition['width']
        node.height = node_definition['height']
        node.location = node_definition['location']

    elif node_definition['class'] == 'ShaderNodeMixRGB':
        for input_definition in node_definition['inputs']:
            if input_definition['class'] == 'NodeSocketFloatFactor':
                node.inputs[input_definition['name']].default_value = input_definition['default_value']
            if input_definition['class'] == 'NodeSocketColor':
                node.inputs[input_definition['name']].default_value = input_definition['default_value']

    elif node_definition['class'] == 'ShaderNodeRGB':

        for output_definition in node_definition['outputs']:
            if output_definition['class'] == 'NodeSocketColor':
                node.outputs[output_definition['name']].default_value = output_definition['default_value']

    return node


def create_template(source_class: str, material: bpy.types.Material) -> None:
    template_filepath = '{}'.format(__file__).replace('\\', '/')
    template_filepath = template_filepath[:template_filepath.rfind('/')]
    template_filepath = '{}/template/{}.json'.format(template_filepath, source_class.lower())
    if not os.path.exists(template_filepath):
        return
    with open(template_filepath, 'r') as template_file:
        template = json.load(template_file)

    # Make sure we're using nodes.
    material.use_nodes = True

    # Remove existing nodes - we're starting from scratch.
    to_delete = [o for o in material.node_tree.nodes]
    while len(to_delete):
        material.node_tree.nodes.remove(to_delete.pop())

    # Create nodes according to template.
    child_cache = dict()
    for node_definition in template['nodes']:
        if node_definition['parent'] is None:
            node = _create_node_from_template(node_tree=material.node_tree, node_definition=node_definition)
            child_cache[node_definition['name']] = node

    for node_definition in template['nodes']:
        if node_definition['parent'] is not None:
            parent = child_cache[node_definition['parent']]
            node = _create_node_from_template(node_tree=material.node_tree, node_definition=node_definition, parent=parent)
            child_cache[node_definition['name']] = node

    for link in template['links']:
        from_node = material.node_tree.nodes[link['from_node']]
        from_socket = [o for o in from_node.outputs if o.name == link['from_socket']][0]
        to_node = material.node_tree.nodes[link['to_node']]
        to_socket = [o for o in to_node.inputs if o.name == link['to_socket']][0]
        material.node_tree.links.new(from_socket, to_socket)


def create_from_template(material:bpy.types.Material, template:dict) -> None:
    material.use_nodes = True

    # Create nodes according to template.
    child_cache = dict()
    for node_definition in template['nodes']:
        if node_definition['parent'] is None:
            node = _create_node_from_template(node_tree=material.node_tree, node_definition=node_definition)
            child_cache[node_definition['name']] = node

    for node_definition in template['nodes']:
        if node_definition['parent'] is not None:
            parent = child_cache[node_definition['parent']]
            node = _create_node_from_template(node_tree=material.node_tree, node_definition=node_definition, parent=parent)
            child_cache[node_definition['name']] = node

    for link_definition in template['links']:
        from_node = child_cache[link_definition['from_node']]
        from_socket = [o for o in from_node.outputs if o.name == link_definition['from_socket']][0]
        to_node = child_cache[link_definition['to_node']]
        to_socket = [o for o in to_node.inputs if o.name == link_definition['to_socket']][0]
        material.node_tree.links.new(from_socket, to_socket)

