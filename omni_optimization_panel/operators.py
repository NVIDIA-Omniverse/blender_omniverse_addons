
# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.

import os
import subprocess
import time

from typing import *
from importlib import reload

import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty)
from bpy.types import (Context, Event, Object, Modifier, NodeTree, Scene)
from mathutils import Vector

from .properties import (OmniSceneOptChopPropertiesMixin, chopProperties)

## ======================================================================
symmetry_axis_items = [
	("X", "X", "X"),
	("Y", "Y", "Y"),
	("Z", "Z", "Z")
]

generate_type_items = [
	("CONVEX_HULL",  "Convex Hull",  "Convex Hull"),
	("BOUNDING_BOX", "Bounding Box", "Bounding Box")
]

generate_name = "OmniSceneOptGenerate"


## ======================================================================
def selected_meshes(scene:Scene) -> List[Object]:
	result = [x for x in scene.collection.all_objects if x.type == "MESH" and x.select_get()]
	return result


def get_plural_count(items) -> (str, int):
	count = len(items)
	plural = '' if count == 1 else 's'
	return plural, count


## ======================================================================
def preserve_selection(func, *args, **kwargs):
	def wrapper(*args, **kwargs):
		selection = [x.name for x in bpy.context.selected_objects]
		active = bpy.context.active_object.name if bpy.context.active_object else None
		result = func(*args, **kwargs)

		scene_objects = bpy.context.scene.objects
		to_select = [ scene_objects[x] for x in selection if x in scene_objects ]
		if active:
			active = scene_objects[active] if active in scene_objects else (to_select[-1] if len(to_select) else None)

		bpy.ops.object.select_all(action="DESELECT")
		for item in to_select:
			item.select_set(True)
		bpy.context.view_layer.objects.active = active

		return result
	return wrapper


## ======================================================================
class OmniSceneOptPropertiesMixin:
	"""
	Blender Properties that are shared between the in-scene preferences pointer
	and the various operators.
	"""
	verbose: BoolProperty(name="Verbose",
						   description="Print information while running",
						   default=False)

	selected: BoolProperty(name="Selected",
						   description="Run on Selected Objects (if False, run on whole Scene)",
						   default=False)

	## export options
	export_textures: BoolProperty(name="Export Textures",
						   description="Export textures when doing a background export",
						   default=True)

	## these are deliberate copies from ui.OmniYes.Properties
	validate: BoolProperty(name="Validate Meshes",
						   description="Attempt to remove invalid geometry",
						   default=True)

	weld: BoolProperty(name="Weld Verts",
					   description="Weld loose vertices",
					   default=False)
	weld_distance: FloatProperty(name="Weld Distance",
								 description="Distance threshold for welds",
								 default=0.0001,
								 min=0.00001,
								 step=0.00001)

	unwrap: BoolProperty(name="Unwrap Mesh UVs",
						 description="Use the Smart Unwrap feature to add new UVs",
						 default=False)
	unwrap_margin: FloatProperty(name="Margin",
								 description="Distance between UV islands",
								 default=0.00,
								 min=0.0,
								 step=0.01)

	decimate: BoolProperty(name="Decimate",
						   description="Reduce polygon and vertex counts on meshes",
						   default=False)
	decimate_ratio: IntProperty(name="Ratio",
								subtype="PERCENTAGE",
								description="Reduce face count to this percentage of original",
								default=50,
								min=10, max=100,
								step=5)
	decimate_use_symmetry: BoolProperty(name="Use Symmetry",
										description="Decimate with Symmetry across an axis",
										default=False)
	decimate_symmetry_axis: EnumProperty(name="Symmetry Axis",
										 description="Axis for symmetry",
										 items=symmetry_axis_items,
										 default="X")
	decimate_min_face_count: IntProperty(name="Minimum Face Count",
										 description="Do not decimate objects with less faces",
										 default=500,
										 min=100,
										 step=10)

	decimate_remove_shape_keys: BoolProperty(name="Remove Shape Keys",
										 description="Remove shape keys to allow meshes with shapes to be decimated",
										 default=False)

	chop: BoolProperty(name="Chop Meshes",
					   description="Physically divide meshes based on size and point count",
					   default=False)

	generate: BoolProperty(name="Generate",
						   description="Generate convex hulls or bounding boxes",
						   default=False)

	merge: BoolProperty(name="Merge Selected",
						description="On Export, merge selected meshes into a single object",
						default=False)


## ======================================================================
class OmniSceneOptGeneratePropertiesMixin:
	generate_duplicate: BoolProperty(name="Create Duplicate",
									 description="Generate a new object instead of replacing the original",
									 default=True)

	generate_type: EnumProperty(name="Generate Type",
								description="Type of geometry to generate",
								items=generate_type_items,
								default="CONVEX_HULL")


## ======================================================================
"""
This is a weird one.

The decimate modifier was failing on multiple objects in order, but
wrapping it in an Operator seems to fix the issues with making sure
the correct things are selected in the Context.
"""

class OBJECT_OT_omni_sceneopt_decimate(bpy.types.Operator, OmniSceneOptPropertiesMixin):
	"""Decimates the selected object using the Decimation modifier."""
	bl_idname  = "omni_sceneopt.decimate"
	bl_label   = "Omni Scene Optimization: Decimate"
	bl_options = {"REGISTER", "UNDO"}

	ratio: IntProperty(name="Ratio",
						subtype="PERCENTAGE",
						description="Reduce face count to this percentage of original",
						default=50,
						min=10, max=100,
						step=5)
	use_symmetry: BoolProperty(name="Use Symmetry",
								description="Decimate with Symmetry across an axis",
								default=True)
	symmetry_axis: EnumProperty(name="Symmetry Axis",
								 description="Axis for symmetry",
								 items=symmetry_axis_items,
								 default="X")
	min_face_count: IntProperty(name="Minimum Face Count",
								 description="Do not decimate objects with less faces",
								 default=500,
								 min=100,
								 step=10)

	@classmethod
	def poll(cls, context:Context) -> bool:
		return bool(context.active_object)

	def execute(self, context:Context) -> Set[str]:
		from .batch import lod

		result = lod.decimate_object(context.active_object,
									 ratio=self.ratio / 100.0,
									 use_symmetry=self.use_symmetry,
									 symmetry_axis=self.symmetry_axis,
									 min_face_count=self.min_face_count,
									 create_duplicate=False)
		return {"FINISHED"}


## ======================================================================
class OmniOverrideMixin:

	def set_active(self, ob:Object):
		try:
			bpy.context.view_layer.objects.active = ob
		except RuntimeError as e:
			print(f"-- unable to set active: {ob.name} ({e}")

	def override(self, objects:List[Object], single=False):
		assert isinstance(objects, (list, tuple)), "'objects' is expected to be a list or tuple"
		assert len(objects), "'objects' cannot be empty"

		## filter out objects not in current view layer
		objects = list(filter(lambda x: x.name in bpy.context.view_layer.objects, objects))

		if single:
			objects = objects[0:1]

		override = {
			'active_object': objects[0],
			'edit_object': None,
			'editable_objects': objects,
			'object': objects[0],
			'objects_in_mode': [],
			'objects_in_mode_unique_data': [],
			'selectable_objects': objects,
			'selected_editable_objects': objects,
			'selected_objects': objects,
			'visible_objects': objects,
		}

		self.set_active(objects[0])
		return bpy.context.temp_override(**override)

	def edit_override(self, objects:List[Object], single=False):
		assert isinstance(objects, (list, tuple)), "'objects' is expected to be a list or tuple"
		assert len(objects), "'objects' cannot be empty"

		if single:
			objects = objects[0:1]

		override = {
			'active_object': objects[0],
			'edit_object': objects[0],
			'editable_objects': objects,
			'object': objects[0],
			'objects_in_mode': objects,
			'objects_in_mode_unique_data': objects,
			'selectable_objects': objects,
			'selected_editable_objects': objects,
			'selected_objects': objects,
			'visible_objects': objects,
		}

		self.set_active(objects[0])
		return bpy.context.temp_override(**override)



## ======================================================================
class OBJECT_OT_omni_sceneopt_optimize(bpy.types.Operator,
									   OmniSceneOptPropertiesMixin,
									   OmniSceneOptChopPropertiesMixin,
									   OmniSceneOptGeneratePropertiesMixin,
									   OmniOverrideMixin):
	"""Run specified optimizations on the scene or on selected objects."""

	bl_idname  = "omni_sceneopt.optimize"
	bl_label   = "Omni Scene Optimization: Optimize Scene"
	bl_options = {"REGISTER", "UNDO"}

	# def draw(self, context:Context):
	# 	"""Empty draw to disable the Operator Props Panel."""
	# 	pass

	def _object_mode(self):
		if not bpy.context.mode == "OBJECT":
			bpy.ops.object.mode_set(mode="OBJECT")

	def _edit_mode(self):
		if not bpy.context.mode == "EDIT_MESH":
			bpy.ops.object.mode_set(mode="EDIT")

	@staticmethod
	def _remove_shape_keys(ob:Object):
		assert ob.type == "MESH", "Cannot be run on non-Mesh Objects."
		## Reversed because we want to remove Basis last, or we will end up
		## with garbage baked in.
		for key in reversed(ob.data.shape_keys.key_blocks):
			ob.shape_key_remove(key)

	@staticmethod
	def _select_one(ob:Object):
		bpy.ops.object.select_all(action="DESELECT")
		ob.select_set(True)
		bpy.context.view_layer.objects.active = ob

	@staticmethod
	def _select_objects(objects:List[Object]):
		bpy.ops.object.select_all(action="DESELECT")
		for item in objects:
			item.select_set(True)
		bpy.context.view_layer.objects.active = objects[-1]

	@staticmethod
	def _get_evaluated(objects:List[Object]) -> List[Object]:
		deps = bpy.context.evaluated_depsgraph_get()
		return [x.evaluated_get(deps).original for x in objects]

	@staticmethod
	def _total_vertex_count(target_objects:List[Object]):
		deps = bpy.context.evaluated_depsgraph_get()
		eval_objs = [x.evaluated_get(deps) for x in target_objects]
		return sum([len(x.data.vertices) for x in eval_objs])

	def do_validate(self, target_objects:List[Object]) -> List[Object]:
		"""Expects to be run in Edit Mode with all meshes selected"""
		total_orig = self._total_vertex_count(target_objects)

		bpy.ops.mesh.select_all(action="SELECT")
		bpy.ops.mesh.dissolve_degenerate()

		total_result = self._total_vertex_count(target_objects)

		if self.verbose:
			plural, obj_count = get_plural_count(target_objects)
			message = f"Validated {obj_count} object{plural}."
			self.report({"INFO"}, message)

		return target_objects

	def do_weld(self, target_objects:List[Object]) -> List[Object]:
		"""Expects to be run in Edit Mode with all meshes selected"""
		bpy.ops.mesh.remove_doubles(threshold=self.weld_distance, use_unselected=True)
		bpy.ops.mesh.normals_make_consistent(inside=False)

		return target_objects

	def do_unwrap(self, target_objects:List[Object]) -> List[Object]:
		bpy.ops.object.select_all(action="DESELECT")
		start = time.time()

		for item in target_objects:
			with self.edit_override([item]):
				bpy.ops.object.mode_set(mode="EDIT")
				bpy.ops.mesh.select_all(action="SELECT")
				bpy.ops.uv.smart_project(island_margin=0.0)
				bpy.ops.uv.select_all(action="SELECT")
				# bpy.ops.uv.average_islands_scale()
				# bpy.ops.uv.pack_islands(margin=self.unwrap_margin)
				bpy.ops.object.mode_set(mode="OBJECT")

		end = time.time()

		if self.verbose:
			plural, obj_count = get_plural_count(target_objects)
			message = f"Unwrapped {obj_count} object{plural} ({end-start:.02f} seconds)."
			self.report({"INFO"}, message)

		return target_objects

	def do_decimate(self, target_objects:List[Object]) -> List[Object]:
		assert bpy.context.mode == "OBJECT", "Decimate must be run in object mode."
		total_orig = self._total_vertex_count(target_objects)
		total_result = 0

		start = time.time()

		for item in target_objects:
			if item.data.shape_keys and len(item.data.shape_keys.key_blocks):
				if not self.decimate_remove_shape_keys:
					self.report({"WARNING"}, f"[ Decimate ] Skipping {item.name} because it has shape keys.")
					continue
				else:
					self._remove_shape_keys(item)

			if len(item.data.polygons) < self.decimate_min_face_count:
				self.report({"INFO"}, f"{item.name} is under face count-- not decimating.")
				continue

			## We're going to use the decimate modifier
			mod = item.modifiers.new("OmniLOD", type="DECIMATE")
			mod.decimate_type = "COLLAPSE"
			mod.ratio = self.decimate_ratio / 100.0
			mod.use_collapse_triangulate = True
			mod.use_symmetry = self.decimate_use_symmetry
			mod.symmetry_axis = self.decimate_symmetry_axis

			## we don't need a full context override here
			self.set_active(item)
			bpy.ops.object.modifier_apply(modifier=mod.name)

			total_result += len(item.data.vertices)

		end = time.time()

		if self.verbose:
			plural, obj_count = get_plural_count(target_objects)
			message = f"Decimated {obj_count} object{plural}. Vertex count original {total_orig} to {total_result} ({end-start:.02f} seconds)."
			self.report({"INFO"}, message)

		return target_objects

	def do_chop(self, target_objects:List[Object]):
		"""
		Assumes all objects are selected and that we are in Object mode
		"""
		assert bpy.context.mode == "OBJECT", "Chop must be run in object mode."
		scene = bpy.context.scene
		attributes = scene.omni_sceneopt_chop.attributes()
		attributes["selected_only"] = self.selected
		bpy.ops.omni_sceneopt.chop(**attributes)
		return target_objects

	def do_generate(self, target_objects:List[Object]):
		with self.override(target_objects):
			bpy.ops.omni_sceneopt.generate(generate_type=self.generate_type,
										 generate_duplicate=self.generate_duplicate)
		return target_objects

	def execute(self, context:Context) -> Set[str]:
		start = time.time()

		active = context.active_object
		if self.selected:
			targets = selected_meshes(context.scene)
		else:
			targets = [x for x in context.scene.collection.all_objects if x.type == "MESH"]
			bpy.ops.object.select_all(action="DESELECT")
			[ x.select_set(True) for x in targets ]

		if active:
			self.set_active(active)

		if not len(targets):
			self.info({"ERROR"}, "No targets specified.")
			return {"CANCELLED"}

		self._object_mode()

		## Have to do vertex counts outside edit mode!
		total_orig = self._total_vertex_count(targets)

		if self.validate or self.weld:
			with self.edit_override(targets):
				bpy.ops.object.mode_set(mode="EDIT")
				## We can run these two operations together because they don't collide
				## or cause issues between each other.
				if self.validate:
					self.do_validate(targets)

				if self.weld:
					self.do_weld(targets)

			## Unfortunately, the rest are object-by-object operations
			self._object_mode()

		total_result = self._total_vertex_count(targets)

		if self.verbose and self.weld:
			plural, obj_count = get_plural_count(targets)
			message = f"Welded {obj_count} object{plural}. Vertex count original {total_orig} to {total_result}."
			self.report({"INFO"}, message)

		if self.unwrap:
			self.do_unwrap(targets)

		if self.decimate:
			self.do_decimate(targets)

		if self.chop:
			self.do_chop(targets)

		if self.generate:
			self.do_generate(targets)

		end = time.time()

		if self.verbose:
			self.report({"INFO"}, f"Optimization complete-- process took {end-start:.02f} seconds")

		return {"FINISHED"}


## ======================================================================
class OBJECT_OT_omni_sceneopt_chop(bpy.types.Operator, OmniSceneOptChopPropertiesMixin):
	"""Chop the specified object into a grid of smaller ones"""
	bl_idname  = "omni_sceneopt.chop"
	bl_label   = "Omni Scene Optimizer: Chop"
	bl_options = {"REGISTER", "UNDO"}

	# def draw(self, context:Context):
	# 	"""Empty draw to disable the Operator Props Panel."""
	# 	pass

	def execute(self, context:Context) -> Set[str]:
		attributes = dict(
			merge=self.merge,
			cut_meshes=self.cut_meshes,
			max_vertices=self.max_vertices,
			min_box_size=self.min_box_size,
			max_depth=self.max_depth,
			print_updated_results=self.print_updated_results,
			create_bounds=self.create_bounds,
			selected_only=self.selected_only
		)

		from .scripts.chop import Chop
		chopper = Chop()
		chopper.execute(self.attributes())

		return {"FINISHED"}


## ======================================================================
class OBJECT_OT_omni_sceneopt_generate(bpy.types.Operator, OmniSceneOptGeneratePropertiesMixin, OmniOverrideMixin):
	"""Generate geometry based on selected objects. Currently supported: Bounding Box, Convex Hull"""
	bl_idname  = "omni_sceneopt.generate"
	bl_label   = "Omni Scene Optimizer: Generate"
	bl_options = {"REGISTER", "UNDO"}

	# def draw(self, context:Context):
	# 	"""Empty draw to disable the Operator Props Panel."""
	# 	pass

	def create_geometry_nodes_group(self, group:NodeTree):
		"""Create or return the shared Generate node group."""
		node_type = {
			"CONVEX_HULL":  "GeometryNodeConvexHull",
			"BOUNDING_BOX": "GeometryNodeBoundBox",
		}[self.generate_type]

		geometry_input = group.nodes["Group Input"]
		geometry_input.location = Vector((-1.5 * geometry_input.width, 0))

		group_output = group.nodes["Group Output"]
		group_output.location = Vector((1.5 * group_output.width, 0))

		node = group.nodes.new(node_type)
		node.name = "Processor"

		group.links.new(geometry_input.outputs['Geometry'], node.inputs['Geometry'])
		group.links.new(node.outputs[0], group_output.inputs['Geometry'])

		return bpy.data.node_groups[generate_name]

	def create_geometry_nodes_modifier(self, ob:Object) -> Modifier:
		if generate_name in ob.modifiers:
			ob.modifiers.remove(ob.modifiers[generate_name])

		if generate_name in bpy.data.node_groups:
			bpy.data.node_groups.remove(bpy.data.node_groups[generate_name])

		mod = ob.modifiers.new(name=generate_name, type="NODES")
		bpy.ops.node.new_geometry_node_group_assign()
		mod.node_group.name = generate_name

		self.create_geometry_nodes_group(mod.node_group)

		return mod

	def create_duplicate(self, ob:Object, token:str) -> Object:
		from .batch import lod
		duplicate = lod.duplicate_object(ob, token, weld=False)
		return duplicate

	@preserve_selection
	def apply_modifiers(self, target_objects:List[Object]):
		count = 0
		for item in target_objects:
			if self.generate_duplicate:
				token = self.generate_type.rpartition("_")[-1]
				duplicate = self.create_duplicate(item, token=token)
				duplicate.parent = item.parent
				duplicate.matrix_world = item.matrix_world.copy()
				bpy.context.scene.collection.objects.unlink(duplicate)
				for collection in item.users_collection:
					collection.objects.link(duplicate)
				item = duplicate

			with self.override([item]):
				mod = self.create_geometry_nodes_modifier(item)
				bpy.context.view_layer.objects.active = item
				item.select_set(True)
				bpy.ops.object.modifier_apply(modifier=mod.name)

			count += 1

	def execute(self, context:Context) -> Set[str]:
		changed = self.apply_modifiers(context.selected_objects)
		if changed:
			group = bpy.data.node_groups["OMNI_SCENEOPT_GENERATE"]
			bpy.data.node_groups.remove(group)
		return {"FINISHED"}


## ======================================================================
class OBJECT_OT_omni_progress(bpy.types.Operator):
	bl_idname  = "omni.progress"
	bl_label   = "Export Optimized USD"
	bl_options = {"REGISTER", "UNDO"}

	message: StringProperty(name="message",
							description="Message to print upon completion.",
							default="")

	_timer = None

	def modal(self, context:Context, event:Event) -> Set[str]:
		if context.scene.omni_progress_active is False:
			message = self.message.strip()
			if len(message):
				self.report({"INFO"}, message)
			return {"FINISHED"}

		context.area.tag_redraw()

		context.window.cursor_set("WAIT")
		return {"RUNNING_MODAL"}

	def invoke(self, context:Context, event:Event) -> Set[str]:
		context.scene.omni_progress_active = True
		self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
		context.window_manager.modal_handler_add(self)
		context.window.cursor_set("WAIT")
		return {"RUNNING_MODAL"}


## ======================================================================
class OBJECT_OT_omni_sceneopt_export(bpy.types.Operator,
									 OmniSceneOptPropertiesMixin,
									 OmniSceneOptChopPropertiesMixin,
									 OmniSceneOptGeneratePropertiesMixin):
	"""Runs specified optimizations on the scene before running a USD Export"""
	bl_idname  = "omni_sceneopt.export"
	bl_label   = "Export USD"
	bl_options = {"REGISTER", "UNDO"}

	filepath: StringProperty(subtype="FILE_PATH")
	filter_glob:    StringProperty(default="*.usd;*.usda;*.usdc", options={"HIDDEN"})
	check_existing: BoolProperty(default=True, options={"HIDDEN"})

	def draw(self, context:Context):
		"""Empty draw to disable the Operator Props Panel."""
		pass

	def invoke(self, context:Context, event:Event) -> Set[str]:
		if len(self.filepath.strip()) == 0:
			self.filepath = "untitled.usdc"
		context.window_manager.fileselect_add(self)
		return {"RUNNING_MODAL"}

	def execute(self, context:Context) -> Set[str]:
		output_path = bpy.path.abspath(self.filepath)
		script_path = os.sep.join((os.path.dirname(os.path.abspath(__file__)), "batch", "optimize_export.py"))

		bpy.ops.omni.progress(message=f"Finished background write to {output_path}")

		bpy.ops.wm.save_mainfile()

		command = " ".join([
				'"{}"'.format(bpy.app.binary_path),
				"--background",
				'"{}"'.format(bpy.data.filepath),
				"--python",
				'"{}"'.format(script_path),
				"--",
				'"{}"'.format(output_path)
			])

		print(command)

		subprocess.check_output(command, shell=True)

		context.scene.omni_progress_active = False

		if self.verbose:
			self.report({"INFO"}, f"Exported optimized scene to: {output_path}")

		return {"FINISHED"}


## ======================================================================
classes = [
	OBJECT_OT_omni_sceneopt_decimate,
	OBJECT_OT_omni_sceneopt_chop,
	OBJECT_OT_omni_sceneopt_generate,
	OBJECT_OT_omni_sceneopt_optimize,
	OBJECT_OT_omni_progress,
	OBJECT_OT_omni_sceneopt_export,

	chopProperties
]


def unregister():
	try:
		del bpy.types.Scene.omni_sceneopt_chop
	except AttributeError:
		pass

	try:
		del bpy.types.Scene.omni_progress_active
	except AttributeError:
		pass

	for cls in reversed(classes):
		try:
			bpy.utils.unregister_class(cls)
		except (ValueError, AttributeError, RuntimeError):
			continue



def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	bpy.types.Scene.omni_sceneopt_chop = bpy.props.PointerProperty(type=chopProperties)
	bpy.types.Scene.omni_progress_active = bpy.props.BoolProperty(default=False)
