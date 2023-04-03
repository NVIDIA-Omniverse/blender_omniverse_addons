from typing import *
import bpy
from bpy.types import (Collection, Context, Image, Object, Material,
					   Mesh, Node, NodeSocket, NodeTree, Scene)
from bpy.props import *


## ======================================================================
usd_kind_items = {
			('COMPONENT', 'component', 'kind: component'),
			('GROUP', 'group', 'kind: group'),
			('ASSEMBLY', 'assembly', 'kind: assembly'),
			('CUSTOM', 'custom', 'kind: custom'),
		}


## ======================================================================
def get_plural_count(items) -> (str, int):
	count = len(items)
	plural = '' if count == 1 else 's'
	return plural, count


## ======================================================================
class OBJECT_OT_omni_set_usd_kind(bpy.types.Operator):
	"""Sets the USD Kind value on the selected objects."""
	bl_idname  = "omni.set_usd_kind"
	bl_label   = "Set USD Kind"
	bl_options = {"REGISTER", "UNDO"}

	kind: EnumProperty(name='kind', description='USD Kind', items=usd_kind_items)
	custom_kind: StringProperty(default="")
	verbose: BoolProperty(default=False)

	@property ## read-only
	def value(self) -> str:
		return self.custom_kind if self.kind == "CUSTOM" else self.kind.lower()

	@classmethod
	def poll(cls, context:Context) -> bool:
		return bool(len(context.selected_objects))

	def execute(self, context:Context) -> Set[str]:
		if self.kind == "NONE":
			self.report({"WARNING"}, "No kind specified-- nothing authored.")
			return {"CANCELLED"}

		for item in context.selected_objects:
			props = item.id_properties_ensure()
			props["usdkind"] = self.value

			props_ui = item.id_properties_ui("usdkind")
			props_ui.update(default=self.value, description="USD Kind")

		if self.verbose:
			plural, count = get_plural_count(context.selected_objects)
			self.report({"INFO"}, f"Set USD Kind to {self.value} for {count} object{plural}.")

		return {"FINISHED"}


## ======================================================================
class OBJECT_OT_omni_set_usd_kind_auto(bpy.types.Operator):
	"""Sets the USD Kind value on scene objects, automatically."""
	bl_idname  = "omni.set_usd_kind_auto"
	bl_label   = "Set USD Kind Auto"
	bl_options = {"REGISTER", "UNDO"}

	verbose: BoolProperty(default=False)

	def execute(self, context:Context) -> Set[str]:
		active = context.active_object
		selected = list(context.selected_objects)

		bpy.ops.object.select_all(action='DESELECT')

		## heuristics
		## First, assign "component" to all unparented empties
		unparented = [x for x in context.scene.collection.all_objects if not x.parent and x.type == "EMPTY"]
		for item in unparented:
			item.select_set(True)
			bpy.ops.omni.set_usd_kind(kind="COMPONENT")
			item.select_set(False)

		if self.verbose:
			plural, count = get_plural_count(unparented)
			self.report({"INFO"}, f"Set USD Kind Automatically on {count} object{plural}.")

		return {"FINISHED"}


## ======================================================================
class OBJECT_OT_omni_clear_usd_kind(bpy.types.Operator):
	"""Clear USD Kind values on the selected objects."""
	bl_idname  = "omni.clear_usd_kind"
	bl_label   = "Clear USD Kind"
	bl_options = {"REGISTER", "UNDO"}

	verbose: BoolProperty(default=False)

	@classmethod
	def poll(cls, context:Context) -> bool:
		return bool(len(context.selected_objects))

	def execute(self, context:Context) -> Set[str]:
		from rna_prop_ui import rna_idprop_ui_prop_update

		total = 0

		for item in context.selected_objects:
			if "usdkind" in item:
				rna_idprop_ui_prop_update(item, "usdkind")
				del item["usdkind"]
				total += 1

		if self.verbose:
			plural, count = get_plural_count(range(total))
			self.report({"INFO"}, f"Cleared USD Kind from {count} object{plural}.")

		return {"FINISHED"}


## ======================================================================
class OBJECT_PT_omni_usd_kind_panel(bpy.types.Panel):
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Omniverse"
	bl_label = "USD Kind"

	def draw(self, context:Context):
		layout = self.layout
		scene  = context.scene

		layout.label(text="USD Kind")

		row = layout.row()
		row.prop(scene.omni_usd_kind, "kind", text="Kind")
		if scene.omni_usd_kind.kind == "CUSTOM":
			row = layout.row()
			row.prop(scene.omni_usd_kind, "custom_kind", text="Custom Kind")

		col = layout.column(align=True)

		op = col.operator(OBJECT_OT_omni_set_usd_kind.bl_idname, icon="PLUS")
		op.kind = scene.omni_usd_kind.kind
		op.custom_kind = scene.omni_usd_kind.custom_kind
		op.verbose = True

		op = col.operator(OBJECT_OT_omni_clear_usd_kind.bl_idname, icon="X")
		op.verbose = True

		op = col.operator(OBJECT_OT_omni_set_usd_kind_auto.bl_idname, icon="BRUSH_DATA")
		op.verbose = True


## ======================================================================
class USDKindProperites(bpy.types.PropertyGroup):
	kind: EnumProperty(name='kind', description='USD Kind', items=usd_kind_items)
	custom_kind: StringProperty(default="")


## ======================================================================
classes = [
	OBJECT_OT_omni_set_usd_kind,
	OBJECT_OT_omni_set_usd_kind_auto,
	OBJECT_OT_omni_clear_usd_kind,
	OBJECT_PT_omni_usd_kind_panel,
	USDKindProperites,
]


def unregister():
	for cls in reversed(classes):
		try:
			bpy.utils.unregister_class(cls)
		except ValueError:
			continue
		except RuntimeError:
			continue

	try:
		del bpy.types.Scene.omni_usd_kind
	except AttributeError:
		pass


def register():
	unregister()

	for cls in classes:
		bpy.utils.register_class(cls)

	bpy.types.Scene.omni_usd_kind = bpy.props.PointerProperty(type=USDKindProperites)


