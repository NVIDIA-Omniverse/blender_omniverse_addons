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

import bpy

from . import developer_mode


class UniversalMaterialMapMenu(bpy.types.Menu):
    bl_label = "Omniverse"
    bl_idname = "OBJECT_MT_umm_node_menu"

    def draw(self, context):
        layout = self.layout

        layout.operator('universalmaterialmap.create_template_omnipbr', text='Replace with OmniPBR graph template')
        layout.operator('universalmaterialmap.create_template_omniglass', text='Replace with OmniGlass graph template')

        if developer_mode:
            layout.operator('universalmaterialmap.generator', text='DEV: Generate Targets')
            layout.operator('universalmaterialmap.instance_to_data_converter', text='DEV: Convert Instance to Data')
            layout.operator('universalmaterialmap.data_to_instance_converter', text='DEV: Convert Data to Instance')
            layout.operator('universalmaterialmap.data_to_data_converter', text='DEV: Convert Data to Data')
            layout.operator('universalmaterialmap.apply_data_to_instance', text='DEV: Apply Data to Instance')
            layout.operator('universalmaterialmap.describe_shader_graph', text='DEV: Describe Shader Graph')
