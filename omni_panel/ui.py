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

from typing import *

import bpy
from bpy.types import (Context, Object, Material, Scene)
from . particle_bake.operators import *
from . material_bake.background_bake import bgbake_ops
# from .material_bake_complex import OBJECT_OT_omni_material_bake
from os.path import join, dirname
import bpy.utils.previews

from .material_bake import baker


## ======================================================================
def get_icons_directory():
    icons_directory = join(dirname(__file__), "icons")
    return icons_directory


## ======================================================================
def _get_bake_types(scene:Scene) -> List[str]:
    result = []
    bake_all = scene.all_maps
    if scene.selected_col or bake_all:
        result.append("DIFFUSE")
    if scene.selected_normal or bake_all:
        result.append("NORMAL")
    if scene.selected_emission or bake_all:
        result.append("EMIT")
    if scene.selected_specular or bake_all:
        result.append("GLOSSY")
    if scene.selected_rough or bake_all:
        result.append("ROUGHNESS")
    if scene.selected_trans or bake_all:
        result.append("TRANSMISSION")

    ## special types
    if scene.omni_bake.bake_metallic or bake_all:
        result.append("METALLIC")

    return ",".join(result)


## ======================================================================
class OBJECT_PT_omni_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Omniverse"
    bl_label = "NVIDIA Omniverse"
    bl_options = {"DEFAULT_CLOSED"}
    version = "0.0.0"

    #retrieve icons
    icons = bpy.utils.previews.new()
    icons_directory = get_icons_directory()
    icons.load("OMNI", join(icons_directory, "ICON.png"), 'IMAGE')

    def draw_header(self, context):
        self.layout.label(text="", icon_value=self.icons["OMNI"].icon_id)

    def draw(self, context):

        layout = self.layout
        scene = context.scene

        # --------Particle Collection Instancing-------------------

        particleOptions = scene.particle_options

        particleCol = self.layout.column(align=True)
        particleCol.label(text="Omni Particles",
                          icon='PARTICLES')
        box = particleCol.box()
        column = box.column(align=True)
        column.prop(particleOptions, "deletePSystemAfterBake")

        row = column.row()
        row.prop(particleOptions, "animateData")
        if particleOptions.animateData:
            row = column.row(align=True)
            row.prop(particleOptions, "selectedStartFrame")
            row.prop(particleOptions, "selectedEndFrame")
            row = column.row()
            row.enabled = False
            row.label(text="Increased Calculation Time", icon='ERROR')

        row = column.row()
        row.scale_y = 1.5
        row.operator('omni.hair_bake',
                     text='Convert',
                     icon='MOD_PARTICLE_INSTANCE')

        if len(bpy.context.selected_objects) != 0 and bpy.context.active_object != None:
            if bpy.context.active_object.select_get() and bpy.context.active_object.type == "MESH":
                layout.separator()

                column = layout.column(align=True)
                column.label(text="Convert Material to:", icon='SHADING_RENDERED')
                box = column.box()

                materialCol = box.column(align=True)
                materialCol.operator('universalmaterialmap.create_template_omnipbr',
                                     text='OmniPBR')
                materialCol.operator('universalmaterialmap.create_template_omniglass',
                                     text='OmniGlass')


## ======================================================================
class OBJECT_PT_omni_bake_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Omniverse"
    bl_label = "Material Baking"
    bl_options = {"DEFAULT_CLOSED"}
    version = "0.0.0"

    #retrieve icons
    icons = bpy.utils.previews.new()
    icons_directory = get_icons_directory()
    icons.load("OMNI", join(icons_directory, "ICON.png"), 'IMAGE')
    icons.load("BAKE",join(icons_directory, "Oven.png"), 'IMAGE')


    def draw_header(self, context):
        self.layout.label(text="", icon="UV_DATA")

    def draw(self, context):
        
        layout = self.layout
        scene = context.scene
        box = layout.box()

        #--------PBR Bake Settings-------------------

        row = box.row()
        if scene.all_maps == True:
            row.prop(scene, "all_maps", icon = 'CHECKBOX_HLT')
        else:
            row.prop(scene, "all_maps", icon = 'CHECKBOX_DEHLT')

            column = box.column(align= True)
            row = column.row()
            
            row.prop(scene, "selected_col")
            row.prop(scene, "selected_normal")

            row = column.row()
            row.prop(scene, "selected_rough")
            row.prop(scene, "selected_specular", text="Gloss")

            row = column.row()
            row.prop(scene, "selected_trans")
            row.prop(scene, "selected_emission")

            row = column.row()
            row.label(text="Special Maps")

            row = column.row()
            row.prop(scene.omni_bake, "bake_metallic")
            row.label(text=" ")

        #--------Texture Settings-------------------
        
        row = box.row()
        row.label(text="Texture Resolution:")
        row.scale_y = 0.5 
        row = box.row()
        row.prop(scene, "texture_res", expand=True)
        row.scale_y = 1 
        if scene.texture_res == "8k" or scene.texture_res == "4k":
            row = box.row()
            row.enabled = False
            row.label(text="Long Bake Times", icon= 'ERROR')
        
        #--------UV Settings-------------------

        column = box.column(align = True)
        row = column.row()
        row.prop(scene, "newUVoption")
        row.prop(scene, "unwrapmargin")

        #--------Other Settings-------------------

        column= box.column(align=True)
        row = column.row()
        if scene.bgbake == "fg":
            text = "Copy objects and apply bakes"
        else:
            text = "Copy objects and apply bakes (after import)"
        
        row.prop(scene, "prepmesh", text=text)
        
        if scene.prepmesh == True:
            if scene.bgbake == "fg":
                text = "Hide source objects after bake"
            else:
                text = "Hide source objects after bake (after import)"
            row = column.row()
            row.prop(scene, "hidesourceobjects", text=text)
        
        #-------------Buttons-------------------------
        
        row = box.row()
        try:
            row.prop(scene.cycles, "device", text="Device")
        except:
            pass

        row = box.row()
        row.scale_y = 1.5
        op = row.operator("omni.bake_maps", icon_value=self.icons["BAKE"].icon_id)

        op.unwrap = scene.newUVoption
        op.bake_types = _get_bake_types(scene)
        op.merge_textures = scene.omni_bake.merge_textures
        op.hide_original = scene.hidesourceobjects
        op.width = op.height = {
            "0.5k": 512,
            "1k": 1024,
            "2k": 2048,
            "4k": 4096,
            "8k": 8192,
        }[scene.texture_res]

        can_bake_poll, error_data = baker.omni_bake_maps_poll(context)
        can_bake_poll_result = {
            -1: f"Cannot bake objects in collection {baker.COLLECTION_NAME}",
            -2: f"Material cannot be baked:",
            -3: "Cycles Renderer Add-on not loaded!"
        }

        if  can_bake_poll < 0:
            row = box.row()
            row.label(text=can_bake_poll_result[can_bake_poll], icon="ERROR")
            if can_bake_poll == -2:
                mesh_name, material_name = error_data
                row = box.row()
                row.label(text=f"{material_name} on {mesh_name}")

        row = column.row()
        row.scale_y = 1

        ##!TODO: Restore background baking
        # row.prop(context.scene, "bgbake", expand=True)

        if scene.bgbake == "bg":
            row = column.row(align= True) 
            
            # - BG status button
            col = row.column()
            if len(bgbake_ops.bgops_list) == 0:
                enable = False
                icon = "TIME"
            else:
                enable = True
                icon = "TIME"
                    
            col.operator("object.omni_bake_bgbake_status", text="", icon=icon)
            col.enabled = enable
            
            # - BG import button
            
            col = row.column()
            if len(bgbake_ops.bgops_list_finished) != 0:
                enable = True
                icon = "IMPORT"
            else:
                enable = False
                icon = "IMPORT"
            
            col.operator("object.omni_bake_bgbake_import", text="", icon=icon)
            col.enabled = enable
            
            #BG erase button
            
            col = row.column()
            if len(bgbake_ops.bgops_list_finished) != 0:
                enable = True
                icon = "TRASH"
            else:
                enable = False
                icon = "TRASH"
            
            col.operator("object.omni_bake_bgbake_clear", text="", icon=icon)
            col.enabled = enable       
            
            row.alignment = 'CENTER'
            row.label(text=f"Running {len(bgbake_ops.bgops_list)} | Finished {len(bgbake_ops.bgops_list_finished)}")


## ======================================================================
class OmniBakePreferences(bpy.types.AddonPreferences):
    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __package__

    img_name_format: bpy.props.StringProperty(name="Image format string",
        default="%OBJ%_%BATCH%_%BAKEMODE%_%BAKETYPE%")
    
    #Aliases
    diffuse_alias: bpy.props.StringProperty(name="Diffuse", default="diffuse")
    metal_alias: bpy.props.StringProperty(name="Metal", default="metalness")
    roughness_alias: bpy.props.StringProperty(name="Roughness", default="roughness")
    glossy_alias: bpy.props.StringProperty(name="Glossy", default="glossy")
    normal_alias: bpy.props.StringProperty(name="Normal", default="normal")
    transmission_alias: bpy.props.StringProperty(name="Transmission", default="transparency")
    transmissionrough_alias: bpy.props.StringProperty(name="Transmission Roughness", default="transparencyroughness")
    clearcoat_alias: bpy.props.StringProperty(name="Clearcost", default="clearcoat")
    clearcoatrough_alias: bpy.props.StringProperty(name="Clearcoat Roughness", default="clearcoatroughness")
    emission_alias: bpy.props.StringProperty(name="Emission", default="emission")
    specular_alias: bpy.props.StringProperty(name="Specular", default="specular")
    alpha_alias: bpy.props.StringProperty(name="Alpha", default="alpha")    
    sss_alias: bpy.props.StringProperty(name="SSS", default="sss")
    ssscol_alias: bpy.props.StringProperty(name="SSS Colour", default="ssscol")

    @classmethod
    def reset_img_string(self):
        prefs = bpy.context.preferences.addons[__package__].preferences
        prefs.property_unset("img_name_format")
        bpy.ops.wm.save_userpref()
