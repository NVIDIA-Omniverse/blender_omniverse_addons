import argparse
import os
import sys

from typing import *
import bpy
from bpy.types import (Collection, Context, Image, Object, Material,
					   Mesh, Node, NodeSocket, NodeTree, Scene)
from bpy.props import *
from mathutils import *


## ======================================================================
OMNI_MATERIAL_NAME = "OmniUVTestMaterial"


## ======================================================================
def select_only(ob:Object):
	"""
	Ensure that only the specified object is selected.
	:param ob: Object to select
	"""
	bpy.ops.object.select_all(action="DESELECT")
	ob.select_set(state=True)
	bpy.context.view_layer.objects.active = ob


## --------------------------------------------------------------------------------
def _selected_meshes(context:Context) -> List[Mesh]:
	"""
	:return: List[Mesh] of all selected mesh objects in active Blender Scene.
	"""
	return [x for x in context.selected_objects if x.type == "MESH"]


## --------------------------------------------------------------------------------
def get_test_material() -> Material:
	image_name = "OmniUVGrid"
	if not image_name in bpy.data.images:
		bpy.ops.image.new(generated_type="COLOR_GRID", width=4096, height=4096, name=image_name, alpha=False)

	if not OMNI_MATERIAL_NAME in bpy.data.materials:
		image = bpy.data.images[image_name]
		material = bpy.data.materials.new(name=OMNI_MATERIAL_NAME)
		## this creates the new graph
		material.use_nodes = True
		tree = material.node_tree

		shader  = tree.nodes['Principled BSDF']
		im_node = tree.nodes.new("ShaderNodeTexImage")
		im_node.location = [-300, 300]
		tree.links.new(im_node.outputs['Color'], shader.inputs['Base Color'])
		im_node.image = image

	return bpy.data.materials[OMNI_MATERIAL_NAME]


## --------------------------------------------------------------------------------
def apply_test_material(ob:Object):
	##!TODO: Generate it
	select_only(ob)
	while len(ob.material_slots):
		bpy.ops.object.material_slot_remove()

	material = get_test_material()

	bpy.ops.object.material_slot_add()
	ob.material_slots[0].material = material


## --------------------------------------------------------------------------------
def unwrap_object(ob:Object, uv_layer_name="OmniUV", apply_material=False, margin=0.0):
	"""
	Unwraps the target object by creating a fixed duplicate and copying the UVs over
	to the original.
	"""

	old_mode = bpy.context.mode
	scene = bpy.context.scene

	if not old_mode == "OBJECT":
		bpy.ops.object.mode_set(mode="OBJECT")

	select_only(ob)

	uv_layers = list(ob.data.uv_layers)
	for layer in uv_layers:
		ob.data.uv_layers.remove(layer)

	bpy.ops.object.mode_set(mode="EDIT")
	bpy.ops.mesh.select_all(action='SELECT')
	bpy.ops.uv.cube_project()
	bpy.ops.object.mode_set(mode="OBJECT")

	duplicate = ob.copy()
	duplicate.data = ob.data.copy()
	scene.collection.objects.link(duplicate)

	## if the two objects are sitting on each other it gets silly,
	## so move the dupe over by double it's Y bounds size
	bound_size = Vector(duplicate.bound_box[0]) - Vector(duplicate.bound_box[-1])
	duplicate.location.y += bound_size.y

	select_only(duplicate)
	bpy.ops.object.mode_set(mode="EDIT")

	bpy.ops.mesh.select_all(action='SELECT')
	bpy.ops.mesh.remove_doubles(threshold=0.01, use_unselected=True)
	bpy.ops.mesh.normals_make_consistent(inside=True)
	bpy.ops.object.mode_set(mode="OBJECT")
	bpy.ops.object.mode_set(mode="EDIT")
	bpy.ops.uv.select_all(action='SELECT')
	bpy.ops.uv.smart_project(island_margin=margin)
	bpy.ops.uv.average_islands_scale()
	bpy.ops.uv.pack_islands(margin=0)
	bpy.ops.object.mode_set(mode="OBJECT")

	## copies from ACTIVE to all other SELECTED
	select_only(ob)

	## This is incredibly broken
	# bpy.ops.object.data_transfer(data_type="UV")

	## snap back now that good UVs exist; the two meshes need to be in the same
	## position in space for the modifier to behave correctly.
	duplicate.matrix_world = ob.matrix_world.copy()

	modifier =  ob.modifiers.new(type="DATA_TRANSFER", name="OmniBake_Transfer")
	modifier.object = duplicate
	modifier.use_loop_data = True
	modifier.data_types_loops = {'UV'}
	modifier.loop_mapping = 'NEAREST_NORMAL'

	select_only(ob)
	bpy.ops.object.modifier_apply(modifier=modifier.name)

	if apply_material:
		apply_test_material(ob)

	bpy.data.objects.remove(duplicate)


## --------------------------------------------------------------------------------
def unwrap_selected(uv_layer_name="OmniUV", apply_material=False, margin=0.0):
	old_mode = bpy.context.mode

	selected_objects = list(bpy.context.selected_objects)
	active = bpy.context.view_layer.objects.active

	selected_meshes = _selected_meshes(bpy.context)

	total = len(selected_meshes)
	count = 1

	print(f"\n\n[ Unwrapping {total} meshes ]")

	for mesh in selected_meshes:
		padd = len(str(total)) - len(str(count))
		print(f"[{'0'*padd}{count}/{total}] Unwrapping {mesh.name}...")
		unwrap_object(mesh, uv_layer_name=uv_layer_name, apply_material=apply_test_material)
		count += 1

	print(f"\n[ Unwrapping complete ]\n\n")

	select_only(selected_objects[0])
	for item in selected_objects[1:]:
		item.select_set(True)
	bpy.context.view_layer.objects.active = active

	if old_mode == "EDIT_MESH":
		bpy.ops.object.mode_set(mode="EDIT")


## --------------------------------------------------------------------------------
def import_usd_file(filepath:str, root_prim=None, visible_only=False):
	all_objects = bpy.context.scene.collection.all_objects
	names = [x.name for x in all_objects]

	try:
		bpy.ops.object.mode_set(mode="OBJECT")
	except RuntimeError:
		pass

	for name in names:
		ob = bpy.data.objects[name]
		bpy.data.objects.remove(ob)

	kwargs = {
		"filepath":filepath,
		"import_cameras": False,
		"import_curves": False,
		"import_lights": False,
		"import_materials": False,
		"import_blendshapes": False,
		"import_volumes": False,
		"import_skeletons": False,
		"import_shapes": False,
		"import_instance_proxies": True,
		"import_visible_only": visible_only,
		"read_mesh_uvs": False,
		"read_mesh_colors": False,
	}

	if root_prim:
		## if you end with a slash it fails
		kwargs["prim_path_mask"] = root_prim[:-1] if root_prim.endswith("/") else root_prim

	bpy.ops.wm.usd_import(**kwargs)
	print(f"Imported USD file: {filepath}")


## --------------------------------------------------------------------------------
def export_usd_file(filepath:str):
	kwargs = {
		"filepath":filepath,
		"visible_objects_only": False,
		"default_prim_path": "/World",
		"root_prim_path": "/World",
		# "generate_preview_surface": False,
		# "generate_mdl": False,
		"merge_transform_and_shape": True,
	}

	bpy.ops.wm.usd_export(**kwargs)
	print(f"Wrote USD file with UVs: {filepath}")


## ======================================================================
if __name__ == "__main__":
	real_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

	parser = argparse.ArgumentParser()

	parser.add_argument('--input', type=str, required=True, help="Path to input USD file")
	parser.add_argument('--output', type=str, help="Path to output USD file (default is input_UV.usd)")
	parser.add_argument('--margin', type=float, default=None, help="Island margin (default is 0.01)")
	parser.add_argument('--root_prim', type=str, default=None,
						help="Root Prim to import. If unspecified, the whole file will be imported.")
	parser.add_argument('--add_test_material', action="store_true")
	parser.add_argument('--visible_only', action="store_true", default=False)

	if not len(real_args):
		parser.print_help()
		sys.exit(1)

	args = parser.parse_args(real_args)

	input_file = os.path.abspath(args.input)

	split = input_file.rpartition(".")
	output_path = args.output or (split[0] + "_UV." + split[-1])
	margin = args.margin or 0.0

	import_usd_file(input_file, root_prim=args.root_prim, visible_only=args.visible_only)
	bpy.ops.object.select_all(action="SELECT")
	unwrap_selected(apply_material=args.add_test_material, margin=margin)
	export_usd_file(output_path)

	sys.exit(0)

