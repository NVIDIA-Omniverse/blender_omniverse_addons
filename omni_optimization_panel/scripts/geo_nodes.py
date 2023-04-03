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
from mathutils import Vector

# the type of geometry node tree to create:
# geometry nodes is currently under development, so feature set is not yet at a stage to be fully utilized
# this puts in place a framework for more customizable and easily implementable optimizations in the future
# geometry nodes is a modifier, but unlike "DECIMATE" or "REMESH", geometry nodes can be customized with a wide array of options.
# similar to other modifiers, if there are multiple objects with the same geo node modifier, the calculations are done independently for each object.
# currently this setup can be used for generating convex hulls, creating bounding box meshes, and subdividing geometry. 
# (GeometryNodeConvexHull, GeometryNodeBoundBox, GeometryNodeSubdivisionSurface)
# as the nodes options in blender expand, A lot more can be done wit it.
# more on geometry nodes: https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/index.html#geometry-nodes

def new_GeometryNodes_group():
    # create a new empty node group that can be used in a GeometryNodes modifier
    # tree only contains a simple input/output node setup
    # the input node gives a geometry, and the output node takes a geometry.
    # nodes then have input and output SOCKET(S). 
    # this basic tree setup will accesses the output socket of the input node in order to connect it to the input socket of the output node
    # in order to make these connections, physical links between index values of inputs and outputs need to be made
    # this tree on its own will do nothing. In order to make changes to the geometry, more nodes must be inserted
    node_group = bpy.data.node_groups.new('GeometryNodes', 'GeometryNodeTree') # this is the container for the nodes
    inNode = node_group.nodes.new('NodeGroupInput') # this is the input node and gives the geometry to be modified.
    inNode.outputs.new('NodeSocketGeometry', 'Geometry') # gets reference to the output socket on the input node
    outNode = node_group.nodes.new('NodeGroupOutput') # this is the output node and returns the geometry that modified.
    outNode.inputs.new('NodeSocketGeometry', 'Geometry') # gets reference to the input socket on the output node
    node_group.links.new(inNode.outputs['Geometry'], outNode.inputs['Geometry']) # makes the link between the two nodes at the given sockets
    inNode.location = Vector((-1.5*inNode.width, 0)) # sets the position of the node in 2d space so that they are readable in the GUI
    outNode.location = Vector((1.5*outNode.width, 0))
    return node_group # now that there is a basic node tree, additional nodes can be inserted into the tree to modify the geometry

def geoTreeBasic(geo_tree, nodes, group_in, group_out, geo_type, attribute):
    # once the base geo tree has been created, we can insert additional pieces
    # this includes: convex hull, bounding box, subdivide
    new_node = nodes.new(geo_type) # create a new node of the specified type
    # insert that node between the input and output node
    geo_tree.links.new(group_in.outputs['Geometry'], new_node.inputs[0])
    geo_tree.links.new(new_node.outputs[0], group_out.inputs['Geometry'])
    if geo_type == 'GeometryNodeSubdivisionSurface': # subsurf node requires an additional input value
        geo_tree.nodes["Subdivision Surface"].inputs[1].default_value = attribute

def geoNodes(objects, geo_type, attribute):
    # TODO: When Geo Nodes develops further, hopefully all other modifier ops can be done through nodes 
    # (currently does not support decimate/remesh)
    modifier = 'NODES'

    # create empty tree - this tree is a container for nodes
    geo_tree = new_GeometryNodes_group()

    # add tree to all objects
    for obj in objects:  # for each object in selected objects, add the desired modifier and adjust its properties
        mod = obj.modifiers.new(name = modifier, type=modifier) # set name of modifier based on its type
        mod.node_group = geo_tree #bpy.data.node_groups[geo_tree.name]
    
    # alter tree - once the default tree has been created, additional nodes can be added in
    nodes = geo_tree.nodes
    group_in = nodes.get('Group Input') # keep track of the input node
    group_out = nodes.get('Group Output') # keep track of the output node
    
    geoTreeBasic(geo_tree, nodes, group_in, group_out, geo_type, attribute) # adds node to make modifications to the geometry
