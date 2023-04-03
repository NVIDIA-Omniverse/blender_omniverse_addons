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

"""
To invoke in Blender script editor:

import bpy

bpy.ops.universalmaterialmap.generator()
bpy.ops.universalmaterialmap.converter()

INFO_HT_header
Header
VIEW3D_HT_tool_header
Info Header: INFO_HT_HEADER
3D View Header: VIEW3D_HT_HEADER
Timeline Header: TIME_HT_HEADER
Outliner Header: OUTLINER_HT_HEADER
Properties Header: PROPERTIES_HT_HEADER, etc.
"""

"""
Menu location problem
https://blender.stackexchange.com/questions/3393/add-custom-menu-at-specific-location-in-the-header#:~:text=Blender%20has%20a%20built%20in,%3EPython%2D%3EUI%20Menu.
"""

bl_info = {
    'name': 'Universal Material Map',
    'author': 'NVIDIA Corporation',
    'description': 'A Blender AddOn based on the Universal Material Map framework.',
    'blender': (3, 1, 0),
    'location': 'View3D',
    'warning': '',
    'category': 'Omniverse'
}

import sys
import importlib

import bpy

from .universalmaterialmap.blender import developer_mode


if developer_mode:

    print('UMM DEBUG: Initializing "{0}"'.format(__file__))

    ordered_module_names = [
        'omni.universalmaterialmap',
        'omni.universalmaterialmap.core',
        'omni.universalmaterialmap.core.feature',
        'omni.universalmaterialmap.core.singleton',
        'omni.universalmaterialmap.core.data',
        'omni.universalmaterialmap.core.util',
        'omni.universalmaterialmap.core.operator',
        'omni.universalmaterialmap.core.service',
        'omni.universalmaterialmap.core.service.core',
        'omni.universalmaterialmap.core.service.delegate',
        'omni.universalmaterialmap.core.service.resources',
        'omni.universalmaterialmap.core.service.store',
        'omni.universalmaterialmap.core.converter',
        'omni.universalmaterialmap.core.converter.core',
        'omni.universalmaterialmap.core.converter.util',
        'omni.universalmaterialmap.core.generator',
        'omni.universalmaterialmap.core.generator.core',
        'omni.universalmaterialmap.core.generator.util',
        'omni.universalmaterialmap.blender',
        'omni.universalmaterialmap.blender.menu',
        'omni.universalmaterialmap.blender.converter',
        'omni.universalmaterialmap.blender.generator',
        'omni.universalmaterialmap.blender.material',
    ]

    for module_name in sys.modules:
        if 'omni.' not in module_name:
            continue
        if module_name not in ordered_module_names:
            raise Exception('Unexpected module name in sys.modules: {0}'.format(module_name))

    for module_name in ordered_module_names:
        if module_name in sys.modules:
            print('UMM reloading: {0}'.format(module_name))
            importlib.reload(sys.modules.get(module_name))


if developer_mode:
    from .universalmaterialmap.blender.converter import OT_InstanceToDataConverter, OT_DataToInstanceConverter, OT_DataToDataConverter, OT_ApplyDataToInstance, OT_DescribeShaderGraph
    from .universalmaterialmap.blender.converter import OT_CreateTemplateOmniPBR, OT_CreateTemplateOmniGlass
    from .universalmaterialmap.blender.menu import UniversalMaterialMapMenu
    from .universalmaterialmap.blender.generator import OT_Generator
else:
    from .universalmaterialmap.blender.converter import OT_CreateTemplateOmniPBR, OT_CreateTemplateOmniGlass
    from .universalmaterialmap.blender.menu import UniversalMaterialMapMenu



def draw_item(self, context):
    layout = self.layout
    layout.menu(UniversalMaterialMapMenu.bl_idname)


def register():
    bpy.utils.register_class(OT_CreateTemplateOmniPBR)
    bpy.utils.register_class(OT_CreateTemplateOmniGlass)
    if developer_mode:
        bpy.utils.register_class(OT_DataToInstanceConverter)
        bpy.utils.register_class(OT_DataToDataConverter)
        bpy.utils.register_class(OT_ApplyDataToInstance)
        bpy.utils.register_class(OT_InstanceToDataConverter)
        bpy.utils.register_class(OT_DescribeShaderGraph)
        bpy.utils.register_class(OT_Generator)

    bpy.utils.register_class(UniversalMaterialMapMenu)
    # lets add ourselves to the main header
    bpy.types.NODE_HT_header.append(draw_item)


def unregister():
    bpy.utils.unregister_class(OT_CreateTemplateOmniPBR)
    bpy.utils.unregister_class(OT_CreateTemplateOmniGlass)
    if developer_mode:
        bpy.utils.unregister_class(OT_DataToInstanceConverter)
        bpy.utils.unregister_class(OT_DataToDataConverter)
        bpy.utils.unregister_class(OT_ApplyDataToInstance)
        bpy.utils.unregister_class(OT_InstanceToDataConverter)
        bpy.utils.unregister_class(OT_DescribeShaderGraph)
        bpy.utils.unregister_class(OT_Generator)

    bpy.utils.unregister_class(UniversalMaterialMapMenu)
    bpy.types.NODE_HT_header.remove(draw_item)


if __name__ == "__main__":
    register()

    # The menu can also be called from scripts
    # bpy.ops.wm.call_menu(name=UniversalMaterialMapMenu.bl_idname)

