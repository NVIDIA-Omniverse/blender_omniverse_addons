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
import os
import shutil
import json
import inspect

from ...data import FileUtility, Target, ConversionGraph, ConversionManifest


def __copy(source_path: str, destination_path: str) -> None:
    try:
        shutil.copy(source_path, destination_path)
    except Exception as error:
        print('Error installing UMM data. Unable to copy source "{0}" to destination "{1}".\n Details: {2}'.format(source_path, destination_path, error))
        raise error


def __install_library(source_root: str, destination_root: str) -> None:
    source_root = source_root.replace('\\', '/')
    destination_root = destination_root.replace('\\', '/')
    for directory, sub_directories, filenames in os.walk(source_root):
        directory = directory.replace('\\', '/')
        destination_directory = directory.replace(source_root, destination_root)
        destination_directory_created = os.path.exists(destination_directory)
        for filename in filenames:
            if not filename.lower().endswith('.json'):
                continue
            source_path = '{0}/{1}'.format(directory, filename)
            destination_path = '{0}/{1}'.format(destination_directory, filename)
            if not destination_directory_created:
                try:
                    os.makedirs(destination_directory)
                    destination_directory_created = True
                except Exception as error:
                    print('Universal Material Map error installing data. Unable to create directory "{0}".\n Details: {1}'.format(destination_directory, error))
                    raise error

            if not os.path.exists(destination_path):
                __copy(source_path=source_path, destination_path=destination_path)
                print('Universal Material Map installed "{0}".'.format(destination_path))
                continue

            try:
                with open(source_path, 'r') as fp:
                    source = FileUtility.FromData(data=json.load(fp)).content
            except Exception as error:
                print('Universal Material Map error installing data. Unable to read source "{0}". \n Details: {1}'.format(source_path, error))
                raise error

            try:
                with open(destination_path, 'r') as fp:
                    destination = FileUtility.FromData(data=json.load(fp)).content
            except Exception as error:
                print('Warning: Universal Material Map error installing data. Unable to read destination "{0}". It is assumed that the installed version is more recent than the one attempted to be installed.\n Details: {1}'.format(destination_path, error))
                continue

            if isinstance(source, Target) and isinstance(destination, Target):
                if source.revision > destination.revision:
                    __copy(source_path=source_path, destination_path=destination_path)
                    print('Universal Material Map installed the more recent revision #{0} of "{1}".'.format(source.revision, destination_path))
                continue

            if isinstance(source, ConversionGraph) and isinstance(destination, ConversionGraph):
                if source.revision > destination.revision:
                    __copy(source_path=source_path, destination_path=destination_path)
                    print('Universal Material Map installed the more recent revision #{0} of "{1}".'.format(source.revision, destination_path))
                continue

            if isinstance(source, ConversionManifest) and isinstance(destination, ConversionManifest):
                if source.version_major < destination.version_major:
                    continue
                if source.version_minor <= destination.version_minor:
                    continue
                __copy(source_path=source_path, destination_path=destination_path)
                print('Universal Material Map installed the more recent revision #{0}.{1} of "{2}".'.format(source.version_major, source.version_minor, destination_path))
                continue


def install() -> None:
    current_path = inspect.getfile(inspect.currentframe()).replace('\\', '/')
    current_path = current_path[:current_path.rfind('/')]

    library_names = []
    for o in os.listdir(current_path):
        path = '{0}/{1}'.format(current_path, o)
        if os.path.isdir(path) and not o == '__pycache__':
            library_names.append(o)

    libraries_directory = os.path.expanduser('~').replace('\\', '/')
    if not libraries_directory.endswith('/Documents'):
        # os.path.expanduser() has different behaviour between 2.7 and 3
        libraries_directory = '{0}/Documents'.format(libraries_directory)
    libraries_directory = '{0}/Omniverse'.format(libraries_directory)

    for library_name in library_names:
        source_root = '{0}/{1}/UMMLibrary'.format(current_path, library_name)
        destination_root = '{0}/{1}/UMMLibrary'.format(libraries_directory, library_name)
        __install_library(source_root=source_root, destination_root=destination_root)
