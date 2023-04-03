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

# Bake helper method
def bakestolist(justcount = False):
    #Assemble properties into list
    selectedbakes = []
    selectedbakes.append("diffuse") if bpy.context.scene.selected_col else False
    selectedbakes.append("metalness") if bpy.context.scene.selected_metal else False
    selectedbakes.append("roughness") if bpy.context.scene.selected_rough else False
    selectedbakes.append("normal") if bpy.context.scene.selected_normal else False
    selectedbakes.append("transparency") if bpy.context.scene.selected_trans else False
    selectedbakes.append("transparencyroughness") if bpy.context.scene.selected_transrough else False
    selectedbakes.append("emission") if bpy.context.scene.selected_emission else False
    selectedbakes.append("specular") if bpy.context.scene.selected_specular else False
    selectedbakes.append("alpha") if bpy.context.scene.selected_alpha else False
    selectedbakes.append("sss") if bpy.context.scene.selected_sss else False
    selectedbakes.append("ssscol") if bpy.context.scene.selected_ssscol else False
    
    if justcount:
        return len(selectedbakes)
    else:
        return selectedbakes


class BakeStatus:
    total_maps = 0
    current_map = 0
    
        
