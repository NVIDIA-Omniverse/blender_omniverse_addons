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
import os
import re
import sys
import json

import bpy

from ..core.data import Library
from ..core.feature import POLLING
from ..core.service import store
from ..core.service import delegate
from ..core.util import get_extension_from_image_file_format


LIBRARY_ID = '195c69e1-7765-4a16-bb3a-ecaa222876d9'
__initialized = False

developer_mode: bool = False

CORE_MATERIAL_PROPERTIES = [
    ('diffuse_color', 'RGBA'),
    ('metallic', 'VALUE'),
    ('specular_color', 'STRING'),
    ('roughness', 'VALUE'),
    ('use_backface_culling', 'BOOLEAN'),
    ('blend_method', 'STRING'),
    ('shadow_method', 'STRING'),
    ('alpha_threshold', 'VALUE'),
    ('use_screen_refraction', 'BOOLEAN'),
    ('refraction_depth', 'VALUE'),
    ('use_sss_translucency', 'BOOLEAN'),
    ('pass_index', 'INT'),
]


def show_message(message: str = '', title: str = 'Message Box', icon: str = 'INFO'):
    try:
        def draw(self, context):
            self.layout.label(text=message)

        bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)
    except:
        print('{0}\n{1}'.format(title, message))


def initialize():
    if getattr(sys.modules[__name__], '__initialized'):
        return
    setattr(sys.modules[__name__], '__initialized', True)

    directory = os.path.expanduser('~').replace('\\', '/')
    if not directory.endswith('/Documents'):
        directory = '{0}/Documents'.format(directory)
    directory = '{0}/Omniverse/Blender/UMMLibrary'.format(directory)

    library = Library.Create(
        library_id=LIBRARY_ID,
        name='Blender',
        manifest=delegate.FilesystemManifest(root_directory='{0}'.format(directory)),
        conversion_graph=delegate.Filesystem(root_directory='{0}/ConversionGraph'.format(directory)),
        target=delegate.Filesystem(root_directory='{0}/Target'.format(directory)),
    )

    store.register_library(library=library)

    from ..blender import converter
    converter.initialize()
    from ..blender import generator
    generator.initialize()
    if POLLING:
        # TODO: On application exit > un_initialize()
        pass


def un_initialize():
    if POLLING:
        store.on_shutdown()


def get_library():
    """
    :return: omni.universalmaterialmap.core.data.Library
    """
    initialize()
    return store.get_library(library_id=LIBRARY_ID)


def __get_value_impl(socket: bpy.types.NodeSocketStandard, depth=0, max_depth=100) -> typing.Any:

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


def get_value(socket: bpy.types.NodeSocketStandard) -> typing.Any:
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
        node.node_tree = bpy.data.node_groups.new('node tree', 'ShaderNodeTree')

        child_cache = dict()

        for child_definition in node_definition['nodes']:
            child_cache[child_definition['name']] = _create_node_from_template(node_tree=node.node_tree, node_definition=child_definition)

        for input_definition in node_definition['inputs']:
            node.node_tree.inputs.new(input_definition['class'], input_definition['name'])
            if input_definition['class'] == 'NodeSocketFloatFactor':
                node.node_tree.inputs[input_definition['name']].min_value = input_definition['min_value']
                node.node_tree.inputs[input_definition['name']].max_value = input_definition['max_value']
                node.node_tree.inputs[input_definition['name']].default_value = input_definition['default_value']
                node.inputs[input_definition['name']].default_value = input_definition['default_value']
            if input_definition['class'] == 'NodeSocketIntFactor':
                node.node_tree.inputs[input_definition['name']].min_value = input_definition['min_value']
                node.node_tree.inputs[input_definition['name']].max_value = input_definition['max_value']
                node.node_tree.inputs[input_definition['name']].default_value = input_definition['default_value']
                node.inputs[input_definition['name']].default_value = input_definition['default_value']
            if input_definition['class'] == 'NodeSocketColor':
                node.node_tree.inputs[input_definition['name']].default_value = input_definition['default_value']
                node.inputs[input_definition['name']].default_value = input_definition['default_value']

        for output_definition in node_definition['outputs']:
            node.node_tree.outputs.new(output_definition['class'], output_definition['name'])

        for link_definition in node_definition['links']:
            from_node = child_cache[link_definition['from_node']]
            from_socket = [o for o in from_node.outputs if o.name == link_definition['from_socket']][0]
            to_node = child_cache[link_definition['to_node']]
            to_socket = [o for o in to_node.inputs if o.name == link_definition['to_socket']][0]
            node.node_tree.links.new(from_socket, to_socket)

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

    for link_definition in template['links']:
        from_node = child_cache[link_definition['from_node']]
        from_socket = [o for o in from_node.outputs if o.name == link_definition['from_socket']][0]
        to_node = child_cache[link_definition['to_node']]
        to_socket = [o for o in to_node.inputs if o.name == link_definition['to_socket']][0]
        material.node_tree.links.new(from_socket, to_socket)


def create_from_template(material: bpy.types.Material, template: dict) -> None:
    # Make sure we're using nodes.
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


def get_parent_material(shader_node: object) -> bpy.types.Material:
    for material in bpy.data.materials:
        if shader_node == material:
            return material
        if not material.use_nodes:
            continue
        if not material.node_tree or not material.node_tree.nodes:
            continue
        for node in material.node_tree.nodes:
            if shader_node == node:
                return material
    return None


def get_template_data_by_shader_node(shader_node: object) -> typing.Tuple[typing.Dict, typing.Dict, str, bpy.types.Material]:
    material: bpy.types.Material = get_parent_material(shader_node=shader_node)
    if material and material.use_nodes and material.node_tree and material.node_tree.nodes:
        template_directory = '{}'.format(__file__).replace('\\', '/')
        template_directory = template_directory[:template_directory.rfind('/')]
        template_directory = f'{template_directory}/template'
        for item in os.listdir(template_directory):
            if item.lower().endswith('_map.json'):
                continue
            if not item.lower().endswith('.json'):
                continue
            template_filepath = f'{template_directory}/{item}'
            with open(template_filepath, 'r') as template_file:
                template = json.load(template_file)
            material_has_all_template_nodes = True
            for node_definition in template['nodes']:
                found_node = False
                for node in material.node_tree.nodes:
                    if node.name == node_definition['name']:
                        found_node = True
                        break
                if not found_node:
                    material_has_all_template_nodes = False
                    break
            if not material_has_all_template_nodes:
                continue
            template_has_all_material_nodes = True
            for node in material.node_tree.nodes:
                found_template = False
                for node_definition in template['nodes']:
                    if node.name == node_definition['name']:
                        found_template = True
                        break
                if not found_template:
                    template_has_all_material_nodes = False
                    break
            if not template_has_all_material_nodes:
                continue

            template_shader_name = template['name']

            map_filename = '{}_map.json'.format(item[:item.rfind('.')])
            template_map_filepath = f'{template_directory}/{map_filename}'
            with open(template_map_filepath, 'r') as template_map_file:
                template_map = json.load(template_map_file)
            return template, template_map, template_shader_name, material

    return None, None, None, None


def get_template_data_by_class_name(class_name: str) -> typing.Tuple[typing.Dict, typing.Dict]:
    template_directory = '{}'.format(__file__).replace('\\', '/')
    template_directory = template_directory[:template_directory.rfind('/')]
    template_directory = f'{template_directory}/template'
    for item in os.listdir(template_directory):
        if item.lower().endswith('_map.json'):
            continue
        if not item.lower().endswith('.json'):
            continue
        template_filepath = f'{template_directory}/{item}'
        with open(template_filepath, 'r') as template_file:
            template = json.load(template_file)
        if not template['name'] == class_name:
            continue

        map_filename = '{}_map.json'.format(item[:item.rfind('.')])
        template_map_filepath = f'{template_directory}/{map_filename}'
        with open(template_map_filepath, 'r') as template_map_file:
            template_map = json.load(template_map_file)
        return template, template_map

    return None, None
