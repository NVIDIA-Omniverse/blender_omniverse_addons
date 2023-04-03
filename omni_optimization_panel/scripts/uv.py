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
import time
import contextlib

from . import blender_class, run_ops_wo_update, select_mesh, utils

class uvUnwrap(blender_class.BlenderClass):
    # settings for GUI version only
    bl_idname = "uv.unwrap_batch"
    bl_label = "Batch UV Unwrap"
    bl_description = "batch uv unwrap objects"
    bl_options = {"REGISTER", "UNDO"}

    def __init__(self):
        self._default_attributes = dict( 
            selected_only= False, # uses only objects selected in scene. For GUI version only
            scale_to_bounds = False, # determines if the unwrapped map gets scaled to the square uv image bounds
            clip_to_bounds = False, # if unwrapping exceeds bounds, it will be clipped off
            unwrap_type = 'Cube', # the method for unwrapping (cube, sphere, cylinder, or smart)
            use_set_size = False, # for cube and cylinder project, use specified projection size for all objects.
            # Overrides scale_to_bounds to False
            set_size = 2, # projection size for cube and cylinder project
            print_updated_results= True # print progress to console
        )

    def execute(self, in_attributes=None):
        attributes = self.get_attributes(in_attributes)
        context = bpy.context

        then = time.time() # start time of script execution

        # blender operates in modes/contexts, and certain operations can only be performed in certain contexts
        if bpy.context.mode != 'OBJECT': # make sure context is object mode.
            bpy.ops.object.mode_set(mode='OBJECT') # if it is not, set it to object mode

        run_ops_wo_update.open_update() # allows for operators to be run without updating scene
        # important especially when working with loops
        self.unwrap(context, attributes)
        run_ops_wo_update.close_update() # must always call close_update if open_update is called

        now = time.time() # time after it finished
        print("TIME FOR UNWRAP: ", round(now-then, 3))

        return {"FINISHED"}

    def unwrap(self, context, attributes):

        scaleBounds = attributes["scale_to_bounds"]
        clipBounds = attributes["clip_to_bounds"]
        unwrapType = attributes["unwrap_type"]
        use_set_size = attributes["use_set_size"]
        set_size = attributes["set_size"]
        print_updated_results = attributes["print_updated_results"]
        
        # select objects
        selected = select_mesh.setSelected(context, attributes["selected_only"], deselectAll = True)
        
        if len(selected):  # run only if there are mesh objects in the 'selected' array
            LINE_UP = '\033[1A' # command to move up a line in the console
            LINE_CLEAR = '\x1b[2K' # command to clear current line in the console
            count = 0 # counter for which object is being calculated
            then = time.time() # start time of loop execution

            for object in selected: # unwrap each object separately 
                object.select_set(True) # select object. This is now the only selected object
                context.view_layer.objects.active = object # set active object. Blender needs active object to be the selected object
                bpy.ops.object.mode_set(mode='EDIT') # make sure context is edit mode. Context switching is object dependent, must be after selection
                bpy.ops.mesh.select_all(action='SELECT') # select all mesh vertices. only selected vertices will be uv unwrapped
                
                # for smart UV projection
                if unwrapType == "Smart":
                    # smart UV can take a long time, so this prints out a progress bar
                    if count and print_updated_results: # if the first object has already been calculated and results should be printed
                        with contextlib.redirect_stdout(None): # smartUV prints an output sometimes. We don't want/need this output this suppresses it
                            self.smartUV(scaleBounds) # perform the uv unwrap
                        now = time.time() # time after unwrapping is complete
                        timeElapsed = now - then
                        remaining = len(selected)-count # number of remaining objects
                        timeLeft = timeElapsed/count * remaining # estimation of remaining time
                        print(LINE_UP, end=LINE_CLEAR) # don't want endless print statements
                        print(LINE_UP, end=LINE_CLEAR) # don't want endless print statements
                        # so move up and clear the previously printed lines and overwrite them
                        print("Object Count = ", count, " Objects Remaining = ", remaining)
                        print(" Elapsed Time = ", round(timeElapsed,3), " Time Remaining = ", round(timeLeft,3)) # print results to console
                    else: # if calculating  the first object or not printing results
                        self.smartUV(scaleBounds) # perform the uv unwrap
                        if print_updated_results:
                            print("Object Count = 0")
                            print("Time Remaining = UNKOWN")

                # for cube projection
                elif unwrapType == "Cube":
                    self.cubeUV(scaleBounds, clipBounds, use_set_size, set_size) # perform the uv unwrap

                # for sphere projection
                elif unwrapType == "Sphere":
                    self.sphereUV(scaleBounds, clipBounds) # perform the uv unwrap

                # for cylinder projection
                elif unwrapType == "Cylinder":
                    self.cylinderUV(scaleBounds, clipBounds, use_set_size, set_size) # perform the uv unwrap

                bpy.ops.object.mode_set(mode='OBJECT') # once complete, make sure context is object mode. 
                # Must be in object mode to select the next object
                object.select_set(False) # deselect the current object. Now there are again no objects selected

                count += 1 # increase the object counter

            for obj in selected: # reselect all originally selected meshes
                obj.select_set(True)
            
        else: 
            utils.do_print_error("NO MESH OBJECTS")
            
        return {'FINISHED'}

    # methods for running each type of uv projection
    def smartUV(self, scale):
        bpy.ops.uv.smart_project(correct_aspect=True, scale_to_bounds=scale)

    def cubeUV(self, scale, clip, use_set_size, size):
        if use_set_size: # user sets cube_size value of cube projection
            bpy.ops.uv.cube_project(scale_to_bounds=False, clip_to_bounds=clip, cube_size=size)
        else:
            bpy.ops.uv.cube_project(scale_to_bounds=scale, clip_to_bounds=clip)

    def sphereUV(self, scale, clip):
        bpy.ops.uv.sphere_project(direction='ALIGN_TO_OBJECT', scale_to_bounds=scale, clip_to_bounds=clip)
        # 'ALIGN_TO_OBJECT' sets the direction of the projection to be consistent regardless of view position/direction
        
    def cylinderUV(self, scale, clip, use_set_size, size):
        if use_set_size: # user sets radius value of cylinder projection
            bpy.ops.uv.cylinder_project(direction='ALIGN_TO_OBJECT', scale_to_bounds=False, clip_to_bounds=clip, radius=size)
        else:
            bpy.ops.uv.cylinder_project(direction='ALIGN_TO_OBJECT', scale_to_bounds=scale, clip_to_bounds=clip)