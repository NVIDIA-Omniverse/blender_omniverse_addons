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
from . import functions
from .data import MasterOperation


def find_node_from_label(label, nodes):
    for node in nodes:
        if node.label == label:
            return node
    
    return False
    
def find_isocket_from_identifier(idname, node):
    for inputsocket in node.inputs:
        if inputsocket.identifier == idname:
            return inputsocket
    
    return False

def find_osocket_from_identifier(idname, node):
    for outputsocket in node.outputs:
        if outputsocket.identifier == idname:
            return outputsocket
    
    return False

def make_link(f_node_label, f_node_ident, to_node_label, to_node_ident, nodetree):
     
    fromnode = find_node_from_label(f_node_label, nodetree.nodes)
    if(fromnode == False):
        return False
    fromsocket = find_osocket_from_identifier(f_node_ident, fromnode)
    tonode = find_node_from_label(to_node_label, nodetree.nodes)
    if(tonode == False):
        return False
    tosocket = find_isocket_from_identifier(to_node_ident, tonode)
    
    nodetree.links.new(fromsocket, tosocket) 
    return True

def wipe_labels(nodes):
    for node in nodes:
        node.label = ""
    
def get_image_from_tag(thisbake, objname):
    
    current_bake_op = MasterOperation.current_bake_operation
    global_mode = current_bake_op.bake_mode
    
    objname = functions.untrunc_if_needed(objname)
    
    batch_name = bpy.context.scene.batchName
    
    result = []
    result = [img for img in bpy.data.images if\
    ("SB_objname" in img and img["SB_objname"] == objname) and\
    ("SB_batch" in img and img["SB_batch"] == batch_name) and\
    ("SB_globalmode" in img and img["SB_globalmode"] == global_mode) and\
    ("SB_thisbake" in img and img["SB_thisbake"] == thisbake)\
    ]

        
    if len(result) > 0:
        return result[0]


    functions.printmsg(f"ERROR: No image with matching tag ({thisbake}) found for object {objname}")
    return False

def create_principled_setup(nodetree, obj):

    functions.printmsg("Creating principled material")

    nodes = nodetree.nodes

    obj_name = obj.name.replace("_OmniBake", "")

    obj.active_material.cycles.displacement_method = 'BOTH'

    #First we wipe out any existing nodes
    for node in nodes:
        nodes.remove(node)

    # Node Frame
    node = nodes.new("NodeFrame")
    node.location = (0,0)
    node.use_custom_color = True
    node.color = (0.149763, 0.214035, 0.0590617)

    #Now create the Principled BSDF
    pnode = nodes.new("ShaderNodeBsdfPrincipled")
    pnode.location = (-25, 335)
    pnode.label = "pnode"
    pnode.use_custom_color = True
    pnode.color = (0.3375297784805298, 0.4575316309928894, 0.08615386486053467)
    pnode.parent = nodes["Frame"]

    #And the output node
    node = nodes.new("ShaderNodeOutputMaterial")
    node.location = (500, 200)
    node.label = "monode"
    node.show_options = False
    node.parent = nodes["Frame"]

    #-----------------------------------------------------------------

    #Node Image texture types Types
    if(bpy.context.scene.selected_col):
        image = get_image_from_tag("diffuse", obj_name)
        node = nodes.new("ShaderNodeTexImage")
        node.hide = True
        node.location = (-500, 250)
        node.label = "col_tex"
        node.image = image
        node.parent = nodes["Frame"]
    
    if(bpy.context.scene.selected_sss):
        node = nodes.new("ShaderNodeTexImage")
        node.hide = True
        node.location = (-500, 210)
        node.label = "sss_tex"
        image = get_image_from_tag("sss", obj_name)
        node.image = image
        node.parent = nodes["Frame"]

    if(bpy.context.scene.selected_ssscol):
        node = nodes.new("ShaderNodeTexImage")
        node.hide = True
        node.location = (-500, 170)
        node.label = "ssscol_tex"
        image = get_image_from_tag("ssscol", obj_name)
        node.image = image
        node.parent = nodes["Frame"]
    
    if(bpy.context.scene.selected_metal):
        node = nodes.new("ShaderNodeTexImage")
        node.hide = True
        node.location = (-500, 130)
        node.label = "metal_tex"
        image = get_image_from_tag("metalness", obj_name)
        node.image = image
        node.parent = nodes["Frame"]
    
    if(bpy.context.scene.selected_specular):
        node = nodes.new("ShaderNodeTexImage")
        node.hide = True
        node.location = (-500, 90)
        node.label = "specular_tex"
        image = get_image_from_tag("specular", obj_name)
        node.image = image
        node.parent = nodes["Frame"]
    
    if(bpy.context.scene.selected_rough):
        node = nodes.new("ShaderNodeTexImage")
        node.hide = True
        node.location = (-500, 50)
        node.label = "roughness_tex"
        image = get_image_from_tag("roughness", obj_name)
        node.image = image
        node.parent = nodes["Frame"]

    if(bpy.context.scene.selected_trans):
        node = nodes.new("ShaderNodeTexImage")
        node.hide = True
        node.location = (-500, -90)
        node.label = "transmission_tex"
        image = get_image_from_tag("transparency", obj_name)
        node.image = image
        node.parent = nodes["Frame"]
    
    if(bpy.context.scene.selected_transrough):
        node = nodes.new("ShaderNodeTexImage")
        node.hide = True
        node.location = (-500, -130)
        node.label = "transmissionrough_tex"
        image = get_image_from_tag("transparencyroughness", obj_name)
        node.image = image
        node.parent = nodes["Frame"]

    if(bpy.context.scene.selected_emission):
        node = nodes.new("ShaderNodeTexImage")
        node.hide = True
        node.location = (-500, -170)
        node.label = "emission_tex"
        image = get_image_from_tag("emission", obj_name)
        node.image = image
        node.parent = nodes["Frame"]
    
    if(bpy.context.scene.selected_alpha):
        node = nodes.new("ShaderNodeTexImage")
        node.hide = True
        node.location = (-500, -210)
        node.label = "alpha_tex"
        image = get_image_from_tag("alpha", obj_name)
        node.image = image
        node.parent = nodes["Frame"]
   
    if(bpy.context.scene.selected_normal):
        node = nodes.new("ShaderNodeTexImage")
        node.hide = True
        node.location = (-500, -318.7)
        node.label = "normal_tex"
        image = get_image_from_tag("normal", obj_name)
        node.image = image
        node.parent = nodes["Frame"]

    #-----------------------------------------------------------------

    # Additional normal map node for normal socket
    if(bpy.context.scene.selected_normal):
        node = nodes.new("ShaderNodeNormalMap")
        node.location = (-220, -240)
        node.label = "normalmap"
        node.show_options = False
        node.parent = nodes["Frame"]

    #-----------------------------------------------------------------

    make_link("emission_tex", "Color", "pnode", "Emission", nodetree)
    make_link("col_tex", "Color", "pnode", "Base Color", nodetree)
    make_link("metal_tex", "Color", "pnode", "Metallic", nodetree)
    make_link("roughness_tex", "Color", "pnode", "Roughness", nodetree)
    make_link("transmission_tex", "Color", "pnode", "Transmission", nodetree)
    make_link("transmissionrough_tex", "Color", "pnode", "Transmission Roughness", nodetree)
    make_link("normal_tex", "Color", "normalmap", "Color", nodetree)
    make_link("normalmap", "Normal", "pnode", "Normal", nodetree)
    make_link("specular_tex", "Color", "pnode", "Specular", nodetree)
    make_link("alpha_tex", "Color", "pnode", "Alpha", nodetree)
    make_link("sss_tex", "Color", "pnode", "Subsurface", nodetree)
    make_link("ssscol_tex", "Color", "pnode", "Subsurface Color", nodetree)

    make_link("pnode", "BSDF", "monode", "Surface", nodetree)

    #---------------------------------------------------
    
    wipe_labels(nodes)

    node = nodes["Frame"]
    node.label = "OMNI PBR"