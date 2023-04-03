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
import time

from . import blender_class, run_ops_wo_update, select_mesh, bounds, utils, fix_mesh

class Chop(blender_class.BlenderClass):
    # settings for GUI version only
    bl_idname = "chop.scene"
    bl_label = "Chop Scene"
    bl_description = "Recursively split scene in half until reaches a desired threshold"
    bl_options = {"REGISTER", "UNDO"}

    print_results = True

    def __init__(self):
        self._default_attributes = dict(
            merge= True, # optionally merge meshes in each split chunk after split recursion is complete
            cut_meshes=True, # split all meshes intersecting each cut plane
            # Cannot set this very low since split creates new triangles(if quads...)
            max_vertices= 100000, # a vertex threshold value, that once a chunk is below, the splitting terminates
            min_box_size= 1, # a size threshold that once a chunk is smaller than, the splitting terminates
            max_depth= 16, # a recursion depth threshold that once is reached, the splitting terminates
            print_updated_results= True, # print progress to console
            create_bounds = False, # create new bounds objects for displaying the cut boundaries. Mostly useful for GUI
            selected_only = False # uses only objects selected in scene. For GUI version only
        )

    def execute(self, in_attributes=None):
        attributes = self.get_attributes(in_attributes)
        context = bpy.context
        Chop.print_results = attributes["print_updated_results"]

        Stats.resetValues()

        Stats.startTime = time.time()
        then = Stats.startTime
        
        # select objects
        selected = select_mesh.setSelected(context, attributes["selected_only"], deselectAll = False)

        if len(selected): # run only if there are selected mesh objects in the scene
            self.split(context, selected, attributes) # starts the splitting process
            now = time.time() # time after it finished
            Stats.printTermination()
            if attributes['merge']:
                Stats.printMerge()
            print("TIME FOR SPLIT: ", round(now-then, 3))
        else: 
            utils.do_print_error("NO MESH OBJECTS")

        return {'FINISHED'}
    
    def getSplitPlane(self, obj_details): # the cut plane used in split. Aligned perpendicular to the longest dimension of the bounds
        # find longest side
        var = {obj_details.x.distance: "x", obj_details.y.distance: "y", obj_details.z.distance: "z"}
        max_dim = var.get(max(var)) # get the axis name of maximum of the three dims

        # adjust the plane normal depending on the axis with the largest dimension
        if max_dim == "x":
            normal = [1,0,0,0]
            axis = "x"
        elif max_dim == "y":
            normal = [0,1,0,0]
            axis = "y"
        else:
            normal = [0,0,1,0]
            axis = "z"
            
        # get data for sub-boxes
        midPt = [obj_details.x.mid,obj_details.y.mid,obj_details.z.mid] # get center of bounds to be able to create the next set of bounds
        return midPt, normal, axis
    
    def getSplitBoxes(self, obj_details, attributes): # get the bounds for the two successive splits during recursion

        # find longest side
        var = {obj_details.x.distance: "x", obj_details.y.distance: "y", obj_details.z.distance: "z"}
        mx = var.get(max(var)) # get the axis name of maximum of the three dims

        mid_0 = [obj_details.x.max, obj_details.y.max, obj_details.z.max] # the longest axis value will be replaced with a mid point
        high = mid_0.copy() # maximum value of bounds
        mid_1 = [obj_details.x.min, obj_details.y.min, obj_details.z.min] # the longest axis value will be replaced with a mid point
        low = mid_1.copy() # minimum value fo bounds
        midPt = [obj_details.x.mid,obj_details.y.mid,obj_details.z.mid] # center point of previous bounds

        # replace the mid point of new bounds depending on the axis with the largest dimension
        if mx == "x":
            mid_0[0] = midPt[0]
            mid_1[0] = midPt[0]
        elif mx == "y":
            mid_0[1] = midPt[1]
            mid_1[1] = midPt[1]
        else:
            mid_0[2] = midPt[2]
            mid_1[2] = midPt[2]

        # Create sub-bounds. These are the two halves of the previous bounds, split along the longest axis of the bounds
        # only need two points to calculate bounds, uses the maximum/minimum value point (high/low) and the set mid point (mid_0/mid_1)
        coords_1 = [high[:], mid_1[:]] # put the points in a list
        box_0 = bounds.bounds(coords_1) # gather attributes of new bounds (max, min, mid, and dim of each axis)
        coords_0 = [low[:], mid_0[:]] # put the points in a list
        box_1 = bounds.bounds(coords_0) # gather attributes of new bounds (max, min, mid, and dim of each axis)
        if attributes["create_bounds"]: # optionally create display objects for viewing bounds
            bounds.boundsObj(coords_1)
            bounds.boundsObj(coords_0)

        return box_0, box_1

    def boxTooSmall(self, obj_details, attributes): # returns whether bounds of current occurrences is too small
        # find longest sides
        dims = [obj_details.x.distance, obj_details.y.distance, obj_details.z.distance] # get the dimensions of each axis of the bounds
        if max(dims) < attributes["min_box_size"]: # if the maximum of the three dims is less than the specified min_box_size
            return True # continue recursion
        return False # end recursion

    def parentEmpty(self, part, children): # for parenting new created objects from split
        parent_name = part.name # part is the original object that was split. keep track of its name
        parent_col = part.users_collection[0] # track the collection of the part as well
        parent_parent = part.parent # if the part object has an existing parent track that too
        bpy.data.objects.remove(part, do_unlink=True) # now that that info is stored, part can be deleted and removed from the scene
        
        # an empty will take the place of the original part
        obj = bpy.data.objects.new(parent_name, None) # create an empty object that will inherit the name of part
        parent_col.objects.link(obj) # connect this object to part's collection
        obj.parent = parent_parent # make this empty the child of part's parent
        
        for child in children: # make the newly created objects from the split operation children of the empty
            child.parent = obj

    def newObj(self, bm, parent): # create a new object for each half of a split
        obj = parent.copy() # parent is the original mesh being split. this contains data such as material, 
        # so it is easiest to start with a copy of the object
        obj.data = parent.data.copy() # need to copy the object mesh data separately
        # TODO: obj.animation_data = sibling.animation_data.copy() # not sure if animation data should be copied. This would do that.
        parent.users_collection[0].objects.link(obj)

        # apply bmesh to new mesh
        bm.to_mesh(obj.data) # Once the new object is formed, bmesh data created during the split process can be transferred to the new obj
        bm.free() # always do this when finished with a bmesh

        return obj

    def checkIntersect(self, obj, axis, center): # for checking cut plane intersection while splitting
        # intersection is checked by testing the objects bounds rather than each vertex individually
        obj_details = bounds.bounds([obj.matrix_world @ Vector(v) for v in obj.bound_box])
        tolerance = .01 # a tolerance value for intersection to prevent cutting a mesh that is in line with cut plane
        # TODO: may need to have user control over this tolerance, or define it relative to total scene size.
        # check for intersection depending on the direction of the cutting
        # boolean is created for both sides of cut plane. 
        # rather than a single boolean checking for intersection, return if mesh is on one or both sides of cut plane.
        if axis == "x":
            intersect_0 = obj_details.x.max > center[0] + tolerance
            intersect_1 = obj_details.x.min < center[0] - tolerance
        elif axis == "y":
            intersect_0 = obj_details.y.max > center[1] + tolerance
            intersect_1 = obj_details.y.min < center[1] - tolerance
        elif axis == "z":
            intersect_0 = obj_details.z.max > center[2] + tolerance
            intersect_1 = obj_details.z.min < center[2] - tolerance

        return intersect_0, intersect_1

    def doSplit(self, partsToSplit, planeOrigin, planeNormal, axis): # perform the actual split
        # split separates the occurrences into two. those halves need to be stored in their own new lists
        occurrences_0 = []
        occurrences_1 = []

        for part in partsToSplit: # iterate over occurrences
            intersect_0, intersect_1 = self.checkIntersect(part, axis, planeOrigin) # only perform split if object intersects the cut plane.
            if intersect_0 and intersect_1: # if mesh has vertices on both sides of cut plane
                Stats.printPart(part) # print the part being processed

                co = part.matrix_world.inverted() @ Vector(planeOrigin) # splitting takes place relative to object space not world space.
                normDir = part.matrix_world.transposed() @ Vector(planeNormal) # need to adjust plane origin and normal for each object.

                bmi = bmesh.new() # 'bmesh' in Blender is data type that contains the 'edit mesh' for an object
                # It allows for much greater control over mesh properties and operations
                bmi.from_mesh(part.data) # attach the mesh to the bmesh container so that changes can be made
                bmo = bmi.copy() # must use two separate bmesh objects because two new occurrence lists are being written to
                
                # bisect_plane is how to split a mesh using a plane. It can only save one side of the split result at a time, so it is done twice
                # save inner mesh data
                bmesh.ops.bisect_plane(bmi, 
                geom=bmi.verts[:]+bmi.edges[:]+bmi.faces[:], # the geometry to be split, which is the first bmesh just created
                dist=0.0001, # a threshold value for the split to check vertex proximity to cut plane
                # TODO: may need to have user control over this tolerance, or define it relative to total scene size.
                plane_co=co, # the cut plane
                plane_no=(normDir.x,normDir.y,normDir.z), # the plane normal direction
                clear_inner=True, # remove the geometry on the positive side of the cut plane
                clear_outer=False) # keep the geometry on the negative side of the cut plane

                # save outer mesh data
                bmesh.ops.bisect_plane(bmo, 
                geom=bmo.verts[:]+bmo.edges[:]+bmo.faces[:], # the geometry to be split, which is the second bmesh just created
                dist=0.0001, # a threshold value for the split to check vertex proximity to cut plane
                plane_co=co, # the cut plane
                plane_no=(normDir.x,normDir.y,normDir.z), # the plane normal direction
                clear_inner=False, # keep the geometry on the positive side of the cut plane
                clear_outer=True) # remove the geometry on the negative side of the cut plane

                # make the bmesh the object's mesh
                # need to transfer the altered bmesh data back to the original mesh
                children = [] # create a list that will contain the newly created split meshes
                obj = self.newObj(bmi, part) # create a new mesh object to attach the inner bmesh data to
                occurrences_0.append(obj) # add new object to inner occurrence list
                children.append(obj) # add new object to children list
                obj2 = self.newObj(bmo, part) # create a new mesh object to attach the outer bmesh data to
                occurrences_1.append(obj2) # add new object to outer occurrence list
                children.append(obj2) # add new object to children list

                self.parentEmpty(part, children) # use children list to fix object parents

                if Chop.print_results: 
                    utils.printClearLine() # clear last printed line before continuing
            # if there are vertices on only one side of the cut plane there is nothing to split so place the existing mesh into the appropriate list
            elif intersect_0:
                occurrences_0.append(part) # add object to inner occurrence list
                part.select_set(False) # deselect object
            else:
                occurrences_1.append(part )# add object to outer occurrence list
                part.select_set(False) # deselect object

        # bisect_plane can create empty objects, or zero vert count meshes. remove those objects before continuing
        occurrences_0 = fix_mesh.deleteEmptyXforms(occurrences_0) # update occurrences_0
        occurrences_1 = fix_mesh.deleteEmptyXforms(occurrences_1) # update occurrences_1

        return occurrences_0, occurrences_1

    def doMerge(self, partsToMerge): # for merging individual meshes within each chunk after split is complete
        if len(partsToMerge) > 1: # if there is only one mesh or zero meshes, there is no merging to do
            then = time.time() # time at the beginning of merge
            ctx = bpy.context.copy() #making a copy of the current context allows for temporary modifications to be made
            # in this case, the temporary context is switching the active and selected objects
            # this allows avoiding needing to deselect and reselect after the merge
            ctx['selected_editable_objects'] = partsToMerge # set the meshes in the chunk being merged to be selected
            ctx['active_object'] = partsToMerge[0] # set active object. Blender needs active object to be the selected object

            parents = [] # a list that will contain the parent of each part being merged
            for merge in partsToMerge:
                parents.append(merge.parent)

            run_ops_wo_update.open_update() # allows for operators to be run without updating scene
            bpy.ops.object.join(ctx) # merges all parts into one
            run_ops_wo_update.close_update() # must always call close_update if open_update is called

            now = time.time() # time after merging is complete
            Stats.mergeTime += (now-then) # add time to total merge time to get an output of total time spent on merge
   
    def recursiveSplit(self, occurrences, attributes, obj_details, depth): # runs checks before each split, and handles recursion
        if not occurrences: # if there are no occurrences, end recursion
            Stats.printPercent(depth, True) # optionally print results before ending recursion
            return
        
        # Check for maximum recursive depth has been reached to terminate and merge
        if attributes["max_depth"] != 0 and depth >= attributes["max_depth"]: # if max recursion depth is 0, the check will be ignored
            Stats.chunks += 1 # each split creates a new chunk, adds only chunks from completed recursive branches
            Stats.printMsg_maxDepth += 1 # "REACHED MAX DEPTH"
            Stats.printPercent(depth) # optionally print results before ending recursion
            if attributes["merge"]: # if merging, do so now
                self.doMerge(occurrences)
            return

        # Check for vertex count threshold and bbox size to terminate and merge
        vertices = utils.getVertexCount(occurrences)
        if self.boxTooSmall(obj_details, attributes) or vertices < attributes["max_vertices"]:
            Stats.chunks += 1 # each split creates a new chunk, adds only chunks form completed recursive branches
            if vertices < attributes["max_vertices"]:
                Stats.printMsg_vertexGoal += 1 # "REACHED VERTEX GOAL"
            elif self.boxTooSmall(obj_details, attributes): # or vertices < attributes["max_vertices"]:
                Stats.printMsg_boxSize += 1 # "BOX TOO SMALL"
            Stats.printPercent(depth) # optionally print results before ending recursion
            if attributes["merge"]: # if merging, do so now
                self.doMerge(occurrences)
            return

        # Keep subdividing
        planeOrigin, planeNormal, axis = self.getSplitPlane(obj_details) # calculate components for cutter object

        # Do the split and merge
        if attributes["cut_meshes"]: # splits meshes in scene based on cut plane and separates them into two halves
            occurrences_0, occurrences_1 = self.doSplit(occurrences, planeOrigin, planeNormal, axis)

        depth += 1 # if split has taken place, increment recursive depth count
        # Recurse. Get bounding box for each half.
        box_0, box_1 = self.getSplitBoxes(obj_details, attributes)
        self.recursiveSplit(occurrences_0, attributes, box_0, depth)
        self.recursiveSplit(occurrences_1, attributes, box_1, depth)
       
    def split(self, context, selected, attributes): # preps original occurrences and file for split
        occurrences = selected # tracks the objects for each recursive split
        # on the first split, this is the selected objects.

        # Initial bbox includes all original occurrences
        boundsCombined = bounds.boundingBox(occurrences) # gets the combined bounds coordinates of the occurrences
        obj_details = bounds.bounds(boundsCombined) # create a dictionary of specific statistics for each axis of bounds

        if attributes["create_bounds"]: # optionally create a bounds object for each recursive split.
            target_coll_name = "BOUNDARIES" # put these objects in a separate collection to keep scene organized
            target_coll = bpy.data.collections.new(target_coll_name) # create a new collection in the master scene collection
            context.scene.collection.children.link(target_coll) # link the newly created collection to the scene
            bounds.boundsObj(boundsCombined) # create bounds obj

        depth = 0 # tracks recursive depth
        print("-----SPLIT HAS BEGUN-----")
        Stats.printPercent(depth) # for optionally printing progress of operation
        self.recursiveSplit(occurrences, attributes, obj_details, depth) # begin recursive split

class Stats():

    startTime= 0 # start time of script execution, used for calculating progress
    printMsg_vertexGoal = 0 # for tracking number of times recursion terminated because vertex goal was reached
    printMsg_boxSize = 0 # for tracking number of times recursion terminated because box was too small
    printMsg_maxDepth = 0 # for tracking number of times recursion terminated because max recursive depth was exceeded
    percent_worked = 0 # for tracking amount of scene that contains objects for progress calculation
    percent_empty = 0 # for tracking amount of scene that is empty for progress calculation
    chunks = 0 # the number of parts created after the recursive split. each chunk may contain multiple meshes/objects
    mergeTime = 0 # for tracking the amount of time spent merging chunks

    def resetValues(): # reset values before running
        Stats.startTime= 0
        Stats.printMsg_vertexGoal = 0
        Stats.printMsg_boxSize = 0
        Stats.printMsg_maxDepth = 0
        Stats.percent_worked = 0
        Stats.percent_empty = 0
        Stats.chunks = 0
        Stats.mergeTime = 0 

    # for printing progress statistics to console
    def printTermination():
        print("Reached Vertex Goal: ", Stats.printMsg_vertexGoal, # print number of times recursion terminated because vertex goal was reached
            "  Box Too Small: ", Stats.printMsg_boxSize, # print number of times recursion terminated because box was too small
            "  Exceeded Max Depth: ", Stats.printMsg_maxDepth) # print number of times recursion terminated because max recursive depth was exceeded
        print("chunks: ", Stats.chunks) # print total number of chunks created from split

    def printMerge():
        print("merge time: ", Stats.mergeTime) # print the total time the merging took

    def printPart(part):
        if Chop.print_results: 
            print("current part being split: ", part) # want to keep track of latest part being split in order to more easily debug if blender crashes

    def printPercent(depth, empty=False): # for printing progress of recursive split
        if Chop.print_results: 
            if depth != 0:
                if empty: # generated chunk contains no geometry it is considered empty
                    Stats.percent_empty += 100/pow(2,depth) # calculated as a fraction of 2 raised to the recursive depth. Gives a measurement of total volume complete
                elif depth: # cannot calculate if depth is zero due to division by zero
                    Stats.percent_worked += 100/pow(2,depth) # calculated as a fraction of 2 raised to the recursive depth. Gives a measurement of total volume complete
                    
                total = Stats.percent_empty + Stats.percent_worked # percent of bounds volume calculated. Includes empty and occupied chunks
                percent_real = Stats.percent_worked/(100-Stats.percent_empty)*100 # calculated based on a ratio of chunks with split meshes to empty chunks.
                # this results in a more accurate calculation of remaining time because empty chunks take virtually zero time to process

                #timer
                now = time.time() # current time elapsed in operation
                if percent_real > 0: # if at least one occupied chunk has been calculated
                    est_comp_time = f"{((now-Stats.startTime)/percent_real*100 - (now-Stats.startTime)):1.0f}" # estimation of remaining time
                    # based on what has already been processed
                else: 
                    est_comp_time = "Unknown"
                
                utils.printClearLine()
                utils.printClearLine()
                # print results to console
                print("\033[93m" + "Percent_empty: ", f"{Stats.percent_empty:.1f}" , "%,   Percent_worked: ", f"{Stats.percent_worked:.1f}", 
                    "%,   Total: ", f"{total:.1f}", "%,    Real: ", f"{percent_real:.1f}", "%")
                print("Estimated time remaining: ", est_comp_time, "s,  Depth: ", depth, "\033[0m")
            else:
                print() # empty lines to prep for the progress printing
                print() # empty lines to prep for the progress printing
