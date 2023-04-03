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
import sys

from .data import Plug


def to_plug_value_type(value: typing.Any, assumed_value_type: str) -> str:
    """Returns matching :class:`omni.universalmaterialmap.core.data.Plug` value type."""
    if sys.version_info.major < 3:
        if isinstance(value, basestring):
            return Plug.VALUE_TYPE_STRING
    else:
        if isinstance(value, str):
            return Plug.VALUE_TYPE_STRING

    if type(value) == bool:
        return Plug.VALUE_TYPE_BOOLEAN

    if isinstance(value, int):
        return Plug.VALUE_TYPE_INTEGER

    if isinstance(value, float):
        return Plug.VALUE_TYPE_FLOAT

    try:
        test = iter(value)
        is_iterable = True
    except TypeError:
        is_iterable = False

    if is_iterable:
        if assumed_value_type == Plug.VALUE_TYPE_LIST:
            return Plug.VALUE_TYPE_LIST

        bum_booleans = 0
        num_integers = 0
        num_floats = 0
        num_strings = 0
        for o in value:
            if sys.version_info.major < 3:
                if isinstance(value, basestring):
                    num_strings += 1
                    continue
            else:
                if isinstance(value, str):
                    num_strings += 1
                    continue

            if type(o) == bool:
                bum_booleans += 1
                continue
            if isinstance(o, int):
                num_integers += 1
                continue
            if isinstance(o, float):
                num_floats += 1

        if num_floats > 0:
            if len(value) == 2:
                return Plug.VALUE_TYPE_VECTOR2
            if len(value) == 3:
                return Plug.VALUE_TYPE_VECTOR3
            if len(value) == 4:
                return Plug.VALUE_TYPE_VECTOR4

        if len(value) == 2 and assumed_value_type == Plug.VALUE_TYPE_VECTOR2:
            return assumed_value_type

        if len(value) == 3 and assumed_value_type == Plug.VALUE_TYPE_VECTOR3:
            return assumed_value_type

        if len(value) == 4 and assumed_value_type == Plug.VALUE_TYPE_VECTOR4:
            return assumed_value_type

        return Plug.VALUE_TYPE_LIST

    return Plug.VALUE_TYPE_ANY


def get_extension_from_image_file_format(format:str, base_name:str) -> str:
    """
    For image formats that have multiple possible extensions,
    determine if we should stick with the current format specifier
    or use the one from the filename itself.
    """
    format = format.lower()
    split = base_name.rpartition(".")[-1]
    extension = split.lower() if len(split) else None

    if format == "open_exr":
        format = "exr"
    elif format == "jpeg":
        format = extension if extension in {"jpeg", "jpg"} else "jpg"
    elif format == "tiff":
        format = extension if extension in {"tiff", "tif"} else "tif"
    elif format == "targa_raw":
        format = "tga"
    return format
