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


import bpy, bmesh
from mathutils import Vector
import collections

def boundsObj(points): # for displaying the bounds of each split chunk
    mesh = bpy.data.meshes.new("mesh")  # add a new mesh
    obj = bpy.data.objects.new("MyObject", mesh)  # add a new object using the new mesh

    # link the new bounds object to the newly created collection in split. 
    # this is the last collection added to the scene, hence index of len -1
    bpy.context.scene.collection.children[len( bpy.context.scene.collection.children)-1].objects.link(obj)

    obj.display_type = 'BOUNDS' # display only the objects bounds in the Blender viewport.
    bm = bmesh.new() # 'bmesh' in Blender is data type that contains the 'edit mesh' for an object
    # allows control over vertices, edges, and faces

    for point in points: # iterate over input bounds(points)
        bm.verts.new(point) # add a new vert

    # make the bmesh the object's mesh
    bm.to_mesh(obj.data) # transfer bmesh data to the new obj
    bm.free()  # always do this when finished with a bmesh

    return obj
    
def boundingBox(objects): # the bounding box used for calculating the split plane
    if not isinstance(objects, list): # if objects is not a list convert it to one
        objects = [objects]

    points_co_global = [] # list of all vertices of all objects from list with global coordinates
    for obj in objects: # iterate over objects list and add its vertices to list
        points_co_global.extend([obj.matrix_world @ Vector(v) for v in obj.bound_box]) # must add points in world space

    return points_co_global

def bounds(coords): # returns a dictionary containing details of split bounds
    zipped = zip(*coords) # The zip() function returns a zip object, which is an iterator of tuples
    push_axis = [] # list that will contain useful for each axis
    for (axis, _list) in zip('xyz', zipped): # for x, y, and z axis calculate set of values and add them to list
        info = lambda: None
        info.max = max(_list) # the maximum value of bounds for each axis
        info.min = min(_list) # the minimum value of bounds for each axis
        info.distance = info.max - info.min # the length of the bounds for each axis
        info.mid = (info.max + info.min)/2 # the center point of bounds for each axis
        push_axis.append(info) # add this info to push_axis

    originals = dict(zip(['x', 'y', 'z'], push_axis)) # create dictionary wit the values from push_axis
    o_details = collections.namedtuple('object_details', ['x', 'y', 'z']) # organize dictionary to be accessed easier

    return o_details(**originals)
