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

# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.

import typing
import traceback

import bpy

from ..core.converter import util


def apply_data_to_instance(instance_name: str,  source_class: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]]) -> dict:
    ## bugfix: Extract class correctly from exporters that name the class like a Python function call.
    real_source_class = source_class.partition("(")[0]

    try:
        for material in bpy.data.materials:
            if not isinstance(material, bpy.types.Material):
                continue
            if material.name == instance_name:
                if util.can_apply_data_to_instance(source_class_name=real_source_class, render_context=render_context, source_data=source_data, instance=material):
                    return util.apply_data_to_instance(source_class_name=real_source_class, render_context=render_context, source_data=source_data, instance=material)
                print(f'Omniverse UMM: Unable to apply data at import for material "{instance_name}". This is not an error - just means that conversion data does not support the material.')
                result = dict()
                result['umm_notification'] = 'incomplete_process'
                result['message'] = 'Not able to convert type "{0}" for render context "{1}" because there is no Conversion Graph for that scenario. No changes were applied to "{2}".'.format(real_source_class, render_context, instance_name)
                return result
    except Exception as error:
        print('Warning: Universal Material Map: function "apply_data_to_instance": Unexpected error:')
        print('\targument "instance_name" = "{0}"'.format(instance_name))
        print('\targument "source_class" = "{0}"'.format(real_source_class))
        print('\targument "render_context" = "{0}"'.format(render_context))
        print('\targument "source_data" = "{0}"'.format(source_data))
        print('\terror: {0}'.format(error))
        print('\tcallstack: {0}'.format(traceback.format_exc()))
        result = dict()
        result['umm_notification'] = 'unexpected_error'
        result['message'] = 'Not able to convert type "{0}" for render context "{1}" because there was an unexpected error. Some changes may have been applied to "{2}". Details: {3}'.format(real_source_class, render_context, instance_name, error)
        return result


def convert_instance_to_data(instance_name: str,  render_context: str) -> typing.List[typing.Tuple[str, typing.Any]]:
    try:
        for material in bpy.data.materials:
            if not isinstance(material, bpy.types.Material):
                continue
            if material.name == instance_name:
                if util.can_convert_instance_to_data(instance=material, render_context=render_context):
                    return util.convert_instance_to_data(instance=material, render_context=render_context)
                result = dict()
                result['umm_notification'] = 'incomplete_process'
                result['message'] = 'Not able to convert material "{0}" for render context "{1}" because there is no Conversion Graph for that scenario.'.format(instance_name, render_context)
                return result

    except Exception as error:
        print('Warning: Universal Material Map: function "convert_instance_to_data": Unexpected error:')
        print('\targument "instance_name" = "{0}"'.format(instance_name))
        print('\targument "render_context" = "{0}"'.format(render_context))
        print('\terror: {0}'.format(error))
        print('\tcallstack: {0}'.format(traceback.format_exc()))
        result = dict()
        result['umm_notification'] = 'unexpected_error'
        result['message'] = 'Not able to convert material "{0}" for render context "{1}" there was an unexpected error. Details: {2}'.format(instance_name, render_context, error)
        return result
    result = dict()
    result['umm_notification'] = 'incomplete_process'
    result['message'] = 'Not able to convert material "{0}" for render context "{1}" because there is no Conversion Graph for that scenario.'.format(instance_name, render_context)
    return result
