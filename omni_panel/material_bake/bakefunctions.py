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
import sys
from .bake_operation import BakeStatus
from .data import MasterOperation, BakeOperation


def optimize():
    
    current_bake_op = MasterOperation.current_bake_operation
    
    MasterOperation.orig_sample_count = bpy.context.scene.cycles.samples

    functions.printmsg("Reducing sample count to 16 for more efficient baking")
    bpy.context.scene.cycles.samples = 16

    return True

def undo_optimize():
    #Restore sample count
    bpy.context.scene.cycles.samples = MasterOperation.orig_sample_count

def common_bake_prep():
    
    #--------------Set Bake Operation Variables----------------------------
    
    current_bake_op = MasterOperation.current_bake_operation
    
    functions.printmsg("================================")
    functions.printmsg("---------Beginning Bake---------")
    functions.printmsg(f"{current_bake_op.bake_mode}")
    functions.printmsg("================================")
    
    #Run information
    op_num = MasterOperation.this_bake_operation_num
    firstop = False
    lastop = False
    if op_num == 1: firstop = True
    if op_num == MasterOperation.total_bake_operations: lastop = True
    
    
    #If this is a pbr bake, gather the selected maps
    if current_bake_op.bake_mode in {BakeOperation.PBR}:
        current_bake_op.assemble_pbr_bake_list()
    
    #Record batch name
    MasterOperation.batch_name = bpy.context.scene.batchName
    
    #Set values based on viewport selection
    current_bake_op.orig_objects = bpy.context.selected_objects.copy()
    current_bake_op.orig_active_object = bpy.context.active_object
    current_bake_op.bake_objects = bpy.context.selected_objects.copy()
    current_bake_op.active_object = bpy.context.active_object

    current_bake_op.orig_engine = bpy.context.scene.render.engine
    
    #Record original UVs for everyone
    if firstop:
        
        for obj in current_bake_op.bake_objects:
            try:
                MasterOperation.orig_UVs_dict[obj.name] = obj.data.uv_layers.active.name
            except AttributeError:
                MasterOperation.orig_UVs_dict[obj.name] = False
    
    #Record the rendering engine
    if firstop:
        MasterOperation.orig_engine = bpy.context.scene.render.engine
    
    current_bake_op.uv_mode = "normal"
    

    
    #----------------------------------------------------------------------
    
    #Force it to cycles
    bpy.context.scene.render.engine = "CYCLES"
    
    bpy.context.scene.render.bake.use_selected_to_active = False
    
    functions.printmsg(f"Selected to active is now {bpy.context.scene.render.bake.use_selected_to_active}")
    
    #If the user doesn't have a GPU, but has still set the render device to GPU, set it to CPU
    if not bpy.context.preferences.addons["cycles"].preferences.has_active_device():
        bpy.context.scene.cycles.device = "CPU"

    #Clear the trunc num for this session
    functions.trunc_num = 0
    functions.trunc_dict = {}

    #Turn off that dam use clear.
    bpy.context.scene.render.bake.use_clear = False

    #Do what we are doing with UVs (only if we are the primary op)
    if firstop:
        functions.processUVS()

    #Optimize
    optimize()

    #Make sure the normal y setting is at default
    bpy.context.scene.render.bake.normal_g = "POS_Y"

    return True    

def common_bake_finishing():
    
    #Run information
    current_bake_op = MasterOperation.current_bake_operation
    op_num = MasterOperation.this_bake_operation_num
    
    firstop = False
    lastop = False
    if op_num == 1: firstop = True
    if op_num == MasterOperation.total_bake_operations: lastop = True
    

    #Restore the original rendering engine
    if lastop:
        bpy.context.scene.render.engine = MasterOperation.orig_engine

    undo_optimize()
    
    #If prep mesh, or save object is selected, or running in the background, then do it
    #We do this on primary run only
    if firstop: 
        if(bpy.context.scene.prepmesh or "--background" in sys.argv):
            functions.prepObjects(current_bake_op.bake_objects, current_bake_op.bake_mode)

    #If the user wants it, restore the original active UV map so we don't confuse anyone
    functions.restore_Original_UVs()

    #Restore the original object selection so we don't confuse anyone
    bpy.ops.object.select_all(action="DESELECT")
    for obj in current_bake_op.orig_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = current_bake_op.orig_active_object

    #Hide all the original objects
    if bpy.context.scene.prepmesh and bpy.context.scene.hidesourceobjects and lastop:
        for obj in current_bake_op.bake_objects:
            obj.hide_set(True)
           
    #Delete placeholder material
    if lastop and "OmniBake_Placeholder" in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials["OmniBake_Placeholder"])
                   
    if "--background" in sys.argv:
        bpy.ops.wm.save_mainfile()

def doBake():
    
    current_bake_op = MasterOperation.current_bake_operation

    #Do the prep we need to do for all bake types
    common_bake_prep()

    #Loop over the bake modes we are using    
    def doBake_actual():
        
        IMGNAME = ""
    
        for thisbake in current_bake_op.pbr_selected_bake_types:  
    
            for obj in current_bake_op.bake_objects:
                #Reset the already processed list
                mats_done = []
    
                functions.printmsg(f"Baking object: {obj.name}")
    
                #Truncate if needed from this point forward
                OBJNAME = functions.trunc_if_needed(obj.name)

                #Create the image we need for this bake (Delete if exists)
                IMGNAME = functions.gen_image_name(obj.name, thisbake)
                functions.create_Images(IMGNAME, thisbake, obj.name)
    
                #Prep the materials one by one
                materials = obj.material_slots
                for matslot in materials:
                    mat = bpy.data.materials.get(matslot.name)
    
                    if mat.name in mats_done:
                        functions.printmsg(f"Skipping material {mat.name}, already processed")
                        #Skip this loop
                        #We don't want to process any materials more than once or bad things happen
                        continue
                    else:
                        mats_done.append(mat.name)
    
                    #Make sure we are using nodes
                    if not mat.use_nodes:
                        functions.printmsg(f"Material {mat.name} wasn't using nodes. Have enabled nodes")
                        mat.use_nodes = True
    
                    nodetree = mat.node_tree
                    nodes = nodetree.nodes
    
                    #Take a copy of material to restore at the end of the process
                    functions.backupMaterial(mat)
    
                    #Create the image node and set to the bake texutre we are using
                    imgnode = nodes.new("ShaderNodeTexImage")
                    imgnode.image = bpy.data.images[IMGNAME]
                    imgnode.label = "OmniBake"
    
                    #Remove all disconnected nodes so don't interfere with typing the material
                    functions.removeDisconnectedNodes(nodetree)

                    #Use additional shader types
                    functions.useAdditionalShaderTypes(nodetree, nodes)
    
                    #Normal and emission bakes require no further material prep. Just skip the rest
                    if(thisbake != "normal" and thisbake != "emission"):
                        #Work out what type of material we are dealing with here and take correct action
                        mat_type = functions.getMatType(nodetree)
    
                        if(mat_type == "MIX"):
                            functions.setup_mix_material(nodetree, thisbake)
                        elif(mat_type == "PURE_E"):
                            functions.setup_pure_e_material(nodetree, thisbake)
                        elif(mat_type == "PURE_P"):
                            functions.setup_pure_p_material(nodetree, thisbake)
    
                    #Last action before leaving this material, make the image node selected and active
                    functions.deselectAllNodes(nodes)
                    imgnode.select = True
                    nodetree.nodes.active = imgnode
    
                
                #Select only this object
                functions.selectOnlyThis(obj)
                
                #We are done with this image, set colour space
                
                functions.set_image_internal_col_space(bpy.data.images[IMGNAME], thisbake)
    
                #Bake the object for this bake mode
                functions.bakeoperation(thisbake, bpy.data.images[IMGNAME])
                
                #Update tracking
                BakeStatus.current_map+=1
                functions.printmsg(f"Bake maps {BakeStatus.current_map} of {BakeStatus.total_maps} complete")
                functions.write_bake_progress(BakeStatus.current_map, BakeStatus.total_maps)
    
                #Restore the original materials
                functions.printmsg("Restoring original materials")
                functions.restoreAllMaterials()
                functions.printmsg("Restore complete")
    
                #Last thing we do with this image is scale it 
                functions.sacle_image_if_needed(bpy.data.images[IMGNAME])

    #Do the bake at least once
    doBake_actual()
    
        
    
    #Finished baking. Perform wind down actions
    common_bake_finishing()