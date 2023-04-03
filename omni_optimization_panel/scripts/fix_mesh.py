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
import bmesh
import time
from functools import reduce

from . import blender_class, run_ops_wo_update, select_mesh, utils

class FixMesh(blender_class.BlenderClass):
    # settings for GUI version only
    bl_idname = "fix.mesh"
    bl_label = "Fix Mesh"
    bl_description = "fix bad meshes in the scene"
    bl_options = {"REGISTER", "UNDO"}

    def __init__(self):
        self._default_attributes = dict(
            selected_only=False, # uses only objects selected in scene. For GUI version only
            fix_bad_mesh = True, # used to remove zero are faces and zero length edges based on the 'dissolve_threshold'
            dissolve_threshold = 0.08, # threshold value for 'fix_bad_mesh'
            merge_vertex = False, # merge connected and disconnected vertices of a mesh by a distance threshold
            merge_threshold = 0.01, # distance value to use for merge_vertex
            remove_existing_sharp = True, # when removing zero area faces, edge data can become messed up, causing bad normals. This helps minimize that.
            fix_normals = True, # optionally fix normals. useful for after 'fix_bad_mesh' to fix the normals as well.
            create_new_custom_normals = True # will auto generate new sharp edges (based on angle)
        )

    def execute(self, in_attributes=None):
        attributes = self.get_attributes(in_attributes)
        context = bpy.context
        
        then = time.time() # start time of script execution
        
        if context.mode != 'OBJECT': # must be in object mode to perform the rest of the operations.
            bpy.ops.object.mode_set(mode='OBJECT')

        # select objects
        selected = select_mesh.setSelected(context, attributes["selected_only"], deselectAll = False)

        if len(selected): # run only if there are selected mesh objects in the scene
             # if removing zero-area-faces/zero-length-edges or merging vertices by distance:
            if attributes["fix_bad_mesh"] or attributes["merge_vertex"]:
                self.fixBadMesh(
                    selected, 
                    attributes["dissolve_threshold"], 
                    attributes["fix_bad_mesh"], 
                    attributes["merge_vertex"], 
                    attributes["merge_threshold"], 
                    attributes["remove_existing_sharp"])
            if attributes["fix_normals"]: # optionally fix bad normals (can often arise after fixing bad mesh)
                self.fixNormals(selected, attributes["create_new_custom_normals"])
        else: 
            utils.do_print_error("NO MESH OBJECTS")

        now = time.time() # time after it finished
        print("TIME FOR FIX MESH: ", round(now-then, 3))

        return {'FINISHED'}

    def fixBadMesh(self, selected, dissolveThreshold = 0.08, fixBadMesh = False, mergeVertex = False, mergeThreshold = 0.1, removeExistingSharp = True):
        # once degenerate dissolve geometry node exists (needs to be developed by Blender), replace this with a GN setup
        # that would go towards producing non-destructive workflows, which is a goal for the GUI version

        # for printing vertex and face data
        startingVerts = utils.getVertexCount(selected)
        startingFaces = utils.getFaceCount(selected)

        bm = bmesh.new() # 'bmesh' in BLender is data type that contains the 'edit mesh' for an object
            # It allows for much greater control over mesh properties and operations
        for object in selected: # loop through each selected object

            utils.printPart(object) # print the current part being fixed.

            mesh = object.data # all mesh objects contain mesh data, that is what we need to alter, not the object itself
            bm.from_mesh(mesh) # attach the mesh to the bmesh container so that changes can be made
            if fixBadMesh:
                bmesh.ops.dissolve_degenerate( # for removing zero area faces and zero length edges
                    bm,
                    dist=dissolveThreshold,
                    edges=bm.edges
                    )
            if mergeVertex:
                bmesh.ops.remove_doubles(
                    bm,
                    verts=bm.verts, 
                    dist=mergeThreshold
                    )
            # Clear sharp state for all edges. This step reduces problems that arise from bad normals
            if removeExistingSharp:
                for edge in bm.edges:
                    edge.smooth = True # smooth is the opposite of sharp, so setting to smooth is the same as removing sharp

            bm.to_mesh(mesh) # need to transfer the altered bmesh data back to the original mesh
            bm.clear() # always clear a bmesh after use
            utils.printClearLine() # remove last print, so that printPart can be updated

        # print vertex and face data
        endingVerts = utils.getVertexCount(selected)
        endingFaces = utils.getFaceCount(selected)
        vertsRemoved = startingVerts-endingVerts
        facesRemoved = startingFaces-endingFaces
        print("Fix Mesh Statistics:")
        utils.do_print("Starting Verts: " + str(startingVerts) + ", Ending Verts: " + str(endingVerts) + ", Verts Removed: " + str(vertsRemoved))
        utils.do_print("Starting Faces: " + str(startingFaces) + ", Ending Faces: " + str(endingFaces) + ", Faces Removed: " + str(facesRemoved))

    def fixNormals(self, selected, createNewCustomNormals):
        run_ops_wo_update.open_update() # allows for operators to be run without updating scene
            # important especially when working with loops

        for o in selected:
            if o.type != 'MESH':
                continue
            bpy.context.view_layer.objects.active = o
            mesh = o.data
            if mesh.has_custom_normals:
                bpy.ops.mesh.customdata_custom_splitnormals_clear()
                if createNewCustomNormals:
                    bpy.ops.mesh.customdata_custom_splitnormals_add()

        run_ops_wo_update.close_update() # must always call close_update if open_update is called

def deleteEmptyXforms(occurrences): # Delete objects with no meshes, or zero vertex count meshes
    # first separate occurrences into two lists to get meshes with zero vertex count
    def partition(p, l): # uses lambda function to efficiently parse data
        return reduce(lambda x, y: x[not p(y)].append(y) or x, l, ([], [])) # if obj has vertices place in x, else place in y
    occurrences_clean, occurrences_dirty = partition(lambda obj:len(obj.data.vertices), occurrences)

    # delete obj with zero vertex count or no meshes
    for obj in occurrences_dirty:
        bpy.data.objects.remove(obj, do_unlink=True)

    # return good meshes
    return occurrences_clean
