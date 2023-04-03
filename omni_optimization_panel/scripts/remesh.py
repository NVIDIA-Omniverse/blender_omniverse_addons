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


# Remeshing reconstructs a mesh to produce clean/uniform geometry, but removes all UV mappings from an object
# There are four different remesh methods. (BLOCKS, SMOOTH, SHARP, VOXEL)
# https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/remesh.html#remesh-modifier

def remesh(objects, remesh_type, prop):

    modifier = 'REMESH' # sets type of modifier to be used
    
    for obj in objects: # for each object in selected objects, add the desired modifier and adjust its properties
        mod = obj.modifiers.new(name = modifier, type=modifier) # set name of modifier based on its type
        mod.mode = remesh_type # sets remesh type (BLOCKS, SMOOTH, SHARP, VOXEL)
        # first three modes produce almost identical typology, but with differing amounts of smoothing (BLOCKS, SMOOTH, SHARP)
        if remesh_type == 'BLOCKS': # "There is no smoothing at all."
            mod.octree_depth = prop # controls the resolution of most of the remesh modifiers.
            # the higher the number, the more geometry created (2^x)
        elif remesh_type == 'SMOOTH': # "Output a smooth surface."
            mod.octree_depth = prop # the higher the number, the more geometry created (2^x)
        elif remesh_type == 'SHARP': # "Similar to Smooth, but preserves sharp edges and corners."
            mod.octree_depth = prop # the higher the number, the more geometry created (2^x)
        elif remesh_type == 'VOXEL': # "Uses an OpenVDB to generate a new manifold mesh from the current geometry 
            # while trying to preserve the mesh’s original volume."
            mod.voxel_size = prop # used for voxel remesh to control resolution. the lower the number, the more geometry created (x)
        else:
            raise TypeError('Invalid Remesh Type')

    return
