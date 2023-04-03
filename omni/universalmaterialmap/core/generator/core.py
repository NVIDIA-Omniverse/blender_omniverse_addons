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

from abc import ABCMeta, abstractmethod
import typing

from ..data import Library, Target


class IGenerator(metaclass=ABCMeta):
    """ """

    @abstractmethod
    def __init__(self):
        super(IGenerator, self).__init__()

    @abstractmethod
    def can_generate_target(self, class_name: str) -> bool:
        """ """
        pass

    @abstractmethod
    def generate_target(self, class_name: str) -> typing.Tuple[Library, Target]:
        """ """
        pass

    @abstractmethod
    def can_generate_targets(self) -> bool:
        """ """
        pass

    @abstractmethod
    def generate_targets(self) -> typing.List[typing.Tuple[Library, Target]]:
        """ """
        pass

    @abstractmethod
    def can_generate_target_from_instance(self, instance: object) -> bool:
        """ """
        pass

    @abstractmethod
    def generate_target_from_instance(self, instance: object) -> typing.Tuple[Library, Target]:
        """ """
        pass
