from tempfile import NamedTemporaryFile
from typing import *

import addon_utils
import bpy
from bpy.types import (Collection, Context, Image, Object, Material,
					   Mesh, Node, NodeSocket, NodeTree, Scene)
from bpy.props import *
from mathutils import *

from omni_panel.material_bake import material_setup


COLLECTION_NAME = "OmniBake_Bakes"


def get_material_output(tree:NodeTree, engine:str="CYCLES") -> Optional[Node]:
	"""
	Find the material output node that applies only to a specific engine.
	:param tree: The NodeTree to search.
	:param engine: The engine to search for.
	:return: The Material Output Node associated with the engine, or None if not found.
	"""
	supported_engines = {"CYCLES", "EEVEE", "ALL"}
	assert engine in supported_engines, f"Only the following engines are supported: {','.join(supported_engines)}"

	result = [x for x in tree.nodes if x.type == "OUTPUT_MATERIAL" and x.target in {"ALL", engine}]
	if len(result):
		return result[0]
	return None


def prepare_collection(scene:Scene) -> Collection:
	"""
	Ensures the bake Collection exists in the specified scene.
	:param scene: The scene to which you wish to add the bake Collection.
	:return: the bake Collection
	"""
	collection = bpy.data.collections.get(COLLECTION_NAME, None) or bpy.data.collections.new(COLLECTION_NAME)

	if not COLLECTION_NAME in scene.collection.children:
		scene.collection.children.link(collection)

	return collection


def select_only(ob:Object):
	"""
	Ensure that only the specified object is selected.
	:param ob: Object to select
	"""
	bpy.ops.object.select_all(action="DESELECT")
	ob.select_set(state=True)
	bpy.context.view_layer.objects.active = ob


def smart_unwrap_object(ob:Object, name:str="OmniBake"):
	"""
	Use Blenders built-in smart unwrap functionality to generate a new UV map.
	:param ob: Mesh Object to unwrap.
	"""
	bpy.ops.object.mode_set(mode="EDIT", toggle=False)

	# Unhide any geo that's hidden in edit mode or it'll cause issues.
	bpy.ops.mesh.reveal()
	bpy.ops.mesh.select_all(action="SELECT")
	bpy.ops.mesh.reveal()

	if name in ob.data.uv_layers:
		ob.data.uv_layers.remove(ob.data.uv_layers[name])

	uv_layer = ob.data.uv_layers.new(name=name)
	uv_layer.active = True

	bpy.ops.uv.select_all(action="SELECT")
	bpy.ops.uv.smart_project(island_margin=0.0)

	bpy.ops.object.mode_set(mode="OBJECT", toggle=False)


def prepare_mesh(ob:Object, collection: Collection, unwrap=False) -> Object:
	"""
	Duplicate the specified Object, also duplicating all its materials.

	:param ob: The object to duplicate.
	:param collection: After duplication, the object will be inserted into this Collection
	:param unwrap: If True, also smart unwrap the object's UVs.
	:return: The newly created duplicate object.
	"""
	assert not ob.name in collection.all_objects, f"{ob.name} is a baked mesh (cannot be used)"

	new_mesh_name = ob.data.name[:56] + "_baked"
	if new_mesh_name in bpy.data.meshes:
		bpy.data.meshes.remove(bpy.data.meshes[new_mesh_name])
	new_mesh = ob.data.copy()
	new_mesh.name = new_mesh_name

	new_name = ob.name[:56] + "_baked"
	if new_name in bpy.data.objects:
		bpy.data.objects.remove(bpy.data.objects[new_name])
	new_object = bpy.data.objects.new(new_name, new_mesh)

	collection.objects.link(new_object)
	select_only(new_object)
	new_object.matrix_world = ob.matrix_world.copy()

	if unwrap:
		smart_unwrap_object(new_object)

	for index, material in enumerate([x.material for x in new_object.material_slots]):
		new_material_name = material.name[:56] + "_baked"
		if new_material_name in bpy.data.materials:
			bpy.data.materials.remove(bpy.data.materials[new_material_name])
		new_material = material.copy()
		new_material.name = new_material_name
		new_object.material_slots[index].material = new_material

	ob.hide_viewport = True
	return new_object


##!<--- TODO: Fix these
def find_node_from_label(label:str, nodes:List[Node]) -> Node:
	for node in nodes:
		if node.label == label:
			return node

	return False


def find_isocket_from_identifier(idname:str, node:Node) -> NodeSocket:
	for inputsocket in node.inputs:
		if inputsocket.identifier == idname:
			return inputsocket

	return False


def find_osocket_from_identifier(idname, node):
	for outputsocket in node.outputs:
		if outputsocket.identifier == idname:
			return outputsocket

	return False


def make_link(f_node_label, f_node_ident, to_node_label, to_node_ident, nodetree):
	fromnode = find_node_from_label(f_node_label, nodetree.nodes)
	if (fromnode == False):
		return False
	fromsocket = find_osocket_from_identifier(f_node_ident, fromnode)
	tonode = find_node_from_label(to_node_label, nodetree.nodes)
	if (tonode == False):
		return False
	tosocket = find_isocket_from_identifier(to_node_ident, tonode)

	nodetree.links.new(fromsocket, tosocket)
	return True
## --->


## ======================================================================
##!TODO: Shader type identification and bake setup
def _nodes_for_type(node_tree:NodeTree, node_type:str) -> List[Node]:
	result = [x for x in node_tree.nodes if x.type == node_type]
	## skip unconnected nodes
	from_nodes = [x.from_node for x in node_tree.links]
	to_nodes   = [x.to_node for x in node_tree.links]
	all_nodes = set(from_nodes + to_nodes)
	result = list(filter(lambda x: x in all_nodes, result))
	return result


def output_nodes_for_engine(node_tree:NodeTree, engine:str) -> List[Node]:
	nodes = _nodes_for_type(node_tree, "OUTPUT_MATERIAL")
	return nodes


def get_principled_nodes(node_tree:NodeTree) -> List[Node]:
	return _nodes_for_type(node_tree, "BSDF_PRINCIPLED")


def identify_shader_type(node_tree:NodeTree) -> str:
	principled_nodes = get_principled_nodes(node_tree)
	emission_nodes = _nodes_for_type(node_tree, "EMISSION")
	mix_nodes = _nodes_for_type(node_tree, "MIX_SHADER")
	outputs = output_nodes_for_engine(node_tree, "CYCLES")
	total_shader_nodes = principled_nodes + emission_nodes + mix_nodes

	## first type: principled straight into the output


## ----------------------------------------------------------------------
def create_principled_setup(material:Material, images:Dict[str,Image]):
	"""
	Creates a new shader setup in the tree of the specified
	material using the baked images, removing all old shader nodes.

	:param material: The material to change.
	:param images: The baked Images dictionary, name:Image pairs.
	"""

	node_tree = material.node_tree
	nodes = node_tree.nodes
	material.cycles.displacement_method = 'BOTH'

	principled_nodes = get_principled_nodes(node_tree)

	for node in filter(lambda x: not x in principled_nodes, nodes):
		nodes.remove(node)

	# Node Frame
	frame = nodes.new("NodeFrame")
	frame.location = (0, 0)
	frame.use_custom_color = True
	frame.color = (0.149763, 0.214035, 0.0590617)

	## reuse the old BSDF if it exists to make sure the non-textured constant inputs are correct
	pnode = principled_nodes[0] if len(principled_nodes) else nodes.new("ShaderNodeBsdfPrincipled")
	pnode.location = (-25, 335)
	pnode.label = "pnode"
	pnode.use_custom_color = True
	pnode.color = (0.3375297784805298, 0.4575316309928894, 0.08615386486053467)
	pnode.parent = nodes["Frame"]

	# And the output node
	node = nodes.new("ShaderNodeOutputMaterial")
	node.location = (500, 200)
	node.label = "monode"
	node.show_options = False
	node.parent = nodes["Frame"]

	make_link("pnode", "BSDF", "monode", "Surface", node_tree)

	# -----------------------------------------------------------------

	# 'COMBINED', 'AO', 'SHADOW', 'POSITION', 'NORMAL', 'UV', 'ROUGHNESS',
	# 'EMIT', 'ENVIRONMENT', 'DIFFUSE', 'GLOSSY', 'TRANSMISSION'

	## These are the currently supported types.
	## More could be supported at a future date.
	if "DIFFUSE" in images:
		node = nodes.new("ShaderNodeTexImage")
		node.hide = True
		node.location = (-500, 250)
		node.label = "col_tex"
		node.image = images["DIFFUSE"]
		node.parent = nodes["Frame"]
		make_link("col_tex", "Color", "pnode", "Base Color", node_tree)

	if "METALLIC" in images:
		node = nodes.new("ShaderNodeTexImage")
		node.hide = True
		node.location = (-500, 140)
		node.label = "metallic_tex"
		node.image = images["METALLIC"]
		node.parent = nodes["Frame"]
		make_link("metallic_tex", "Color", "pnode", "Metallic", node_tree)

	if "GLOSSY" in images:
		node = nodes.new("ShaderNodeTexImage")
		node.hide = True
		node.location = (-500, 90)
		node.label = "specular_tex"
		node.image = images["GLOSSY"]
		node.parent = nodes["Frame"]
		make_link("specular_tex", "Color", "pnode", "Specular", node_tree)

	if "ROUGHNESS" in images:
		node = nodes.new("ShaderNodeTexImage")
		node.hide = True
		node.location = (-500, 50)
		node.label = "roughness_tex"
		node.image = images["ROUGHNESS"]
		node.parent = nodes["Frame"]
		make_link("roughness_tex", "Color", "pnode", "Roughness", node_tree)

	if "TRANSMISSION" in images:
		node = nodes.new("ShaderNodeTexImage")
		node.hide = True
		node.location = (-500, -90)
		node.label = "transmission_tex"
		node.image = images["TRANSMISSION"]
		node.parent = nodes["Frame"]
		make_link("transmission_tex", "Color", "pnode", "Transmission", node_tree)

	if "EMIT" in images:
		node = nodes.new("ShaderNodeTexImage")
		node.hide = True
		node.location = (-500, -170)
		node.label = "emission_tex"
		node.image = images["EMIT"]
		node.parent = nodes["Frame"]
		make_link("emission_tex", "Color", "pnode", "Emission", node_tree)

	if "NORMAL" in images:
		node = nodes.new("ShaderNodeTexImage")
		node.hide = True
		node.location = (-500, -318.7)
		node.label = "normal_tex"
		image = images["NORMAL"]
		node.image = image
		node.parent = nodes["Frame"]

		# Additional normal map node for normal socket
		node = nodes.new("ShaderNodeNormalMap")
		node.location = (-220, -240)
		node.label = "normalmap"
		node.show_options = False
		node.parent = nodes["Frame"]
		make_link("normal_tex", "Color", "normalmap", "Color", node_tree)
		make_link("normalmap", "Normal", "pnode", "Normal", node_tree)

	# -----------------------------------------------------------------
	## wipe all labels
	for item in nodes:
		item.label = ""

	node = nodes["Frame"]
	node.label = "OMNI PBR"

	for type, image in images.items():
		if type in {"DIFFUSE", "EMIT"}:
			image.colorspace_settings.name = "sRGB"
		else:
			image.colorspace_settings.name = "Non-Color"


## ======================================================================
def _selected_meshes(context:Context) -> List[Mesh]:
	"""
	:return: List[Mesh] of all selected mesh objects in active Blender Scene.
	"""
	return [x for x in context.selected_objects if x.type == "MESH"]


def _material_can_be_baked(material:Material) -> bool:
	outputs = output_nodes_for_engine(material.node_tree, "CYCLES")
	if not len(outputs) == 1:
		return False

	try:
		from_node = outputs[0].inputs["Surface"].links[0].from_node
	except IndexError:
		return False

	##!TODO: Support one level of mix with principled inputs
	if not from_node.type == "BSDF_PRINCIPLED":
		return False

	return True


def omni_bake_maps_poll(context:Context) -> (int, Any):
	"""
	:return: 1 if we can bake
	         0 if no meshes are selected
	         -1 if any selected meshes are already in the bake collection
	         -2 if mesh contains non-bakeable materials
	         -3 if Cycles renderer isn't loaded
	"""
	## Cycles renderer is not available
	_, loaded_state = addon_utils.check("cycles")
	if not loaded_state:
		return (-3, None)

	selected = _selected_meshes(context)
	if not len(selected):
		return (0, None)

	for mesh in selected:
		for material in [slot.material for slot in mesh.material_slots]:
			if not _material_can_be_baked(material):
				return (-2, [mesh.name, material.name])

	collection = bpy.data.collections.get(COLLECTION_NAME, None)
	if collection is None:
		## We have selected meshes but no collection-- early out
		return (1, None)

	in_collection = [x for x in selected if x.name in collection.all_objects]
	if len(in_collection):
		return (-1, None)

	return (1, None)


## ======================================================================
class OmniBakerProperties(bpy.types.PropertyGroup):
	bake_metallic: BoolProperty(name="Metallic",
								default=True)

	merge_textures: BoolProperty(name="Merge Textures",
								description="Bake all materials for each object onto a single map",
								default=True)


## ======================================================================
class OBJECT_OT_omni_bake_maps(bpy.types.Operator):
	"""Bake specified passes on the selected Mesh object."""
	bl_idname  = "omni.bake_maps"
	bl_label   = "Bake Maps"
	bl_options = {"REGISTER", "UNDO"}

	base_bake_types = {
		##!TODO: Possibly support these at a later date?
		# "COMBINED", "AO", "SHADOW", "POSITION", "UV", "ENVIRONMENT",
		"DIFFUSE",
		"NORMAL",
		"EMIT",
		"GLOSSY",
		"ROUGHNESS",
		"TRANSMISSION",
	}

	special_bake_types = {
		"METALLIC": "Metallic",
	}

	unwrap:         BoolProperty(default=False, description="Unwrap")
	hide_original:  BoolProperty(default=False, description="Hide Original")
	width:          IntProperty(default=1024, min=128, max=8192, description="Width")
	height:         IntProperty(default=1024, min=128, max=8192, description="Height")
	bake_types:     StringProperty(default="DIFFUSE")
	merge_textures: BoolProperty(default=True, description="Merge Textures")

	@classmethod
	def poll(cls, context:Context) -> bool:
		return omni_bake_maps_poll(context)[0] == 1

	def draw(self, context:Context):
		"""Empty draw to disable the Operator Props Panel."""
		pass

	def _get_bake_emission_target(self, node_tree:NodeTree) -> Node:
		bake_emission_name = "OmniBake_Emission"

		if not bake_emission_name in node_tree.nodes:
			node = node_tree.nodes.new("ShaderNodeEmission")
			node.name = bake_emission_name
			output = get_material_output(node_tree, "CYCLES")
			node.location = output.location + Vector((-200.0, -100.0))

		return node_tree.nodes[bake_emission_name]

	def _copy_connection(self, material:Material, bsdf:Node, bake_type:str, target_socket:NodeSocket) -> bool:
		if not bake_type in self.special_bake_types:
			return False

		orig_socket = bsdf.inputs[self.special_bake_types[bake_type]]
		if not len(orig_socket.links):
			## copy over the color and return
			if orig_socket.type == "VECTOR":
				for index in range(4):
					target_socket.default_value[index] = orig_socket.default_value
			elif orig_socket.type in {"VECTOR", "RGBA"}:
				for index in range(3):
					target_socket.default_value[index] = orig_socket.default_value[index]
					target_socket.default_value[3] = 1.0
			else:
				## should never arrive here
				return False
		else:
			input_socket = orig_socket.links[0].from_socket
			material.node_tree.links.new(input_socket, target_socket)

		return True

	def _create_bake_texture_names(self, ob:Object, bake_types:List[str]) -> List[str]:
		result = []

		for material in [x.material for x in ob.material_slots]:
			material_name = material.name.rpartition('_baked')[0]
			for bake_type in bake_types:
				if self.merge_textures:
					image_name = f"{ob.name}__{bake_type}"
				else:
					image_name = f"{ob.name}_{material_name}_{bake_type}"
				result.append(image_name)

		return result

	def report(self, type:Set[str], message:str):
		print(message)
		super(OBJECT_OT_omni_bake_maps, self).report(type, message)

	def execute(self, context:Context) -> Set[str]:
		wm = context.window_manager
		scene = context.scene
		scene_engine = scene.render.engine
		scene.render.engine = "CYCLES"
		scene_use_clear = scene.render.bake.use_clear
		scene.render.bake.use_clear = False
		collection = prepare_collection(scene)
		all_bake_types = self.base_bake_types | self.special_bake_types.keys()
		valid_types_str = "Valid types are: " + ", ".join(all_bake_types)

		self.report({"INFO"}, f"Bake types: {self.bake_types}")

		bake_types = self.bake_types.split(",")

		if not len(bake_types):
			self.report({"ERROR"}, "No bake type specified. " + valid_types_str)

		for bake_type in bake_types:
			if not bake_type in all_bake_types:
				self.report({"ERROR"}, f"Bake type '{bake_type}' is not valid. " + valid_types_str)
				return {"CANCELLED"}

		selected_meshes = _selected_meshes(context)
		count = 0
		total = 0
		for mesh in selected_meshes:
			count += len(mesh.material_slots) * len(bake_types)

		wm.progress_begin(total, count)
		bpy.ops.object.mode_set(mode="OBJECT")

		for mesh_object in _selected_meshes(context):
			mesh_object.hide_select = mesh_object.hide_render = mesh_object.hide_viewport = False
			baked_ob = prepare_mesh(mesh_object, collection, unwrap=self.unwrap)

			uv_layer = "OmniBake" if self.unwrap else baked_ob.data.uv_layers.active.name

			bpy.ops.object.select_all(action="DESELECT")
			baked_ob.select_set(True)
			context.view_layer.objects.active = baked_ob

			self.report({"INFO"}, f"Baking Object {baked_ob.name}")

			baked_materials = []

			## Because of merge_textures, we have to create the names now and clear them
			## before the whole bake process starts
			bake_image_names = self._create_bake_texture_names(baked_ob, bake_types)

			## if merge_textures is on there'll be some repeats
			for image_name in set(bake_image_names):
				if image_name in bpy.data.images:
					bpy.data.images.remove(bpy.data.images[image_name])
				image = bpy.data.images.new(image_name, self.width, self.height,
											float_buffer=(image_name.endswith(("NORMAL", "EMIT"))) )
				# if bake_type in {"DIFFUSE", "EMIT"}:
				# 	image.colorspace_settings.name = "sRGB"
				# else:
				# 	image.colorspace_settings.name = "Non-Color"
				image.colorspace_settings.name = "Raw"

				if self.merge_textures:
					temp_file = NamedTemporaryFile(prefix=bake_type, suffix=".png", delete=False)
					image.filepath = temp_file.name

			image_index = 0

			for material_index, material in enumerate([x.material for x in baked_ob.material_slots]):
				self.report({"INFO"}, f" => Material: {material.name}")

				tree = material.node_tree

				baked_ob.active_material_index = material_index

				for node in tree.nodes:
					node.select = False

				output = get_material_output(tree)
				bsdf   = output.inputs["Surface"].links[0].from_node

				if "OmniBakeImage" in tree.nodes:
					tree.nodes.remove(tree.nodes["OmniBakeImage"])

				bake_image_node = tree.nodes.new("ShaderNodeTexImage")
				bake_image_node.name = "OmniBakeImage"
				bake_image_node.location = output.location.copy()
				bake_image_node.location.x += 200.0
				bake_image_node.select = True
				tree.nodes.active = bake_image_node

				## for special cases
				bake_emission = self._get_bake_emission_target(tree)
				original_link = output.inputs["Surface"].links[0]
				original_from, original_to = original_link.from_socket, original_link.to_socket

				baked_images = {}

				for bake_type in bake_types:
					image_name = bake_image_names[image_index]
					image = bpy.data.images[image_name]
					bake_image_node.image = image.original if image.original else image

					self.report({"INFO"}, f"====> Baking {material.name} pass {bake_type}...")

					kwargs = {}
					if bake_type in {"DIFFUSE"}:
						## ensure no black due to bad direct / indirect lighting
						kwargs["pass_filter"] = {"COLOR"}
						scene.render.bake.use_pass_indirect = False
						scene.render.bake.use_pass_direct = False

					if bake_type in self.special_bake_types:
						## cheat by running the bake through emit after reconnecting
						real_bake_type = "EMIT"
						tree.links.new(bake_emission.outputs["Emission"], original_to)
						self._copy_connection(material, bsdf, bake_type, bake_emission.inputs["Color"])
					else:
						real_bake_type = bake_type
						tree.links.new(original_from, original_to)


					## have to do this every pass?
					if bake_type in {"DIFFUSE", "EMIT"}:
						image.colorspace_settings.name = "sRGB"
					else:
						image.colorspace_settings.name = "Non-Color"

					bpy.ops.object.bake(type=real_bake_type, width=self.width, height=self.height, uv_layer=uv_layer,
										use_clear=False, margin=1, **kwargs)

					if self.merge_textures:
						## I know this seems weird, but if you don't save the file here
						## post-bake when merging, the texture gets corrupted and you end
						## up with a texture that's taking up ram, but can't be loaded
						## for rendering (comes up pink in Cycles)
						image.save()

					self.report({"INFO"}, "... Done.")
					baked_images[bake_type] = image

					total += 1
					image_index += 1
					wm.progress_update(total)
					wm.update_tag()

				for node in bake_image_node, bake_emission:
					tree.nodes.remove(node)

				tree.links.new(original_from, original_to)

				baked_materials.append((material, baked_images))

			for material, images in baked_materials:
				## Perform conversion after all images are baked
				## If this is not done, then errors can arise despite not
				## replacing shader indices.
				create_principled_setup(material, images)

			for image in [bpy.data.images[x] for x in bake_image_names]:
				image.pack()

			## Set new UV map as active if it exists
			if "OmniBake" in baked_ob.data.uv_layers:
				baked_ob.data.uv_layers["OmniBake"].active_render = True

			if self.hide_original:
				mesh_object.hide_set(True)

		wm.progress_end()

		scene.render.engine = scene_engine
		scene.render.bake.use_clear = scene_use_clear

		return {"FINISHED"}


## ======================================================================
module_classes = [
	OBJECT_OT_omni_bake_maps,

	OmniBakerProperties,
]


def register():
	for cls in module_classes:
		bpy.utils.register_class(cls)

	bpy.types.Scene.omni_bake = bpy.props.PointerProperty(type=OmniBakerProperties)


def unregister():
	for cls in reversed(module_classes):
		bpy.utils.unregister_class(cls)

	try:
		del bpy.types.Scene.omni_bake
	except (AttributeError, RuntimeError):
		pass

