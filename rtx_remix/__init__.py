
import bpy

from . import (operators, ui)

bl_info = {
    "name": "RTX Remix Panel",
    "author": "NVIDIA Corporation",
    "version": (1, 0, 0),
    "blender": (4, 1, 0),
    "location": "View3D > Toolbar > Omniverse",
    "description": "Contains useful templates for moving textured, shaded objects into RTX Remix",
    "warning": "",
    "doc_url": "",
    "category": "Omniverse",
}

classes = [
	operators.OT_CreateTemplateOmniPBR,
	operators.OT_CreateTemplateOmniGlass,
	ui.OBJECT_PT_rtx_remix_panel,
]


def register():
	unregister()

	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in classes:
		try:
			bpy.utils.unregister_class(cls)
		except:
			pass

