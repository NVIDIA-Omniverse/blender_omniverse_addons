
# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.

bl_info = {
	"name": "Audio2Face Tools",
	"author": "NVIDIA Corporation",
	"version": (1, 0, 1),
	"blender": (3, 4, 0),
	"location": "View3D > Toolbar > Omniverse",
	"description": "NVIDIA Omniverse tools for working with Audio2Face",
	"warning": "",
	"doc_url": "",
	"category": "Omniverse",
}

## ======================================================================
_previews = None


def __del__(self):
	if self.icons:
		bpy.utils.previews.remove(self.icons)
		self.icons = None


## ======================================================================
import os
from importlib import reload

import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty,
					   IntProperty, PointerProperty, StringProperty)
from bpy.utils import previews

from omni_audio2face import (operators, ui)
for module in (operators, ui):
	reload(module)

from omni_audio2face.ui import OBJECT_PT_Audio2FacePanel
from omni_audio2face.operators import (
	OMNI_OT_PrepareScene,
	OMNI_OT_MarkExportMesh,
	OMNI_OT_ExportPreparedScene,
	OMNI_OT_ChooseUSDFile,
	OMNI_OT_ChooseAnimCache,
	OMNI_OT_ImportRigFile,
	OMNI_OT_TransferShapeData,
	OMNI_OT_ImportAnimation,
)


## ======================================================================
class Audio2FaceToolsSettings(bpy.types.PropertyGroup):
	## shapes stuff
	use_face_selection: BoolProperty(description="Use Face Selection")
	export_project: BoolProperty(description="Export Project File", default=True)
	export_filepath: StringProperty(description="Export Path")
	import_filepath: StringProperty(description="Shapes Import Path")

	## anim import settings
	import_anim_path: StringProperty(description="Anim Cache Path")
	anim_start_type: EnumProperty(
							items=[("CURRENT", "At Play Head", "Load Clip at the playhead"),
								   ("CUSTOM", "Custom", "Choose a custom start frame")],
							default="CURRENT")
	anim_start_frame: IntProperty(default=0)
	anim_frame_rate:  FloatProperty(default=60.0, min=1.0)
	anim_apply_scale: BoolProperty(default=True)
	anim_set_range:   BoolProperty(default=False)
	anim_load_to:     EnumProperty(
							items=[("CURRENT", "Current Action", "Load curves onto current Action"),
								   ("CLIP", "Clip", "Load curves as a new Action for NLE use")],
							default="CURRENT")
	anim_overwrite: BoolProperty(default=False, name="Overwrite Existing Clips")

	## Store pointers to all the meshes for the full setup.
	mesh_skin: PointerProperty(type=bpy.types.Object)
	mesh_tongue: PointerProperty(type=bpy.types.Object)
	mesh_eye_left: PointerProperty(type=bpy.types.Object)
	mesh_eye_right: PointerProperty(type=bpy.types.Object)
	mesh_gums_lower: PointerProperty(type=bpy.types.Object)

	transfer_apply_fix: BoolProperty(name="Apply Fix",
		description="Apply Basis to points not part of the head during transfer",
									 default=False)


## ======================================================================
def preload_icons() -> previews.ImagePreviewCollection:
	"""Preload icons used by the interface."""

	icons_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
	all_icons = {
		"AUDIO2FACE": "omni_audio2face.png",
	}

	preview = previews.new()

	for name, filepath in all_icons.items():
		preview.load(name, os.path.join(icons_directory, filepath), "IMAGE")

	return preview


## ======================================================================
classes = (
	Audio2FaceToolsSettings,

	OBJECT_PT_Audio2FacePanel,

	OMNI_OT_PrepareScene,
	OMNI_OT_MarkExportMesh,
	OMNI_OT_ExportPreparedScene,
	OMNI_OT_ChooseUSDFile,
	OMNI_OT_ChooseAnimCache,
	OMNI_OT_ImportRigFile,
	OMNI_OT_TransferShapeData,
	OMNI_OT_ImportAnimation,
)


def register():
	unregister()

	global _previews
	_previews = preload_icons()

	for item in classes:
		bpy.utils.register_class(item)

	OBJECT_PT_Audio2FacePanel.icons = _previews

	bpy.types.Scene.audio2face = bpy.props.PointerProperty(type=Audio2FaceToolsSettings)
	bpy.types.Object.a2f_original = bpy.props.PointerProperty(type=bpy.types.Object)

	version = bl_info["version"]
	version = str(version[0]) + str(version[1]) + str(version[2])

	OBJECT_PT_Audio2FacePanel.version = f"{str(version[0])}.{str(version[1])}.{str(version[2])}"


## ======================================================================
def unregister():
	# User preferences
	for item in classes:
		try:
			bpy.utils.unregister_class(item)
		except:
			continue

	if hasattr(bpy.types.Scene, "audio2face"):
		del bpy.types.Scene.audio2face
	if hasattr(bpy.types.Object, "a2f_original"):
		del bpy.types.Object.a2f_original

	## icons
	global _previews
	if _previews:
		OBJECT_PT_Audio2FacePanel.icons = None
		bpy.utils.previews.remove(_previews)
		_previews = None
