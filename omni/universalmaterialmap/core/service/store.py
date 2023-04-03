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
import os
import uuid
import traceback

from .. import data
from .. import operator
from ..feature import POLLING
from ..singleton import Singleton
from .core import ChangeEvent, IDelegate
from .delegate import Filesystem, FilesystemManifest, FilesystemSettings
from .resources import install

COMMON_LIBRARY_ID = '327ef29b-8358-441b-b2f0-4a16a9afd349'

libraries_directory = os.path.expanduser('~').replace('\\', '/')
if not libraries_directory.endswith('/Documents'):
    # os.path.expanduser() has different behaviour between 2.7 and 3
    libraries_directory = '{0}/Documents'.format(libraries_directory)
libraries_directory = '{0}/Omniverse'.format(libraries_directory)

common_library_directory = '{0}/ConnectorCommon/UMMLibrary'.format(libraries_directory)
cache_directory = '{0}/Cache'.format(common_library_directory)

COMMON_LIBRARY = data.Library.Create(
    library_id=COMMON_LIBRARY_ID,
    name='Common',
    manifest=FilesystemManifest(root_directory='{0}'.format(common_library_directory)),
    conversion_graph=Filesystem(root_directory='{0}/ConversionGraph'.format(common_library_directory)),
    target=Filesystem(root_directory='{0}/Target'.format(common_library_directory)),
    settings=FilesystemSettings(root_directory='{0}'.format(common_library_directory)),
)

DEFAULT_LIBRARIES = [COMMON_LIBRARY]


class _ItemProvider(object):

    """ Class provides IO interface for a single UMM Library item. """

    def __init__(self, identifier: str, library_delegate: IDelegate = None, cache_delegate: IDelegate = None):
        super(_ItemProvider, self).__init__()
        self._library_delegate: typing.Union[IDelegate, typing.NoReturn] = library_delegate
        self._cache_delegate: typing.Union[IDelegate, typing.NoReturn] = cache_delegate
        self._identifier: str = identifier
        self._file_util: typing.Union[data.FileUtility, typing.NoReturn] = None
        self._content_cache: dict = dict()

    def revert(self) -> None:
        if self._file_util:
            self._file_util.content.deserialize(data=self._content_cache)

    def has_unsaved_changes(self) -> bool:
        if not self._file_util:
            return False
        return not self._file_util.content.serialize() == self._content_cache

    def read(self, update: bool = False) -> None:
        """
        TODO: Check if path has changed since last read from disk.
        """
        if not self._library_delegate and not self._cache_delegate:
            raise Exception('Not supported: No delegate available to read().')

        # update_cache() assumes that read() prioritizes reading with library delegate!
        delegate = self._library_delegate if self._library_delegate else self._cache_delegate
        if not self._file_util:
            contents = delegate.read(identifier=self._identifier)
            if contents is not None:
                self._file_util = data.FileUtility.FromData(data=contents)
                self._update_content_cache()
        elif update:
            contents = delegate.read(identifier=self._identifier)
            self._file_util.content.deserialize(data=contents)

    def create(self, instance: data.Serializable) -> None:
        self._file_util = data.FileUtility.FromInstance(instance=instance)
        self.write()

    def write(self, content: data.Serializable = None) -> None:
        if not self._library_delegate and not self._cache_delegate:
            raise Exception('Not supported: No delegate available to write().')

        if content:
            if not self._file_util:
                self._file_util = data.FileUtility.FromInstance(instance=content)
            else:
                self._file_util._content = content
        elif not self._file_util:
            raise Exception('Not supported: _ItemProvider not initialized properly prior to "write()"')

        contents = self._file_util.serialize()
        if self._library_delegate:
            self._library_delegate.write(identifier=self._identifier, contents=contents)
        if self._cache_delegate:
            self._cache_delegate.write(identifier=self._identifier, contents=contents)

        self._update_content_cache()

    def delete(self) -> None:
        if not self._library_delegate and not self._cache_delegate:
            raise Exception('Not supported: No delegate available to delete().')

        if self._library_delegate:
            self._library_delegate.delete(identifier=self._identifier)
        if self._cache_delegate:
            self._cache_delegate.delete(identifier=self._identifier)

        self._file_util = None
        self._content_cache = None

    def _update_content_cache(self) -> None:
        if not self._file_util:
            self._content_cache = dict()
        else:
            self._content_cache = self._file_util.content.serialize()

    def update_cache(self) -> bool:
        if not self._library_delegate or not self._cache_delegate:
            return False
        # Assumes that read() prioritizes reading with library delegate!
        try:
            self.read()
        except Exception as error:
            print('Warning: Universal Material Map error reading data with identifier "{0}". Cache will not be updated due to the read error.\n\tDetails: "{1}".\n\tCallstack: {2}'.format(self._identifier, error, traceback.format_exc()))
            return False
        self._cache_delegate.write(identifier=self._identifier, contents=self._file_util.serialize())

    def on_shutdown(self):
        self._cache_delegate = None
        self._library_delegate = None
        self._identifier = None
        self._file_util = None
        self._content_cache = None

    @property
    def content(self) -> data.Serializable:
        return self._file_util.content


class _LibraryProvider(object):
    """ Class provides IO interface for a single UMM Library. """

    @staticmethod
    def _transfer_data(source: IDelegate, target: IDelegate) -> bool:
        """ Returns True if transfer was made. """
        if not source or not target:
            return False
        for identifier in source.get_ids():
            target.write(identifier=identifier, contents=source.read(identifier=identifier))
        return True

    def __init__(self, library: data.Library):
        super(_LibraryProvider, self).__init__()
        self._library: data.Library = library

        if POLLING:
            self._manifest_subscription: uuid.uuid4 = None
            self._conversion_graph_subscription: uuid.uuid4 = None
            self._target_subscription: uuid.uuid4 = None

        self._manifest_cache: typing.Union[IDelegate, typing.NoReturn] = None
        self._conversion_graph_cache: typing.Union[IDelegate, typing.NoReturn] = None
        self._target_cache: typing.Union[IDelegate, typing.NoReturn] = None
        self._settings_cache: typing.Union[IDelegate, typing.NoReturn] = None

        self._manifest_providers: typing.Dict[str, _ItemProvider] = dict()
        self._conversion_graph_providers: typing.Dict[str, _ItemProvider] = dict()
        self._target_providers: typing.Dict[str, _ItemProvider] = dict()
        self._settings_providers: typing.Dict[str, _ItemProvider] = dict()

        self._initialize()

    def _initialize(self) -> None:

        cache: _ItemProvider
        for cache in self._manifest_providers.values():
            cache.on_shutdown()
        for cache in self._conversion_graph_providers.values():
            cache.on_shutdown()
        for cache in self._target_providers.values():
            cache.on_shutdown()
        for cache in self._settings_providers.values():
            cache.on_shutdown()

        self._manifest_providers = dict()
        self._conversion_graph_providers = dict()
        self._target_providers = dict()
        self._settings_providers = dict()

        if not self._library:
            return

        if not self._library.id == COMMON_LIBRARY_ID:
            self._manifest_cache = FilesystemManifest(
                root_directory='{0}/{1}'.format(cache_directory, self._library.id)
            )
            self._conversion_graph_cache = Filesystem(
                root_directory='{0}/{1}/ConversionGraph'.format(cache_directory, self._library.id)
            )
            self._target_cache = Filesystem(
                root_directory='{0}/{1}/Target'.format(cache_directory, self._library.id)
            )
            self._settings_cache = FilesystemSettings(
                root_directory='{0}/{1}'.format(cache_directory, self._library.id)
            )

        if not self._library.id == COMMON_LIBRARY_ID and not self._library.is_read_only:
            self._update_cache()

    def _update_cache(self) -> None:
        if self._library.is_read_only:
            return

        self._update_cache_table(
            source=self._library.manifest,
            target=self._manifest_cache,
            providers=self._manifest_providers,
        )

        self._update_cache_table(
            source=self._library.conversion_graph,
            target=self._conversion_graph_cache,
            providers=self._conversion_graph_providers,
        )

        self._update_cache_table(
            source=self._library.target,
            target=self._target_cache,
            providers=self._target_providers,
        )

        self._update_cache_table(
            source=self._library.settings,
            target=self._settings_cache,
            providers=self._settings_providers,
        )

    def _update_cache_table(self, source: IDelegate, target: IDelegate, providers: dict) -> None:

        if self._library.is_read_only:
            return

        if not source or not target:
            return

        for identifier in source.get_ids():
            if identifier not in providers.keys():
                provider = _ItemProvider(
                    identifier=identifier,
                    library_delegate=source,
                    cache_delegate=target
                )
                providers[identifier] = provider
            else:
                provider = providers[identifier]
            provider.update_cache()

    def get_settings(self) -> typing.List[data.Settings]:
        if not self._library.settings:
            return []
        settings: typing.List[data.Settings] = []
        for identifier in self._library.settings.get_ids():
            if identifier not in self._settings_providers.keys():
                cache = _ItemProvider(
                    identifier=identifier,
                    library_delegate=self._library.settings,
                    cache_delegate=self._settings_cache
                )
                self._settings_providers[identifier] = cache
            else:
                cache = self._settings_providers[identifier]

            cache.read()

            setting = typing.cast(data.Settings, cache.content)
            settings.append(setting)

        return settings

    def get_manifests(self) -> typing.List[data.ConversionManifest]:
        delegate = self._library.manifest if self._library.manifest else self._manifest_cache
        if not delegate:
            return []

        manifests: typing.List[data.ConversionManifest] = []
        conversion_graphs: typing.List[data.ConversionGraph] = None

        for identifier in delegate.get_ids():
            if identifier not in self._manifest_providers.keys():
                cache = _ItemProvider(
                    identifier=identifier,
                    library_delegate=self._library.manifest,
                    cache_delegate=self._manifest_cache
                )
                self._manifest_providers[identifier] = cache
            else:
                cache = self._manifest_providers[identifier]

            cache.read()
            manifest = typing.cast(data.ConversionManifest, cache.content)

            if not conversion_graphs:
                conversion_graphs = self.get_conversion_graphs()

            for item in manifest.conversion_maps:
                if not item._conversion_graph:
                    for conversion_graph in conversion_graphs:
                        if conversion_graph.id == item.conversion_graph_id:
                            item._conversion_graph = conversion_graph
                            break

            manifests.append(manifest)

        if POLLING:
            if self._library.manifest and not self._manifest_subscription:
                self._manifest_subscription = self._library.manifest.add_change_subscription(callback=self._on_store_manifest_changes)

        return manifests

    def get_conversion_graphs(self) -> typing.List[data.ConversionGraph]:
        delegate = self._library.conversion_graph if self._library.conversion_graph else self._conversion_graph_cache
        if not delegate:
            return []

        conversion_graphs: typing.List[data.ConversionGraph] = []
        for identifier in delegate.get_ids():
            if identifier not in self._conversion_graph_providers.keys():
                cache = _ItemProvider(
                    identifier=identifier,
                    library_delegate=self._library.conversion_graph,
                    cache_delegate=self._conversion_graph_cache
                )
                try:
                    cache.read()
                except Exception as error:
                    print('Warning: Universal Material Map error reading Conversion Graph data with identifier "{0}". Graph will not be available for use inside UMM.\n\tDetails: "{1}".\n\tCallstack: {2}'.format(identifier, error, traceback.format_exc()))
                    continue
                self._conversion_graph_providers[identifier] = cache
            else:
                cache = self._conversion_graph_providers[identifier]
                try:
                    cache.read()
                except Exception as error:
                    print('Warning: Universal Material Map error reading Conversion Graph data with identifier "{0}". Graph will not be available for use inside UMM.\n\tDetails: "{1}".\n\tCallstack: {2}'.format(identifier, error, traceback.format_exc()))
                    continue

            conversion_graph = typing.cast(data.ConversionGraph, cache.content)
            conversion_graph._library = self._library
            conversion_graph.filename = identifier
            conversion_graph._exists_on_disk = True
            conversion_graphs.append(conversion_graph)

        if POLLING:
            if self._library.conversion_graph and not self._conversion_graph_subscription:
                self._conversion_graph_subscription = self._library.conversion_graph.add_change_subscription(callback=self._on_store_conversion_graph_changes)

        return conversion_graphs

    def get_targets(self) -> typing.List[data.Target]:
        delegate = self._library.target if self._library.target else self._target_cache
        if not delegate:
            return []
        targets: typing.List[data.Target] = []
        for identifier in delegate.get_ids():
            if identifier not in self._target_providers.keys():
                cache = _ItemProvider(
                    identifier=identifier,
                    library_delegate=self._library.target,
                    cache_delegate=self._target_cache
                )
                self._target_providers[identifier] = cache
            else:
                cache = self._target_providers[identifier]

            cache.read()
            target = typing.cast(data.Target, cache.content)
            target.store_id = identifier
            targets.append(target)

        if POLLING:
            if self._library.target and not self._target_subscription:
                self._target_subscription = self._library.target.add_change_subscription(callback=self._on_store_target_changes)

        return targets

    def _on_store_manifest_changes(self, event: ChangeEvent) -> None:
        if not POLLING:
            raise NotImplementedError()
        print('_on_store_manifest_changes', event)

    def _on_store_conversion_graph_changes(self, event: ChangeEvent) -> None:
        if not POLLING:
            raise NotImplementedError()
        print('_on_store_conversion_graph_changes', event)

    def _on_store_target_changes(self, event: ChangeEvent) -> None:
        if not POLLING:
            raise NotImplementedError()
        print('_on_store_target_changes...', event, self)

    def revert(self, item: data.Serializable) -> bool:
        """
        Returns True if the item existed in a data store and was successfully reverted.
        """
        if isinstance(item, data.ConversionGraph):
            if item.filename not in self._conversion_graph_providers.keys():
                return False
            filename = item.filename
            library = item.library
            cache = self._conversion_graph_providers[item.filename]
            cache.revert()
            item.filename = filename
            item._library = library
            item._exists_on_disk = True
            return True

        if isinstance(item, data.Target):
            if item.store_id not in self._target_providers.keys():
                return False
            cache = self._target_providers[item.store_id]
            cache.revert()
            return True

        if isinstance(item, data.ConversionManifest):
            if item.store_id not in self._manifest_providers.keys():
                return False
            cache = self._manifest_providers[item.store_id]
            cache.revert()
            return True

        if isinstance(item, data.Settings):
            if item.store_id not in self._settings_providers.keys():
                return False
            cache = self._settings_providers[item.store_id]
            cache.revert()
            return True

    def write(self, item: data.Serializable, identifier: str = None, overwrite: bool = False) -> None:
        if isinstance(item, data.Settings):
            if not item.store_id:
                raise Exception('Not supported: Settings must have a valid store id in order to write the item.')
            if not self._library.settings:
                raise Exception('Library "{0}" with id="{1}" does not support a Settings store.'.format(self._library.name, self._library.id))
            if item.store_id not in self._settings_providers.keys():
                cache = _ItemProvider(
                    identifier=item.store_id,
                    library_delegate=self._library.settings,
                    cache_delegate=self._settings_cache
                )
                self._settings_providers[item.store_id] = cache
            else:
                if not overwrite:
                    return

                cache = self._settings_providers[item.store_id]
            cache.write(content=item)
            return

        if isinstance(item, data.ConversionManifest):
            if not item.store_id:
                raise Exception('Not supported: Conversion Manifest must have a valid store id in order to write the item.')
            if item.store_id not in self._manifest_providers.keys():
                cache = _ItemProvider(
                    identifier=item.store_id,
                    library_delegate=self._library.manifest,
                    cache_delegate=self._manifest_cache
                )
                self._manifest_providers[item.store_id] = cache
            else:
                if not overwrite:
                    return

                cache = self._manifest_providers[item.store_id]
            cache.write(content=item)
            return

        if isinstance(item, data.ConversionGraph):
            if not item.filename and not identifier:
                raise Exception('Not supported: Conversion Manifest must have a valid store id in order to write the item.')

            key = identifier if identifier else item.filename

            if key not in self._conversion_graph_providers.keys():
                cache = _ItemProvider(
                    identifier=key,
                    library_delegate=self._library.conversion_graph,
                    cache_delegate=self._conversion_graph_cache
                )
                self._conversion_graph_providers[key] = cache
            else:
                if not overwrite:
                    return

                cache = self._conversion_graph_providers[key]
            item.revision += 1
            cache.write(content=item)

            if identifier:
                item.filename = identifier
                item._exists_on_disk = True

            item._library = self._library

            return

        if isinstance(item, data.Target):
            if not item.store_id:
                raise Exception(
                    'Not supported: Conversion Manifest must have a valid store id in order to write the item.')

            if item.store_id not in self._target_providers.keys():
                cache = _ItemProvider(
                    identifier=item.store_id,
                    library_delegate=self._library.target,
                    cache_delegate=self._target_cache
                )
                self._target_providers[item.store_id] = cache
            else:
                if not overwrite:
                    return

                cache = self._target_providers[item.store_id]
            cache.write(content=item)
            return

        raise NotImplementedError()

    def delete(self, item: data.Serializable) -> None:
        if isinstance(item, data.Settings):
            if not item.store_id:
                raise Exception('Not supported: Settings must have a valid store id in order to write the item.')
            if not self._library.settings:
                raise Exception('Library "{0}" with id="{1}" does not support a Settings store.'.format(self._library.name, self._library.id))
            if item.store_id not in self._settings_providers.keys():
                return

            cache = self._settings_providers[item.store_id]
            cache.delete()
            cache.on_shutdown()
            del self._settings_providers[item.store_id]
            return

        if isinstance(item, data.ConversionManifest):
            if not item.store_id:
                raise Exception('Not supported: Conversion Manifest must have a valid store id in order to write the item.')
            if item.store_id not in self._manifest_providers.keys():
                return

            cache = self._manifest_providers[item.store_id]
            cache.delete()
            cache.on_shutdown()
            del self._manifest_providers[item.store_id]
            return

        if isinstance(item, data.ConversionGraph):
            if not item.filename:
                raise Exception('Not supported: Conversion Manifest must have a valid store id in order to write the item.')

            if item.filename not in self._conversion_graph_providers.keys():
                return

            cache = self._conversion_graph_providers[item.filename]
            cache.delete()
            cache.on_shutdown()
            del self._conversion_graph_providers[item.filename]
            return

        if isinstance(item, data.Target):
            if not item.store_id:
                raise Exception(
                    'Not supported: Conversion Manifest must have a valid store id in order to write the item.')

            if item.store_id not in self._target_providers.keys():
                return

            cache = self._target_providers[item.store_id]
            cache.write(content=item)
            cache.on_shutdown()
            del self._target_providers[item.store_id]
            return

        raise NotImplementedError()

    def can_show_in_store(self, item: data.Serializable) -> bool:
        if isinstance(item, data.ConversionGraph):
            delegate = self._library.conversion_graph if self._library.conversion_graph else self._conversion_graph_cache
            if not delegate:
                return False
            return delegate.can_show_in_store(identifier=item.filename)
        if isinstance(item, data.Target):
            delegate = self._library.target if self._library.target else self._target_cache
            if not delegate:
                return False
            return delegate.can_show_in_store(identifier=item.store_id)
        return False

    def show_in_store(self, item: data.Serializable) -> None:
        if isinstance(item, data.ConversionGraph):
            delegate = self._library.conversion_graph if self._library.conversion_graph else self._conversion_graph_cache
            if not delegate:
                return
            return delegate.show_in_store(identifier=item.filename)
        if isinstance(item, data.Target):
            delegate = self._library.target if self._library.target else self._target_cache
            if not delegate:
                return
            return delegate.show_in_store(identifier=item.store_id)

    @property
    def library(self) -> data.Library:
        return self._library

    @library.setter
    def library(self, value: data.Library) -> None:
        if self._library == value:
            return

        if POLLING:
            if self._library:
                if self._manifest_subscription and self._library.manifest:
                    self._library.manifest.remove_change_subscription(subscription_id=self._manifest_subscription)

                if self._conversion_graph_subscription and self._library.conversion_graph:
                    self._library.conversion_graph.remove_change_subscription(subscription_id=self._conversion_graph_subscription)

                if self._target_subscription and self._library.target:
                    self._library.target.remove_change_subscription(subscription_id=self._target_subscription)

        self._library = value

        self._initialize()


@Singleton
class __Manager:

    def __init__(self):

        install()

        self._library_caches: typing.Dict[str, _LibraryProvider] = dict()

        self._operators: typing.List[data.Operator] = [
            operator.And(),
            operator.Add(),
            operator.BooleanSwitch(),
            operator.ColorSpaceResolver(),
            operator.ConstantBoolean(),
            operator.ConstantFloat(),
            operator.ConstantInteger(),
            operator.ConstantRGB(),
            operator.ConstantRGBA(),
            operator.ConstantString(),
            operator.Equal(),
            operator.GreaterThan(),
            operator.LessThan(),
            operator.ListGenerator(),
            operator.ListIndex(),
            operator.MayaTransparencyResolver(),
            operator.MergeRGB(),
            operator.MergeRGBA(),
            operator.MDLColorSpace(),
            operator.MDLTextureResolver(),
            operator.Multiply(),
            operator.Not(),
            operator.Or(),
            operator.Remap(),
            operator.SplitRGB(),
            operator.SplitRGBA(),
            operator.SplitTextureData(),
            operator.Subtract(),
            operator.ValueResolver(),
            operator.ValueTest(),
        ]

        for o in self._operators:
            if len([item for item in self._operators if item.id == o.id]) == 1:
                continue
            raise Exception('Operator id "{0}" is not unique.'.format(o.id))

        provider = _LibraryProvider(library=COMMON_LIBRARY)
        self._library_caches[COMMON_LIBRARY_ID] = provider

        render_contexts = [
            'MDL',
            'USDPreview',
            'Blender',
        ]

        settings = provider.get_settings()
        if len(settings) == 0:
            self._settings: data.Settings = data.Settings()
            for render_context in render_contexts:
                self._settings.render_contexts.append(render_context)
                self._settings.render_contexts.append(render_context)
            self._save_settings()
        else:
            self._settings: data.Settings = settings[0]
            added_render_context = False
            for render_context in render_contexts:
                if render_context not in self._settings.render_contexts:
                    self._settings.render_contexts.append(render_context)
                    added_render_context = True
            if added_render_context:
                self._save_settings()

        for i in range(len(self._settings.libraries)):
            for library in DEFAULT_LIBRARIES:
                if self._settings.libraries[i].id == library.id:
                    self._settings.libraries[i] = library
                    break

        for library in DEFAULT_LIBRARIES:
            if len([o for o in self._settings.libraries if o.id == library.id]) == 0:
                self._settings.libraries.append(library)

        for library in self._settings.libraries:
            self.register_library(library=library)

    def _save_settings(self) -> None:
        if COMMON_LIBRARY_ID not in self._library_caches.keys():
            raise Exception('Not supported: Common library not in cache. Unable to save settings.')
        cache = self._library_caches[COMMON_LIBRARY_ID]
        cache.write(item=self._settings, identifier=None, overwrite=True)

    def register_library(self, library: data.Library) -> None:
        preferences_changed = False
        to_remove = []
        for item in self._settings.libraries:
            if item.id == library.id:
                if not item == library:
                    to_remove.append(item)
        for item in to_remove:
            self._settings.libraries.remove(item)
            preferences_changed = True
        if library not in self._settings.libraries:
            self._settings.libraries.append(library)
            preferences_changed = True

        if preferences_changed:
            self._save_settings()

        if library.id not in self._library_caches.keys():
            self._library_caches[library.id] = _LibraryProvider(library=library)
        else:
            cache = self._library_caches[library.id]
            cache.library = library

    def register_render_contexts(self, context: str) -> None:
        """Register a render context such as MDL or USD Preview."""
        if context not in self._settings.render_contexts:
            self._settings.render_contexts.append(context)
            self._save_settings()

    def get_assembly(self, reference: data.TargetInstance) -> typing.Union[data.Target, None]:
        cache: _LibraryProvider
        for cache in self._library_caches.values():
            for target in cache.get_targets():
                if target.id == reference.target_id:
                    return target
        return None

    def get_assemblies(self, library: data.Library = None) -> typing.List[data.Target]:
        if library:
            if library.id not in self._library_caches.keys():
                return []
            cache = self._library_caches[library.id]
            return cache.get_targets()

        targets: typing.List[data.Target] = []

        cache: _LibraryProvider
        for cache in self._library_caches.values():
            targets.extend(cache.get_targets())

        return targets

    def get_documents(self, library: data.Library = None) -> typing.List[data.ConversionGraph]:
        conversion_graphs: typing.List[data.ConversionGraph] = []

        if library:
            if library.id not in self._library_caches.keys():
                return []
            cache = self._library_caches[library.id]
            conversion_graphs = cache.get_conversion_graphs()

        else:
            cache: _LibraryProvider
            for cache in self._library_caches.values():
                conversion_graphs.extend(cache.get_conversion_graphs())

        for conversion_graph in conversion_graphs:
            self._completed_document_serialization(conversion_graph=conversion_graph)

        return conversion_graphs

    def get_document(self, library: data.Library, document_filename: str) -> typing.Union[data.ConversionGraph, typing.NoReturn]:
        if library.id not in self._library_caches.keys():
            return None

        cache = self._library_caches[library.id]
        for conversion_graph in cache.get_conversion_graphs():
            if conversion_graph.filename == document_filename:
                self._completed_document_serialization(conversion_graph=conversion_graph)
                return conversion_graph
        return None

    def can_show_in_filesystem(self, document: data.ConversionGraph) -> bool:
        if not document.library:
            return False
        if document.library.id not in self._library_caches.keys():
            return False
        cache = self._library_caches[document.library.id]
        return cache.can_show_in_store(item=document)

    def show_in_filesystem(self, document: data.ConversionGraph) -> None:
        if not document.library:
            return
        if document.library.id not in self._library_caches.keys():
            return
        cache = self._library_caches[document.library.id]
        cache.show_in_store(item=document)

    def get_document_by_id(self, library: data.Library, document_id: str) -> typing.Union[data.ConversionGraph, typing.NoReturn]:
        for conversion_graph in self.get_documents(library=library):
            if conversion_graph.id == document_id:
                return conversion_graph
        return None

    def create_new_document(self, library: data.Library) -> data.ConversionGraph:
        conversion_graph = data.ConversionGraph()
        conversion_graph._library = library
        conversion_graph.filename = ''
        self._completed_document_serialization(conversion_graph=conversion_graph)
        return conversion_graph

    def _completed_document_serialization(self, conversion_graph: data.ConversionGraph) -> None:
        build_dag = len(conversion_graph.target_instances) == 0
        for reference in conversion_graph.target_instances:
            if reference.target and reference.target.id == reference.target_id:
                continue
            reference.target = self.get_assembly(reference=reference)
            build_dag = True
        if build_dag:
            conversion_graph.build_dag()

    def create_from_source(self, source: data.ConversionGraph) -> data.ConversionGraph:
        new_conversion_graph = data.ConversionGraph()
        new_id = new_conversion_graph.id
        new_conversion_graph.deserialize(data=source.serialize())
        new_conversion_graph._id = new_id
        new_conversion_graph._library = source.library
        new_conversion_graph.filename = source.filename
        self._completed_document_serialization(conversion_graph=new_conversion_graph)
        return new_conversion_graph

    def revert(self, library: data.Library, instance: data.Serializable) -> bool:
        """
        Returns True if the file existed on disk and was successfully reverted.
        """
        if not library:
            return False

        if library.id not in self._library_caches.keys():
            return False

        cache = self._library_caches[library.id]
        if cache.revert(item=instance):
            if isinstance(instance, data.ConversionGraph):
                self._completed_document_serialization(conversion_graph=instance)
            return True
        return False

    def find_documents(self, source_class: str, library: data.Library = None) -> typing.List[data.ConversionGraph]:
        conversion_graphs = []
        for conversion_graph in self.get_documents(library=library):
            if not conversion_graph.source_node:
                continue
            for node in conversion_graph.source_node.target.nodes:
                if node.class_name == source_class:
                    conversion_graphs.append(conversion_graph)
        return conversion_graphs

    def find_assembly(self, assembly_class: str, library: data.Library = None) -> typing.List[data.Target]:
        targets = []
        for target in self.get_assemblies(library=library):
            for node in target.nodes:
                if node.class_name == assembly_class:
                    targets.append(target)
                    break
        return targets

    def _get_manifest_filepath(self, library: data.Library) -> str:
        return '{0}/ConversionManifest.json'.format(library.path)

    def get_conversion_manifest(self, library: data.Library) -> data.ConversionManifest:
        if library.id not in self._library_caches.keys():
            return data.ConversionManifest()
        cache = self._library_caches[library.id]
        manifests = cache.get_manifests()
        if len(manifests):
            manifest = manifests[0]
            for conversion_map in manifest.conversion_maps:
                if conversion_map.conversion_graph is None:
                    continue
                self._completed_document_serialization(conversion_graph=conversion_map.conversion_graph)
            return manifest
        return data.ConversionManifest()

    def save_conversion_manifest(self, library: data.Library, manifest: data.ConversionManifest) -> None:
        if library.id not in self._library_caches.keys():
            return
        cache = self._library_caches[library.id]
        cache.write(item=manifest)

    def write(self, filename: str, instance: data.Serializable, library: data.Library, overwrite: bool = False) -> None:

        if not filename.strip():
            raise Exception('Invalid filename: empty string.')

        if library.id not in self._library_caches.keys():
            raise Exception('Cannot write to a library that is not registered')

        if not filename.lower().endswith('.json'):
            filename = '{0}.json'.format(filename)

        cache = self._library_caches[library.id]
        cache.write(item=instance, identifier=filename, overwrite=overwrite)

    def delete_document(self, document: data.ConversionGraph) -> bool:
        if not document.library:
            return False

        if document.library.id not in self._library_caches.keys():
            return False

        cache = self._library_caches[document.library.id]
        cache.delete(item=document)
        return True

    def is_graph_entity_id(self, identifier: str) -> bool:
        for item in self.get_assemblies():
            if item.id == identifier:
                return True
        return False

    def get_graph_entity(self, identifier: str) -> data.GraphEntity:
        for item in self.get_assemblies():
            if item.id == identifier:
                return data.TargetInstance.FromAssembly(assembly=item)
        for item in self.get_operators():
            if item.id == identifier:
                return data.OperatorInstance.FromOperator(operator=item)
        raise Exception('Graph Entity with id "{0}" cannot be found'.format(identifier))

    def register_operator(self, operator: data.Operator):
        if operator not in self._operators:
            self._operators.append(operator)

    def get_operators(self) -> typing.List[data.Operator]:
        return self._operators

    def is_operator_id(self, identifier: str) -> bool:
        for item in self.get_operators():
            if item.id == identifier:
                return True
        return False

    def on_shutdown(self):
        if len(self._library_caches.keys()):
            provider: _LibraryProvider
            for provider in self._library_caches.values():
                provider.library = None
            self._library_caches = dict()

    @property
    def libraries(self) -> typing.List[data.Library]:
        return self._settings.libraries


def register_library(library: data.Library) -> None:
    """ """
    __Manager().register_library(library=library)


def get_libraries() -> typing.List[data.Library]:
    """ """
    return __Manager().libraries


def get_library(library_id: str) -> data.Library:
    """ """
    for library in __Manager().libraries:
        if library.id == library_id:
            return library
    raise Exception('Library with id "{0}" not found.'.format(library_id))


def get_assembly(reference: data.TargetInstance) -> data.Target:
    """ """
    # TODO: Is this still needed?
    return __Manager().get_assembly(reference=reference)


def write(filename: str, instance: data.Serializable, library: data.Library, overwrite: bool = False) -> None:
    """ """
    __Manager().write(filename=filename, instance=instance, library=library, overwrite=overwrite)


def get_assemblies(library: data.Library = None) -> typing.List[data.Target]:
    """ """
    return __Manager().get_assemblies(library=library)


def is_graph_entity_id(identifier: str) -> bool:
    """ """
    return __Manager().is_graph_entity_id(identifier=identifier)


def get_graph_entity(identifier: str) -> data.GraphEntity:
    """ """
    return __Manager().get_graph_entity(identifier=identifier)


def get_documents(library: data.Library = None) -> typing.List[data.ConversionGraph]:
    """ """
    return __Manager().get_documents(library=library)


def get_document(library: data.Library, document_filename: str) -> typing.Union[data.ConversionGraph, typing.NoReturn]:
    """ """
    # TODO: Is this still needed?
    return __Manager().get_document(library=library, document_filename=document_filename)


def create_new_document(library: data.Library) -> data.ConversionGraph:
    """ """
    return __Manager().create_new_document(library=library)


def create_from_source(source: data.ConversionGraph) -> data.ConversionGraph:
    """ """
    return __Manager().create_from_source(source=source)


def revert(library: data.Library, instance: data.Serializable) -> bool:
    """
    Returns True if the file existed on disk and was successfully reverted.
    """
    return __Manager().revert(library, instance)


def find_documents(source_class: str, library: data.Library = None) -> typing.List[data.ConversionGraph]:
    """ """
    # TODO: Is this still needed?
    return __Manager().find_documents(source_class=source_class, library=library)


def find_assembly(assembly_class: str, library: data.Library = None) -> typing.List[data.Target]:
    """ """
    # TODO: Is this still needed?
    return __Manager().find_assembly(assembly_class=assembly_class, library=library)


def register_operator(operator: data.Operator):
    """ """
    __Manager().register_operator(operator=operator)


def get_operators() -> typing.List[data.Operator]:
    """ """
    return __Manager().get_operators()


def is_operator_id(identifier: str) -> bool:
    """ """
    return __Manager().is_operator_id(identifier=identifier)


def delete_document(document: data.ConversionGraph) -> bool:
    """ """
    return __Manager().delete_document(document=document)


def get_conversion_manifest(library: data.Library) -> data.ConversionManifest:
    """ """
    return __Manager().get_conversion_manifest(library=library)


def get_render_contexts() -> typing.List[str]:
    """Returns list of registered render contexts."""
    return __Manager()._settings.render_contexts[:]


def register_render_contexts(context: str) -> None:
    """Register a render context such as MDL or USD Preview."""
    __Manager().register_render_contexts(context=context)


def can_show_in_filesystem(document: data.ConversionGraph) -> bool:
    """Checks if the operating system can display where a document is saved on disk."""
    return __Manager().can_show_in_filesystem(document=document)


def show_in_filesystem(document: data.ConversionGraph) -> None:
    """Makes the operating system display where a document is saved on disk."""
    return __Manager().show_in_filesystem(document=document)


def on_shutdown() -> None:
    """Makes the operating system display where a document is saved on disk."""
    return __Manager().on_shutdown()

