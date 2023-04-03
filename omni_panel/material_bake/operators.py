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
import sys
import subprocess
import os
from .bake_operation import BakeStatus, bakestolist
from .data import MasterOperation, BakeOperation
from . import functions
from . import bakefunctions
from .background_bake import bgbake_ops
from pathlib import Path
import tempfile


class OBJECT_OT_omni_bake_mapbake(bpy.types.Operator):
    """Start the baking process"""
    bl_idname = "object.omni_bake_mapbake"
    bl_label = "Bake"
    bl_options = {'REGISTER', 'UNDO'}  # create undo state

        
    def execute(self, context):
        
        def commence_bake(needed_bake_modes):
            
            #Prepare the BakeStatus tracker for progress bar
            num_of_objects = 0
            num_of_objects = len(bpy.context.selected_objects)
            
            total_maps = 0
            for need in needed_bake_modes:
                if need == BakeOperation.PBR:
                    total_maps+=(bakestolist(justcount=True) * num_of_objects)
                    
            BakeStatus.total_maps = total_maps
            
            #Clear the MasterOperation stuff
            MasterOperation.clear()
            
            #Need to know the total operations
            MasterOperation.total_bake_operations = len(needed_bake_modes)
            
            #Master list of all ops
            bops = []
            
            for need in needed_bake_modes:
                #Create operation
                bop = BakeOperation()
                
                #Set master level attributes
                #-------------------------------
                bop.bake_mode = need
                #-------------------------------
                
                bops.append(bop)
                functions.printmsg(f"Created operation for {need}")
            
            #Run queued operations
            for bop in bops:
                MasterOperation.this_bake_operation_num+=1
                MasterOperation.current_bake_operation = bop
                if bop.bake_mode == BakeOperation.PBR:
                    functions.printmsg("Running PBR bake")
                    bakefunctions.doBake()
            
            return True        
        
        
        
        ######################TEMP###############################################
        
        needed_bake_modes = []
        needed_bake_modes.append(BakeOperation.PBR)
            
        #Clear the progress stuff
        BakeStatus.current_map = 0
        BakeStatus.total_maps = 0        
        
        #If we have been called in background mode, just get on with it. Checks should be done.
        if "--background" in sys.argv:
            if "OmniBake_Bakes" in bpy.data.collections:
                #Remove any prior baked objects
                bpy.data.collections.remove(bpy.data.collections["OmniBake_Bakes"])
            
            #Bake
            commence_bake(needed_bake_modes)
            
            self.report({"INFO"}, "Bake complete")
            return {'FINISHED'}
            
        functions.deselect_all_not_mesh()

        #We are in foreground, do usual checks
        """
        result = True
        for need in needed_bake_modes:
            if not functions.startingChecks(bpy.context.selected_objects, need):
                result = False
        
        if not result:
            return {"CANCELLED"}
        """
        
        #If the user requested background mode, fire that up now and exit
        if bpy.context.scene.bgbake == "bg":
            bpy.ops.wm.save_mainfile()
            filepath = filepath = bpy.data.filepath
            process = subprocess.Popen(
                [bpy.app.binary_path, "--background",filepath, "--python-expr",\
                "import bpy;\
                import os;\
                from pathlib import Path;\
                savepath=Path(bpy.data.filepath).parent / (str(os.getpid()) + \".blend\");\
                bpy.ops.wm.save_as_mainfile(filepath=str(savepath), check_existing=False);\
                bpy.ops.object.omni_bake_mapbake();"],
                shell=False)
            
            bgbake_ops.bgops_list.append([process, bpy.context.scene.prepmesh, bpy.context.scene.hidesourceobjects])            
            
            self.report({"INFO"}, "Background bake process started")
            return {'FINISHED'}
        
        #If we are doing this here and now, get on with it
            
        #Create a bake operation
        commence_bake(needed_bake_modes)
        
        self.report({"INFO"}, "Bake complete")
        return {'FINISHED'}
    
#--------------------BACKGROUND BAKE----------------------------------

class OBJECT_OT_omni_bake_bgbake_status(bpy.types.Operator):
    bl_idname = "object.omni_bake_bgbake_status"
    bl_label = "Check on the status of bakes running in the background"
    
    
    def execute(self, context):
        msg_items = []
        
        
        #Display remaining
        if len(bgbake_ops.bgops_list) == 0:
            msg_items.append("No background bakes are currently running")
        
        else:
            msg_items.append(f"--------------------------")
            for p in bgbake_ops.bgops_list:
                
                t = Path(tempfile.gettempdir())
                t = t / f"OmniBake_Bgbake_{str(p[0].pid)}"            
                try:
                    with open(str(t), "r") as progfile:
                        progress = progfile.readline()
                except:
                    #No file yet, as no bake operation has completed yet. Holding message
                    progress = 0
                
                msg_items.append(f"RUNNING: Process ID: {str(p[0].pid)} - Progress {progress}%")
                msg_items.append(f"--------------------------")
            
        functions.ShowMessageBox(msg_items, "Background Bake Status(es)")
        
        return {'FINISHED'} 

class OBJECT_OT_omni_bake_bgbake_import(bpy.types.Operator):
    bl_idname = "object.omni_bake_bgbake_import"
    bl_label = "Import baked objects previously baked in the background"
    bl_options = {'REGISTER', 'UNDO'}  # create undo state
    
    def execute(self, context):
        
        if bpy.context.mode != "OBJECT":
            self.report({"ERROR"}, "You must be in object mode")
            return {'CANCELLED'} 
            
        for p in bgbake_ops.bgops_list_finished:
            
            savepath = Path(bpy.data.filepath).parent
            pid_str = str(p[0].pid)
            path = savepath / (pid_str + ".blend")
            path = str(path) + "\\Collection\\"
            
            #Record the objects and collections before append (as append doesn't give us a reference to the new stuff)
            functions.spot_new_items(initialise=True, item_type="objects")
            functions.spot_new_items(initialise=True, item_type="collections")
            functions.spot_new_items(initialise=True, item_type="images")
            
            #Append
            bpy.ops.wm.append(filename="OmniBake_Bakes", directory=path, use_recursive=False, active_collection=False)
            
            #If we didn't actually want the objects, delete them
            if not p[1]:
                #Delete objects we just imported (leaving only textures)
                
                for obj_name in functions.spot_new_items(initialise=False, item_type = "objects"):
                    bpy.data.objects.remove(bpy.data.objects[obj_name])
                for col_name in functions.spot_new_items(initialise=False, item_type = "collections"):
                    bpy.data.collections.remove(bpy.data.collections[col_name])                
              
            #If we have to hide the source objects, do it
            if p[2]:
                #Get the newly introduced objects:
                objects_before_names = functions.spot_new_items(initialise=False, item_type="objects")
                
                for obj_name in objects_before_names:
                    #Try this in case there are issues with long object names.. better than a crash
                    try:
                        bpy.data.objects[obj_name.replace("_Baked", "")].hide_set(True)
                    except:
                        pass
                           
            #Delete the temp blend file
            try:
                os.remove(str(savepath / pid_str) + ".blend")
                os.remove(str(savepath / pid_str) + ".blend1")
            except:
                pass
        
        #Clear list for next time
        bgbake_ops.bgops_list_finished = []
        
        
        #Confirm back to user
        self.report({"INFO"}, "Import complete")
        
        messagelist = []
        
        messagelist.append(f"{len(functions.spot_new_items(initialise=False, item_type='objects'))} objects imported")
        messagelist.append(f"{len(functions.spot_new_items(initialise=False, item_type='images'))} textures imported")
        
        functions.ShowMessageBox(messagelist, "Import complete", icon = 'INFO')

        #If we imported an image, and we already had an image with the same name, get rid of the original in favour of the imported
        new_images_names = functions.spot_new_items(initialise=False, item_type="images")
        
        #Find any .001s
        for imgname in new_images_names:
            try:
                int(imgname[-3:])
                
                #Delete the existing version
                bpy.data.images.remove(bpy.data.images[imgname[0:-4]])
                
                #Rename our version
                bpy.data.images[imgname].name = imgname[0:-4]
                
            except ValueError:
                pass
                
                
        return {'FINISHED'} 

class OBJECT_OT_omni_bake_bgbake_clear(bpy.types.Operator):
    """Delete the background bakes because you don't want to import them into Blender. NOTE: If you chose to save bakes or FBX externally, these are safe and NOT deleted. This is just if you don't want to import into this Blender session"""
    bl_idname = "object.omni_bake_bgbake_clear"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}  # create undo state

    
    def execute(self, context):
        savepath = Path(bpy.data.filepath).parent
        
        for p in bgbake_ops.bgops_list_finished:
            pid_str = str(p[0].pid)
            try:
                os.remove(str(savepath / pid_str) + ".blend")
                os.remove(str(savepath / pid_str) + ".blend1")
            except:
                pass
        
        bgbake_ops.bgops_list_finished = []
        
        return {'FINISHED'} 