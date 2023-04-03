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


from bpy.types import Panel
from os.path import join, dirname
import bpy.utils.previews

#---------------Custom ICONs----------------------

def get_icons_directory():
    icons_directory = join(dirname(__file__), "icons")
    return icons_directory

class OPTIMIZE_PT_Panel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "OPTIMIZE SCENE"
    bl_category = "Omniverse"
    
    #retrieve icons
    icons = bpy.utils.previews.new()
    icons_directory = get_icons_directory()
    icons.load("OMNI", join(icons_directory, "ICON.png"), 'IMAGE')
    icons.load("GEAR", join(icons_directory, "gear.png"), 'IMAGE')
    

    def draw(self, context):

        layout = self.layout

        layout.label(text="Omniverse", icon_value=self.icons["OMNI"].icon_id)

        optimizeOptions = context.scene.optimize_options
        modifyOptions = context.scene.modify_options
        uvOptions = context.scene.uv_options
        chopOptions = context.scene.chop_options

        # OPERATOR SETTINGS
        box = layout.box()
        col = box.column(align= True)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("optimize.scene", text = "Optimize Scene", icon_value=self.icons["GEAR"].icon_id)
        col.separator()
        row2 = col.row(align=True)
        row2.scale_y = 1.3
        row2.prop(optimizeOptions, "operation", text="Operation")
        col.separator()
        col.prop(optimizeOptions, "print_attributes", expand= True)

        box2 = layout.box()
        box2.label(text= "OPERATION PROPERTIES:")
        col2 = box2.column(align= True)
        
        # MODIFY SETTINGS
        if optimizeOptions.operation == 'modify':
            row = col2.row(align= True)
            row.prop(modifyOptions, "modifier", text="Modifier")
            row2 = col2.row(align= True)
            row3 = col2.row(align= True)
            
            #DECIMATE
            if modifyOptions.modifier == 'DECIMATE':
                row2.prop(modifyOptions, "decimate_type", expand= True)
                if modifyOptions.decimate_type == 'COLLAPSE':
                    row3.prop(modifyOptions, "ratio", expand= True)
                elif modifyOptions.decimate_type == 'UNSUBDIV':
                    row3.prop(modifyOptions, "iterations", expand= True)
                elif modifyOptions.decimate_type == 'DISSOLVE':
                    row3.prop(modifyOptions, "angle", expand= True)
            #REMESH
            elif modifyOptions.modifier == 'REMESH':
                row2.prop(modifyOptions, "remesh_type", expand= True)
                if modifyOptions.remesh_type == 'BLOCKS':
                    row3.prop(modifyOptions, "oDepth", expand= True)
                if modifyOptions.remesh_type == 'SMOOTH':
                    row3.prop(modifyOptions, "oDepth", expand= True)
                if modifyOptions.remesh_type == 'SHARP':
                    row3.prop(modifyOptions, "oDepth", expand= True)
                if modifyOptions.remesh_type == 'VOXEL':
                    row3.prop(modifyOptions, "voxel_size", expand= True)
            #NODES
            elif modifyOptions.modifier == 'NODES':
                row2.prop(modifyOptions, "geo_type")
                if modifyOptions.geo_type == "GeometryNodeSubdivisionSurface":
                    row2.prop(modifyOptions, "geo_attribute", expand= True)
        
            col2.prop(modifyOptions, "selected_only", expand= True)
            col2.prop(modifyOptions, "apply_mod", expand= True)

            box3 = col2.box()
            col3 = box3.column(align=True)
            col3.label(text="FIX MESH BEFORE MODIFY")
            col3.prop(modifyOptions, "fix_bad_mesh", expand= True)
            if modifyOptions.fix_bad_mesh:
                col3.prop(modifyOptions, "dissolve_threshold", expand= True)
            col3.prop(modifyOptions, "merge_vertex", expand= True)
            if modifyOptions.merge_vertex:
                col3.prop(modifyOptions, "merge_threshold", expand= True)
            if modifyOptions.fix_bad_mesh or modifyOptions.merge_vertex:
                col3.prop(modifyOptions, "remove_existing_sharp", expand= True)
            col3.prop(modifyOptions, "fix_normals", expand= True)
            if modifyOptions.fix_normals:
                col3.prop(modifyOptions, "create_new_custom_normals", expand= True)

            # use_modifier_stack= modifyOptions.use_modifier_stack,
            # modifier_stack=[["DECIMATE", "COLLAPSE", 0.5]],

        # FIX MESH SETTINGS
        elif optimizeOptions.operation == 'fixMesh':
            col2.prop(modifyOptions, "selected_only", expand= True)
            col3 = col2.column(align=True)
            col3.prop(modifyOptions, "fix_bad_mesh", expand= True)
            if modifyOptions.fix_bad_mesh:
                col3.prop(modifyOptions, "dissolve_threshold", expand= True)
            col3.prop(modifyOptions, "merge_vertex", expand= True)
            if modifyOptions.merge_vertex:
                col3.prop(modifyOptions, "merge_threshold", expand= True)
            if modifyOptions.fix_bad_mesh or modifyOptions.merge_vertex:
                col3.prop(modifyOptions, "remove_existing_sharp", expand= True)
            col3.prop(modifyOptions, "fix_normals", expand= True)
            if modifyOptions.fix_normals:
                col3.prop(modifyOptions, "create_new_custom_normals", expand= True)

        # UV SETTINGS
        elif optimizeOptions.operation == 'uv':
            if uvOptions.unwrap_type == 'Smart':
                col2.label(text= "SMART UV CAN BE SLOW", icon='ERROR')
            else:
                col2.label(text= "Unwrap Type")
            col2.prop(uvOptions, "unwrap_type", expand= True)
            col2.prop(uvOptions, "selected_only", expand= True)
            col2.prop(uvOptions, "scale_to_bounds", expand= True)
            col2.prop(uvOptions, "clip_to_bounds", expand= True)
            col2.prop(uvOptions, "use_set_size", expand= True)
            if uvOptions.use_set_size:
                col2.prop(uvOptions, "set_size", expand= True)
            col2.prop(uvOptions, "print_updated_results", expand= True)

        # CHOP SETTINGS
        elif optimizeOptions.operation == 'chop':
            col2.prop(chopOptions, "selected_only", expand= True)
            col2.prop(chopOptions, "cut_meshes", expand= True)
            col2.prop(chopOptions, "max_vertices", expand= True)
            col2.prop(chopOptions, "min_box_size", expand= True)
            col2.prop(chopOptions, "max_depth", expand= True)
            col2.prop(chopOptions, "merge", expand= True)
            col2.prop(chopOptions, "create_bounds", expand= True)
            col2.prop(chopOptions, "print_updated_results", expand= True)