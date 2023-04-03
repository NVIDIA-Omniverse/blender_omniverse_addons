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

bl_info = {
    "name": "Omni Panel",
    "author": "NVIDIA Corporation",
    "version": (1, 1, 1),
    "blender": (3, 4, 0),
    "location": "View3D > Toolbar > Omniverse",
    "description": "Nvidia Omniverse bake materials for export to usd",
    "warning": "",
    "doc_url": "",
    "category": "Omniverse",
}

import bpy

#Import classes	
from .material_bake.operators import (OBJECT_OT_omni_bake_mapbake,
OBJECT_OT_omni_bake_bgbake_status, OBJECT_OT_omni_bake_bgbake_import, OBJECT_OT_omni_bake_bgbake_clear)	
from .ui import (OBJECT_PT_omni_panel, OBJECT_PT_omni_bake_panel, OmniBakePreferences)
from .particle_bake.operators import(MyProperties, PARTICLES_OT_omni_hair_bake)

from .material_bake import baker

from .workflow import usd_kind

classes = [
    OBJECT_OT_omni_bake_mapbake,
    OBJECT_PT_omni_panel,
    OBJECT_PT_omni_bake_panel,
    OmniBakePreferences,
    OBJECT_OT_omni_bake_bgbake_status,
    OBJECT_OT_omni_bake_bgbake_import,
    OBJECT_OT_omni_bake_bgbake_clear,
    MyProperties,
    PARTICLES_OT_omni_hair_bake,
]


def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

#---------------------UPDATE FUNCTIONS--------------------------------------------
def prepmesh_update(self, context):
    if context.scene.prepmesh == False:
        context.scene.hidesourceobjects = False
    else:
        context.scene.hidesourceobjects = True

def texture_res_update(self, context):
    if context.scene.texture_res == "0.5k":
        context.scene.imgheight = 1024/2
        context.scene.imgwidth = 1024/2
        context.scene.render.bake.margin = 6

    elif context.scene.texture_res == "1k":
        context.scene.imgheight = 1024
        context.scene.imgwidth = 1024
        context.scene.render.bake.margin = 10
        
    elif context.scene.texture_res == "2k":
        context.scene.imgheight = 1024*2
        context.scene.imgwidth = 1024*2
        context.scene.render.bake.margin = 14
        
    elif context.scene.texture_res == "4k":
        context.scene.imgheight = 1024*4
        context.scene.imgwidth = 1024*4
        context.scene.render.bake.margin = 20

    elif context.scene.texture_res == "8k":
        context.scene.imgheight = 1024*8
        context.scene.imgwidth = 1024*8
        context.scene.render.bake.margin = 32

def newUVoption_update(self, context):
    if bpy.context.scene.newUVoption == True:
        bpy.context.scene.prefer_existing_sbmap = False

def all_maps_update(self,context):
    bpy.context.scene.selected_col = True
    bpy.context.scene.selected_metal = True
    bpy.context.scene.selected_rough = True
    bpy.context.scene.selected_normal = True
    bpy.context.scene.selected_trans = True
    bpy.context.scene.selected_transrough = True
    bpy.context.scene.selected_emission = True
    bpy.context.scene.selected_specular = True
    bpy.context.scene.selected_alpha = True
    bpy.context.scene.selected_sss = True
    bpy.context.scene.selected_ssscol = True


#-------------------END UPDATE FUNCTIONS----------------------------------------------

def register():
    # usd_kind.register()
    baker.register()

    for cls in classes:
        bpy.utils.register_class(cls)
    
    global bl_info
    version = bl_info["version"]
    version = str(version[0]) + str(version[1]) + str(version[2])
    
    OBJECT_PT_omni_bake_panel.version = f"{str(version[0])}.{str(version[1])}.{str(version[2])}"
    
    
    #Global variables
    
    des = "Texture Resolution"
    bpy.types.Scene.texture_res = bpy.props.EnumProperty(name="Texture Resolution", default="1k", description=des,
                                                         items=[
                                                        ("0.5k", "0.5k", f"Texture Resolution of {1024/2} x {1024/2}"),
                                                        ("1k", "1k", f"Texture Resolution of 1024 x 1024"),
                                                        ("2k", "2k", f"Texture Resolution of {1024*2} x {1024*2}"),
                                                        ("4k", "4k", f"Texture Resolution of {1024*4} x {1024*4}"),
                                                        ("8k", "8k", f"Texture Resolution of {1024*8} x {1024*8}")
                                                        ],
                                                         update = texture_res_update)

    des = "Distance to cast rays from target object to selected object(s)"
    bpy.types.Scene.ray_distance = bpy.props.FloatProperty(name="Ray Distance", default = 0.2, description=des)
    bpy.types.Scene.ray_warning_given = bpy.props.BoolProperty(default = False)

    #--- MAPS -----------------------
    bpy.types.Scene.omnibake_error = bpy.props.StringProperty(default="")

    des = "Bake all maps (Diffuse, Metal, SSS, SSS Col. Roughness, Normal, Transmission, Transmission Roughness, Emission, Specular, Alpha, Displacement)"
    bpy.types.Scene.all_maps = bpy.props.BoolProperty(name="Bake All Maps", default = True, description=des, update = all_maps_update)

    des = "Bake a PBR Colour map"
    bpy.types.Scene.selected_col = bpy.props.BoolProperty(name="Diffuse", default = True, description=des)
    des = "Bake a PBR Metalness map"
    bpy.types.Scene.selected_metal = bpy.props.BoolProperty(name="Metal", description=des, default= True)
    des = "Bake a PBR Roughness or Glossy map"
    bpy.types.Scene.selected_rough = bpy.props.BoolProperty(name="Roughness", description=des, default= True)
    des = "Bake a Normal map"
    bpy.types.Scene.selected_normal = bpy.props.BoolProperty(name="Normal", description=des, default= True)
    des = "Bake a PBR Transmission map"
    bpy.types.Scene.selected_trans = bpy.props.BoolProperty(name="Transmission", description=des, default= True)
    des = "Bake a PBR Transmission Roughness map"
    bpy.types.Scene.selected_transrough = bpy.props.BoolProperty(name="TR Rough", description=des, default= True)
    des = "Bake an Emission map"
    bpy.types.Scene.selected_emission = bpy.props.BoolProperty(name="Emission", description=des, default= True)
    des = "Bake a Subsurface map"
    bpy.types.Scene.selected_sss = bpy.props.BoolProperty(name="SSS", description=des, default= True)
    des = "Bake a Subsurface colour map"
    bpy.types.Scene.selected_ssscol = bpy.props.BoolProperty(name="SSS Col", description=des, default= True)
    des = "Bake a Specular/Reflection map"
    bpy.types.Scene.selected_specular = bpy.props.BoolProperty(name="Specular", description=des, default= True)
    des = "Bake a PBR Alpha map"
    bpy.types.Scene.selected_alpha = bpy.props.BoolProperty(name="Alpha", description=des, default= True)
 
    #------------------------------------------UVs-----------------------------------------
    
    des = "Use Smart UV Project to create a new UV map for your objects (or target object if baking to a target). See Blender Market FAQs for more details"
    bpy.types.Scene.newUVoption = bpy.props.BoolProperty(name="New UV(s)", description=des, update=newUVoption_update, default= False)
    des = "If one exists for the object being baked, use any existing UV maps called 'OmniBake' for baking (rather than the active UV map)"
    bpy.types.Scene.prefer_existing_sbmap = bpy.props.BoolProperty(name="Prefer existing UV maps called OmniBake", description=des)
    
    des = "New UV Method"
    bpy.types.Scene.newUVmethod = bpy.props.EnumProperty(name="New UV Method", default="SmartUVProject_Individual", description=des, items=[
    ("SmartUVProject_Individual", "Smart UV Project (Individual)", "Each object gets a new UV map using Smart UV Project")])

    des = "Margin between islands to use for Smart UV Project"
    bpy.types.Scene.unwrapmargin = bpy.props.FloatProperty(name="Margin", default=0.03, description=des, min=0.0, step=0.01)

    des = "Bake to normal UVs"
    bpy.types.Scene.uv_mode = bpy.props.EnumProperty(name="UV Mode", default="normal", description=des, items=[
    ("normal", "Normal", "Normal UV maps")])
    
    #--------------------------------Prep/CleanUp----------------------------------

    des = "Create a copy of your selected objects in Blender (or target object if baking to a target) and apply the baked textures to it. If you are baking in the background, this happens after you import"
    bpy.types.Scene.prepmesh = bpy.props.BoolProperty(name="Copy objects and apply bakes", default = True, description=des, update=prepmesh_update)
    des = "Hide the source object that you baked from in the viewport after baking. If you are baking in the background, this happens after you import"
    bpy.types.Scene.hidesourceobjects = bpy.props.BoolProperty(name="Hide source objects after bake", default = True, description=des)
        
    des = "Set the height of the baked image that will be produced"
    bpy.types.Scene.imgheight = bpy.props.IntProperty(name="Height", default=1024, description=des)
    des = "Set the width of the baked image that will be produced"
    bpy.types.Scene.imgwidth = bpy.props.IntProperty(name="Width", default=1024, description=des)
    
    des="Name to apply to these bakes (is incorporated into the bakes file name, provided you have included this in the image format string - see addon preferences). NOTE: To maintain compatibility, only MS Windows acceptable characters will be used"
    bpy.types.Scene.batchName = bpy.props.StringProperty(name="Batch name", description=des, default="Bake1", maxlen=20)
    
    #---------------------Where To Bake?-------------------------------------------

    bpy.types.Scene.bgbake = bpy.props.EnumProperty(name="Background Bake", default="fg", items=[
    ("fg", "Foreground", "Perform baking in the foreground. Blender will lock up until baking is complete"),
    ("bg", "Background", "Perform baking in the background, leaving you free to continue to work in Blender while the baking is being carried out")
    ])

    #---------------------Filehanding & Particles------------------------------------------
    
    bpy.types.Scene.particle_options = bpy.props.PointerProperty(type= MyProperties)

    #-------------------Additional Shaders-------------------------------------------

    des = "Allows for use of Add, Diffuse, Glossy, Glass, Refraction, Transparent, Anisotropic Shaders. May cause inconsistent results"
    bpy.types.Scene.more_shaders = bpy.props.BoolProperty(name="Use Additional Shader Types", default=False, description=des)
    


def unregister():
    # usd_kind.unregister()
    baker.unregister()

    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.particle_options
    del bpy.types.Scene.more_shaders

    del bpy.types.Scene.newUVoption
    del bpy.types.Scene.prepmesh
    del bpy.types.Scene.unwrapmargin
    del bpy.types.Scene.texture_res
    del bpy.types.Scene.hidesourceobjects
    del bpy.types.Scene.batchName
    del bpy.types.Scene.bgbake
    
    del bpy.types.Scene.imgheight
    del bpy.types.Scene.imgwidth