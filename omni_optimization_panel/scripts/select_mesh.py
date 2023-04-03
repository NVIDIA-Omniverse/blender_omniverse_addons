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


# for selecting only mesh objects in the scene. To be used by multiple other files.

def setSelected(context, selectedOnly = False, deselectAll = True):
        
    def select(input):
        for obj in input:
            if obj.type == 'MESH': # only mesh objects, ignore lights/cameras/curves/etc.
                selected.append(obj) # add object to array
            if deselectAll: # may want all objects deselected at end of processing
                obj.select_set(False) # make sure all objects are deselected before continuing.
            else: 
                obj.select_set(obj.type == 'MESH') # select only mesh objects
    
    selected = [] # an empty array that will be used to store the objects that need to be unwrapped 

    objects=[ob for ob in context.view_layer.objects if ob.visible_get()] # only want to look at visible objects. process will fail otherwise
    if not selectedOnly: # selectedOnly is for GUI version only
        select(objects)
    elif len(context.selected_objects): # run only if there are selected objects in the scene to isolate just the selected meshes
        select(context.selected_objects)

    return selected