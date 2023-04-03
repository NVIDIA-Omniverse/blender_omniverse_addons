
# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.

import json
import os
import re
import sys
from typing import *

import numpy as np

import bpy
import bmesh
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty)
from bpy.types import (Collection, Context, Event, Mesh, Object, Scene)

from mathutils import *


## ======================================================================
def _get_filepath(scene:Scene, as_import:bool=False) -> str:
	if as_import:
		result = scene.audio2face.import_filepath.strip()
	else:
		result = scene.audio2face.export_filepath.strip()
	return result


## ======================================================================
def _get_or_create_collection(collection:Collection, name:str) -> Collection:
	"""Find a child collection of the specified collection, or create it if it does not exist."""
	result = collection.children.get(name, None)
	if not result:
		result = bpy.data.collections.new(name)
		collection.children.link(result)

	## Make sure this is visible or things'll break in other ways down the line
	if result.is_evaluated:
		result = result.original
	result.hide_render = result.hide_viewport = result.hide_select = False

	result_lc = [x for x in bpy.context.view_layer.layer_collection.children if x.collection is result]
	if len(result_lc):
		result_lc = result_lc[0]
		result_lc.exclude = False
		result_lc.hide_viewport = False
	else:
		print(f"-- Warning: No layer collection found for {result.name}")
	return result


## ======================================================================
def ensure_scene_collections(scene:Scene) -> Tuple[bpy.types.Collection]:
	"""Make sure that all Audio2Face scene collections exist."""

	a2f_collection = _get_or_create_collection(scene.collection, "Audio2Face")
	a2f_export = _get_or_create_collection(a2f_collection, "A2F Export")
	a2f_export_static = _get_or_create_collection(a2f_export, "A2F Export Static")
	a2f_export_dynamic = _get_or_create_collection(a2f_export, "A2F Export Dynamic")

	return a2f_collection, a2f_export, a2f_export_static, a2f_export_dynamic


## ======================================================================
def _get_base_collection() -> Collection:
	return bpy.data.collections.get("Audio2Face", None)


def _get_import_collection() -> Collection:
	return bpy.data.collections.get("A2F Import", None)


def _get_export_collection() -> Collection:
	return bpy.data.collections.get("A2F Export", None)


## ======================================================================
class OMNI_OT_PrepareScene(bpy.types.Operator):
	"""Prepares the active scene for interaction with Audio2Face"""
	bl_idname = "audio2face.prepare_scene"
	bl_label = "Prepare Scene for Audio2Face"
	bl_options = {"REGISTER", "UNDO"}

	@classmethod
	def poll(cls, context:Context) -> bool:
		return bool(context.scene)

	def execute(self, context:Context) -> Set[str]:
		scene = context.scene
		ensure_scene_collections(scene)

		self.report({"INFO"}, "A2F: Scene is prepped.")

		return {'FINISHED'}


## ======================================================================
def selected_mesh_objects(context:Context) -> List[Object]:
	"""Return a filtered list of Mesh objects from the context."""
	a2f_collection = bpy.data.collections.get("Audio2Face", None)
	export_objects = {x.name for x in a2f_collection.all_objects} if a2f_collection else {}
	result = [x for x in context.selected_objects if x.data and isinstance(x.data, bpy.types.Mesh)]
	result = list(filter(lambda x: not x.name in export_objects and x.data and isinstance(x.data, bpy.types.Mesh), result))
	return result


## ======================================================================
def export_mesh_poll(context:Context) -> bool:
	"""
	Check for a mesh object selection if use_face_selection is false,
	or an edit mode face selection otherwise.
	"""
	valid_mesh = len(selected_mesh_objects(context))
	is_poly_edit_mode = context.tool_settings.mesh_select_mode[2]

	if context.scene.audio2face.use_face_selection:
		if (context.mode == "EDIT_MESH"
			and is_poly_edit_mode
			and valid_mesh
			and len(context.active_object.data.count_selected_items())
			and context.active_object.data.count_selected_items()[2]):
			return True
	else:
		if context.mode == "OBJECT" and valid_mesh:
			return True

	return False


## ======================================================================
def make_valid_name(name:str) -> str:
	result = name.replace("-","_").replace(" ","_").replace(".","_")
	return result


## ======================================================================
def process_export_mesh(orig:Object, target_collection:Collection, is_dynamic:bool, split:bool):
	"""
	Processes the selected mesh for export, adding original vertex
	indices and copying it over into the target collection.
	"""
	assert isinstance(orig.data, bpy.types.Mesh)

	obj_dupe_name = make_valid_name(orig.name) + "__Audio2Face_EX"
	if obj_dupe_name in bpy.data.objects:
		bpy.data.objects.remove(bpy.data.objects[obj_dupe_name])

	mesh_dupe = orig.data.copy()
	mesh_dupe.name = make_valid_name(orig.data.name) + "__Audio2Face_EX"

	obj_dupe = bpy.data.objects.new(obj_dupe_name, mesh_dupe)
	target_collection.objects.link(obj_dupe)
	obj_dupe.a2f_original = orig

	bpy.ops.object.mode_set(mode="OBJECT")

	orig.select_set(False)
	obj_dupe.select_set(True)

	## Clean out all extraneous data.
	for item in obj_dupe.modifiers, obj_dupe.vertex_groups:
		item.clear()

	obj_dupe.shape_key_clear()

	## Add a custom data layer to remember the original point indices.
	attr = obj_dupe.data.attributes.get("index_orig",
										obj_dupe.data.attributes.new("index_orig", "INT", "POINT"))
	vertex_count = len(obj_dupe.data.vertices)
	attr.data.foreach_set("value", np.arange(vertex_count))

	bpy.ops.object.mode_set(mode="OBJECT")

	if split:
		## Delete all unselected faces.
		deps = bpy.context.evaluated_depsgraph_get()

		indices = [x.index for x in orig.data.polygons if not x.select]

		bm = bmesh.new()
		bm.from_object(obj_dupe, deps)
		bm.faces.ensure_lookup_table()

		## Must convert to list; delete does not accept map objects
		selected = list(map(lambda x: bm.faces[x], indices))

		bpy.ops.object.mode_set(mode="EDIT")
		bmesh.ops.delete(bm, geom=selected, context="FACES")

		bpy.ops.object.mode_set(mode="OBJECT")
		bm.to_mesh(obj_dupe.data)

	## Make sure to snap the object into place.
	obj_dupe.matrix_world = orig.matrix_world.copy()

	return obj_dupe


## =====================================================a=================
class OMNI_OT_MarkExportMesh(bpy.types.Operator):
	"""Tags the selected mesh as static for Audio2Face."""
	bl_idname = "audio2face.mark_export_mesh"
	bl_label = "Mark Mesh for Export"
	bl_options = {"REGISTER", "UNDO"}

	is_dynamic: BoolProperty(description="Mesh is Dynamic", default=False)

	@classmethod
	def poll(cls, context:Context) -> bool:
		return export_mesh_poll(context)

	def execute(self, context:Context) -> Set[str]:
		a2f_collection, a2f_export, a2f_export_static, a2f_export_dynamic = ensure_scene_collections(context.scene)
		target_collection = a2f_export_dynamic if self.is_dynamic else a2f_export_static

		split = context.scene.audio2face.use_face_selection

		processed_meshes = []
		for mesh in selected_mesh_objects(context):
			context.view_layer.objects.active = mesh
			result = process_export_mesh(mesh, target_collection, self.is_dynamic, split)
			processed_meshes.append(result)

		context.view_layer.objects.active = processed_meshes[-1]

		return {'FINISHED'}


## ======================================================================
class OMNI_OT_ChooseUSDFile(bpy.types.Operator):
	"""File chooser with proper extensions."""
	bl_idname  = "collections.usd_choose_file"
	bl_label   = "Choose USD File"
	bl_options = {"REGISTER"}

	## Required for specifying extensions.
	filepath:       StringProperty(subtype="FILE_PATH")
	operation:      EnumProperty(items=[("IMPORT", "Import", ""),("EXPORT", "Export", "")], default="IMPORT", options={"HIDDEN"})
	filter_glob:    StringProperty(default="*.usd;*.usda;*.usdc", options={"HIDDEN"})
	check_existing: BoolProperty(default=True, options={"HIDDEN"})

	def execute(self, context:Context):
		real_path = os.path.abspath(bpy.path.abspath(self.filepath))
		real_path = real_path.replace("\\", "/")

		if self.operation == "EXPORT":
			context.scene.audio2face.export_filepath = real_path
		else:
			context.scene.audio2face.import_filepath = real_path

		return {"FINISHED"}

	def invoke(self, context:Context, event:Event) -> Set[str]:
		if len(self.filepath.strip()) == 0:
			self.filepath = "untitled.usdc"
		context.window_manager.fileselect_add(self)
		return {"RUNNING_MODAL"}


## ======================================================================
class OMNI_OT_ChooseAnimCache(bpy.types.Operator):
	"""File chooser with proper extensions."""
	bl_idname  = "collections.usd_choose_anim_cache"
	bl_label   = "Choose Animation Cache"
	bl_options = {"REGISTER"}

	## Required for specifying extensions.
	filepath:       StringProperty(subtype="FILE_PATH")
	filter_glob:    StringProperty(default="*.usd;*.usda;*.usdc;*.json", options={"HIDDEN"})
	check_existing: BoolProperty(default=True, options={"HIDDEN"})

	def execute(self, context:Context):
		real_path = os.path.abspath(bpy.path.abspath(self.filepath))
		real_path = real_path.replace("\\", "/")

		context.scene.audio2face.import_anim_path = real_path

		return {"FINISHED"}

	def invoke(self, context:Context, event:Event) -> Set[str]:
		context.window_manager.fileselect_add(self)
		return {"RUNNING_MODAL"}


## ======================================================================
class OMNI_OT_ExportPreparedScene(bpy.types.Operator):
	"""Exports prepared scene as USD for Audio2Face."""
	bl_idname = "audio2face.export_prepared_scene"
	bl_label = "Export Prepared Scene"
	bl_options = {"REGISTER"}

	@classmethod
	def poll(cls, context:Context) -> bool:
		a2f_export = _get_export_collection()
		child_count = len(a2f_export.all_objects) if a2f_export else 0
		path = _get_filepath(context.scene)
		return a2f_export and child_count and len(path)

	def execute(self, context:Context) -> Set[str]:
		## Grab filepath before the scene switches
		scene = context.scene
		filepath = _get_filepath(scene)

		export_scene = bpy.data.scenes.get("a2f_export",
									bpy.data.scenes.new("a2f_export"))
		for child_collection in list(export_scene.collection.children):
			export_scene.collection.children.remove(child_collection)

		export_collection = _get_export_collection()
		export_scene.collection.children.link(export_collection)
		context.window.scene = export_scene

		args = {
			"filepath": filepath,
			"start": scene.frame_current,
			"end": scene.frame_current,
			"convert_to_cm": False,
			"export_lights": False,
			"export_cameras": False,
			"export_materials": False,
			"export_textures": False,
			"default_prim_path": "/World",
			"root_prim_path": "/World",
		}

		result = bpy.ops.wm.usd_export(**args)

		context.window.scene = scene
		bpy.data.scenes.remove(export_scene)
		export_scene = None

		## generate the project file
		if scene.audio2face.export_project:
			project_filename = os.path.basename(filepath)
			skin   = scene.audio2face.mesh_skin
			tongue = scene.audio2face.mesh_tongue
			eye_left = scene.audio2face.mesh_eye_left
			eye_right= scene.audio2face.mesh_eye_right
			gums = scene.audio2face.mesh_gums_lower

			a2f_export_static = bpy.data.collections.get("A2F Export Static", None)
			static_objects = list(a2f_export_static.objects) if a2f_export_static else []
			a2f_export_dynamic = bpy.data.collections.get("A2F Export Dynamic", None)
			dynamic_objects = list(a2f_export_dynamic.objects) if a2f_export_dynamic else []

			for mesh in skin, tongue:
				if mesh in dynamic_objects:
					dynamic_objects.pop(dynamic_objects.index(mesh))

			for mesh in eye_left, eye_right, gums:
				if mesh in static_objects:
					static_objects.pop(static_objects.index(mesh))

			transfer_data = ""
			if skin:
				transfer_data += '\t\tstring mm:skin = "/World/character_root/{}/{}"\n'.format(make_valid_name(skin.name),
																				make_valid_name(skin.data.name))
			if tongue:
				transfer_data += '\t\tstring mm:tongue = "/World/character_root/{}/{}"\n'.format(make_valid_name(tongue.name),
																				  make_valid_name(tongue.data.name))
			if eye_left:
				transfer_data += '\t\tstring[] mm:l_eye = ["/World/character_root/{}/{}"]\n'.format(make_valid_name(eye_left.name),
																				 make_valid_name(eye_left.data.name))
			if eye_right:
				transfer_data += '\t\tstring[] mm:r_eye = ["/World/character_root/{}/{}"]\n'.format(make_valid_name(eye_right.name),
																				 make_valid_name(eye_right.data.name))
			if gums:
				transfer_data += '\t\tstring[] mm:gums = ["/World/character_root/{}/{}"]\n'.format(make_valid_name(gums.name),
																				make_valid_name(gums.data.name))
			if len(static_objects):
				transfer_data += '\t\tstring[] mm:extra_static = [{}]\n'.format(
					', '.join(['"/World/character_root/{}/{}"'.format(make_valid_name(x.name), make_valid_name(x.data.name))
							   for x in static_objects])
				)
			if len(dynamic_objects):
				transfer_data += '\t\tstring[] mm:extra_dynamic = [{}]\n'.format(
					', '.join(['"/World/character_root/{}/{}"'.format(make_valid_name(x.name), make_valid_name(x.data.name))
							   for x in dynamic_objects])
				)

			template = ""
			template_path = os.sep.join([os.path.dirname(os.path.abspath(__file__)), "templates", "project_template.usda"])
			with open(template_path, "r") as fp:
				template = fp.read()

			template = template.replace("%filepath%", project_filename)
			template = template.replace("%transfer_data%", transfer_data)

			project_usd_filepath = filepath.rpartition(".")[0] + "_project.usda"
			with open(project_usd_filepath, "w") as fp:
				fp.write(template)

			self.report({"INFO"}, f"Exported project to: '{project_usd_filepath}'")
		else:
			self.report({"INFO"}, f"Exported head to: '{filepath}'")

		return result


## ======================================================================
def _abs_path(file_path:str) -> str:
	if not len(file_path) > 2:
		return file_path

	if file_path[0] == '/' and file_path[1] == '/':
		file_path = bpy.path.abspath(file_path)

	return os.path.abspath(file_path)


## ======================================================================
class OMNI_OT_ImportRigFile(bpy.types.Operator):
	"""Imports a rigged USD file from Audio2Face"""
	bl_idname = "audio2face.import_rig"
	bl_label = "Import Rig File"
	bl_options = {"REGISTER", "UNDO"}

	@classmethod
	def poll(cls, context:Context) -> bool:
		return len(_get_filepath(context.scene, as_import=True))

	def execute(self, context:Context) -> Set[str]:
		filepath = _get_filepath(context.scene, as_import=True)
		args = {
			"filepath": filepath,
			"import_skeletons": False,
			"import_materials": False,
		}

		scene = context.scene

		## Switching the active collection requires this odd code.
		base = _get_or_create_collection(scene.collection, "Audio2Face")
		import_col = _get_or_create_collection(base, "A2F Import")
		base_lc = [x for x in context.view_layer.layer_collection.children if x.collection is base][0]
		import_lc = [x for x in base_lc.children if x.collection is import_col][0]
		context.view_layer.active_layer_collection = import_lc

		if not context.mode == 'OBJECT':
			try:
				bpy.ops.object.mode_set(mode="OBJECT")
			except RuntimeError:
				pass

		if len(import_col.all_objects):
			bpy.ops.object.select_all(action="DESELECT")
			## Let's clean out the import collection on each go to keep things simple
			bpy.ops.object.select_same_collection(collection=import_col.name)
			bpy.ops.object.delete()

		## Make sure the import collection is selected so the imported objects
		## get assigned to it.
		# scene.view_layers[0].active_layer_collection.collection = import_col
		bpy.ops.object.select_all(action='DESELECT')

		override = context.copy()
		override["collection"] = bpy.data.collections["A2F Import"]
		result = bpy.ops.wm.usd_import(**args)

		roots = [x for x in import_col.objects if not x.parent]

		for root in roots:
			## bugfix: don't reset rotation, since there may have been a rotation
			## carried over from the blender scene and we want to line up visibly
			## even though it has no bearing on the shape transfer.
			root.scale = [1.0, 1.0, 1.0]

		## Strip out any childless empties, like joint1.
		empties = [x for x in import_col.objects if not len(x.children) and x.type == "EMPTY"]
		for empty in empties:
			bpy.data.objects.remove(empty)

		self.report({"INFO"}, f"Imported Rig from: {filepath}")
		return {"FINISHED"}


## ======================================================================
class AnimData:
	"""Small data holder unifying what's coming in from JSON and USD(A)"""
	def __init__(self, clip_name:str, shapes:List[str], key_data:List[List[float]], start_frame:int=0, frame_rate:float=60.0):
		self.clip_name = clip_name
		self.shapes = shapes
		self.num_frames = len(key_data)
		self.key_data = self._swizzle_data(key_data)
		self.start_frame = start_frame
		self.frame_rate = frame_rate

	def curves(self):
		for index, name in enumerate(self.shapes):
			yield f'key_blocks["{name}"].value', self.key_data[index]

	def _swizzle_data(self, data:List[List[float]]) -> List[List[float]]:
		"""Massage the data a bit for writing directly to the curves"""
		result = []
		for index, _ in enumerate(self.shapes):
			result.append( [data[frame][index] for frame in range(self.num_frames)] )
		return result


class OMNI_OT_ImportAnimation(bpy.types.Operator):
	"""Imports a shape key animation from an Audio2Face USDA file or JSON"""
	bl_idname = "audio2face.import_animation"
	bl_label = "Import Animation"
	bl_options = {"REGISTER", "UNDO"}

	start_type:  EnumProperty(
							name="Start Type",
							items=[("CURRENT", "Current Action", "Load Clip at the playhead"),
								   ("CUSTOM", "Custom", "Choose a custom start frame")],
							default="CURRENT")
	start_frame: IntProperty(default=1, name="Start Frame", description="Align start of animation to this frame")
	frame_rate:  FloatProperty(default=60.0, min=1.0, name="Frame Rate", description="Frame Rate of file you're importing")
	set_range:   BoolProperty(default=False, name="Set Range", description="If checked, set the scene animation frame range to the imported file's range")
	apply_scale: BoolProperty(default=False, name="Apply Clip Scale",
							  description="If checked and the clip framerate differs from the scene, scale the keys to match")
	load_to:     EnumProperty(
					name="Load To",
					description="Load animation to current Action, or to a new Action Clip",
					items=[("CURRENT", "Current Action", "Load curves onto current Action"),
						   ("CLIP", "Clip", "Load curves as a new Action Clip (for NLE use)")],
					default="CURRENT")
	overwrite:   BoolProperty(default=False, name="Overwrite Existing Clips")

	@classmethod
	def poll(cls, context:Context) -> bool:
		have_file = len(context.scene.audio2face.import_anim_path)
		have_mesh = context.active_object and context.active_object.type == "MESH"
		have_selection = context.active_object in context.selected_objects
		is_object_mode = context.mode == "OBJECT"
		return all([have_file, have_mesh, have_selection, is_object_mode])

	def apply_animation(self, animation:AnimData, ob:Object):
		shapes = ob.data.shape_keys
		action = None

		start_frame = bpy.context.scene.frame_current if self.start_type == "CURRENT" else self.start_frame

		if shapes.animation_data is None:
			shapes.animation_data_create()

		nla_tracks = shapes.animation_data.nla_tracks

		if self.load_to == "CLIP":
			def _predicate(track):
				for strip in track.strips:
					if strip.action and strip.action.name == animation.clip_name:
						return True
				return False

			if len(nla_tracks):
				existing_tracks = list(filter(_predicate, nla_tracks))
				if len(existing_tracks) and not self.overwrite:
					self.report({"ERROR"}, f"Clip named {animation.clip_name} already exists; aborting.")
					return False
				else:
					## remove the track(s) specified for overwrites
					for track in existing_tracks:
						self.report({"INFO"}, f"Removing old track {track.name}")
						nla_tracks.remove(track)

			if not animation.clip_name in bpy.data.actions:
				bpy.data.actions.new(animation.clip_name)
			action = bpy.data.actions[animation.clip_name]
			offset = 0
		else:
			if not shapes.animation_data.action:
				bpy.data.actions.new(animation.clip_name)
				action = shapes.animation_data.action = bpy.data.actions[animation.clip_name]
			else:
				action = shapes.animation_data.action
			offset = start_frame

		## clean out old curves
		to_clean = []
		for curve in action.fcurves:
			for name in animation.shapes:
				if f'["{name}"]' in curve.data_path:
					to_clean.append(curve)

		for curve in to_clean:
			action.fcurves.remove(curve)

		scene_framerate = bpy.context.scene.render.fps
		clip_scale = 1.0
		clip_to_scene_scale = scene_framerate / animation.frame_rate
		if self.apply_scale and self.load_to == "CURRENT" and not (int(animation.frame_rate) == int(scene_framerate)):
			clip_scale = clip_to_scene_scale

		for data_path, values in animation.curves():
			curve = action.fcurves.new(data_path)
			curve.keyframe_points.add(len(values))
			for index, value in enumerate(values):
				curve.keyframe_points[index].co = (float(index) * clip_scale + offset, value)

		if self.load_to == "CLIP":
			## I'm really not sure if this is the correct idea, but when loading as clip
			## we push a new NLA_Track and add the action as a strip, then offset it using
			## the strip frame start.
			track = nla_tracks.new()
			track.name = animation.clip_name + "_NLE"
			strip = track.strips.new(animation.clip_name, start_frame, action)
			if self.apply_scale:
				strip.scale = clip_to_scene_scale

			for item in [x for x in nla_tracks if not x == track]:
				item.select = False

			track.select = True

	def load_animation_usda(self, clip_name:str, file_path:str) -> AnimData:
		"""
		Do a quick parse of the input USDA file in plain text, as we can't use the USD Python API yet.
		!TODO: When the USD Python API is available, switch to it instead.
		"""

		with open(file_path, "r") as fp:
			source = fp.read().strip()

			## quick sanity checks; not robust!
			if not all([
					source.startswith("#usda"),
					"framesPerSecond = " in source,
					"uniform token[] blendShapes = [" in source,
					"float[] blendShapeWeights.timeSamples = {" in source,
					"token[] custom:mh_curveNames = [" in source,
					"float[] custom:mh_curveValues.timeSamples = {" in source]):
				self.report({"ERROR"}, f"USDA not a weights animation cache: {file_path}")
				return None

			end_time    = int(source.partition("endTimeCode = ")[-1].partition("\n")[0])
			frame_rate  = int(source.partition("framesPerSecond = ")[-1].partition("\n")[0])
			start_frame = int(source.partition("startTimeCode = ")[-1].partition("\n")[0])

			shape_names = source.partition("uniform token[] blendShapes = [")[-1].partition("]")[0]
			shape_names = shape_names.replace('"','').replace(' ', '').split(',')

			## strip to timeSamples, split lines, then split off the index and parse out the arrays into floats
			samples = source.partition("float[] blendShapeWeights.timeSamples = {")[-1].partition("}")[0].strip().split('\n')
			weights = [list(map(float, x.partition(": [")[-1].rpartition("]")[0].replace(" ", "").split(","))) for x in samples]

			## capture frame rate
			frame_rate = float(source.partition("framesPerSecond = ")[-1].partition("\n")[0])
			return AnimData(clip_name=clip_name, shapes=shape_names, key_data=weights, frame_rate=frame_rate)

	def load_animation_json(self, clip_name:str, file_path:str) -> AnimData:
		assert file_path.lower().endswith(".json")
		file_path = _abs_path(file_path)

		data = None
		with open(file_path, "r") as fp:
			try:
				data = json.load(fp)
			except:
				return None

		if not "facsNames" in data or not "weightMat" in data or not "numFrames" in data:
			self.report({"ERROR"}, f"Malformed JSON file (missing data): {file_path}")
			return None

		if not data["numFrames"] == len(data["weightMat"]):
			self.report({"ERROR"}, f"Malformed JSON: malformed file. Expected {data['numFrames']} frames, found {len(data['weightMat'])} -- {file_path}")
			return None

		return AnimData(clip_name=clip_name, shapes=data["facsNames"], key_data=data["weightMat"],
						frame_rate=self.frame_rate)

	def load_animation(self, file_path:str, ob:Object) -> bool:
		assert ob and isinstance(ob, (bpy.types.Object))
		if not file_path.endswith((".usda", ".json")):
			self.report({"Error"}, f"Path should point to a USDA or JSON file: {file_path}")
			return False

		clip_name = os.path.basename(file_path).partition(".")[0]

		self.report({"INFO"}, f"Loading anim: {file_path}")
		if file_path.endswith(".json"):
			data = self.load_animation_json(clip_name, file_path)
		else:
			data = self.load_animation_usda(clip_name, file_path)

		if data is None:
			self.report({"ERROR"}, f"Unable to load data from file {file_path}")
			return False

		self.apply_animation(data, ob)

		return True

	def execute(self, context:Context) -> Set[str]:
		scene = context.scene
		ob = context.active_object
		if not self.load_animation(scene.audio2face.import_anim_path, ob):
			return {"CANCELLED"}
		return {"FINISHED"}


## ======================================================================
class OMNI_OT_TransferShapeData(bpy.types.Operator):
	"""Transfers shape data from imported rig heads to the original meshes."""
	bl_idname = "audio2face.transfer_shape_data"
	bl_label = "Transfer Shape Data"
	bl_options = {"REGISTER", "UNDO"}

	apply_fix: BoolProperty(name="Apply Fix",
							description="Propate Basis shape to all parts of the mesh not covered by the head, to prevent vertex vomit.",
							default=False)

	@classmethod
	def poll(cls, context:Context) -> bool:
		collection = _get_import_collection()
		if collection is None:
			return False
		meshes = [x.name for x in collection.objects if x.type == "MESH"]
		return bool(len(meshes))

	def _get_collection_meshes(self, collection:Collection) -> List["bpy.data.Mesh"]:
		result = [x for x in collection.all_objects if x.type == "MESH"]
		return result

	def _build_mapping_table(self, import_meshes:Collection, export_meshes:Collection) -> Dict:
		result = {}
		for imported in import_meshes:
			## Intentionally doing the exported data name but the import object name
			## because of how the imports work on both sides.
			token = imported.name.rpartition("__Audio2Face_EX")[0]
			for exported in export_meshes:
				exported_token = exported.data.name.rpartition("__Audio2Face_EX")[0]
				if exported_token == token:
					result[imported] = exported
		return result

	def _transfer_shapes(self, context:Context, source:Object, target:Object, mapping_object:Object) -> int:
		"""
		Transfers shapes from the source mesh to the target.

		:returns: The number of shapes transferred.
		"""
		assert source.data and source.data.shape_keys, "Source object has no shape key data."
		wm = context.window_manager
		result = 0

		## Run these to make sure they're all visible, checked, and in the view layer
		a2f_collection, _, _, _ = ensure_scene_collections(context.scene)
		_get_or_create_collection(a2f_collection, "A2F Import")

		blocks = source.data.shape_keys.key_blocks
		total_shapes = len(blocks)

		if not context.mode == "OBJECT" and context.active_object:
			bpy.ops.object.mode_set(mode="OBJECT")

		bpy.ops.object.select_all(action="DESELECT")
		source.select_set(True)
		target.select_set(True)
		context.view_layer.objects.active = target

		basis = target.data.shape_keys.key_blocks["Basis"]

		wm.progress_begin(0, total_shapes)

		start_index = len(target.data.shape_keys.key_blocks)

		## Grab the mapping array using the new Attributes API.
		mapping_indices = np.zeros(len(source.data.vertices), dtype=np.int32)
		attr = mapping_object.data.attributes['index_orig']
		attr.data.foreach_get("value", mapping_indices)

		for index, block in enumerate(blocks):
			if block.name == "Basis":
				continue

			target.shape_key_add(name=block.name, from_mix=False)
			target_key_block = target.data.shape_keys.key_blocks[block.name]
			target_key_block.relative_key = basis

			for index, target_index in enumerate(mapping_indices):
				target_key_block.data[target_index].co	 = block.data[index].co

			self.report({"INFO"}, f"Transferred shape {block.name} from {source.name} to {target.name}")
			result += 1
			wm.progress_update(index)

		wm.progress_end()

		if self.apply_fix:
			self._select_verts_inverse(target, mapping_indices)

			bpy.ops.object.mode_set(mode="EDIT")

			wm.progress_begin(0, total_shapes)
			for index in range(start_index, start_index+total_shapes-1):
				shape = target.data.shape_keys.key_blocks[index]
				self.report({"INFO"}, f"Fixing shape: {shape.name}")
				target.active_shape_key_index = index
				bpy.ops.mesh.blend_from_shape(shape='Basis', blend=1.0, add=False)
				wm.progress_update(index)

			bpy.ops.object.mode_set(mode="OBJECT")
			wm.progress_end()

		return result

	def _select_verts_inverse(self, ob:Object, mapping_indices:Iterable[int]) -> int:
		"""
		Set the vertex selection of the target object to the inverse of
		what's in mapping_indices through the bmesh API.

		:returns: The number of vertices selected.
		"""
		result = 0
		bm = bmesh.new()
		bm.from_mesh(ob.data)

		for v in bm.verts:
			should_set = not (v.index in mapping_indices)
			v.select_set(should_set)
			result += int(should_set)

		bm.to_mesh(ob.data)

	def _clean_shapes(self, ob:Object, shapes_list:List[str]) -> int:
		"""
		For each named shape, remove it from ob's shape keys.

		:returns: The number of shapes removed
		"""

		self.report({"INFO"}, f"Cleaning {', '.join(shapes_list)}")

		if ob.data.shape_keys is None:
			return 0

		result = 0
		for shape in shapes_list:
			key = ob.data.shape_keys.key_blocks.get(shape)
			if key:
				ob.shape_key_remove(key)
				result +=1

		return result

	def execute(self, context:Context) -> Set[str]:
		## Transfer shape data over automatically
		scene = context.scene

		export_meshes = self._get_collection_meshes(_get_export_collection())
		import_meshes = self._get_collection_meshes(_get_import_collection())

		total = 0
		mapping_table = self._build_mapping_table(import_meshes, export_meshes).items()
		self.report({"INFO"}, f"{mapping_table}")

		for source, mapping_object in mapping_table:
			## hop to the true original mesh
			target = mapping_object.a2f_original

			source_shapes = [x.name for x in source.data.shape_keys.key_blocks if not x.name == "Basis"]
			count = self._clean_shapes(target, source_shapes)
			self.report({"INFO"}, f"Cleaned {count} shape{'' if count == 1 else 's'} from {target.name}")

			## regrab the target object now that it's been modified and we're
			## holding onto an old pointer
			target = mapping_object.a2f_original

			## bugfix: add a Basis target if none exists
			if target.data.shape_keys is None or not "Basis" in target.data.shape_keys.key_blocks:
				target.shape_key_add(name="Basis", from_mix=False)

			result = self._transfer_shapes(context, source, target, mapping_object)
			self.report({"INFO"}, f"Transferred {result} shape{'' if result == 1 else 's'} from {source.name} to {target.name}")
			total += result

		self.report({"INFO"}, f"Transferred {total} total shape{'' if total == 1 else 's'}")
		return {"FINISHED"}
