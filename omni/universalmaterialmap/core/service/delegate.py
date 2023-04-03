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
import json
import subprocess
import threading
import platform
import uuid

from ..feature import POLLING
from .core import ChangeEvent, IDelegate


class Filesystem(IDelegate):

    def __init__(self, root_directory: str):
        super(Filesystem, self).__init__()
        if POLLING:
            self.__is_polling: bool = False
            self.__poll_timer: threading.Timer = None
            self.__poll_data: typing.Dict[str, float] = dict()
            self.__poll_subscriptions: typing.Dict[uuid.uuid4, typing.Callable[[ChangeEvent], typing.NoReturn]] = dict()
            self.__pending_write_ids: typing.List[str] = []
            self.__pending_delete_ids: typing.List[str] = []
        self._root_directory: str = root_directory

    def __start_polling(self) -> None:
        if not POLLING:
            return
        if self.__is_polling:
            return
        self.__is_polling = True

        # Store current state in self.__poll_data so that __on_timer we only notify of changes since starting to poll
        self.__poll_data = dict()
        self.__pending_change_ids = []
        identifiers = self.get_ids()
        for identifier in identifiers:
            filepath = '{0}/{1}'.format(self._root_directory, identifier)
            modified_time = os.path.getmtime(filepath) if platform.system() == 'Windows' else os.stat(filepath).st_mtime
            self.__poll_data[identifier] = modified_time

        self.__poll_timer = threading.Timer(5, self.__on_timer)
        self.__poll_timer.start()

    def __on_timer(self):
        print('UMM PING')
        if not POLLING:
            return
        if not self.__is_polling:
            return
        try:
            identifiers = self.get_ids()
            added = [o for o in identifiers if o not in self.__poll_data.keys() and o not in self.__pending_write_ids]
            removed = [o for o in self.__poll_data.keys() if o not in identifiers and o not in self.__pending_delete_ids]
            modified_maybe = [o for o in identifiers if o not in added and o not in removed and o not in self.__pending_write_ids]
            modified = []
            for identifier in modified_maybe:
                filepath = '{0}/{1}'.format(self._root_directory, identifier)
                modified_time = os.path.getmtime(filepath) if platform.system() == 'Windows' else os.stat(filepath).st_mtime
                if self.__poll_data[identifier] == modified_time:
                    continue
                modified.append(identifier)
                self.__poll_data[identifier] = modified_time

            for identifier in added:
                filepath = '{0}/{1}'.format(self._root_directory, identifier)
                self.__poll_data[identifier] = os.path.getmtime(filepath) if platform.system() == 'Windows' else os.stat(filepath).st_mtime

            for identifier in removed:
                del self.__poll_data[identifier]

            if len(added) + len(modified) + len(removed) > 0:
                event = ChangeEvent(added=tuple(added), modified=tuple(modified), removed=tuple(removed))
                for callbacks in self.__poll_subscriptions.values():
                    callbacks(event)
        except Exception as error:
            print('WARNING: Universal Material Map failed to poll {0} for file changes.\nDetail: {1}'.format(self._root_directory, error))
        self.__poll_timer.run()

    def __stop_polling(self) -> None:
        if not POLLING:
            return
        self.__is_polling = False
        try:
            self.__poll_timer.cancel()
        except:
            pass
        self.__poll_data = dict()

    def can_poll(self) -> bool:
        if not POLLING:
            return False
        return True

    def start_polling(self):
        if not POLLING:
            return
        self.__start_polling()

    def stop_polling(self):
        if not POLLING:
            return
        self.__stop_polling()

    def add_change_subscription(self, callback: typing.Callable[[ChangeEvent], typing.NoReturn]) -> uuid.uuid4:
        if not POLLING:
            raise NotImplementedError('Polling feature not enabled.')
        for key, value in self.__poll_subscriptions.items():
            if value == callback:
                return key
        key = uuid.uuid4()
        self.__poll_subscriptions[key] = callback
        self.start_polling()
        return key

    def remove_change_subscription(self, subscription_id: uuid.uuid4) -> None:
        if not POLLING:
            raise NotImplementedError('Polling feature not enabled.')
        if subscription_id in self.__poll_subscriptions.keys():
            del self.__poll_subscriptions[subscription_id]
        if len(self.__poll_subscriptions.keys()) == 0:
            self.stop_polling()

    def get_ids(self) -> typing.List[str]:
        identifiers: typing.List[str] = []
        for directory, sub_directories, filenames in os.walk(self._root_directory):
            for filename in filenames:
                if not filename.lower().endswith('.json'):
                    continue
                identifiers.append(filename)
            break
        return identifiers

    def read(self, identifier: str) -> typing.Union[typing.Dict, typing.NoReturn]:
        if not identifier.lower().endswith('.json'):
            raise Exception('Invalid identifier: "{0}" does not end with ".json".'.format(identifier))
        filepath = '{0}/{1}'.format(self._root_directory, identifier)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as pointer:
                    contents = json.load(pointer)
                    if not isinstance(contents, dict):
                        raise Exception('Not supported: Load of file "{0}" did not resolve to a dictionary. Could be due to reading same file twice too fast.'.format(filepath))
                    return contents
            except Exception as error:
                print('Failed to open file "{0}"'.format(filepath))
                raise error
        return None

    def write(self, identifier: str, contents: typing.Dict) -> None:
        if not identifier.lower().endswith('.json'):
            raise Exception('Invalid identifier: "{0}" does not end with ".json".'.format(identifier))

        if not isinstance(contents, dict):
            raise Exception('Not supported: Argument "contents" is not an instance of dict.')

        if not os.path.exists(self._root_directory):
            os.makedirs(self._root_directory)

        if POLLING:
            if identifier not in self.__pending_write_ids:
                self.__pending_write_ids.append(identifier)

        filepath = '{0}/{1}'.format(self._root_directory, identifier)
        with open(filepath, 'w') as pointer:
            json.dump(contents, pointer, indent=4)

        if POLLING:
            # Store the modified time so that we don't trigger a notification. We only want notifications when changes are caused by external modifiers.
            self.__poll_data[identifier] = os.path.getmtime(filepath) if platform.system() == 'Windows' else os.stat(filepath).st_mtime
            self.__pending_write_ids.remove(identifier)

    def delete(self, identifier: str) -> None:
        if not identifier.lower().endswith('.json'):
            raise Exception('Invalid identifier: "{0}" does not end with ".json".'.format(identifier))

        if POLLING:
            if identifier not in self.__pending_delete_ids:
                self.__pending_delete_ids.append(identifier)

        filepath = '{0}/{1}'.format(self._root_directory, identifier)
        if os.path.exists(filepath):
            os.remove(filepath)

        if POLLING:
            # Remove the item from self.__poll_data so that we don't trigger a notification. We only want notifications when changes are caused by external modifiers.
            if identifier in self.__poll_data.keys():
                del self.__poll_data[identifier]
            self.__pending_delete_ids.remove(identifier)

    def can_show_in_store(self, identifier: str) -> bool:
        filepath = '{0}/{1}'.format(self._root_directory, identifier)
        return os.path.exists(filepath)

    def show_in_store(self, identifier: str) -> None:
        filepath = '{0}/{1}'.format(self._root_directory, identifier)
        if os.path.exists(filepath):
            subprocess.Popen(r'explorer /select,"{0}"'.format(filepath.replace('/', '\\')))


class FilesystemManifest(Filesystem):

    def __init__(self, root_directory: str):
        super(FilesystemManifest, self).__init__(root_directory=root_directory)

    def get_ids(self) -> typing.List[str]:
        identifiers: typing.List[str] = []
        for directory, sub_directories, filenames in os.walk(self._root_directory):
            for filename in filenames:
                if not filename.lower() == 'conversionmanifest.json':
                    continue
                identifiers.append(filename)
            break
        return identifiers


class FilesystemSettings(Filesystem):

    def __init__(self, root_directory: str):
        super(FilesystemSettings, self).__init__(root_directory=root_directory)

    def get_ids(self) -> typing.List[str]:
        identifiers: typing.List[str] = []
        for directory, sub_directories, filenames in os.walk(self._root_directory):
            for filename in filenames:
                if not filename.lower() == 'settings.json':
                    continue
                identifiers.append(filename)
            break
        return identifiers