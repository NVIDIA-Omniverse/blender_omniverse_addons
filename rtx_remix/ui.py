
import bpy

from . import operators

class OBJECT_PT_rtx_remix_panel(bpy.types.Panel):
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Omniverse"
	bl_label = "RTX Remix"
	bl_options = {"DEFAULT_CLOSED"}

	def draw_header(self, context):
		self.layout.label(text="", icon="NODE_MATERIAL")

	def draw(self, context):

		layout = self.layout
		scene = context.scene
		box = layout.box()

		col = box.column(align=True)

		col.operator(operators.OT_CreateTemplateOmniPBR.bl_idname,
                     icon="MOD_PARTICLE_INSTANCE")

		col.operator(operators.OT_CreateTemplateOmniGlass.bl_idname,
                     icon="MOD_PARTICLE_INSTANCE")
