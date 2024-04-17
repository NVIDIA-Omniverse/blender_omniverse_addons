
# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.

import os
from typing import *

import bpy

from omni_audio2face.operators import (
	OMNI_OT_PrepareScene,
	OMNI_OT_MarkExportMesh,
	OMNI_OT_ChooseUSDFile,
	OMNI_OT_ChooseAnimCache,
	OMNI_OT_ExportPreparedScene,
	OMNI_OT_ImportRigFile,
	OMNI_OT_TransferShapeData,
	OMNI_OT_ImportAnimation,
)


## ======================================================================
class OBJECT_PT_Audio2FacePanel(bpy.types.Panel):
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Omniverse"
	bl_label = "Audio2Face"
	bl_options = {"DEFAULT_CLOSED"}

	version = "0.0.0"

	icons = None

	def draw_header(self, context):
		self.layout.label(text="", icon_value=self.icons["AUDIO2FACE"].icon_id)

	# draw the panel
	def draw(self, context):
		use_face_selection = context.scene.audio2face.use_face_selection
		is_poly_edit_mode = context.tool_settings.mesh_select_mode[2] and context.mode == "EDIT_MESH"
		a2f_export_static = bpy.data.collections.get("A2F Export Static", None)
		a2f_export_dynamic = bpy.data.collections.get("A2F Export Dynamic", None)

		layout = self.layout

		layout.label(text="Face Prep and Export", icon="EXPORT")

		row = layout.row(align=True)
		op = row.operator(OMNI_OT_MarkExportMesh.bl_idname, text="Export Static")
		op.is_dynamic = False
		op = row.operator(OMNI_OT_MarkExportMesh.bl_idname, text="Export Dynamic")
		op.is_dynamic = True

		row = layout.row(align=True)
		row.prop(context.scene.audio2face, "use_face_selection", text="")
		if use_face_selection and not is_poly_edit_mode:
			row.label(text="Use Faces: Must be in Polygon Edit Mode!", icon="ERROR")
		else:
			row.label(text="Use Face Selection?")

		## mesh selections
		col = layout.column(align=True)
		if a2f_export_dynamic:
			col.prop_search(context.scene.audio2face, "mesh_skin", a2f_export_dynamic, "objects", text="Skin Mesh: ")
			col.prop_search(context.scene.audio2face, "mesh_tongue", a2f_export_dynamic, "objects", text="Tongue Mesh: ")
		else:
			col.label(text="Dynamic Meshes are required to set Skin and Tongue", icon="ERROR")
			col.label(text=" ")

		if a2f_export_static:
			col.prop_search(context.scene.audio2face, "mesh_eye_left", a2f_export_static, "objects", text="Left Eye Mesh: ")
			col.prop_search(context.scene.audio2face, "mesh_eye_right", a2f_export_static, "objects", text="Right Eye Mesh: ")
			col.prop_search(context.scene.audio2face, "mesh_gums_lower", a2f_export_static, "objects", text="Lower Gums Mesh: ")
		else:
			col.label(text="Static Meshes are required to set Eyes", icon="ERROR")
			col.label(text=" ")

		col = layout.column(align=True)
		row = col.row(align=True)
		row.prop(context.scene.audio2face, "export_filepath", text="Export Path: ")
		op = row.operator(OMNI_OT_ChooseUSDFile.bl_idname, text="", icon="FILE_FOLDER")
		op.operation = "EXPORT"

		col.prop(context.scene.audio2face, "export_project", text="Export With Project File")

		row = col.row(align=True)
		collection = bpy.data.collections.get("A2F Export", None)
		child_count = len(collection.all_objects) if collection else 0
		args = {
			"text": "Export Face USD" if child_count else "No meshes available for Export",
		}
		op = row.operator(OMNI_OT_ExportPreparedScene.bl_idname, **args)

		## Import Side -- after Audio2Face has transferred the shapes
		layout.separator()
		layout.label(text="Face Shapes Import", icon="IMPORT")

		col = layout.column(align=True)
		row = col.row(align=True)
		row.prop(context.scene.audio2face, "import_filepath", text="Shapes Import Path")
		op = row.operator(OMNI_OT_ChooseUSDFile.bl_idname, text="", icon="FILE_FOLDER")
		op.operation = "IMPORT"

		col = layout.column(align=True)
		col.operator(OMNI_OT_ImportRigFile.bl_idname)

		row = col.row(align=True)
		op = row.operator(OMNI_OT_TransferShapeData.bl_idname)
		op.apply_fix = context.scene.audio2face.transfer_apply_fix
		row.prop(context.scene.audio2face, "transfer_apply_fix", icon="MODIFIER", text="")

		col = layout.column(align=True)
		col.label(text="Anim Cache Path")
		row = col.row(align=True)
		row.prop(context.scene.audio2face, "import_anim_path", text="")
		row.operator(OMNI_OT_ChooseAnimCache.bl_idname, text="", icon="FILE_FOLDER")

		if context.scene.audio2face.import_anim_path.lower().endswith(".json"):
			col.prop(context.scene.audio2face, "anim_frame_rate", text="Source Framerate")

		row = col.row(align=True)
		row.prop(context.scene.audio2face, "anim_start_type", text="Start Frame")

		if context.scene.audio2face.anim_start_type == "CUSTOM":
			row.prop(context.scene.audio2face, "anim_start_frame", text="")

		col.prop(context.scene.audio2face, "anim_load_to", text="Load To")

		row = col.row(align=True)
		row.prop(context.scene.audio2face, "anim_apply_scale", text="Apply Clip Scale")
		if context.scene.audio2face.anim_load_to == "CLIP":
			row.prop(context.scene.audio2face, "anim_overwrite")

		op_label = ("Please change to Object Mode" if not context.mode == "OBJECT"
					else ("Import Animation Clip" if OMNI_OT_ImportAnimation.poll(context)
						  else "Please Select Target Mesh"))

		op = col.operator(OMNI_OT_ImportAnimation.bl_idname, text=op_label)
		op.start_type = context.scene.audio2face.anim_start_type
		op.frame_rate = context.scene.audio2face.anim_frame_rate
		op.start_frame = context.scene.audio2face.anim_start_frame
		op.set_range = context.scene.audio2face.anim_set_range
		op.load_to = context.scene.audio2face.anim_load_to
		op.overwrite = context.scene.audio2face.anim_overwrite
		op.apply_scale = context.scene.audio2face.anim_apply_scale


