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


from bpy.types import Operator

from . import modify, fix_mesh, chop, uv, utils

class OPTIMIZE_OT_Scene(Operator):
    bl_idname = "optimize.scene"
    bl_label = "Optimize Scene"
    bl_description = "Optimize scene based on operation and set parameters"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        self.get_attributes(context)

        return {'FINISHED'}

    def get_attributes(self, context):
        optimizeOptions = context.scene.optimize_options
        modifyOptions = context.scene.modify_options
        uvOptions = context.scene.uv_options
        chopOptions = context.scene.chop_options

        if optimizeOptions.operation == "modify":
            attributes = dict(
                selected_only= modifyOptions.selected_only,
                apply_mod= modifyOptions.apply_mod,
                fix_bad_mesh = modifyOptions.fix_bad_mesh,
                dissolve_threshold = modifyOptions.dissolve_threshold,
                merge_vertex = modifyOptions.merge_vertex,
                merge_threshold = modifyOptions.merge_threshold,
                remove_existing_sharp = modifyOptions.remove_existing_sharp,
                fix_normals = modifyOptions.fix_normals,
                create_new_custom_normals = modifyOptions.create_new_custom_normals,
                modifier= modifyOptions.modifier,
                # use_modifier_stack= modifyOptions.use_modifier_stack,
                # modifier_stack= modifyOptions.modifier_stack,
                decimate_type= modifyOptions.decimate_type,
                ratio= modifyOptions.ratio,
                iterations= modifyOptions.iterations,
                angle= modifyOptions.angle,
                remesh_type= modifyOptions.remesh_type,
                oDepth= modifyOptions.oDepth,
                voxel_size= modifyOptions.voxel_size,
                geo_type= modifyOptions.geo_type,
                geo_attribute= modifyOptions.geo_attribute
            )

        elif optimizeOptions.operation == "fixMesh":
            attributes = dict(
                selected_only=modifyOptions.selected_only,
                fix_bad_mesh = modifyOptions.fix_bad_mesh,
                dissolve_threshold = modifyOptions.dissolve_threshold,
                merge_vertex = modifyOptions.merge_vertex,
                merge_threshold = modifyOptions.merge_threshold,
                remove_existing_sharp = modifyOptions.remove_existing_sharp,
                fix_normals = modifyOptions.fix_normals,
                create_new_custom_normals = modifyOptions.create_new_custom_normals
            )

        elif optimizeOptions.operation == "uv":
            attributes = dict( 
                selected_only= uvOptions.selected_only,
                scale_to_bounds = uvOptions.scale_to_bounds,
                clip_to_bounds = uvOptions.clip_to_bounds,
                unwrap_type = uvOptions.unwrap_type,
                use_set_size = uvOptions.use_set_size,
                set_size = uvOptions.set_size,
                print_updated_results= uvOptions.print_updated_results
            )

        elif optimizeOptions.operation == "chop":
            attributes = dict(
                merge= chopOptions.merge,
                cut_meshes= chopOptions.cut_meshes,
                max_vertices= chopOptions.max_vertices,
                min_box_size= chopOptions.min_box_size,
                max_depth= chopOptions.max_depth,
                print_updated_results= chopOptions.print_updated_results,
                create_bounds = chopOptions.create_bounds,
                selected_only = chopOptions.selected_only
            )

        if optimizeOptions.print_attributes:
            print(attributes)
        self.process_operation(optimizeOptions.operation, attributes)

    def process_operation(self, operation, attributes):
        start = utils.start_time()

        blender_cmd = None
        if operation == 'modify':
            # Modify Scene
            blender_cmd = modify.Modify()
        elif operation == 'fixMesh':
            # Clean Scene
            blender_cmd = fix_mesh.FixMesh()
        elif operation == 'chop':
            # Chop Scene
            blender_cmd = chop.Chop()
        elif operation == 'uv':
            # Unwrap scene
            blender_cmd = uv.uvUnwrap()
        elif operation == "noop":
            # Runs the load/save USD round trip without modifying the scene.
            utils.do_print("No-op for this scene")
            return
        else:
            utils.do_print_error("Unknown operation: " + operation + " - add function call to process_file in process.py")
            return

        # Run the command
        if blender_cmd:
            blender_cmd.execute(attributes)
        else:
            utils.do_print_error("No Blender class found to run")

        utils.report_time(start, "operation")
