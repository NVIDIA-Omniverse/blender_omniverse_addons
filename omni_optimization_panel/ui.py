
# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.

import os
from typing import *

import bpy
from bpy.utils import previews
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty)
from bpy.types import (Context, Object, Operator, Scene)

from .operators import (
	OBJECT_OT_omni_sceneopt_optimize,
	OBJECT_OT_omni_sceneopt_export,
	OmniSceneOptPropertiesMixin,
	OmniSceneOptGeneratePropertiesMixin,

	selected_meshes,
	symmetry_axis_items
)


## ======================================================================
def preload_icons() -> previews.ImagePreviewCollection:
	"""Preload icons used by the interface."""

	icons_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
	all_icons = {
		"GEAR": "gear.png",
		"ICON": "ICON.png",
	}

	preview = previews.new()

	for name, filepath in all_icons.items():
		preview.load(name, os.path.join(icons_directory, filepath), "IMAGE")

	return preview


## ======================================================================
class OmniSceneOptProperties(bpy.types.PropertyGroup,
							 OmniSceneOptPropertiesMixin,
							 OmniSceneOptGeneratePropertiesMixin):
	"""We're only here to register the mixins through the PropertyGroup"""
	pass


## ======================================================================
def can_run_optimization(scene:Scene) -> bool:
	if scene.omni_sceneopt.selected and not len(selected_meshes(scene)):
		return False

	has_operations = any((
		scene.omni_sceneopt.validate,
		scene.omni_sceneopt.weld,
		scene.omni_sceneopt.decimate,
		scene.omni_sceneopt.unwrap,
		scene.omni_sceneopt.chop,
		scene.omni_sceneopt.generate,
	))

	if not has_operations:
		return False

	return True


## ======================================================================
class OBJECT_PT_OmniOptimizationPanel(bpy.types.Panel):
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Omniverse"
	bl_label = "Scene Optimizer"
	bl_options = {"DEFAULT_CLOSED"}

	icons = preload_icons()

	@staticmethod
	def _apply_parameters(settings, op:Operator):
		"""Copy parameters from the scene-level settings blob to an operator"""
		invalid = {"bl_rna", "name", "rna_type"}

		for property_name in filter(lambda x: not x[0] == '_' and not x in invalid, dir(settings)):
			if hasattr(op, property_name):
				value = getattr(settings, property_name)
				setattr(op, property_name, value)

		op.verbose = True

	def draw_validate(self, layout, scene: Scene):
		box = layout.box()
		box.prop(scene.omni_sceneopt, "validate")

	def draw_weld(self, layout, scene: Scene):
		box = layout.box()
		box.prop(scene.omni_sceneopt, "weld")

		if not scene.omni_sceneopt.weld:
			return

		box.prop(scene.omni_sceneopt, "weld_distance")

	def draw_decimate(self, layout, scene: Scene):
		box = layout.box()
		box.prop(scene.omni_sceneopt, "decimate")

		if not scene.omni_sceneopt.decimate:
			return

		box.prop(scene.omni_sceneopt, "decimate_ratio")
		box.prop(scene.omni_sceneopt, "decimate_min_face_count")
		row = box.row()
		row.prop(scene.omni_sceneopt, "decimate_use_symmetry")
		row = row.row()
		row.prop(scene.omni_sceneopt, "decimate_symmetry_axis", text="")
		row.enabled = scene.omni_sceneopt.decimate_use_symmetry
		box.prop(scene.omni_sceneopt, "decimate_remove_shape_keys")

	def draw_unwrap(self, layout, scene: Scene):
		box = layout.box()
		box.prop(scene.omni_sceneopt, "unwrap")

		if not scene.omni_sceneopt.unwrap:
			return

		box.prop(scene.omni_sceneopt, "unwrap_margin")

	def draw_chop(self, layout, scene: Scene):
		box = layout.box()
		box.prop(scene.omni_sceneopt, "chop")

		if not scene.omni_sceneopt.chop:
			return

		col = box.column(align=True)
		col.prop(scene.omni_sceneopt_chop, "max_vertices")
		col.prop(scene.omni_sceneopt_chop, "min_box_size")
		col.prop(scene.omni_sceneopt_chop, "max_depth")

		box.prop(scene.omni_sceneopt_chop, "create_bounds")

	def draw_generate(self, layout, scene: Scene):
		box = layout.box()
		box.prop(scene.omni_sceneopt, "generate", text="Generate Bounding Mesh")

		if not scene.omni_sceneopt.generate:
			return

		col = box.column(align=True)
		col.prop(scene.omni_sceneopt, "generate_type")
		col.prop(scene.omni_sceneopt, "generate_duplicate")

	def draw_operators(self, layout, context:Context, scene:Scene):
		layout.label(text="")
		row = layout.row(align=True)
		row.label(text="Run Operations", icon="PLAY")
		row.prop(scene.omni_sceneopt, "selected", text="Selected Meshes Only")

		run_text = f"{'Selected' if scene.omni_sceneopt.selected else 'Scene'}"

		col = layout.column(align=True)
		op = col.operator(OBJECT_OT_omni_sceneopt_optimize.bl_idname,
						  text=f"Optimize {run_text}",
						  icon_value=self.icons["GEAR"].icon_id)
		self._apply_parameters(scene.omni_sceneopt, op)
		col.enabled = can_run_optimization(scene)

		col = layout.column(align=True)
		op = col.operator(OBJECT_OT_omni_sceneopt_export.bl_idname,
						  text=f"Export Optimized Scene to USD",
						  icon='EXPORT')
		self._apply_parameters(scene.omni_sceneopt, op)

		col.label(text="Export Options")
		row = col.row(align=True)
		row.prop(scene.omni_sceneopt, "merge")
		row.prop(scene.omni_sceneopt, "export_textures")

	def draw(self, context:Context):
		scene = context.scene
		layout = self.layout

		self.draw_validate(layout, scene=scene)
		self.draw_weld(layout, scene=scene)
		self.draw_unwrap(layout, scene=scene)
		self.draw_decimate(layout, scene=scene)
		self.draw_chop(layout, scene=scene)
		self.draw_generate(layout, scene=scene)
		self.draw_operators(layout, context, scene=scene)


## ======================================================================
classes = [
	OBJECT_PT_OmniOptimizationPanel,
	OmniSceneOptProperties,
]

def unregister():
	try:
		del bpy.types.Scene.omni_sceneopt
	except (ValueError, AttributeError, RuntimeError):
		pass

	for cls in reversed(classes):
		try:
			bpy.utils.unregister_class(cls)
		except (ValueError, AttributeError, RuntimeError):
			continue


def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	bpy.types.Scene.omni_sceneopt = bpy.props.PointerProperty(type=OmniSceneOptProperties)

