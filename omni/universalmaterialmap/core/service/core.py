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

import abc
import typing
import uuid


class ChangeEvent(object):

    def __init__(self, added: typing.Tuple[str], modified: typing.Tuple[str], removed: typing.Tuple[str]):
        super(ChangeEvent, self).__init__()
        self.__added: typing.Tuple[str] = added
        self.__modified: typing.Tuple[str] = modified
        self.__removed: typing.Tuple[str] = removed

    def __str__(self):
        o = 'omni.universalmaterialmap.core.service.core.ChangeEvent('
        o += '\n\tadded: '
        o += ', '.join(self.__added)
        o += '\n\tmodified: '
        o += ', '.join(self.__modified)
        o += '\n\tremoved: '
        o += ', '.join(self.__removed)
        o += '\n)'
        return o

    @property
    def added(self) -> typing.Tuple[str]:
        return self.__added

    @property
    def modified(self) -> typing.Tuple[str]:
        return self.__modified

    @property
    def removed(self) -> typing.Tuple[str]:
        return self.__removed


class IDelegate(metaclass=abc.ABCMeta):
    """ Interface for an online library database table. """

    @abc.abstractmethod
    def get_ids(self) -> typing.List[str]:
        """ Returns a list of identifiers. """
        raise NotImplementedError

    @abc.abstractmethod
    def read(self, identifier: str) -> typing.Dict:
        """ Returns a JSON dictionary if an item by the given identifier exists - otherwise None """
        raise NotImplementedError

    @abc.abstractmethod
    def write(self, identifier: str, contents: typing.Dict) -> str:
        """ Creates or updates an item by using the JSON contents data. """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, identifier: str) -> None:
        """ Deletes an item by the given identifier if it exists. """
        raise NotImplementedError

    @abc.abstractmethod
    def can_show_in_store(self, identifier: str) -> bool:
        """ Deletes an item by the given identifier if it exists. """
        raise NotImplementedError

    @abc.abstractmethod
    def show_in_store(self, identifier: str) -> None:
        """ Deletes an item by the given identifier if it exists. """
        raise NotImplementedError

    @abc.abstractmethod
    def can_poll(self) -> bool:
        """ States if delegate is able to poll file changes and provide subscription to those changes. """
        raise NotImplementedError

    @abc.abstractmethod
    def start_polling(self) -> None:
        """ Starts monitoring files for changes. """
        raise NotImplementedError

    @abc.abstractmethod
    def stop_polling(self) -> None:
        """ Stops monitoring files for changes. """
        raise NotImplementedError

    @abc.abstractmethod
    def add_change_subscription(self, callback: typing.Callable[[ChangeEvent], typing.NoReturn]) -> uuid.uuid4:
        """ Creates a subscription for file changes in location managed by delegate. """
        raise NotImplementedError

    @abc.abstractmethod
    def remove_change_subscription(self, subscription_id: uuid.uuid4) -> None:
        """ Removes the subscription for file changes in location managed by delegate. """
        raise NotImplementedError