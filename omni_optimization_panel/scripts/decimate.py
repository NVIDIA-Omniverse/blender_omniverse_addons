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


# Decimation reduces geometry while maintaining form and UVs
# There are three different decimation methods. Each method produces different results, with its own pros/cons)
# https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/decimate.html#decimate-modifier

def decimate(objects, decimate_type, prop):

    modifier = 'DECIMATE' # sets type of modifier to be used
    
    for obj in objects: # for each object in selected objects, add the desired modifier and adjust its properties
        if len(obj.data.polygons) > 3: # decimation cannot be performed on meshes with 3 or less faces
            mod = obj.modifiers.new(name = modifier, type=modifier) # set name of modifier based on its type
            mod.decimate_type = decimate_type # sets decimation type
            if decimate_type == 'COLLAPSE': # "Merges vertices together progressively, taking the shape of the mesh into account.""
                mod.ratio = prop # the ratio value used for collapse decimation. Is a ratio of total faces. (x/1)
            elif decimate_type == 'UNSUBDIV': # "It is intended for meshes with a mainly grid-based topology (without giving uneven geometry)"
                mod.iterations = prop # the number of un-subdivisions performed. The higher the number, the less geometry remaining (1/2^x)
            elif decimate_type == 'DISSOLVE': # "It reduces details on forms comprised of mainly flat surfaces."
                mod.angle_limit = prop # the reduction is limited to an angle between faces (x degrees)
                mod.delimit = {'UV'}
            else:
                raise TypeError('Invalid Decimate Type')

    return
