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

"""
Convert Queries & Actions
#########################

DCC Connectors and other conversion solutions will want to use this module.

There are three different conversion strategies available:

1. Source *class* and *data*.
    The framework finds a suitable conversion template and returns data indicating a *target class* and data for setting its attributes.

    For example:

        .. code::

            from omni.universalmaterialmap.core.converter import util

            if util.can_convert_data_to_data(
                class_name='lambert',
                render_context='MDL',
                source_data=[
                    ('color', 'color_texture.png'),
                    ('normalCamera', 'normal_texture.png')
                ]):
                data = util.convert_data_to_data(
                    class_name='lambert',
                    render_context='MDL',
                    source_data=[
                        ('color', 'color_texture.png'),
                        ('normalCamera', 'normal_texture.png')
                    ]
                )

    ...could return:

        .. code::

            [
                ('umm_target_class', 'omnipbr'),
                ('diffuse_texture', 'color_texture.png'),
                ('normalmap_texture', 'normal_texture.png'),
            ]

    Note that the first value pair :code:`('umm_target_class', 'omnipbr')` indicates the object class that should be used for conversion. All other value pairs indicate attribute names and attribute values.

    Using this strategy puts very little responsibility on the conversion workers to understand assets. They merely have to apply the arguments to a conversion template, compute the internal graph, and spit out the results.
    It also means that the solution invoking the converter will have to gather the necessary arguments from some object or data source.

2. Source *instance* into conversion data.
    Here we use an object instance in order to get the same data as in strategy #1 above.

    For example:

        .. code::

            from omni.universalmaterialmap.core.converter import util

            if util.can_convert_instance(
                instance=MyLambertPyNode,
                render_context='MDL'):
                data = util.convert_instance_to_data(
                    instance=MyLambertPyNode,
                    render_context='MDL'
                )

    ...could return:

        .. code::

            [
                ('umm_target_class', 'omnipbr'),
                ('diffuse_texture', 'color_texture.png'),
                ('normalmap_texture', 'normal_texture.png'),
            ]

    Note that the first value pair :code:`('umm_target_class', 'omnipbr')` indicates the object class that should be used for conversion. All other value pairs indicate attribute names and attribute values.

    The advantage here is that the user of the framework can rely on a converter's understanding of objects and attributes.
    The downside is that there has to be an actual asset or dependency graph loaded.

3. Source *instance* into converted object.
    In this approach the converter will create a new object and set its properties/attributes based on a conversion template.

    For example:

    .. code::

        from omni.universalmaterialmap.core.converter import util

        if util.can_convert_instance(
            instance=MyLambertPyNode,
            render_context='MDL'):
            node = util.convert_instance_to_instance(
                instance=MyLambertPyNode,
                render_context='MDL'
            )

    ...could create and return an MDL material in the current Maya scene.

Manifest Query
##############

Module has methods for querying its conversion capabilities as indicated by library manifests.
This could be useful when wanting to expose commands for converting assets within a DCC application scene.

Note that this API does not require any data or object instance argument. It's a more *general* query.

.. code::

    from omni.universalmaterialmap.core.converter import util

    manifest = util.get_conversion_manifest()
    #   Returns data indicating what source class can be converted to a render context.
    #
    #   Example:
    #        [
    #            ('lambert', 'MDL'),
    #            ('blinn', 'MDL'),
    #        ]

    if (my_class_name, 'MDL') in manifest:
        # Do something

"""

import sys
import typing
import traceback

from .. import data
from .core import ICoreConverter, IDataConverter, IObjectConverter

_debug_mode = False

__converters: typing.List['ICoreConverter'] = []

TARGET_CLASS_IDENTIFIER = 'umm_target_class'


def register(converter: ICoreConverter) -> typing.NoReturn:
    """ Registers the converter at the top of the internal list - overriding previously registered converters - for future queries and processes. """
    converters = getattr(sys.modules[__name__], '__converters')
    if converter not in converters:
        if _debug_mode:
            print('UMM: core.converter.util: Registering converter: "{0}"'.format(converter))
        converters.insert(0, converter)
    elif _debug_mode:
        print('UMM: core.converter.util: Not registering converter because it is already registered: "{0}"'.format(converter))


def un_register(converter: ICoreConverter) -> typing.NoReturn:
    """ Removes the converter from internal list of converters and will ignore it for future queries and processes. """
    converters = getattr(sys.modules[__name__], '__converters')
    if converter in converters:
        if _debug_mode:
            print('UMM: core.converter.util: un-registering converter: "{0}"'.format(converter))
        converters.remove(converter)
    elif _debug_mode:
        print('UMM: core.converter.util: Not un-registering converter because it not registered to begin with: "{0}"'.format(converter))


def can_create_instance(class_name: str) -> bool:
    """ Resolves if a converter can create a node. """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IObjectConverter):
            if converter.can_create_instance(class_name=class_name):
                if _debug_mode:
                    print('UMM: core.converter.util: converter can create instance: "{0}"'.format(converter))
                return True
    if _debug_mode:
        print('UMM: core.converter.util: no converter can create instance.')
    return False


def create_instance(class_name: str) -> object:
    """ Creates an asset using the first converter in the internal list that supports the class_name. """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IObjectConverter):
            if converter.can_create_instance(class_name=class_name):
                if _debug_mode:
                    print('UMM: core.converter.util: converter creating instance: "{0}"'.format(converter))
                return converter.create_instance(class_name=class_name)
    raise Exception('Registered converters does not support class "{0}".'.format(class_name))


def can_set_plug_value(instance: object, plug: data.Plug) -> bool:
    """ Resolves if a converter can set the plug's value given the instance and its attributes. """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IObjectConverter):
            if _debug_mode:
                print('UMM: core.converter.util: converter can set plug value: "{0}"'.format(converter))
            if converter.can_set_plug_value(instance=instance, plug=plug):
                return True
    if _debug_mode:
        print('UMM: core.converter.util: converter cannot set plug value given instance "{0}" and plug "{1}"'.format(instance, plug))
    return False


def set_plug_value(instance: object, plug: data.Plug) -> typing.NoReturn:
    """ Sets the plug's value given the value of the instance's attribute named the same as the plug. """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IObjectConverter):
            if converter.can_set_plug_value(instance=instance, plug=plug):
                if _debug_mode:
                    print('UMM: core.converter.util: converter setting plug value: "{0}"'.format(converter))
                return converter.set_plug_value(instance=instance, plug=plug)
    raise Exception('Registered converters does not support action.')


def can_set_instance_attribute(instance: object, name: str) -> bool:
    """ Resolves if a converter can set an attribute by the given name on the instance. """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IObjectConverter):
            if _debug_mode:
                print('UMM: core.converter.util: converter can set instance attribute: "{0}", "{1}", "{2}"'.format(converter, instance, name))
            if converter.can_set_instance_attribute(instance=instance, name=name):
                return True
    if _debug_mode:
        print('UMM: core.converter.util: cannot set instance attribute: "{0}", "{1}"'.format(instance, name))
    return False


def set_instance_attribute(instance: object, name: str, value: typing.Any) -> typing.NoReturn:
    """ Sets the named attribute on the instance to the value. """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IObjectConverter):
            if converter.can_set_instance_attribute(instance=instance, name=name):
                if _debug_mode:
                    print('UMM: core.converter.util: converter setting instance attribute: "{0}", "{1}", "{2}", "{3}"'.format(converter, instance, name, value))
                return converter.set_instance_attribute(instance=instance, name=name, value=value)
    raise Exception('Registered converters does not support action.')


def can_convert_instance(instance: object, render_context: str) -> bool:
    """ Resolves if a converter can convert the instance to another object given the render_context. """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IObjectConverter):
            if _debug_mode:
                print('UMM: core.converter.util: converter can convert instance: "{0}", "{1}", "{2}"'.format(converter, instance, render_context))
            if converter.can_convert_instance(instance=instance, render_context=render_context):
                return True
    return False


def convert_instance_to_instance(instance: object, render_context: str) -> typing.Any:
    """ Interprets the instance and instantiates another object given the render_context. """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IObjectConverter):
            if converter.can_convert_instance(instance=instance, render_context=render_context):
                if _debug_mode:
                    print('UMM: core.converter.util: converter converting instance: "{0}", "{1}", "{2}"'.format(converter, instance, render_context))
                return converter.convert_instance_to_instance(instance=instance, render_context=render_context)
    raise Exception('Registered converters does not support action.')


def can_convert_instance_to_data(instance: object, render_context: str) -> bool:
    """ Resolves if a converter can convert the instance to another object given the render_context. """
    try:
        converters = getattr(sys.modules[__name__], '__converters')
        for converter in converters:
            if isinstance(converter, IObjectConverter):
                if converter.can_convert_instance_to_data(instance=instance, render_context=render_context):
                    return True
    except Exception as error:
        print('Warning: Universal Material Map: function "can_convert_instance_to_data": Unexpected error:')
        print('\targument "instance" = "{0}"'.format(instance))
        print('\targument "render_context" = "{0}"'.format(render_context))
        print('\terror: {0}'.format(error))
        print('\tcallstack: {0}'.format(traceback.format_exc()))
    return False


def convert_instance_to_data(instance: object, render_context: str) -> typing.List[typing.Tuple[str, typing.Any]]:
    """
    Returns a list of key value pairs in tuples.
    The first pair is ("umm_target_class", "the_class_name") indicating the conversion target class.
    """
    try:
        converters = getattr(sys.modules[__name__], '__converters')
        for converter in converters:
            if isinstance(converter, IObjectConverter):
                if converter.can_convert_instance_to_data(instance=instance, render_context=render_context):
                    result = converter.convert_instance_to_data(instance=instance, render_context=render_context)
                    print('Universal Material Map: convert_instance_to_data({0}, "{1}") generated data:'.format(instance, render_context))
                    print('\t(')
                    for o in result:
                        print('\t\t{0}'.format(o))
                    print('\t)')
                    return result
    except Exception as error:
        print('Warning: Universal Material Map: function "convert_instance_to_data": Unexpected error:')
        print('\targument "instance" = "{0}"'.format(instance))
        print('\targument "render_context" = "{0}"'.format(render_context))
        print('\terror: {0}'.format(error))
        print('\tcallstack: {0}'.format(traceback.format_exc()))
        result = dict()
        result['umm_notification'] = 'unexpected_error'
        result['message'] = 'Not able to convert "{0}" for render context "{1}" because there was an unexpected error. Details: {2}'.format(instance, render_context, error)
        return result
    raise Exception('Registered converters does not support action.')


def can_convert_attribute_values(instance: object, render_context: str, destination: object) -> bool:
    """ Resolves if the instance's attribute values can be converted and set on the destination object's attributes. """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IObjectConverter):
            if converter.can_convert_attribute_values(instance=instance, render_context=render_context, destination=destination):
                return True
    return False


def convert_attribute_values(instance: object, render_context: str, destination: object) -> typing.NoReturn:
    """ Attribute values are converted and set on the destination object's attributes. """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IObjectConverter):
            if converter.can_convert_attribute_values(instance=instance, render_context=render_context, destination=destination):
                return converter.convert_attribute_values(instance=instance, render_context=render_context, destination=destination)
    raise Exception('Registered converters does not support action.')


def can_convert_data_to_data(class_name: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]]) -> bool:
    """ Resolves if a converter can convert the given class and source_data to another class and target data. """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IDataConverter):
            if converter.can_convert_data_to_data(class_name=class_name, render_context=render_context, source_data=source_data):
                return True
    return False


def convert_data_to_data(class_name: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]]) -> typing.List[typing.Tuple[str, typing.Any]]:
    """
    Returns a list of key value pairs in tuples.
    The first pair is ("umm_target_class", "the_class_name") indicating the conversion target class.
    """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IDataConverter):
            if converter.can_convert_data_to_data(class_name=class_name, render_context=render_context, source_data=source_data):
                result = converter.convert_data_to_data(class_name=class_name, render_context=render_context, source_data=source_data)
                print('Universal Material Map: convert_data_to_data("{0}", "{1}") generated data:'.format(class_name, render_context))
                print('\t(')
                for o in result:
                    print('\t\t{0}'.format(o))
                print('\t)')
                return result
    raise Exception('Registered converters does not support action.')


def can_apply_data_to_instance(source_class_name: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]], instance: object) -> bool:
    """ Resolves if a converter can create one or more instances given the arguments. """
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        if isinstance(converter, IObjectConverter):
            if converter.can_apply_data_to_instance(source_class_name=source_class_name, render_context=render_context, source_data=source_data, instance=instance):
                return True
    return False


def apply_data_to_instance(source_class_name: str, render_context: str, source_data: typing.List[typing.Tuple[str, typing.Any]], instance: object) -> dict:
    """
    Returns a list of created objects.
    """
    try:
        converters = getattr(sys.modules[__name__], '__converters')
        for converter in converters:
            if isinstance(converter, IObjectConverter):
                if converter.can_apply_data_to_instance(source_class_name=source_class_name, render_context=render_context, source_data=source_data, instance=instance):
                    converter.apply_data_to_instance(source_class_name=source_class_name, render_context=render_context, source_data=source_data, instance=instance)
                    print('Universal Material Map: apply_data_to_instance("{0}", "{1}") completed.'.format(instance, render_context))
                    result = dict()
                    result['umm_notification'] = 'success'
                    result['message'] = 'Material conversion data applied to "{0}".'.format(instance)
                    return result
        result = dict()
        result['umm_notification'] = 'incomplete_process'
        result['message'] = 'Not able to convert type "{0}" for render context "{1}" because there is no Conversion Graph for that scenario. No changes were applied to "{2}".'.format(source_class_name, render_context, instance)
        return result
    except Exception as error:
        print('UMM: Unexpected error: {0}'.format(traceback.format_exc()))
        result = dict()
        result['umm_notification'] = 'unexpected_error'
        result['message'] = 'Not able to convert type "{0}" for render context "{1}" because there was an unexpected error. Some changes may have been applied to "{2}". Details: {3}'.format(source_class_name, render_context, instance, error)
        return result


def get_conversion_manifest() -> typing.List[typing.Tuple[str, str]]:
    """
    Returns data indicating what source class can be converted to a render context.

    Example: [('lambert', 'MDL'), ('blinn', 'MDL'),]
    """
    manifest: typing.List[typing.Tuple[str, str]] = []
    converters = getattr(sys.modules[__name__], '__converters')
    for converter in converters:
        manifest.extend(converter.get_conversion_manifest())
    return manifest

