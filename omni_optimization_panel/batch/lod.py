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
def select_only(ob:Object):
	"""
	Ensure that only the specified object is selected.
	:param ob: Object to select
	"""
	bpy.ops.object.select_all(action="DESELECT")
	ob.select_set(state=True)
	bpy.context.view_layer.objects.active = ob


## --------------------------------------------------------------------------------
def _selected_meshes(context:Context, use_instancing=True) -> List[Mesh]:
	"""
	:return: List[Mesh] of all selected mesh objects in active Blender Scene.
	"""
	## instances support
	meshes    = [x for x in context.selected_objects if x.type == "MESH"]
	instances = [x for x in context.selected_objects if x.type == "EMPTY" and x.instance_collection]

	if use_instancing:
		for inst in instances:
			instance_meshes = [x for x in inst.instance_collection.all_objects if x.type == "MESH"]
			meshes += instance_meshes

	meshes = list(set(meshes))
	return meshes


## --------------------------------------------------------------------------------
def copy_object_parenting(source_ob:Object, target_ob:Object):
	"""
	Copy parenting and Collection membership from a source object.
	"""
	target_collections = list(target_ob.users_collection)
	for collection in target_collections:
		collection.objects.unlink(target_ob)

	for collection in source_ob.users_collection:
		collection.objects.link(target_ob)
	target_ob.parent = source_ob.parent


## --------------------------------------------------------------------------------
def find_unique_name(name:str, library:Iterable) -> str:
	"""
	Given a Blender library, find a unique name that does
	not exist in it.
	"""
	if not name in library:
		return name

	index = 0
	result_name = name + f".{index:03d}"
	while result_name in library:
		index += 1
		result_name = name + f".{index:03d}"

	print(f"Unique Name: {result_name}")
	return result_name


## --------------------------------------------------------------------------------
def duplicate_object(ob:Object, token:str="D", weld=True) -> Object:
	"""
	Duplicates the specified object, maintaining the same parenting
	and collection memberships.
	"""
	base_name = "__".join((ob.name.rpartition("__")[0] if "__" in ob.name else ob.name, token))
	base_data = "__".join((ob.data.name.rpartition("__")[0] if "__" in ob.data.name else ob.data.name, token))

	if base_name in bpy.data.objects:
		base_name = find_unique_name(base_name, bpy.data.objects)
	if base_data in bpy.data.objects:
		base_data = find_unique_name(base_data, bpy.data.objects)

	data = ob.data.copy()
	data.name = base_data

	duplicate = bpy.data.objects.new(base_name, data)

	## Ensure scene collection membership
	## Prototypes might not have this or be in the view layer
	if not duplicate.name in bpy.context.scene.collection.all_objects:
		bpy.context.scene.collection.objects.link(duplicate)

	select_only(duplicate)

	## decimate doesn't work on unwelded triangle soups
	if weld:
		bpy.ops.object.mode_set(mode="EDIT")
		bpy.ops.mesh.select_all(action="SELECT")
		bpy.ops.mesh.remove_doubles(threshold=0.01, use_unselected=True)
		bpy.ops.object.mode_set(mode="OBJECT")

	return duplicate


## --------------------------------------------------------------------------------
def delete_mesh_object(ob:Object):
	"""
	Removes object from the Blender library.
	"""
	base_name = ob.name
	data_name = ob.data.name
	bpy.data.objects.remove(bpy.data.objects[base_name])
	bpy.data.meshes.remove(bpy.data.meshes[data_name])


## --------------------------------------------------------------------------------
def decimate_object(ob:Object, token:str=None, ratio:float=0.5,
					use_symmetry:bool=False, symmetry_axis="X",
					min_face_count:int=3,
					create_duplicate=True):
	old_mode = bpy.context.mode
	scene = bpy.context.scene

	token = token or "DCM"

	if create_duplicate:
		target = duplicate_object(ob, token=token)
	else:
		target = ob

	if len(target.data.polygons) < min_face_count:
		print(f"{target.name} is under face count-- not decimating.")
		return target

	## We're going to use the decimate modifier
	mod = target.modifiers.new("OmniLOD", type="DECIMATE")
	mod.decimate_type = "COLLAPSE"
	mod.ratio = ratio
	mod.use_collapse_triangulate = True
	mod.use_symmetry = use_symmetry
	mod.symmetry_axis = symmetry_axis

	bpy.ops.object.select_all(action="DESELECT")
	target.select_set(True)
	bpy.context.view_layer.objects.active = target
	bpy.ops.object.modifier_apply(modifier=mod.name)

	return target


## --------------------------------------------------------------------------------
def decimate_selected(ratios:List[float]=[0.5], min_face_count=3, use_symmetry:bool=False, symmetry_axis="X", use_instancing=True):
	assert isinstance(ratios, (list, tuple)), "Ratio should be a list of floats from 0.1 to 1.0"
	for value in ratios:
		assert 0.1 <= value <= 1.0, f"Invalid ratio value {value} -- should be between 0.1 and 1.0"

	selected_objects = list(bpy.context.selected_objects)
	active = bpy.context.view_layer.objects.active

	selected_meshes = _selected_meshes(bpy.context, use_instancing=use_instancing)

	total = len(selected_meshes) * len(ratios)
	count = 1

	print(f"\n\n[ Generating {total} decimated LOD meshes (minimum face count: {min_face_count}]")

	for mesh in selected_meshes:
		welded_duplicate = duplicate_object(mesh, token="welded")

		for index, ratio in enumerate(ratios):
			padd = len(str(total)) - len(str(count))
			token = f"LOD{index}"
			orig_count = len(welded_duplicate.data.vertices)
			lod_duplicate = decimate_object(welded_duplicate, ratio=ratio, token=token, use_symmetry=use_symmetry,
							symmetry_axis=symmetry_axis, min_face_count=min_face_count)
			print(f"[{'0'*padd}{count}/{total}] Decimating {mesh.name} to {ratio} ({orig_count} >> {len(lod_duplicate.data.vertices)}) ...")
			copy_object_parenting(mesh, lod_duplicate)
			count += 1

		delete_mesh_object(welded_duplicate)

	print(f"\n[ Decimation complete ]\n\n")


## --------------------------------------------------------------------------------
def import_usd_file(filepath:str, root_prim:Optional[str]=None, visible_only:bool=False, use_instancing:bool=True):
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
		"import_materials": True,
		"import_blendshapes": False,
		"import_volumes": False,
		"import_skeletons": False,
		"import_shapes": False,
		"import_instance_proxies": True,
		"import_visible_only": visible_only,
		"read_mesh_uvs": True,
		"read_mesh_colors": False,
		"use_instancing": use_instancing,
		"validate_meshes": True,
	}

	if root_prim:
		## if you end with a slash it fails
		kwargs["prim_path_mask"] = root_prim[:-1] if root_prim.endswith("/") else root_prim

	bpy.ops.wm.usd_import(**kwargs)
	print(f"Imported USD file: {filepath}")


## --------------------------------------------------------------------------------
def export_usd_file(filepath:str, use_instancing:bool=True):
	kwargs = {
		"filepath":filepath,
		"visible_objects_only": False,
		"default_prim_path": "/World",
		"root_prim_path": "/World",
		"generate_preview_surface": True,
		"export_materials": True,
		"export_uvmaps": True,
		"merge_transform_and_shape": True,
		"use_instancing": use_instancing,
	}

	bpy.ops.wm.usd_export(**kwargs)
	print(f"Wrote USD file with UVs: {filepath}")


## ======================================================================
if __name__ == "__main__":
	real_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

	parser = argparse.ArgumentParser()

	parser.add_argument('--input', type=str, required=True, help="Path to input USD file")
	parser.add_argument('--output', type=str, help="Path to output USD file (default is input_LOD.usd)")
	parser.add_argument('--ratios', type=str, required=True, help='Ratios to use as a space-separated string, ex: "0.5 0.2"')
	parser.add_argument('--use_symmetry', action="store_true", default=False, help="Decimate with symmetry enabled.")
	parser.add_argument('--symmetry_axis', default="X", help="Symmetry axis to use (X, Y, or Z)")
	parser.add_argument('--visible_only', action="store_true", default=False, help="Only import visible prims from the input USD file.")
	parser.add_argument('--min_face_count', type=int, default=3, help="Minimum number of faces for decimation.")
	parser.add_argument('--no_instancing', action="store_false", help="Process the prototype meshes of instanced prims.")
	parser.add_argument('--root_prim', type=str, default=None,
						help="Root Prim to import. If unspecified, the whole file will be imported.")

	if not len(real_args):
		parser.print_help()
		sys.exit(1)

	args = parser.parse_args(real_args)

	input_file = os.path.abspath(args.input)

	split = input_file.rpartition(".")
	output_path = args.output or (split[0] + "_LOD." + split[-1])

	ratios = args.ratios
	if not " " in ratios:
		ratios = [float(ratios)]
	else:
		ratios = list(map(lambda x: float(x), ratios.split(" ")))

	use_instancing = not args.no_instancing

	import_usd_file(input_file, root_prim=args.root_prim, visible_only=args.visible_only, use_instancing=use_instancing)
	bpy.ops.object.select_all(action="SELECT")
	decimate_selected(ratios=ratios, min_face_count=args.min_face_count, use_symmetry=args.use_symmetry, symmetry_axis=args.symmetry_axis, use_instancing=use_instancing)
	export_usd_file(output_path, use_instancing=use_instancing)

	sys.exit(0)

