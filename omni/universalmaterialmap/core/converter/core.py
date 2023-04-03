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

from ..data import Plug


class ICoreConverter(metaclass=ABCMeta):
    """ """

    @abstractmethod
    def __init__(self):
        super(ICoreConverter, self).__init__()

    @abstractmethod
    def get_conversion_manifest(self) -> typing.List[typing.Tuple[str, str]]:
        """
        Returns data indicating what source class can be converted to a render context.

        Example: [('lambert', 'MDL'), ('blinn', 'MDL'),]
        """
        raise NotImplementedError()


class IObjectConverter(ICoreConverter):
    """ """

    @abstractmethod
    def can_create_instance(self, class_name: str) -> bool:
        """ Returns true if worker can generate an object of the given class name. """
        raise NotImplementedError()

    @abstractmethod
    def create_instance(self, class_name: str) -> object:
        """ Creates an object of the given class name. """
        raise NotImplementedError()

    @abstractmethod
    def can_set_plug_value(self, instance: object, plug: Plug) -> bool:
        """ Returns true if worker can set the plug's value given the instance and its attributes. """
        raise NotImplementedError()

    @abstractmethod
    def set_plug_value(self, instance: object, plug: Plug) -> typing.NoReturn:
        """ Sets the plug's value given the value of the instance's attribute named the same as the plug. """
        raise NotImplementedError()

    @abstractmethod
    def can_set_instance_attribute(self, instance: object, name: str):
        """ Resolves if worker can set an attribute by the given name on the instance. """
        return False

    @abstractmethod
    def set_instance_attribute(self, instance: object, name: str, value: typing.Any) -> typing.NoReturn:
        """ Sets the named attribute on the instance to the value. """
        raise NotImplementedError()

    @abstractmethod
    def can_convert_instance(self, instance: object, render_context: str) -> bool:
        """ Resolves if worker can convert the instance to another object given the render_context. """
        return False

    @abstractmethod
    def convert_instance_to_instance(self, instance: object, render_context: str) -> typing.Any:
        """ Converts the instance to another object given the render_context. """
        raise NotImplementedError()

    @abstractmethod
    def can_convert_instance_to_data(self, instance: object, render_context: str) -> bool:
        """ Resolves if worker can convert the instance to another object given the render_context. """
        return False

    @abstractmethod
    def convert_instance_to_data(self, instance: object, render_context: str) -> typing.List[typing.Tuple[str, typing.Any]]:
        """
        Returns a list of key value pairs in tuples.
        The first pair is ("umm_target_class", "the_class_name") indicating the conversion target class.
        """
        raise NotImplementedError()

    @abstractmethod
    def can_convert_attribute_values(self, instance: object, render_context: str, destination: object) -> bool:
        """ Resolves if the instance's attribute values can be converted and set on the destination object's attributes. """
        raise NotImplementedError()

    @abstractmethod
    def convert_attribute_values(self, instance: object, render_context: str, destination: object) -> typing.NoReturn:
        """ Attribute values are converted and set on the destination object's attributes. """
        raise NotImplementedError()

    @abstractmethod
    def can_apply_data_to_instance(self, source_class_name: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]], instance: object) -> bool:
        """ Resolves if worker can convert the instance to another object given the render_context. """
        return False

    @abstractmethod
    def apply_data_to_instance(self, source_class_name: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]], instance: object) -> dict:
        """
        Returns a notification object

        Examples:
            {
                'umm_notification': "success",
                'message': "Material \"Material_A\" was successfully converted from \"OmniPBR\" data."
            }

            {
                'umm_notification': "incomplete_process",
                'message': "Not able to convert \"Material_B\" using \"CustomMDL\" since there is no Conversion Graph supporting that scenario."
            }

            {
                'umm_notification': "unexpected_error",
                'message': "Not able to convert \"Material_C\" using \"OmniGlass\" due to an unexpected error. Details: \"cannot set property to None\"."
            }
        """
        raise NotImplementedError()


class IDataConverter(ICoreConverter):
    """ """

    @abstractmethod
    def can_convert_data_to_data(self, class_name: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]]) -> bool:
        """ Resolves if worker can convert the given class and source_data to another class and target data. """
        return False

    @abstractmethod
    def convert_data_to_data(self, class_name: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]]) -> typing.List[typing.Tuple[str, typing.Any]]:
        """
        Returns a list of key value pairs in tuples.
        The first pair is ("umm_target_class", "the_class_name") indicating the conversion target class.
        """
        raise NotImplementedError()
