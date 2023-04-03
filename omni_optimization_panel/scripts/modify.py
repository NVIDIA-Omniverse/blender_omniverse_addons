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
import math

from . import blender_class, select_mesh, fix_mesh, decimate, remesh, geo_nodes, utils

# Master Class for all modifiers
class Modify(blender_class.BlenderClass):
    # settings for GUI version only
    bl_idname = "modify.scene"
    bl_label = "Modify Scene"
    bl_description = "Modify the scene based on set parameters"
    bl_options = {"REGISTER", "UNDO"}

    def __init__(self):
        self._default_attributes = dict(
            selected_only=True, # uses only objects selected in scene. For GUI version only
            apply_mod=True, # applies the generated modifiers. Should always be true for command line running
            fix_bad_mesh = True, # used to remove zero are faces and zero length edges based on the 'dissolve_threshold'
            dissolve_threshold = .08, # threshold value for 'fix_bad_mesh'
            merge_vertex = False, # merge connected and disconnected vertices of a mesh by a distance threshold
            merge_threshold = 0.01, # distance value to use for merge_vertex
            remove_existing_sharp = True, # when removing zero area faces, edge data can become messed up, causing bad normals. This helps minimize that.
            fix_normals = True, # optionally fix normals. useful for after 'fix_bad_mesh' to fix the normals as well.
            create_new_custom_normals = True, # useful for after 'fix_bad_mesh' to fix the normals as well. 
            modifier= "DECIMATE",  # determines which modifier type to use if 'use_modifier_stack' is False. (DECIMATE, REMESH, NODES, or SUBSURF)
            # Some common modifier names for reference:'DECIMATE''REMESH''NODES''SUBSURF''SOLIDIFY''ARRAY''BEVEL'
            use_modifier_stack= False, # allows use of more that one modifier sequentially. Useful for more specific customizable workflows.
            modifier_stack=[["DECIMATE", "COLLAPSE", 0.5]], # determines which modifier(s) to use if 'use_modifier_stack' is True.(DECIMATE, REMESH, NODES)
                # Modifiers are procedural adjustments to a mesh. The modifiers are stored in 'modifier_stack'. 
                # Most modifiers have different options for calculation. for instance the 'DECIMATE' modifier options are stored in 'decimate_type'
            decimate_type="COLLAPSE", # the type of decimation being performed(COLLAPSE, UNSUBDIV, or DISSOLVE)
                # Each method produces different results, with its own pros/cons)
                # https://docs.google.com/document/d/1pkMZxgW4Xn_KJymFlKOo5XIkK2YleVYtyLJztTUTyAY/edit
                # COLLAPSE: "Merges vertices together progressively, taking the shape of the mesh into account.""
                # UNSUBDIV: "It is intended for meshes with a mainly grid-based topology (without giving uneven geometry)"
                # DISSOLVE: "It reduces details on forms comprised of mainly flat surfaces."
            ratio=0.5, # the ratio value used for collapse decimation.
            iterations=2, # the number of un-subdivisions performed
            angle=15.0, # attribute used when performing dissolve decimation.
            remesh_type="VOXEL", # the type of remesh being performed(BLOCKS, SMOOTH, SHARP, VOXEL)
                # remeshing removes all UV mappings from an object
                # https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/remesh.html#remesh-modifier
                # first three modes produce almost identical typology, but with differing amounts of smoothing (BLOCKS, SMOOTH, SHARP)
                # BLOCKS: "There is no smoothing at all."
                # SMOOTH: "Output a smooth surface."
                # SHARP: "Similar to Smooth, but preserves sharp edges and corners."
                # VOXEL: "Uses an OpenVDB to generate a new manifold mesh from the current geometry while trying to preserve the mesh’s original volume."
            oDepth=4, # stands for octree depth and controls the resolution of most of the remesh modifiers
            voxel_size=0.1, # used for voxel remesh to control resolution
            geo_type="GeometryNodeBoundBox", # the type of geometry node tree to create:
                # (GeometryNodeConvexHull, GeometryNodeBoundBox, GeometryNodeSubdivisionSurface)
                # geometry nodes is currently under development, so feature set is not yet at a stage to be fully utilized
                # this puts in place a framework for more customizable and easily implementable optimizations in the future
                # more on geometry nodes: https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/index.html#geometry-nodes
            geo_attribute=2  # a generic attribute variable that can be used for the different geo node types
        )

    def execute(self, in_attributes=None):
        attributes = self.get_attributes(in_attributes)
        context = bpy.context
        
        then = time.time() # start time of script execution.
        
        # shorthands for multi-used attributes
        modifier = attributes["modifier"]
        decimate_type = attributes["decimate_type"] 
        angle = attributes["angle"]
        remesh_type = attributes["remesh_type"]

        if context.mode != 'OBJECT': # must be in object mode to perform the rest of the operations.
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # select objects
        selected = select_mesh.setSelected(context, attributes["selected_only"], deselectAll = False)

        if len(selected): # run only if there are selected mesh objects in the scene
            if attributes["fix_bad_mesh"]: # optionally fix bad meshes. Can also be done separately before hand
                fix_mesh.FixMesh.fixBadMesh(
                    self,
                    selected, 
                    attributes["dissolve_threshold"], 
                    attributes["fix_bad_mesh"], 
                    attributes["merge_vertex"], 
                    attributes["merge_threshold"], 
                    attributes["remove_existing_sharp"])
            if attributes["fix_normals"]: # optionally fix bad normals (can often arise after fixing bad mesh)
                fix_mesh.FixMesh.fixNormals(self, selected, attributes["create_new_custom_normals"])
            
            # for printing vertex and face data
            startingVerts = utils.getVertexCount(selected)
            startingFaces = utils.getFaceCount(selected)

            if attributes["use_modifier_stack"]:
                for mod in attributes["modifier_stack"]:
                    self.run_modifier(selected, mod[0], mod[1], mod[2])
            else:
                #Decimate
                if modifier == 'DECIMATE':
                    sub_mod = decimate_type
                    if decimate_type == 'COLLAPSE':
                        prop = attributes["ratio"]
                    elif decimate_type == 'UNSUBDIV':
                        prop = attributes["iterations"]
                    elif decimate_type == 'DISSOLVE':
                        angle = math.radians(angle) # need to change angle to radians for the modifier
                        prop = angle
                #Remesh
                elif modifier == 'REMESH':
                    sub_mod = remesh_type
                    if remesh_type == 'BLOCKS' or remesh_type == 'SMOOTH' or remesh_type == 'SHARP':
                        prop = attributes["oDepth"]
                    if remesh_type == 'VOXEL':
                        prop = attributes["voxel_size"]
                #Geometry Nodes
                elif modifier == 'NODES':
                    sub_mod = attributes["geo_type"]
                    prop = attributes["geo_attribute"]
                else:
                    sub_mod = None
                    prop = None
                
                self.run_modifier(selected, modifier, sub_mod, prop)
                raise RuntimeError
                
            # apply modifiers once above loop is complete
            if attributes["apply_mod"]:
                context.view_layer.objects.active = selected[0] # need to set one of the selected objects as the active object
                # arbitrarily choosing to set the first object in selected_objects list.  (there can only be one AO, but multiple SO)
                # this is necessary for the applying the modifiers.
                bpy.ops.object.convert(target='MESH') # applies all modifiers of each selected mesh. this preps the scene for proper export.

            # print vertex and face data
            endingVerts = utils.getVertexCount(selected)
            endingFaces = utils.getFaceCount(selected)
            vertsRemoved = startingVerts-endingVerts
            facesRemoved = startingFaces-endingFaces
            print("Modify Mesh Statistics:")
            utils.do_print("Starting Verts: " + str(startingVerts) + ", Ending Verts: " + str(endingVerts) + ", Verts Removed: " + str(vertsRemoved))
            utils.do_print("Starting Faces: " + str(startingFaces) + ", Ending Faces: " + str(endingFaces) + ", Faces Removed: " + str(facesRemoved))

        else: 
            utils.do_print_error("NO MESH OBJECTS")

        now = time.time() # time after it finished.
        print("TIME FOR MODIFY: ", round(now-then, 3))

        return {'FINISHED'} # "return {"FINISHED"} (or return{"CANCELED"}) is how Blender understands that an operator call is complete
    
    def run_modifier(self, objects, modifier, sub_mod = None, prop = None):
        # RUN BASED ON TYPE OF MODIFIER AND MODIFIER SUB_TYPE. Each modifier requires different input variables/values
        # Decimate
        if modifier == 'DECIMATE':
            decimate.decimate(objects, sub_mod, prop)
        # Remesh
        elif modifier == 'REMESH':
            remesh.remesh(objects, sub_mod, prop)
        # Geometry Nodes
        elif modifier == 'NODES':
            geo_nodes.geoNodes(objects, sub_mod, prop)
