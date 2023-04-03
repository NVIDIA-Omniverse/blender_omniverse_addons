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

import sys
import typing

from ..data import Library, Target
from .core import IGenerator

__generators: typing.List['IGenerator'] = []


def register(generator: IGenerator) -> typing.NoReturn:
    """ Registers the generator at the top of the internal list - overriding previously registered generators - for future queries and processes. """
    generators = getattr(sys.modules[__name__], '__generators')
    if generator not in generators:
        generators.insert(0, generator)


def un_register(generator: IGenerator) -> typing.NoReturn:
    """ Removes the generator from internal list of generators and will ignore it for future queries and processes. """
    generators = getattr(sys.modules[__name__], '__generators')
    if generator in generators:
        generators.remove(generator)


def can_generate_target(class_name: str) -> bool:
    """ """
    generators = getattr(sys.modules[__name__], '__generators')
    for generator in generators:
        if generator.can_generate_target(class_name=class_name):
            return True
    return False


def generate_target(class_name: str) -> typing.Tuple[Library, Target]:
    """ """
    generators = getattr(sys.modules[__name__], '__generators')
    for generator in generators:
        if generator.can_generate_target(class_name=class_name):
            print('UMM using generator "{0}" for class_name "{1}".'.format(generator, class_name))
            return generator.generate_target(class_name=class_name)
    raise Exception('Registered generators does not support action.')


def generate_targets() -> typing.List[typing.Tuple[Library, Target]]:
    """ Generates targets from all registered workers that are able to. """
    targets = []
    generators = getattr(sys.modules[__name__], '__generators')
    for generator in generators:
        if generator.can_generate_targets():
            print('UMM using generator "{0}" for generating targets.'.format(generator))
            targets.extend(generator.generate_targets())
    return targets


def can_generate_target_from_instance(instance: object) -> bool:
    """ """
    generators = getattr(sys.modules[__name__], '__generators')
    for generator in generators:
        if generator.can_generate_target_from_instance(instance=instance):
            return True
    return False


def generate_target_from_instance(instance: object) -> typing.List[typing.Tuple[Library, Target]]:
    """ Generates targets from all registered workers that are able to. """
    generators = getattr(sys.modules[__name__], '__generators')
    for generator in generators:
        if generator.can_generate_target_from_instance(instance=instance):
            print('UMM using generator "{0}" for instance "{1}".'.format(generator, instance))
            return generator.generate_target_from_instance(instance=instance)
