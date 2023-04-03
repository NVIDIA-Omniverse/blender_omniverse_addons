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

from pathlib import Path
from ..ui import OmniBakePreferences
import bpy
from bpy.types import *
import os
import sys
import tempfile
from . import material_setup
from .data import MasterOperation

#Global variables
psocketname = {
    "diffuse": "Base Color",
    "metalness": "Metallic",
    "roughness": "Roughness",
    "normal": "Normal",
    "transparency": "Transmission",
    "transparencyroughness": "Transmission Roughness",
    "specular": "Specular",
    "alpha": "Alpha",
    "sss": "Subsurface",
    "ssscol": "Subsurface Color",
    "displacement": "Displacement"
    }

def printmsg(msg):
    print(f"BAKE: {msg}")                 

def gen_image_name(obj_name, baketype):
    
    current_bake_op = MasterOperation.current_bake_operation
    
    #First, let's get the format string we are working with
    prefs = bpy.context.preferences.addons[OmniBakePreferences.bl_idname].preferences
    image_name = prefs.img_name_format
    
    #The easy ones
    image_name = image_name.replace("%OBJ%", obj_name)
    image_name = image_name.replace("%BATCH%", bpy.context.scene.batchName)
    
    #Bake mode
    image_name = image_name.replace("%BAKEMODE%", current_bake_op.bake_mode)    
    
    #The hard ones
    if baketype == "diffuse":
        image_name = image_name.replace("%BAKETYPE%", prefs.diffuse_alias)
    elif baketype == "metalness":
        image_name = image_name.replace("%BAKETYPE%", prefs.metal_alias)
    elif baketype == "roughness":
        image_name = image_name.replace("%BAKETYPE%", prefs.roughness_alias)
    elif baketype == "normal":
        image_name = image_name.replace("%BAKETYPE%", prefs.normal_alias)
    elif baketype == "transparency":
        image_name = image_name.replace("%BAKETYPE%", prefs.transmission_alias)
    elif baketype == "transparencyroughness":
        image_name = image_name.replace("%BAKETYPE%", prefs.transmissionrough_alias)
    elif baketype == "emission":
        image_name = image_name.replace("%BAKETYPE%", prefs.emission_alias)
    elif baketype == "specular":
        image_name = image_name.replace("%BAKETYPE%", prefs.specular_alias)
    elif baketype == "alpha":
        image_name = image_name.replace("%BAKETYPE%", prefs.alpha_alias)
    elif baketype == "sss":
        image_name = image_name.replace("%BAKETYPE%", prefs.sss_alias)
    elif baketype == "ssscol":
        image_name = image_name.replace("%BAKETYPE%", prefs.ssscol_alias)
    #Displacement is not currently Implemented
    elif baketype == "displacement":
        image_name = image_name.replace("%BAKETYPE%", prefs.displacement_alias)
    else:
        image_name = image_name.replace("%BAKETYPE%", baketype)
    
    return image_name

def removeDisconnectedNodes(nodetree):
    nodes = nodetree.nodes
    
    #Loop through nodes
    repeat = False
    for node in nodes: 
        if node.type == "BSDF_PRINCIPLED" and len(node.outputs[0].links) == 0:
            #Not a player, delete node
            nodes.remove(node)
            repeat = True
        elif node.type == "EMISSION" and len(node.outputs[0].links) == 0:
            #Not a player, delete node
            nodes.remove(node)
            repeat = True
        elif node.type == "MIX_SHADER" and len(node.outputs[0].links) == 0:
            #Not a player, delete node
            nodes.remove(node)
            repeat = True
        elif node.type == "ADD_SHADER" and len(node.outputs[0].links) == 0:
            #Not a player, delete node
            nodes.remove(node)
            repeat = True
        #Displacement is not currently Implemented
        elif node.type == "DISPLACEMENT" and len(node.outputs[0].links) == 0:
            #Not a player, delete node
            nodes.remove(node)
            repeat = True
    
    #If we removed any nodes, we need to do this again
    if repeat:
        removeDisconnectedNodes(nodetree)
            
def backupMaterial(mat):
    dup = mat.copy()
    dup.name = mat.name + "_OmniBake"

def restoreAllMaterials():
    #Not efficient but, if we are going to do things this way, we need to loop over every object in the scene 
    dellist = []
    for obj in bpy.data.objects:
        for slot in obj.material_slots:
            origname = slot.name
            #Try to set to the corresponding material that was the backup
            try:
                slot.material = bpy.data.materials[origname + "_OmniBake"]
                
                #If not already on our list, log the original material (that we messed with) for mass deletion
                if origname not in dellist:
                    dellist.append(origname)
                
            except KeyError:
                #Not been backed up yet. Must not have processed an object with that material yet
                pass
                
    #Delete the unused materials
    for matname in dellist:
        bpy.data.materials.remove(bpy.data.materials[matname])
    
    #Rename all materials to the original name, leaving us where we started
    for mat in bpy.data.materials:
        if "_OmniBake" in mat.name:
            mat.name = mat.name.replace("_OmniBake", "")

def create_Images(imgname, thisbake, objname):
    #thisbake is subtype e.g. diffuse, ao, etc.
    
    current_bake_op = MasterOperation.current_bake_operation
    global_mode = current_bake_op.bake_mode
    batch = MasterOperation.batch_name
    
    printmsg(f"Creating image {imgname}")
    
    #Get the image height and width from the interface
    IMGHEIGHT = bpy.context.scene.imgheight
    IMGWIDTH = bpy.context.scene.imgwidth
    
    #If it already exists, remove it.
    if(imgname in bpy.data.images):
        bpy.data.images.remove(bpy.data.images[imgname])
    
    #Create image 32 bit or not 32 bit
    if thisbake == "normal" :
        image = bpy.data.images.new(imgname, IMGWIDTH, IMGHEIGHT, float_buffer=True)
    else:
        image = bpy.data.images.new(imgname, IMGWIDTH, IMGHEIGHT, float_buffer=False)
    
    #Set tags
    image["SB_objname"] = objname
    image["SB_batch"] = batch
    image["SB_globalmode"] = global_mode
    image["SB_thisbake"] = thisbake
    
    #Always mark new images fake user when generated in the background
    if "--background" in sys.argv:
        image.use_fake_user = True
    
    #Store it at bake operation level
    MasterOperation.baked_textures.append(image)

def deselectAllNodes(nodes):
    for node in nodes:
        node.select = False
    
def findSocketConnectedtoP(pnode, thisbake):
    #Get socket name for this bake mode
    socketname = psocketname[thisbake]
    
    #Get socket of the pnode
    socket = pnode.inputs[socketname]
    fromsocket = socket.links[0].from_socket
    
    #Return the socket connected to the pnode
    return fromsocket

def get_input_socket_name(node, thisbake) -> str:
    pass


def createdummynodes(nodetree, thisbake):
    #Loop through pnodes
    nodes = nodetree.nodes
    
    for node in nodes:
        if node.type in {"BSDF_PRINCIPLED"}:
            pnode = node
            #Get socket name for this bake mode
            socketname = psocketname[thisbake]
    
            #Get socket of the pnode
            psocket = pnode.inputs[socketname]
    
            #If it has something plugged in, we can leave it here
            if(len(psocket.links) > 0):
                continue

            #Get value of the unconnected socket
            val = psocket.default_value
    
            #If this is base col or ssscol, add an RGB node and set it's value to that of the socket
            if(socketname == "Base Color" or socketname == "Subsurface Color"):
                rgb = nodetree.nodes.new("ShaderNodeRGB")
                rgb.outputs[0].default_value = val
                rgb.label = "OmniBake"
                nodetree.links.new(rgb.outputs[0], psocket)

            #If this is anything else, use a value node
            else:
                vnode = nodetree.nodes.new("ShaderNodeValue")
                vnode.outputs[0].default_value = val
                vnode.label = "OmniBake"
                nodetree.links.new(vnode.outputs[0], psocket)

def bakeoperation(thisbake, img):
    
    printmsg(f"Beginning bake for {thisbake}")
    
    if(thisbake != "normal"):
        bpy.ops.object.bake(type="EMIT", save_mode="INTERNAL", use_clear=True)
    else:
        bpy.ops.object.bake(type="NORMAL", save_mode="INTERNAL", use_clear=True)
        
    #Always pack the image for now
    img.pack()

def startingChecks(objects, bakemode):

    messages = []
    
    if len(objects) == 0:
        messages.append("ERROR: Nothing selected for bake")
        
    #Are any of our objects hidden?
    for obj in objects:
        if (obj.hide_viewport == True) or (obj.hide_get(view_layer=bpy.context.view_layer) == True):
            messages.append(f"ERROR: Object '{obj.name}' is hidden in viewport (eye icon in outliner) or in the current view lawyer (computer screen icon in outliner)")
        
    #What about hidden from rendering?
    for obj in objects:
        if obj.hide_render:
            messages.append(f"ERROR: Object '{obj.name}' is hidden for rendering (camera icon in outliner)")
    
    #None of the objects can have zero faces
    for obj in objects:
        if len(obj.data.polygons) < 1:
            messages.append(f"ERROR: Object '{obj.name}' has no faces")
    
    if(bpy.context.mode != "OBJECT"): ##!TODO(kiki): switch back
        messages.append("ERROR: Not in object mode")
      
    #PBR Bake Checks
    for obj in objects:
        
        #Is it mesh?
        if obj.type != "MESH":
            messages.append(f"ERROR: Object {obj.name} is not mesh")
            #Must continue here - other checks will throw exceptions
            continue
        
        #Are UVs OK?
        if bpy.context.scene.newUVoption == False and len(obj.data.uv_layers) == 0:
            messages.append(f"ERROR: Object {obj.name} has no UVs, and you aren't generating new ones")
            continue
    
        #Are materials OK? Fix if not
        if not checkObjectValidMaterialConfig(obj):
            fix_invalid_material_config(obj)
            
        #Do all materials have valid PBR config?
        if bpy.context.scene.more_shaders == False:
            for slot in obj.material_slots:
                mat = slot.material
                result = checkMatsValidforPBR(mat)
                if len(result) > 0:
                    for node_name in result:
                        messages.append(f"ERROR: Node '{node_name}' in material '{mat.name}' on object '{obj.name}' is not valid for PBR bake. In order to use more than just Princpled, Emission, and Mix Shaders, turn on 'Use additional Shader Types'!")
        else:
            for slot in obj.material_slots:
                mat = slot.material
                result = checkExtraMatsValidforPBR(mat)
                if len(result) > 0:
                    for node_name in result:
                        messages.append(f"ERROR: Node '{node_name}' in material '{mat.name}' on object '{obj.name}' is not supported")

    #Let's report back
    if len(messages) != 0:
        ShowMessageBox(messages, "Errors occured", "ERROR")
        return False
    else:
        #If we get here then everything looks good
        return True
    
    #------------------------------------------
    
def processUVS():

    current_bake_op = MasterOperation.current_bake_operation
 
    #------------------NEW UVS ------------------------------------------------------------
    
    if bpy.context.scene.newUVoption:
        printmsg("We are generating new UVs")
        printmsg("We are unwrapping each object individually with Smart UV Project")

        objs = current_bake_op.bake_objects
        
        for obj in objs:
            if("OmniBake" in obj.data.uv_layers):
                obj.data.uv_layers.remove(obj.data.uv_layers["OmniBake"])
            obj.data.uv_layers.new(name="OmniBake")
            obj.data.uv_layers["OmniBake"].active = True
            #Will set active object
            selectOnlyThis(obj)
            
            #Blender 2.91 kindly breaks Smart UV Project in object mode so... yeah... thanks
            bpy.ops.object.mode_set(mode="EDIT", toggle=False)
            #Unhide any geo that's hidden in edit mode or it'll cause issues.
            bpy.ops.mesh.reveal()
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.reveal()

            bpy.ops.uv.smart_project(island_margin=bpy.context.scene.unwrapmargin)
            
            bpy.ops.object.mode_set(mode="OBJECT", toggle=False)
                    
     #------------------END NEW UVS ------------------------------------------------------------
    
    else: #i.e. New UV Option was not selected
        printmsg("We are working with the existing UVs")
        
        if bpy.context.scene.prefer_existing_sbmap:
            printmsg("We are preferring existing UV maps called OmniBake. Setting them to active")
            for obj in current_bake_op.bake_objects:
                if("OmniBake" in obj.data.uv_layers):
                    obj.data.uv_layers["OmniBake"].active = True
         
    #Before we finish, restore the original selected and active objects
    bpy.ops.object.select_all(action="DESELECT")
    for obj in current_bake_op.orig_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = current_bake_op.orig_active_object
    
    #Done
    return True

def restore_Original_UVs():
    
    current_bake_op = MasterOperation.current_bake_operation
    
    #First the bake objects
    for obj in current_bake_op.bake_objects:
        if MasterOperation.orig_UVs_dict[obj. name] != None:
            original_uv = MasterOperation.orig_UVs_dict[obj.name]
            obj.data.uv_layers.active = obj.data.uv_layers[original_uv]
    
def setupEmissionRunThrough(nodetree, m_output_node, thisbake, ismix=False):
    
    nodes = nodetree.nodes
    pnode = find_pnode(nodetree)
    
    #Create emission shader
    emissnode = nodes.new("ShaderNodeEmission")
    emissnode.label = "OmniBake"
    
    #Connect to output
    if(ismix):
        #Find the existing mix node before we create a new one
        existing_m_node = find_mnode(nodetree)
        
        #Add a mix shader node and label it
        mnode = nodes.new("ShaderNodeMixShader")
        mnode.label = "OmniBake"
        
        #Connect new mix node to the output
        fromsocket = mnode.outputs[0]
        tosocket = m_output_node.inputs[0]
        nodetree.links.new(fromsocket, tosocket)

        #Connect new emission node to the first mix slot (leaving second empty)
        fromsocket = emissnode.outputs[0]
        tosocket = mnode.inputs[1]
        nodetree.links.new(fromsocket, tosocket)
        
        #If there is one, plug the factor from the original mix node into our new mix node
        if(len(existing_m_node.inputs[0].links) > 0):
            fromsocket = existing_m_node.inputs[0].links[0].from_socket
            tosocket = mnode.inputs[0]
            nodetree.links.new(fromsocket, tosocket)
        #If no input, add a value node set to same as the mnode factor
        else:
            val = existing_m_node.inputs[0].default_value
            vnode = nodes.new("ShaderNodeValue")
            vnode.label = "OmniBake"
            vnode.outputs[0].default_value = val
            
            fromsocket = vnode.outputs[0]
            tosocket = mnode.inputs[0]
            nodetree.links.new(fromsocket, tosocket)

    else:
        #Just connect our new emission to the output
        fromsocket = emissnode.outputs[0]
        tosocket = m_output_node.inputs[0]
        nodetree.links.new(fromsocket, tosocket)
            
    #Create dummy nodes for the socket for this bake if needed
    createdummynodes(nodetree, pnode, thisbake)
            
    #Connect whatever is in Principled Shader for this bakemode to the emission
    fromsocket = findSocketConnectedtoP(pnode, thisbake)
    tosocket = emissnode.inputs[0]
    nodetree.links.new(fromsocket, tosocket)        

#---------------------Node Finders---------------------------

def find_pnode(nodetree):
    nodes = nodetree.nodes
    for node in nodes:
        if(node.type == "BSDF_PRINCIPLED"):
            return node
    #We never found it
    return False

def find_enode(nodetree):
    nodes = nodetree.nodes
    for node in nodes:
        if(node.type == "EMISSION"):
            return node
    #We never found it
    return False

def find_mnode(nodetree):
    nodes = nodetree.nodes
    for node in nodes:
        if(node.type == "MIX_SHADER"):
            return node
    #We never found it
    return False

def find_onode(nodetree):
    nodes = nodetree.nodes
    for node in nodes:
        if(node.type == "OUTPUT_MATERIAL"):
            return node
    #We never found it
    return False

def checkObjectValidMaterialConfig(obj):
    #Firstly, check it actually has material slots
    if len(obj.material_slots) == 0:
        return False
    
    #Check the material slots all have a material assigned
    for slot in obj.material_slots:
        if slot.material == None:
            return False
    
    #All materials must be using nodes
    for slot in obj.material_slots:
        if slot.material.use_nodes == False:
            return False
    #If we get here, everything looks good
    return True           
    
def getMatType(nodetree):
    if (find_pnode(nodetree) and find_mnode(nodetree)):
        return "MIX"
    elif(find_pnode(nodetree)):
        return "PURE_P"
    elif(find_enode(nodetree)):
        return "PURE_E"
    else:
        return "INVALID"

def prepObjects(objs, baketype):
    
    current_bake_op = MasterOperation.current_bake_operation
    
    printmsg("Creating prepared object")
    #First we prepare objectes
    export_objects = []
    for obj in objs:
       #-------------Create the prepared mesh----------------------------------------
        
        #Object might have a truncated name. Should use this if it's there
        objname = trunc_if_needed(obj.name)
        
        new_obj = obj.copy()
        new_obj.data = obj.data.copy()
        new_obj["SB_createdfrom"] = obj.name
        
        #clear all materials
        new_obj.data.materials.clear()
        new_obj.name = objname + "_OmniBake"
        
        #Create a collection for our baked objects if it doesn't exist
        if "OmniBake_Bakes" not in bpy.data.collections:
            c = bpy.data.collections.new("OmniBake_Bakes")
            bpy.context.scene.collection.children.link(c)

        #Make sure it's visible and enabled for current view laywer or it screws things up
        bpy.context.view_layer.layer_collection.children["OmniBake_Bakes"].exclude = False
        bpy.context.view_layer.layer_collection.children["OmniBake_Bakes"].hide_viewport = False
        c = bpy.data.collections["OmniBake_Bakes"]
        
        
        #Link object to our new collection
        c.objects.link(new_obj)
        
        #Append this object to the export list
        export_objects.append(new_obj)  
        
        
        
        #---------------------------------UVS--------------------------------------
        
        uvlayers = new_obj.data.uv_layers
        #If we generated new UVs, it will be called "OmniBake" and we are using that. End of.
        #Same if we are being called for Sketchfab upload, and last bake used new UVs
        if bpy.context.scene.newUVoption:
            pass
        
        #If there is an existing map called OmniBake, and we are preferring it, use that
        elif ("OmniBake" in uvlayers) and bpy.context.scene.prefer_existing_sbmap:
            pass
            
        #Even if we are not preferring it, if there is just one map called OmniBake, we are using that
        elif ("OmniBake" in uvlayers) and len(uvlayers) <2:
            pass
            
        #If there is an existing map called OmniBake, and we are not preferring it, it has to go
        #Active map becommes OmniBake
        elif ("OmniBake" in uvlayers) and not bpy.context.scene.prefer_existing_sbmap:
            uvlayers.remove(uvlayers["OmniBake"])
            active_layer = uvlayers.active
            active_layer.name = "OmniBake"
            
        #Finally, if none of the above apply, we are just using the active map
        #Active map becommes OmniBake
        else:
            active_layer = uvlayers.active
            active_layer.name = "OmniBake"
            
        #In all cases, we can now delete everything other than OmniBake
        deletelist = []
        for uvlayer in uvlayers:
            if (uvlayer.name != "OmniBake"):
                deletelist.append(uvlayer.name)
        for uvname in deletelist:
            uvlayers.remove(uvlayers[uvname])
        
    #---------------------------------END UVS--------------------------------------

        #Create a new material
        #call it same as object + batchname + baked
        mat = bpy.data.materials.get(objname + "_" + bpy.context.scene.batchName + "_baked")
        if mat is None:
            mat = bpy.data.materials.new(name=objname + "_" + bpy.context.scene.batchName +"_baked")
        
        # Assign it to object
        mat.use_nodes = True
        new_obj.data.materials.append(mat)
        
    #Set up the materials for each object
    for obj in export_objects:
            
        #Should only have one material
        mat = obj.material_slots[0].material
        nodetree = mat.node_tree
        
        material_setup.create_principled_setup(nodetree, obj)

        #Change object name to avoid collisions
        obj.name = obj.name.replace("_OmniBake", "_Baked")    
             
    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_objects:
        obj.select_set(state=True)
    
    if (not bpy.context.scene.prepmesh) and (not "--background" in sys.argv):
        #Deleted duplicated objects
        for obj in export_objects:
            bpy.data.objects.remove(obj)
    #Add the created objects to the bake operation list to keep track of them
    else:
        for obj in export_objects:
            MasterOperation.prepared_mesh_objects.append(obj)

def selectOnlyThis(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(state=True)
    bpy.context.view_layer.objects.active = obj
    
def setup_pure_p_material(nodetree, thisbake):
    #Create dummy nodes as needed
    createdummynodes(nodetree, thisbake)
    
    #Create emission shader
    nodes = nodetree.nodes
    m_output_node = find_onode(nodetree)
    loc = m_output_node.location
    
    #Create an emission shader
    emissnode = nodes.new("ShaderNodeEmission")
    emissnode.label = "OmniBake"
    emissnode.location = loc
    emissnode.location.y = emissnode.location.y + 200
    
    #Connect our new emission to the output
    fromsocket = emissnode.outputs[0]
    tosocket = m_output_node.inputs[0]
    nodetree.links.new(fromsocket, tosocket)
            
    #Connect whatever is in Principled Shader for this bakemode to the emission
    fromsocket = findSocketConnectedtoP(find_pnode(nodetree), thisbake)
    tosocket = emissnode.inputs[0]
    nodetree.links.new(fromsocket, tosocket) 

def setup_pure_e_material(nodetree, thisbake):
    #If baking something other than emission, mute the emission modes so they don't contaiminate our bake
    if thisbake != "Emission":
        nodes = nodetree.nodes
        for node in nodes:
            if node.type == "EMISSION":
                node.mute = True
                node.label = "OmniBakeMuted"

def setup_mix_material(nodetree, thisbake):
    #No need to mute emission nodes. They are automuted by setting the RGBMix to black
    nodes = nodetree.nodes
    
    #Create dummy nodes as needed
    createdummynodes(nodetree, thisbake)
    
    #For every mix shader, create a mixrgb above it
    #Also connect the factor input to the same thing
    created_mix_nodes = {}
    for node in nodes:
        if node.type == "MIX_SHADER":
            loc = node.location
            rgbmix = nodetree.nodes.new("ShaderNodeMixRGB")
            rgbmix.label = "OmniBake"
            rgbmix.location = loc
            rgbmix.location.y = rgbmix.location.y + 200
                        
            
            #If there is one, plug the factor from the original mix node into our new mix node
            if(len(node.inputs[0].links) > 0):
                fromsocket = node.inputs[0].links[0].from_socket
                tosocket = rgbmix.inputs["Fac"]
                nodetree.links.new(fromsocket, tosocket)
            #If no input, add a value node set to same as the mnode factor
            else:
                val = node.inputs[0].default_value
                vnode = nodes.new("ShaderNodeValue")
                vnode.label = "OmniBake"
                vnode.outputs[0].default_value = val
            
                fromsocket = vnode.outputs[0]
                tosocket = rgbmix.inputs[0]
                nodetree.links.new(fromsocket, tosocket)
                
            #Keep a dictionary with paired shader mix node
            created_mix_nodes[node.name] = rgbmix.name
                
    #Loop over the RGBMix nodes that we created
    for node in created_mix_nodes:
        mshader = nodes[node]
        rgb = nodes[created_mix_nodes[node]]
               
        #Mshader - Socket 1
        #First, check if there is anything plugged in at all
        if len(mshader.inputs[1].links) > 0:
            fromnode = mshader.inputs[1].links[0].from_node
            
            if fromnode.type == "BSDF_PRINCIPLED":
                #Get the socket we are looking for, and plug it into RGB socket 1
                fromsocket = findSocketConnectedtoP(fromnode, thisbake)
                nodetree.links.new(fromsocket, rgb.inputs[1])
            elif fromnode.type == "MIX_SHADER":
                #If it's a mix shader on the other end, connect the equivilent RGB node
                #Get the RGB node for that mshader
                fromrgb = nodes[created_mix_nodes[fromnode.name]]
                fromsocket = fromrgb.outputs[0]
                nodetree.links.new(fromsocket, rgb.inputs[1])
            elif fromnode.type == "EMISSION":
                #Set this input to black
                rgb.inputs[1].default_value = (0.0, 0.0, 0.0, 1)
            elif fromnode.type == "GROUP":
                pass
            else:
                printmsg("Error, invalid node config")
        else:
            rgb.inputs[1].default_value = (0.0, 0.0, 0.0, 1)
                    
        #Mshader - Socket 2
        if len(mshader.inputs[2].links) > 0:
            fromnode = mshader.inputs[2].links[0].from_node
            if fromnode.type == "BSDF_PRINCIPLED":
                #Get the socket we are looking for, and plug it into RGB socket 2
                fromsocket = findSocketConnectedtoP(fromnode, thisbake)
                nodetree.links.new(fromsocket, rgb.inputs[2])
            elif fromnode.type == "MIX_SHADER":
                #If it's a mix shader on the other end, connect the equivilent RGB node
                #Get the RGB node for that mshader
                fromrgb = nodes[created_mix_nodes[fromnode.name]]
                fromsocket = fromrgb.outputs[0]
                nodetree.links.new(fromsocket, rgb.inputs[2])
            elif fromnode.type == "EMISSION":
                #Set this input to black
                rgb.inputs[2].default_value = (0.0, 0.0, 0.0, 1)
            elif fromnode.type == "GROUP":
                pass
            else:
                printmsg("Error, invalid node config")
        else:
            rgb.inputs[2].default_value = (0.0, 0.0, 0.0, 1)
                
    #Find the output node with location
    m_output_node = find_onode(nodetree)
    loc = m_output_node.location
    
    #Create an emission shader
    emissnode = nodes.new("ShaderNodeEmission")
    emissnode.label = "OmniBake"
    emissnode.location = loc
    emissnode.location.y = emissnode.location.y + 200
    
    #Get the original mix node that was connected to the output node
    socket = m_output_node.inputs["Surface"]
    fromnode = socket.links[0].from_node
    
    #Find our created mix node that is paired with it
    rgbmix = nodes[created_mix_nodes[fromnode.name]]
    
    #Plug rgbmix into emission
    nodetree.links.new(rgbmix.outputs[0], emissnode.inputs[0])
    
    #Plug emission into output
    nodetree.links.new(emissnode.outputs[0], m_output_node.inputs[0])

#------------Long Name Truncation-----------------------
trunc_num = 0
trunc_dict = {}
def trunc_if_needed(objectname):
    
    global trunc_num
    global trunc_dict
    
    #If we already truncated this, just return that
    if objectname in trunc_dict:
        printmsg(f"Object name {objectname} was previously truncated. Returning that.")
        return trunc_dict[objectname]
    
    #If not, let's see if we have to truncate it
    elif len(objectname) >= 38:
        printmsg(f"Object name {objectname} is too long and will be truncated")
        trunc_num += 1
        truncdobjectname = objectname[0:34] + "~" + str(trunc_num)
        trunc_dict[objectname] = truncdobjectname
        return truncdobjectname
    
    #If nothing else, just return the original name
    else:
        return objectname
        
def untrunc_if_needed(objectname):
    
    global trunc_num
    global trunc_dict
    
    for t in trunc_dict:
        if trunc_dict[t] == objectname:
            printmsg(f"Returning untruncated value {t}")
            return t
    
    return objectname
    
def ShowMessageBox(messageitems_list, title, icon = 'INFO'):

    def draw(self, context):
        for m in messageitems_list:
            self.layout.label(text=m)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)
    
#---------------Bake Progress--------------------------------------------

def write_bake_progress(current_operation, total_operations):
    progress = int((current_operation / total_operations) * 100)
    
    t = Path(tempfile.gettempdir())
    t = t / f"OmniBake_Bgbake_{os.getpid()}"

    with open(str(t), "w") as progfile:
        progfile.write(str(progress))
        
#---------------End Bake Progress--------------------------------------------

past_items_dict = {}
def spot_new_items(initialise=True, item_type="images"):
    
    global past_items_dict
    
    if item_type == "images":
        source = bpy.data.images
    elif item_type == "objects":
        source = bpy.data.objects
    elif item_type == "collections":
        source = bpy.data.collections
    
    
    #First run
    if initialise:
        #Set to empty list for this item type
        past_items_dict[item_type] = []
        
        for source_item in source:
            past_items_dict[item_type].append(source_item.name)
        return True
    
    else:
        #Get the list of items for this item type from the dict
        past_items_list = past_items_dict[item_type]
        new_item_list_names = []
        
        for source_item in source:
            if source_item.name not in past_items_list:
                new_item_list_names.append(source_item.name)
        
        return new_item_list_names

#---------------Validation Checks-------------------------------------------

def checkMatsValidforPBR(mat):

    nodes = mat.node_tree.nodes

    valid = True
    invalid_node_names = []
    
    for node in nodes:
        if len(node.outputs) > 0:
            if node.outputs[0].type == "SHADER" and not (node.bl_idname == "ShaderNodeBsdfPrincipled" or node.bl_idname == "ShaderNodeMixShader" or node.bl_idname == "ShaderNodeEmission"):
                #But is it actually connected to anything?
                if len(node.outputs[0].links) >0:
                    invalid_node_names.append(node.name)
    
    return invalid_node_names

def checkExtraMatsValidforPBR(mat):
    nodes = mat.node_tree.nodes
    invalid_node_names = []

    supported_node_types = {
        "ShaderNodeBsdfPrincipled",
        "ShaderNodeMixShader",
        "ShaderNodeAddShader",
        "ShaderNodeEmission",
        "ShaderNodeBsdfGlossy",
        "ShaderNodeBsdfGlass",
        "ShaderNodeBsdfRefraction",
        "ShaderNodeBsdfDiffuse",
        "ShaderNodeBsdfAnisotropic",
        "ShaderNodeBsdfTransparent",
    }

    for node in filter(lambda x: bool(len(node.outputs)), nodes):
        if node.outputs[0].type == "GROUP":
            ## Support baking for group nodes even if they're in an odd spot
            continue
        if node.outputs[0].type == "SHADER" and node.bl_idname not in supported_node_types:
            #But is it actually connected to anything?
            if len(node.outputs[0].links) > 0:
                invalid_node_names.append(node.name)
                
    return invalid_node_names

def deselect_all_not_mesh():
    import bpy

    for obj in bpy.context.selected_objects:
        if obj.type != "MESH":
             obj.select_set(False)

    #Do we still have an active object?
    if bpy.context.active_object == None:
        #Pick arbitary
        bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
        
def fix_invalid_material_config(obj):
    
    if "OmniBake_Placeholder" in bpy.data.materials:
        mat = bpy.data.materials["OmniBake_Placeholder"]
    else:
        mat = bpy.data.materials.new("OmniBake_Placeholder")
        bpy.data.materials["OmniBake_Placeholder"].use_nodes = True

    # Assign it to object
    if len(obj.material_slots) > 0:
        #Assign it to every empty slot
        for slot in obj.material_slots:
            if slot.material == None:
                slot.material = mat
    else:
        # no slots
        obj.data.materials.append(mat)
    
    #All materials must use nodes
    for slot in obj.material_slots:
        mat = slot.material
        if mat.use_nodes == False:
            mat.use_nodes = True
            
    return True

def sacle_image_if_needed(img):
    
    printmsg("Scaling images if needed")
    
    context = bpy.context
    width = img.size[0]
    height = img.size[1]
    
    proposed_width = 0
    proposed_height = 0
    
    if context.scene.texture_res == "0.5k": proposed_width, proposed_height = 512,512
    if context.scene.texture_res == "1k": proposed_width, proposed_height = 1024,1024
    if context.scene.texture_res == "2k": proposed_width, proposed_height = 1024*2,1024*2
    if context.scene.texture_res == "4k": proposed_width, proposed_height = 1024*4,1024*4
    if context.scene.texture_res == "8k": proposed_width, proposed_height = 1024*8,1024*8
        
    if width != proposed_width or height != proposed_height:
        img.scale(proposed_width, proposed_height)

def set_image_internal_col_space(image, thisbake):
    if thisbake != "diffuse" and thisbake != "emission":
        image.colorspace_settings.name = "Non-Color"

#------------------------Allow Additional Shaders----------------------------

def findProperInput(OName, pnode):
    for input in pnode.inputs:
        if OName == "Anisotropy":
            OName = "Anisotropic"
        if OName == "Rotation":
            OName = "Anisotropic Rotation"
        if OName == "Color":
            OName = "Base Color"
        if input.identifier == OName:
            return input

def useAdditionalShaderTypes(nodetree, nodes):
    count = 0
    for node in nodes:
        if (node.type == "BSDF_GLOSSY" or 
        node.type == "BSDF_GLASS" or 
        node.type == "BSDF_REFRACTION" or 
        node.type == "BSDF_DIFFUSE" or 
        node.type == "BSDF_ANISOTROPIC" or 
        node.type == "BSDF_TRANSPARENT" or 
        node.type == "ADD_SHADER"):
            if node.type == "ADD_SHADER":
                pnode = nodes.new("ShaderNodeMixShader")
                pnode.label = "mixNew" +  str(count)
            else:
                pnode = nodes.new("ShaderNodeBsdfPrincipled")
                pnode.label = "BsdfNew" + str(count)
                
            pnode.location = node.location
            pnode.use_custom_color = True
            pnode.color = (0.3375297784805298, 0.4575316309928894, 0.08615386486053467)

            for input in node.inputs:
                if len(input.links) != 0:
                    fromNode = input.links[0].from_node
                    for output in fromNode.outputs:
                        if len(output.links) != 0:
                            for linkOut in output.links:
                                if linkOut.to_node == node:
                                    inSocket = findProperInput(input.identifier, pnode)
                                    nodetree.links.new(output, inSocket) 
                else:
                    inSocket = findProperInput(input.identifier, pnode)
                    if inSocket.name != "Shader":
                        inSocket.default_value = input.default_value
                    
            if len(node.outputs[0].links) != 0:
                for link in node.outputs[0].links:
                    toNode = link.to_node
                    for input in toNode.inputs:
                        if len(input.links) != 0:
                            if input.links[0].from_node == node:
                                nodetree.links.new(pnode.outputs[0], input)

            if node.type == "BSDF_REFRACTION" or node.type == "BSDF_GLASS":
                pnode.inputs[15].default_value = 1
            if node.type == "BSDF_DIFFUSE":
                pnode.inputs[5].default_value = 0   
            if node.type == "BSDF_ANISOTROPIC" or node.type == "BSDF_GLOSSY":
                pnode.inputs[4].default_value = 1
                pnode.inputs[5].default_value = 0
            if node.type == "BSDF_TRANSPARENT":
                pnode.inputs[7].default_value = 0
                pnode.inputs[15].default_value = 1
                pnode.inputs[14].default_value = 1
            
            pnode.hide = True   
            pnode.select = False
            
            nodetree.nodes.remove(node)
            count += 1