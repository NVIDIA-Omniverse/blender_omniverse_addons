import os
import sys
import time

import bpy
from omni_optimization_panel.operators import OmniOverrideMixin

omniover = OmniOverrideMixin()


## ======================================================================
def perform_scene_merge():
	"""
	Combine all selected mesh objects into a single mesh.
	"""
	orig_scene = bpy.context.scene

	selected    = [x for x in bpy.context.selected_objects if x.type == "MESH"]
	if not len(selected):
		print("-- No objects selected for merge.")
		return

	merge_collection = bpy.data.collections.new("MergeCollection") if not "MergeCollection" in bpy.data.collections else bpy.data.collections["MergeCollection"]
	merge_scene      = bpy.data.scenes.new("MergeScene") if not "MergeScene" in bpy.data.scenes else bpy.data.scenes["MergeScene"]

	for child in merge_scene.collection.children:
		merge_scene.collection.children.unlink(child)

	for ob in merge_collection.all_objects:
		merge_collection.objects.unlink(ob)

	to_merge = set()
	sources  = set()

	for item in selected:
		to_merge.add(item)
		merge_collection.objects.link(item)
		if not item.instance_type == "NONE":
			item.show_instancer_for_render = True
			child_set = set(item.children)
			to_merge |= child_set
			sources  |= child_set

	merge_scene.collection.children.link(merge_collection)
	bpy.context.window.scene = merge_scene

	for item in to_merge:
		try:
			merge_collection.objects.link(item)
		except RuntimeError:
			continue

	## make sure to remove shape keys and merge modifiers for all merge_collection objects
	for item in merge_collection.all_objects:
		with omniover.override([item], single=True):
			if item.data.shape_keys:
				bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
			for mod in item.modifiers:
				bpy.ops.object.modifier_apply(modifier=mod.name, single_user=True)

	## turns out the make_duplis_real function swaps selection for you, and
	## leaves non-dupli objects selected
	bpy.ops.object.select_all(action="SELECT")
	bpy.ops.object.duplicates_make_real()
		## this invert and delete is removing the old instancer objects
	bpy.ops.object.select_all(action="INVERT")
	for item in sources:
		item.select_set(True)
	bpy.ops.object.delete(use_global=False)
	bpy.ops.object.select_all(action="SELECT")
	## need an active object for join poll()
	bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
	bpy.ops.object.join()


## ======================================================================
if __name__ == "__main__":
	real_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
	if not len(real_args):
		print("-- No output path name.")
		sys.exit(-1)

	output_file = real_args[-1]

	## make sure the add-on is properly loaded
	bpy.ops.preferences.addon_enable(module="omni_optimization_panel")

	start_time = time.time()

	## pull all attribute names from all mixins for passing on to the optimizer
	sceneopts = bpy.context.scene.omni_sceneopt
	chopopts  = bpy.context.scene.omni_sceneopt_chop

	skips = {"bl_rna", "name", "rna_type"}

	optimize_kwargs = {}
	for item in sceneopts, chopopts:
		for key in filter(lambda x: not x.startswith("__") and not x in skips, dir(item)):
			optimize_kwargs[key] = getattr(item, key)

	print(f"optimize kwargs: {optimize_kwargs}")

	if sceneopts.merge:
		## merge before because of the possibility of objects getting created
		perform_scene_merge()
		bpy.ops.wm.save_as_mainfile(filepath=output_file.rpartition(".")[0]+".blend")

	## always export whole scene
	optimize_kwargs["selected"] = False
	optimize_kwargs["verbose"] = True
	bpy.ops.omni_sceneopt.optimize(**optimize_kwargs)

	optimize_time = time.time()
	print(f"Optimization time: {(optimize_time - start_time):.2f} seconds.")

	export_kwargs = {
		"filepath": output_file,
		"visible_objects_only": False,
		"default_prim_path": "/World",
		"root_prim_path": "/World",
		"material_prim_path": "/World/materials",
		"generate_preview_surface": True,
		"export_materials": True,
		"export_uvmaps": True,
		"merge_transform_and_shape": True,
		"use_instancing": True,
		"export_textures": sceneopts.export_textures,
	}

	bpy.ops.wm.usd_export(**export_kwargs)

	export_time = time.time()

	print(f"Wrote optimized USD file: {output_file}")
	print(f"Export time: {(export_time - optimize_time):.2f} seconds.")
	print(f"Total time:  {(export_time - start_time):.2f} seconds.")

	sys.exit(0)

