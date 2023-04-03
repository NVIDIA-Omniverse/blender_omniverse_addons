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


from bpy.ops import _BPyOpsSubModOp

view_layer_update = _BPyOpsSubModOp._view_layer_update

def open_update(): 
    # blender operator calls update the scene each time after running
    # updating the scene can take a long time, esp for large scenes. So we want to delay update until we are finished
    # there is not an official way to suppress this update, so we need to use a workaround

    def dummy_view_layer_update(context): # tricks blender into thinking the scene has been updated and instead passes
        pass
    
    _BPyOpsSubModOp._view_layer_update = dummy_view_layer_update
            
def close_update(): # in the end, still need to update scene, so this manually calls update
    _BPyOpsSubModOp._view_layer_update = view_layer_update