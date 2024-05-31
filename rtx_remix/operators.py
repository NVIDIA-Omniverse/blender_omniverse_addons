# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# Copyright (c) 2021-2024 NVIDIA CORPORATION.  All rights reserved.

import typing
import os
import re
import sys
import json

import bpy

from .material_templates import create_template

def _rtx_material_poll(context:bpy.types.Context) -> bool:
	"""RTX Remix material Operators poll predicate"""
	if context.active_object and context.active_object.active_material:
		return True

	return False

class OT_CreateTemplateOmniPBR(bpy.types.Operator):
	bl_idname = "rtxremix.create_template_omnipbr"
	bl_label = "Convert to OmniPBR"
	bl_description = "RTX Remix: Convert active material to OmniPBR"

	@classmethod
	def poll(cls, context:bpy.types.Context) -> bool:
		return _rtx_material_poll(context)

	def execute(self, context):
		material = bpy.context.active_object.active_material
		create_template(source_class="OmniPBR", material=material)
		self.report({"INFO"}, f"Replaced Material '{material.name}' with OmniPBR")
		return {"FINISHED"}


class OT_CreateTemplateOmniGlass(bpy.types.Operator):
	bl_idname = "rtxremix.create_template_omniglass"
	bl_label = "Convert to OmniGlass"
	bl_description = "RTX Remix: Convert active material to OmniGlass"

	@classmethod
	def poll(cls, context:bpy.types.Context) -> bool:
		return _rtx_material_poll(context)

	def execute(self, context):
		material = bpy.context.active_object.active_material
		create_template(source_class="OmniGlass", material=material)
		self.report({"INFO"}, f"Replaced Material '{material.name}' with OmniGlass")
		return {"FINISHED"}

