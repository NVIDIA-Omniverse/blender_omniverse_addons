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

import time
import bpy
import numpy as np

class MyProperties(bpy.types.PropertyGroup):
    deletePSystemAfterBake: bpy.props.BoolProperty(
       name = "Delete PS after converting",
       description = "Delete selected particle system after conversion",
       default = False
    )
    progressBar: bpy.props.StringProperty(
        name = "Progress",
        description = "Progress of Particle Conversion",
        default = "RUNNING"
    )
    animateData: bpy.props.BoolProperty(
        name = "Keyframe Animation",
        description = "Add a keyframe for each particle for each of the specified frames",
        default = False
    )
    selectedStartFrame: bpy.props.IntProperty(
        name = "Start",
        description = "Frame to begin keyframes",
        default = 1
    )
    selectedEndFrame: bpy.props.IntProperty(
        name = "End",
        description = "Frame to stop keyframes",
        default = 3
    )

# def fixEndFrame():
#     particleOptions = context.particle_options
#     particleOptions.selectedEndFrame = particleOptions.selectedStartFrame


particleSystemVisibility = []
particleSystemRender = []

def getOriginalModifiers(parent):
    particleSystemVisibility.clear()
    particleSystemRender.clear()
    for mod in parent.modifiers:
        if mod.type == 'PARTICLE_SYSTEM':
            particleSystemVisibility.append(mod.show_viewport)
            particleSystemRender.append(mod.show_render)

def restoreOriginalModifiers(parent):
    count = 0
    for mod in parent.modifiers:
        if mod.type == 'PARTICLE_SYSTEM':
            mod.show_viewport = particleSystemVisibility[count]
            mod.show_render = particleSystemRender[count]
            count+=1

def hideOtherModifiers(parent, countH):
    count = 0
    for mod in parent.modifiers:
        if mod.type == 'PARTICLE_SYSTEM':
            if countH != count:
                mod.show_viewport = False
            count += 1

def particleSystemVisible(parent, countP):
    countS = 0
    for mod in parent.modifiers:
        if mod.type == 'PARTICLE_SYSTEM':
            if countP == countS:
                return mod.show_viewport
            else:
                countS += 1


# Omni Hair Bake
class PARTICLES_OT_omni_hair_bake(bpy.types.Operator):
    """Convert blender particles for Omni scene instancing"""
    bl_idname = "omni.hair_bake"
    bl_label = "Omni Hair Bake"
    bl_options = {'REGISTER', 'UNDO'}  # create undo state

    def execute(self, context):

        particleOptions = context.scene.particle_options

        startTime= time.time()

        print()
        print("____BEGINING PARTICLE CONVERSION______")

        #Deselect Non-meshes
        for obj in bpy.context.selected_objects:
            if obj.type != "MESH":
                obj.select_set(False)
                print("not mesh")

        #Do we still have an active object?
        if bpy.context.active_object == None:
            #Pick arbitary
            bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
        
        for parentObj in bpy.context.selected_objects:
            
            print()
            print("--Staring " + parentObj.name + ":")

            getOriginalModifiers(parentObj)

            countH = 0
            countP = 0
            countPS = 0
            
            showEmmiter = False
            hasPS = False
            for currentPS in parentObj.particle_systems:
                
                hideOtherModifiers(parentObj, countH)
                countH+=1

                hasVisible = particleSystemVisible(parentObj, countP)
                countP+=1

                if currentPS != None and hasVisible:
                    hasPS = True

                    bpy.ops.object.select_all(action='DESELECT')

                    renderType = currentPS.settings.render_type
                    emmitOrHair = currentPS.settings.type
                    
                    if parentObj.show_instancer_for_viewport == True:
                        showEmmiter = True
                    
                    if renderType == 'OBJECT' or renderType == 'COLLECTION':

                        count = 0
                        listInst = []
                        listInstScale = []

                        # For Object Instances
                        if renderType == 'OBJECT':
                            instObj = currentPS.settings.instance_object
                            # Duplicate Instanced Object
                            dupInst = instObj.copy()
                            bpy.context.collection.objects.link(dupInst)

                            dupInst.select_set(True)
                            dupInst.location = (0,0,0)

                            bpy.ops.object.move_to_collection(collection_index=0, is_new=True, new_collection_name="INST_"+str(dupInst.name))
                            dupInst.select_set(False)
                            count += 1
                            listInst.append(dupInst)
                            listInstScale.append(instObj.scale)

                        # For Collection Instances 
                        if renderType == 'COLLECTION':
                            instCol = currentPS.settings.instance_collection.objects
                            countW = 0
                            weight = 1
                            for obj in instCol:
                                # Duplicate Instanced Object
                                dupInst = obj.copy()
                                bpy.context.collection.objects.link(dupInst)

                                dupInst.select_set(True)
                                dupInst.location = (0,0,0)

                                bpy.ops.object.move_to_collection(collection_index=0, is_new=True, new_collection_name="INST_"+str(dupInst.name))
                                dupInst.select_set(False)
                                
                                if parentObj.particle_systems.active.settings.use_collection_count:
                                    weight = currentPS.settings.instance_weights[countW].count

                                print("Instance Count: " + str(weight))

                                for i in range(weight):
                                    count += 1
                                    listInst.append(dupInst)
                                    listInstScale.append(obj.scale)
                                
                                countW += 1

                        # For Path Instances *NOT SUPPORTED
                        if renderType == 'PATH':
                            print("path no good")
                            return {'FINISHED'}

                        if renderType == 'NONE':
                            print("no instances")
                            return {'FINISHED'}
                        
                        #DOES NOTHING RIGHT NOW
                        #if overwriteExsisting:
                            #bpy.ops.outliner.delete(hierarchy=True)

                        # Variables
                        parentObj.select_set(True)
                        parentCollection = parentObj.users_collection[0]
                        nameP = parentObj.particle_systems[countPS].name # get name of object's particle system

                        # Create Empty as child
                        o = bpy.data.objects.new( "empty", None)
                        o.name = "EM_" + nameP
                        o.parent = parentObj
                        parentCollection.objects.link( o )

                        # FOR ANIMATED EMITTER DATA
                        if particleOptions.animateData and emmitOrHair == 'EMITTER':
                            print("--ANIMATED EMITTER--")
                            #Prep for Keyframing
                            collectionInstances = []

                            # Calculate Dependency Graph
                            degp = bpy.context.evaluated_depsgraph_get()
                            # Evaluate the depsgraph (Important step)
                            particle_systems = parentObj.evaluated_get(degp).particle_systems
                            # All particles of selected particle system
                            activePS = particle_systems[countPS]
                            particles = activePS.particles
                            # Total Particles
                            totalParticles = len(particles)

                            #Currently does NOT work
                            # if activePS.type == 'HAIR':
                                # hairLength = particles[0].hair_length
                                # print(hairLength)
                                # print(bpy.types.ParticleHairKey.co_object(parentObj,parentObj.modifiers[0], particles[0]))
                                # key = particles[0].hair_keys
                                # print(key)
                                # coo = key.co
                                # print(coo)
                                # print(particles[0].location)

                            #Beginings of supporting use random, requires more thought
                                # obInsttt = parentObj.evaluated_get(degp).object_instances
                                # for i in obInsttt:
                                #     obj = i.object
                                #     print(obj.name)

                                # for obj in degp.object_instances:
                                #     print(obj.instance_object)
                                #     print(obj.particle_system)
                        
                            # Handle instances for construction of scene collections **Fast**
                            for i in range(totalParticles):

                                childObj = particles[i]
                                calculateChild = False

                                if childObj.birth_time <= particleOptions.selectedEndFrame and childObj.die_time > particleOptions.selectedStartFrame:
                                        calculateChild = True

                                if calculateChild:
                                    modInst = i % count

                                    #Works for "use count" but not "pick random"
                                    dupColName = str(listInst[modInst].users_collection[0].name)

                                    #Create Collection Instance
                                    source_collection = bpy.data.collections[dupColName]
                                    instance_obj = bpy.data.objects.new(
                                        name= "Inst_" + listInst[modInst].name + "." + str(i), 
                                        object_data=None
                                    )
                                    instance_obj.empty_display_type = 'SINGLE_ARROW'
                                    instance_obj.empty_display_size = .1
                                    instance_obj.instance_collection = source_collection
                                    instance_obj.instance_type = 'COLLECTION'
                                    parentCollection.objects.link(instance_obj)
                                    instance_obj.parent = o
                                    instance_obj.matrix_parent_inverse = o.matrix_world.inverted()

                                    collectionInstances.append(instance_obj)
                            
                            print("Using " + str(len(collectionInstances)))
                            print("Out of " + str(totalParticles) + " instances")

                            collectionCount = len(collectionInstances)

                            startFrame = particleOptions.selectedStartFrame
                            endFrame = particleOptions.selectedEndFrame

                            #Do we need to swap start and end frame?
                            if particleOptions.selectedStartFrame > particleOptions.selectedEndFrame:
                                endFrame = startFrame
                                startFrame = particleOptions.selectedEndFrame

                            for frame in range(startFrame, endFrame + 1):
                                print("frame = " + str(frame))
                                bpy.context.scene.frame_current = frame

                                # Calculate Dependency Graph for each frame
                                degp = bpy.context.evaluated_depsgraph_get()
                                particle_systems = parentObj.evaluated_get(degp).particle_systems
                                particles = particle_systems[countPS].particles


                                for i in range(collectionCount):            
                                    activeCol = collectionInstances[i]
                                    activeDup = particles[i]

                                    #Keyframe Visibility, Scale, Location, and Rotation
                                    if activeDup.alive_state == 'UNBORN' or activeDup.alive_state == 'DEAD':
                                        activeCol.scale = (0,0,0)
                                        activeCol.keyframe_insert(data_path='scale')
                                        activeCol.hide_viewport = True
                                        activeCol.hide_render = True
                                        activeCol.keyframe_insert("hide_viewport")
                                        activeCol.keyframe_insert("hide_render") 
                                    else:
                                        activeCol.hide_viewport = False
                                        activeCol.hide_render = False

                                        scale = activeDup.size

                                        activeCol.location = activeDup.location
                                        activeCol.rotation_mode = 'QUATERNION'
                                        activeCol.rotation_quaternion = activeDup.rotation
                                        activeCol.rotation_mode = 'XYZ'
                                        activeCol.scale = (scale, scale, scale)

                                        activeCol.keyframe_insert(data_path='location')
                                        activeCol.keyframe_insert(data_path='rotation_euler')
                                        activeCol.keyframe_insert(data_path='scale')
                                        activeCol.keyframe_insert("hide_viewport")
                                        activeCol.keyframe_insert("hide_render")

                        # FOR ANIMATED HAIR DATA
                        elif particleOptions.animateData and emmitOrHair == 'HAIR':
                            print("--ANIMATED HAIR--")
                            #Prep for Keyframing
                            bpy.ops.object.duplicates_make_real(use_base_parent=True, use_hierarchy=True) # bake particles
                            dups = bpy.context.selected_objects
                            lengthDups = len(dups)
                            
                            collectionInstances = []

                            # Handle instances for construction of scene collections **Fast**
                            for i in range(lengthDups):

                                childObj = dups.pop(0)
                                modInst = i % count

                                #Works for "use count" but not "pick random"
                                dupColName = str(listInst[modInst].users_collection[0].name)

                                #Create Collection Instance
                                source_collection = bpy.data.collections[dupColName]
                                instance_obj = bpy.data.objects.new(
                                    name= "Inst_" + childObj.name, 
                                    object_data=None
                                )
                                instance_obj.empty_display_type = 'SINGLE_ARROW'
                                instance_obj.empty_display_size = .1
                                instance_obj.instance_collection = source_collection
                                instance_obj.instance_type = 'COLLECTION'
                                parentCollection.objects.link(instance_obj)
                                instance_obj.parent = o

                                bpy.data.objects.remove(childObj, do_unlink=True)
                                collectionInstances.append(instance_obj)
                            
                            print(str(len(collectionInstances)) + " instances")

                            collectionCount = len(collectionInstances)

                            startFrame = particleOptions.selectedStartFrame
                            endFrame = particleOptions.selectedEndFrame

                            #Do we need to swap start and end frame?
                            if particleOptions.selectedStartFrame > particleOptions.selectedEndFrame:
                                endFrame = startFrame
                                startFrame = particleOptions.selectedEndFrame

                            for frame in range(startFrame, endFrame + 1):
                                print("frame = " + str(frame))
                                bpy.context.scene.frame_current = frame

                                # Calculate hairs for each frame
                                parentObj.select_set(True)
                                bpy.ops.object.duplicates_make_real(use_base_parent=True, use_hierarchy=True) # bake particles
                                tempdups = bpy.context.selected_objects

                                for i in range(collectionCount):
                                    activeDup = tempdups.pop(0)        
                                    activeCol = collectionInstances[i]

                                    #Keyframe Scale, Location, and Rotation
                                    activeCol.location = activeDup.location
                                    activeCol.rotation_euler = activeDup.rotation_euler
                                    activeCol.scale = activeDup.scale

                                    activeCol.keyframe_insert(data_path='location')
                                    activeCol.keyframe_insert(data_path='rotation_euler')
                                    activeCol.keyframe_insert(data_path='scale')
                                
                                    bpy.data.objects.remove(activeDup, do_unlink=True)
                                            
                        # FOR SINGLE FRAME CONVERSION
                        else:
                            print("--SINGLE FRAME--")
                            bpy.ops.object.duplicates_make_real(use_base_parent=True, use_hierarchy=True) # bake particles
                            dups = bpy.context.selected_objects
                            lengthDups = len(dups)

                            # Handle instances for construction of scene collections **Fast**
                            for i in range(lengthDups):

                                childObj = dups.pop(0)
                                modInst = i % count

                                dupColName = str(listInst[modInst].users_collection[0].name)
                                loc=childObj.location
                                rot=childObj.rotation_euler
                                newScale = np.divide(childObj.scale, listInstScale[modInst])

                                #Create Collection Instance
                                source_collection = bpy.data.collections[dupColName]
                                instance_obj = bpy.data.objects.new(
                                    name= "Inst_" + childObj.name, 
                                    object_data=None
                                )
                                instance_obj.empty_display_type = 'SINGLE_ARROW'
                                instance_obj.empty_display_size = .1
                                instance_obj.instance_collection = source_collection
                                instance_obj.instance_type = 'COLLECTION'
                                instance_obj.location = loc
                                instance_obj.rotation_euler = rot
                                instance_obj.scale = newScale
                                parentCollection.objects.link(instance_obj)
                                instance_obj.parent = o

                                bpy.data.objects.remove(childObj, do_unlink=True)


                        for obj in listInst:
                            bpy.context.view_layer.layer_collection.children[obj.users_collection[0].name].exclude = True
                            
                        #Make parent object active object again
                        parentObj.select_set(True)
                        bpy.context.view_layer.objects.active = parentObj
                    
                    else:
                        print("Must be object or collection instance")

                else:
                    print("Object has no active particle system")

                restoreOriginalModifiers(parentObj)
                countPS += 1
            
            #Handle PS after converting
            if particleOptions.deletePSystemAfterBake:
                if showEmmiter == False and hasPS == True:
                    bpy.context.active_object.hide_render = True
                    bpy.context.active_object.hide_set(True)

                countI = 0
                for ps in range(len(parentObj.particle_systems)):
                    if particleSystemVisibility[ps] == True:
                        parentObj.particle_systems.active_index = countI
                        bpy.ops.object.particle_system_remove()
                    else:
                        countI+=1

            else:
                countI = 0
                for mod in parentObj.modifiers:
                    if mod.type == 'PARTICLE_SYSTEM':
                        mod.show_viewport = False
                        if particleSystemVisibility[countI] == True:
                            mod.show_render = False
                        countI+=1

        print ("My program took", time.time() - startTime, " seconds to run") # run time
        return {'FINISHED'}