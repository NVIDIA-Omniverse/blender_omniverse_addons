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
import uuid
import sys
import importlib

from .service.core import IDelegate


class ChangeNotification(object):

    def __init__(self, item: object, property_name: str, old_value: typing.Any, new_value: typing.Any):
        super(ChangeNotification, self).__init__()
        self._item: object = item
        self._property_name: str = property_name
        self._old_value: typing.Any = old_value
        self._new_value: typing.Any = new_value

    @property
    def item(self) -> object:
        """ """
        return self._item

    @property
    def property_name(self) -> str:
        """ """
        return self._property_name

    @property
    def old_value(self) -> typing.Any:
        """ """
        return self._old_value

    @property
    def new_value(self) -> typing.Any:
        """ """
        return self._new_value


class Notifying(object):
    """Base class providing change notification capability"""

    def __init__(self):
        super(Notifying, self).__init__()
        self._changed_callbacks: typing.Dict[uuid.uuid4, typing.Callable[[ChangeNotification], typing.NoReturn]] = dict()

    def add_changed_fn(self, callback: typing.Callable[[ChangeNotification], typing.NoReturn]) -> uuid.uuid4:
        for key, value in self._changed_callbacks.items():
            if value == callback:
                return key

        key = uuid.uuid4()
        self._changed_callbacks[key] = callback
        return key

    def remove_changed_fn(self, callback_id: uuid.uuid4) -> None:
        if callback_id in self._changed_callbacks.keys():
            del self._changed_callbacks[callback_id]

    def _notify(self, notification: ChangeNotification):
        for callback in self._changed_callbacks.values():
            callback(notification)

    def destroy(self):
        self._changed_callbacks = None


class Subscribing(Notifying):

    def __init__(self):
        super(Subscribing, self).__init__()
        self._subscriptions: typing.Dict[Notifying, uuid.uuid4] = dict()

    def _subscribe(self, notifying: Notifying) -> uuid.uuid4:
        if notifying in self._subscriptions.keys():
            return self._subscriptions[notifying]
        self._subscriptions[notifying] = notifying.add_changed_fn(self._on_notification)

    def _unsubscribe(self, notifying: Notifying) -> None:
        if notifying in self._subscriptions.keys():
            callback_id = self._subscriptions[notifying]
            del self._subscriptions[notifying]
            notifying.remove_changed_fn(callback_id=callback_id)

    def _on_notification(self, notification: ChangeNotification) -> None:
        pass


class ManagedListInsert(object):

    def __init__(self, notifying: Notifying, index: int):
        super(ManagedListInsert, self).__init__()
        self._notifying: Notifying = notifying
        self._index: int = index

    @property
    def notifying(self) -> Notifying:
        """ """
        return self._notifying

    @property
    def index(self) -> int:
        """ """
        return self._index


class ManagedListRemove(object):

    def __init__(self, notifying: Notifying, index: int):
        super(ManagedListRemove, self).__init__()
        self._notifying: Notifying = notifying
        self._index: int = index

    @property
    def notifying(self) -> Notifying:
        """ """
        return self._notifying

    @property
    def index(self) -> int:
        """ """
        return self._index


class ManagedListNotification(object):

    ADDED_ITEMS: int = 0
    UPDATED_ITEMS: int = 1
    REMOVED_ITEMS: int = 2

    def __init__(self, managed_list: 'ManagedList', items: typing.List[typing.Union[ManagedListInsert, ChangeNotification, ManagedListRemove]]):
        super(ManagedListNotification, self).__init__()
        self._managed_list: ManagedList = managed_list
        self._inserted_items: typing.List[ManagedListInsert] = []
        self._change_notifications: typing.List[ChangeNotification] = []
        self._removed_items: typing.List[ManagedListRemove] = []
        self._kind: int = -1
        if isinstance(items[0], ManagedListInsert):
            self._kind = ManagedListNotification.ADDED_ITEMS
            self._inserted_items = typing.cast(typing.List[ManagedListInsert], items)
        elif isinstance(items[0], ChangeNotification):
            self._kind = ManagedListNotification.UPDATED_ITEMS
            self._change_notifications = typing.cast(typing.List[ChangeNotification], items)
        elif isinstance(items[0], ManagedListRemove):
            self._kind = ManagedListNotification.REMOVED_ITEMS
            self._removed_items = typing.cast(typing.List[ManagedListRemove], items)
        else:
            raise Exception('Unexpected object: "{0}" of type "{1}".'.format(items[0], type(items[0])))

    @property
    def managed_list(self) -> 'ManagedList':
        """ """
        return self._managed_list

    @property
    def kind(self) -> int:
        """ """
        return self._kind

    @property
    def inserted_items(self) -> typing.List[ManagedListInsert]:
        """ """
        return self._inserted_items

    @property
    def change_notifications(self) -> typing.List[ChangeNotification]:
        """ """
        return self._change_notifications

    @property
    def removed_items(self) -> typing.List[ManagedListRemove]:
        """ """
        return self._removed_items


class ManagedList(object):

    def __init__(self, items: typing.List[Notifying] = None):
        super(ManagedList, self).__init__()
        self._subscriptions: typing.Dict[Notifying, uuid.uuid4] = dict()
        self._changed_callbacks: typing.Dict[uuid.uuid4, typing.Callable[[ManagedListNotification], typing.NoReturn]] = dict()
        self._managed_items: typing.List[Notifying] = []
        if items:
            for o in items:
                self._manage_item(notifying=o)

    def __iter__(self):
        return iter(self._managed_items)

    def _manage_item(self, notifying: Notifying) -> typing.Union[Notifying, None]:
        """ Subscribes to managed item. Returns item only if it became managed. """
        if notifying in self._managed_items:
            return None
        self._managed_items.append(notifying)
        self._subscriptions[notifying] = notifying.add_changed_fn(self._on_notification)
        return notifying

    def _unmanage_item(self, notifying: Notifying) -> typing.Union[typing.Tuple[Notifying, int], typing.Tuple[None, int]]:
        """ Unsubscribes to managed item. Returns item only if it became unmanaged.  """
        if notifying not in self._managed_items:
            return None, -1
        index = self._managed_items.index(notifying)
        self._managed_items.remove(notifying)
        callback_id = self._subscriptions[notifying]
        del self._subscriptions[notifying]
        notifying.remove_changed_fn(callback_id=callback_id)
        return notifying, index

    def _on_notification(self, notification: ChangeNotification) -> None:
        self._notify(
            notification=ManagedListNotification(
                managed_list=self,
                items=[notification]
            )
        )

    def _notify(self, notification: ManagedListNotification):
        for callback in self._changed_callbacks.values():
            callback(notification)

    def add_changed_fn(self, callback: typing.Callable[[ManagedListNotification], typing.NoReturn]) -> uuid.uuid4:
        for key, value in self._changed_callbacks.items():
            if value == callback:
                return key

        key = uuid.uuid4()
        self._changed_callbacks[key] = callback
        return key

    def remove_changed_fn(self, callback_id: uuid.uuid4) -> None:
        if callback_id in self._changed_callbacks.keys():
            del self._changed_callbacks[callback_id]

    def append(self, notifying: Notifying) -> None:
        if self._manage_item(notifying=notifying) is not None:
            self._notify(
                ManagedListNotification(
                    managed_list=self,
                    items=[ManagedListInsert(notifying=notifying, index=self.index(notifying=notifying))]
                )
            )

    def extend(self, notifying: typing.List[Notifying]) -> None:
        added = []
        for o in notifying:
            o = self._manage_item(notifying=o)
            if o:
                added.append(o)
        if len(added) == 0:
            return
        self._notify(
            ManagedListNotification(
                managed_list=self,
                items=[ManagedListInsert(notifying=o, index=self.index(notifying=o)) for o in added]
            )
        )

    def remove(self, notifying: Notifying) -> None:
        notifying, index = self._unmanage_item(notifying=notifying)
        if notifying:
            self._notify(
                ManagedListNotification(
                    managed_list=self,
                    items=[ManagedListRemove(notifying=notifying, index=index)]
                )
            )

    def remove_all(self) -> None:
        items = [ManagedListRemove(notifying=o, index=i) for i, o in enumerate(self._managed_items)]
        for callback_id, notifying in self._subscriptions.items():
            notifying.remove_changed_fn(callback_id=callback_id)
        self._subscriptions = dict()
        self._managed_items = []
        self._notify(
            ManagedListNotification(
                managed_list=self,
                items=items
            )
        )

    def pop(self, index: int = 0) -> Notifying:
        notifying, index = self._unmanage_item(self._managed_items[index])
        self._notify(
            ManagedListNotification(
                managed_list=self,
                items=[ManagedListRemove(notifying=notifying, index=index)]
            )
        )
        return notifying

    def index(self, notifying: Notifying) -> int:
        if notifying in self._managed_items:
            return self._managed_items.index(notifying)
        return -1


class Serializable(Subscribing):
    """Base class providing serialization method template"""

    def __init__(self):
        super(Serializable, self).__init__()

    def serialize(self) -> dict:
        """ """
        return dict()

    def deserialize(self, data: dict) -> None:
        """ """
        pass


class Base(Serializable):
    """Base class providing id property"""

    @classmethod
    def Create(cls) -> 'Base':
        return cls()

    def __init__(self):
        super(Base, self).__init__()
        self._id: str = str(uuid.uuid4())

    def serialize(self) -> dict:
        """ """
        output = super(Base, self).serialize()
        output['_id'] = self._id
        return output

    def deserialize(self, data: dict) -> None:
        """ """
        super(Base, self).deserialize(data=data)
        self._id = data['_id'] if '_id' in data.keys() else str(uuid.uuid4())

    @property
    def id(self) -> str:
        """ """
        return self._id


class DagNode(Base):
    """Base class providing input and outputs of :class:`omni.universalmaterialmap.core.data.Plug` """

    def __init__(self):
        super(DagNode, self).__init__()
        self._inputs: typing.List[Plug] = []
        self._outputs: typing.List[Plug] = []
        self._computing: bool = False

    def serialize(self) -> dict:
        """ """
        output = super(DagNode, self).serialize()
        output['_inputs'] = [plug.serialize() for plug in self.inputs]
        output['_outputs'] = [plug.serialize() for plug in self.outputs]
        return output

    def deserialize(self, data: dict) -> None:
        """ """
        super(DagNode, self).deserialize(data=data)

        old_inputs = self._inputs[:]
        old_outputs = self._outputs[:]

        while len(self._inputs):
            self._unsubscribe(notifying=self._inputs.pop())
        while len(self._outputs):
            self._unsubscribe(notifying=self._outputs.pop())

        plugs = []
        if '_inputs' in data.keys():
            for o in data['_inputs']:
                plug = Plug(parent=self)
                plug.deserialize(data=o)
                plugs.append(plug)
        self._inputs = plugs
        plugs = []
        if '_outputs' in data.keys():
            for o in data['_outputs']:
                plug = Plug(parent=self)
                plug.deserialize(data=o)
                plugs.append(plug)
        self._outputs = plugs

        for o in self._inputs:
            self._subscribe(notifying=o)
        for o in self._outputs:
            self._subscribe(notifying=o)

        if not old_inputs == self._inputs:
            self._notify(
                ChangeNotification(
                    item=self,
                    property_name='inputs',
                    old_value=old_inputs,
                    new_value=self._inputs[:]
                )
            )

        if not old_inputs == self._outputs:
            self._notify(
                ChangeNotification(
                    item=self,
                    property_name='outputs',
                    old_value=old_outputs,
                    new_value=self._outputs[:]
                )
            )

    def _on_notification(self, notification: ChangeNotification) -> None:
        if notification.item == self:
            return
        # Re-broadcast notification
        self._notify(notification=notification)

    def invalidate(self, plug: 'Plug'):
        pass

    def compute(self) -> None:
        """ """
        if self._computing:
            return
        self._computing = True
        self._compute_inputs(input_plugs=self._inputs)
        self._compute_outputs(output_plugs=self._outputs)
        self._computing = False

    def _compute_inputs(self, input_plugs: typing.List['Plug']):
        # Compute dependencies
        for plug in input_plugs:
            if not plug.input:
                continue
            if not plug.input.parent:
                continue
            if not plug.input.is_invalid:
                continue
            plug.input.parent.compute()

        # Set computed_value
        for plug in input_plugs:
            if plug.input:
                plug.computed_value = plug.input.computed_value
            else:
                plug.computed_value = plug.value

    def _compute_outputs(self, output_plugs: typing.List['Plug']):
        # Compute dependencies
        for plug in output_plugs:
            if not plug.input:
                continue
            if not plug.input.parent:
                continue
            if not plug.input.is_invalid:
                continue
            plug.input.parent.compute()

        # Set computed_value
        for plug in output_plugs:
            if plug.input:
                plug.computed_value = plug.input.computed_value
            else:
                plug.computed_value = plug.value

    def add_input(self) -> 'Plug':
        raise NotImplementedError()

    def can_remove_plug(self, plug: 'Plug') -> bool:
        return plug.is_removable

    def remove_plug(self, plug: 'Plug') -> None:
        if not plug.is_removable:
            raise Exception('Plug is not removable')
        notifications = []
        if plug in self._inputs:
            old_value = self._inputs[:]
            self._unsubscribe(notifying=plug)
            self._inputs.remove(plug)
            notifications.append(
                ChangeNotification(
                    item=self,
                    property_name='inputs',
                    old_value=old_value,
                    new_value=self._inputs[:]
                )
            )

        if plug in self._outputs:
            old_value = self._outputs[:]
            self._unsubscribe(notifying=plug)
            self._outputs.remove(plug)
            notifications.append(
                ChangeNotification(
                    item=self,
                    property_name='outputs',
                    old_value=old_value,
                    new_value=self._outputs[:]
                )
            )

        destination: Plug
        for destination in plug.outputs:
            destination.input = None

        for notification in notifications:
            self._notify(notification=notification)

    @property
    def can_add_input(self) -> bool:
        return False

    @property
    def inputs(self) -> typing.List['Plug']:
        """ """
        return self._inputs

    @property
    def outputs(self) -> typing.List['Plug']:
        """ """
        return self._outputs


class GraphEntity(DagNode):
    """Base class providing omni.kit.widget.graph properties for a data item."""
    OPEN = 0
    MINIMIZED = 1
    CLOSED = 2

    def __init__(self):
        super(GraphEntity, self).__init__()
        self._display_name: str = ''
        self._position: typing.Union[typing.Tuple[float, float], None] = None
        self._expansion_state: int = GraphEntity.OPEN
        self._show_inputs: bool = True
        self._show_outputs: bool = True
        self._show_peripheral: bool = False

    def serialize(self) -> dict:
        """ """
        output = super(GraphEntity, self).serialize()
        output['_display_name'] = self._display_name
        output['_position'] = self._position
        output['_expansion_state'] = self._expansion_state
        output['_show_inputs'] = self._show_inputs
        output['_show_outputs'] = self._show_outputs
        output['_show_peripheral'] = self._show_peripheral
        return output

    def deserialize(self, data: dict) -> None:
        """ """
        super(GraphEntity, self).deserialize(data=data)
        self._display_name = data['_display_name'] if '_display_name' in data.keys() else ''
        self._position = data['_position'] if '_position' in data.keys() else None
        self._expansion_state = data['_expansion_state'] if '_expansion_state' in data.keys() else GraphEntity.OPEN
        self._show_inputs = data['_show_inputs'] if '_show_inputs' in data.keys() else True
        self._show_outputs = data['_show_outputs'] if '_show_outputs' in data.keys() else True
        self._show_peripheral = data['_show_peripheral'] if '_show_peripheral' in data.keys() else False

    @property
    def display_name(self) -> str:
        """ """
        return self._display_name

    @display_name.setter
    def display_name(self, value: str) -> None:
        """ """
        if self._display_name is value:
            return
        notification = ChangeNotification(
                    item=self,
                    property_name='display_name',
                    old_value=self._display_name,
                    new_value=value
                )
        self._display_name = value
        self._notify(notification=notification)

    @property
    def position(self) -> typing.Union[typing.Tuple[float, float], None]:
        """ """
        return self._position

    @position.setter
    def position(self, value: typing.Union[typing.Tuple[float, float], None]) -> None:
        """ """
        if self._position is value:
            return
        notification = ChangeNotification(
                    item=self,
                    property_name='position',
                    old_value=self._position,
                    new_value=value
                )
        self._position = value
        self._notify(notification=notification)

    @property
    def expansion_state(self) -> int:
        """ """
        return self._expansion_state

    @expansion_state.setter
    def expansion_state(self, value: int) -> None:
        """ """
        if self._expansion_state is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='expansion_state',
            old_value=self._expansion_state,
            new_value=value
        )
        self._expansion_state = value
        self._notify(notification=notification)

    @property
    def show_inputs(self) -> bool:
        """ """
        return self._show_inputs

    @show_inputs.setter
    def show_inputs(self, value: bool) -> None:
        """ """
        if self._show_inputs is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='show_inputs',
            old_value=self._show_inputs,
            new_value=value
        )
        self._show_inputs = value
        self._notify(notification=notification)

    @property
    def show_outputs(self) -> bool:
        """ """
        return self._show_outputs

    @show_outputs.setter
    def show_outputs(self, value: bool) -> None:
        """ """
        if self._show_outputs is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='show_outputs',
            old_value=self._show_outputs,
            new_value=value
        )
        self._show_outputs = value
        self._notify(notification=notification)

    @property
    def show_peripheral(self) -> bool:
        """ """
        return self._show_peripheral

    @show_peripheral.setter
    def show_peripheral(self, value: bool) -> None:
        """ """
        if self._show_peripheral is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='show_peripheral',
            old_value=self._show_peripheral,
            new_value=value
        )
        self._show_peripheral = value
        self._notify(notification=notification)


class Connection(Serializable):

    def __init__(self):
        super(Connection, self).__init__()
        self._source_id = ''
        self._destination_id = ''

    def serialize(self) -> dict:
        output = super(Connection, self).serialize()
        output['_source_id'] = self._source_id
        output['_destination_id'] = self._destination_id
        return output

    def deserialize(self, data: dict) -> None:
        super(Connection, self).deserialize(data=data)
        self._source_id = data['_source_id'] if '_source_id' in data.keys() else ''
        self._destination_id = data['_destination_id'] if '_destination_id' in data.keys() else ''

    @property
    def source_id(self):
        return self._source_id

    @property
    def destination_id(self):
        return self._destination_id


class Plug(Base):
    """
    A Plug can be:
        a source
        an output
        both a source and an output
        a container for a static value - most likely as an output
        a container for an editable value - most likely as an output


    plug.default_value      Starting point and for resetting.
    plug.value              Apply as computed_value if there is no input or dependency providing a value.
    plug.computed_value     Final value. Could be thought of as plug.output_value.

    Plug is_dirty on

        input connect
        input disconnect
        value change if not connected

    A Plug is_dirty if

        it is_dirty
        its input is_dirty
        any dependency is_dirty
    """

    VALUE_TYPE_ANY = 'any'
    VALUE_TYPE_FLOAT = 'float'
    VALUE_TYPE_INTEGER = 'int'
    VALUE_TYPE_STRING = 'str'
    VALUE_TYPE_BOOLEAN = 'bool'
    VALUE_TYPE_NODE_ID = 'node_id'
    VALUE_TYPE_VECTOR2 = 'vector2'
    VALUE_TYPE_VECTOR3 = 'vector3'
    VALUE_TYPE_VECTOR4 = 'vector4'
    VALUE_TYPE_ENUM = 'enum'
    VALUE_TYPE_LIST = 'list'

    VALUE_TYPES = [
        VALUE_TYPE_ANY,
        VALUE_TYPE_FLOAT,
        VALUE_TYPE_INTEGER,
        VALUE_TYPE_STRING,
        VALUE_TYPE_BOOLEAN,
        VALUE_TYPE_NODE_ID,
        VALUE_TYPE_VECTOR2,
        VALUE_TYPE_VECTOR3,
        VALUE_TYPE_VECTOR4,
        VALUE_TYPE_ENUM,
        VALUE_TYPE_LIST,
    ]

    @classmethod
    def Create(
            cls,
            parent: DagNode,
            name: str,
            display_name: str,
            value_type: str = 'any',
            editable: bool = False,
            is_removable: bool = False,
    ) -> 'Plug':
        instance = cls(parent=parent)
        instance._name = name
        instance._display_name = display_name
        instance._value_type = value_type
        instance._is_editable = editable
        instance._is_removable = is_removable
        return instance

    def __init__(self, parent: DagNode):
        super(Plug, self).__init__()
        self._parent: DagNode = parent
        self._name: str = ''
        self._display_name: str = ''
        self._value_type: str = Plug.VALUE_TYPE_ANY
        self._internal_value_type: str = Plug.VALUE_TYPE_ANY
        self._is_peripheral: bool = False
        self._is_editable: bool = False
        self._is_removable: bool = False
        self._default_value: typing.Any = None
        self._computed_value: typing.Any = None
        self._value: typing.Any = None
        self._is_invalid: bool = False
        self._input: typing.Union[Plug, typing.NoReturn] = None
        self._outputs: typing.List[Plug] = []
        self._enum_values: typing.List = []

    def serialize(self) -> dict:
        output = super(Plug, self).serialize()
        output['_name'] = self._name
        output['_display_name'] = self._display_name
        output['_value_type'] = self._value_type
        output['_internal_value_type'] = self._internal_value_type
        output['_is_peripheral'] = self._is_peripheral
        output['_is_editable'] = self._is_editable
        output['_is_removable'] = self._is_removable
        output['_default_value'] = self._default_value
        output['_value'] = self._value
        output['_enum_values'] = self._enum_values
        return output

    def deserialize(self, data: dict) -> None:
        super(Plug, self).deserialize(data=data)
        self._input = None
        self._name = data['_name'] if '_name' in data.keys() else ''
        self._display_name = data['_display_name'] if '_display_name' in data.keys() else ''
        self._value_type = data['_value_type'] if '_value_type' in data.keys() else Plug.VALUE_TYPE_ANY
        self._internal_value_type = data['_internal_value_type'] if '_internal_value_type' in data.keys() else None
        self._is_peripheral = data['_is_peripheral'] if '_is_peripheral' in data.keys() else False
        self._is_editable = data['_is_editable'] if '_is_editable' in data.keys() else False
        self._is_removable = data['_is_removable'] if '_is_removable' in data.keys() else False
        self._default_value = data['_default_value'] if '_default_value' in data.keys() else None
        self._value = data['_value'] if '_value' in data.keys() else self._default_value
        self._enum_values = data['_enum_values'] if '_enum_values' in data.keys() else []

    def invalidate(self) -> None:
        if self._is_invalid:
            return
        self._is_invalid = True
        if self.parent:
            self.parent.invalidate(self)

    @property
    def parent(self) -> DagNode:
        return self._parent

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if self._name is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='name',
            old_value=self._name,
            new_value=value
        )
        self._name = value
        self._notify(notification=notification)

    @property
    def display_name(self) -> str:
        return self._display_name

    @display_name.setter
    def display_name(self, value: str) -> None:
        if self._display_name is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='display_name',
            old_value=self._display_name,
            new_value=value
        )
        self._display_name = value
        self._notify(notification=notification)

    @property
    def value_type(self) -> str:
        return self._value_type

    @value_type.setter
    def value_type(self, value: str) -> None:
        if self._value_type is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='value_type',
            old_value=self._value_type,
            new_value=value
        )
        self._value_type = value
        self._notify(notification=notification)

    @property
    def internal_value_type(self) -> str:
        return self._internal_value_type

    @internal_value_type.setter
    def internal_value_type(self, value: str) -> None:
        if self._internal_value_type is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='internal_value_type',
            old_value=self._internal_value_type,
            new_value=value
        )
        self._internal_value_type = value
        self._notify(notification=notification)

    @property
    def is_removable(self) -> bool:
        return self._is_removable

    @property
    def is_peripheral(self) -> bool:
        return self._is_peripheral

    @is_peripheral.setter
    def is_peripheral(self, value: bool) -> None:
        if self._is_peripheral is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='is_peripheral',
            old_value=self._is_peripheral,
            new_value=value
        )
        self._is_peripheral = value
        self._notify(notification=notification)

    @property
    def computed_value(self) -> typing.Any:
        return self._computed_value

    @computed_value.setter
    def computed_value(self, value: typing.Any) -> None:
        if self._computed_value is value:
            self._is_invalid = False
            self._value = self._computed_value
            return
        notification = ChangeNotification(
            item=self,
            property_name='computed_value',
            old_value=self._computed_value,
            new_value=value
        )
        if self._input and self._input.is_invalid:
            print('WARNING: Universal Material Map: Compute encountered an unexpected state: input invalid after compute. Results may be incorrect.')
            print('\tplug: "{0}"'.format(self.name))
            if self._parent:
                print('\tplug.parent: "{0}"'.format(self._parent.__class__.__name__))
            print('\tplug.input: "{0}"'.format(self._input.name))
            if self._input.parent:
                print('\tplug.input.parent: "{0}"'.format(self._input.parent.__class__.__name__))
            return
        self._is_invalid = False

        self._computed_value = value
        self._value = self._computed_value
        self._notify(notification=notification)

    @property
    def value(self) -> typing.Any:
        return self._value

    @value.setter
    def value(self, value: typing.Any) -> None:
        if self._value is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='value',
            old_value=self._value,
            new_value=value
        )
        self._value = value
        self._notify(notification=notification)

        if self._input is None:
            self.invalidate()

    @property
    def is_invalid(self) -> typing.Any:
        if self._input and self._input._is_invalid:
            return True
        return self._is_invalid

    @property
    def input(self) -> typing.Union['Plug', typing.NoReturn]:
        return self._input

    @input.setter
    def input(self, value: typing.Union['Plug', typing.NoReturn]) -> None:
        if self._input is value:
            return

        notification = ChangeNotification(
            item=self,
            property_name='input',
            old_value=self._input,
            new_value=value
        )
        self._input = value
        self._notify(notification=notification)

        self.invalidate()

    @property
    def outputs(self) -> typing.List['Plug']:
        return self._outputs

    @property
    def is_editable(self) -> bool:
        return self._is_editable

    @is_editable.setter
    def is_editable(self, value: bool) -> None:
        if self._is_editable is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='is_editable',
            old_value=self._is_editable,
            new_value=value
        )
        self._is_editable = value
        self._notify(notification=notification)

    @property
    def default_value(self) -> typing.Any:
        return self._default_value

    @default_value.setter
    def default_value(self, value: typing.Any) -> None:
        if self._default_value is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='default_value',
            old_value=self._default_value,
            new_value=value
        )
        self._default_value = value
        self._notify(notification=notification)

    @property
    def enum_values(self) -> typing.List:
        return self._enum_values

    @enum_values.setter
    def enum_values(self, value: typing.List) -> None:
        if self._enum_values is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='enum_values',
            old_value=self._enum_values,
            new_value=value
        )
        self._enum_values = value
        self._notify(notification=notification)


class Node(DagNode):

    @classmethod
    def Create(cls, class_name: str) -> 'Node':
        instance = typing.cast(Node, super(Node, cls).Create())
        instance._class_name = class_name
        return instance

    def __init__(self):
        super(Node, self).__init__()
        self._class_name: str = ''

    def serialize(self) -> dict:
        output = super(Node, self).serialize()
        output['_class_name'] = self._class_name
        return output

    def deserialize(self, data: dict) -> None:
        super(Node, self).deserialize(data=data)
        self._class_name = data['_class_name'] if '_class_name' in data.keys() else ''

    @property
    def class_name(self):
        return self._class_name


class Client(Serializable):
    ANY_VERSION = 'any'
    NO_VERSION = 'none'

    DCC_OMNIVERSE_CREATE = 'Omniverse Create'
    DCC_3DS_MAX = '3ds MAX'
    DCC_MAYA = 'Maya'
    DCC_HOUDINI = 'Houdini'
    DCC_SUBSTANCE_DESIGNER = 'Substance Designer'
    DCC_SUBSTANCE_PAINTER = 'Substance Painter'
    DCC_BLENDER = 'Blender'

    @classmethod
    def Autodesk_3dsMax(cls, version: str = ANY_VERSION) -> 'Client':
        instance = Client()
        instance._name = Client.DCC_3DS_MAX
        instance._version = version
        return instance

    @classmethod
    def Autodesk_Maya(cls, version: str = ANY_VERSION) -> 'Client':
        instance = Client()
        instance._name = Client.DCC_MAYA
        instance._version = version
        return instance

    @classmethod
    def OmniverseCreate(cls, version: str = ANY_VERSION) -> 'Client':
        instance = Client()
        instance._name = Client.DCC_OMNIVERSE_CREATE
        instance._version = version
        return instance

    @classmethod
    def Blender(cls, version: str = ANY_VERSION) -> 'Client':
        instance = Client()
        instance._name = Client.DCC_BLENDER
        instance._version = version
        return instance

    def __init__(self):
        super(Client, self).__init__()
        self._name: str = ''
        self._version: str = ''

    def __eq__(self, other: 'Client') -> bool:
        if not isinstance(other, Client):
            return False
        return other.name == self._name and other.version == self._version

    def is_compatible(self, other: 'Client') -> bool:
        if not isinstance(other, Client):
            return False
        if other == self:
            return True
        return other._version == Client.ANY_VERSION or self._version == Client.ANY_VERSION

    def serialize(self) -> dict:
        output = super(Client, self).serialize()
        output['_name'] = self._name
        output['_version'] = self._version
        return output

    def deserialize(self, data: dict) -> None:
        super(Client, self).deserialize(data=data)
        self._name = data['_name'] if '_name' in data.keys() else ''
        self._version = data['_version'] if '_version' in data.keys() else ''

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def version(self) -> str:
        return self._version

    @version.setter
    def version(self, value: str) -> None:
        self._version = value


class AssemblyMetadata(Serializable):
    CATEGORY_BASE = 'Base Materials'
    CATEGORY_CONNECTOR = 'Connector Materials'

    CATEGORIES = [
        CATEGORY_BASE,
        CATEGORY_CONNECTOR,
    ]

    def __init__(self):
        super(AssemblyMetadata, self).__init__()
        self._category = ''
        self._name = ''
        self._keywords: typing.List[str] = []
        self._supported_clients: typing.List[Client] = []

    def serialize(self) -> dict:
        output = super(AssemblyMetadata, self).serialize()
        output['_category'] = self._category
        output['_name'] = self._name
        output['_keywords'] = self._keywords
        output['_supported_clients'] = [o.serialize() for o in self._supported_clients]
        return output

    def deserialize(self, data: dict) -> None:
        super(AssemblyMetadata, self).deserialize(data=data)
        self._category = data['_category'] if '_category' in data.keys() else ''
        self._name = data['_name'] if '_name' in data.keys() else ''
        self._keywords = data['_keywords'] if '_keywords' in data.keys() else ''
        items = []
        if '_supported_clients' in data.keys():
            for o in data['_supported_clients']:
                item = Client()
                item.deserialize(data=o)
                items.append(item)
        self._supported_clients = items

    @property
    def category(self) -> str:
        return self._category

    @category.setter
    def category(self, value: str) -> None:
        self._category = value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def keywords(self) -> typing.List[str]:
        return self._keywords

    @keywords.setter
    def keywords(self, value: typing.List[str]) -> None:
        self._keywords = value

    @property
    def supported_clients(self) -> typing.List[Client]:
        return self._supported_clients


class Target(GraphEntity):

    def __init__(self):
        super(Target, self).__init__()
        self._nodes: typing.List[Node] = []
        self._metadata: AssemblyMetadata = AssemblyMetadata()
        self._root_node_id: str = ''
        self._root_node: Node = None
        self._revision: int = 0
        self._store_id: str = ''
        self._connections: typing.List[Connection] = []

    def serialize(self) -> dict:
        output = super(Target, self).serialize()
        output['_nodes'] = [node.serialize() for node in self.nodes]
        output['_metadata'] = self._metadata.serialize()
        output['_root_node_id'] = self._root_node_id
        output['_revision'] = self._revision
        output['_connections'] = [o.serialize() for o in self._connections]
        return output

    def deserialize(self, data: dict) -> None:
        super(Target, self).deserialize(data=data)

        self._root_node_id = data['_root_node_id'] if '_root_node_id' in data.keys() else ''

        nodes = []
        if '_nodes' in data.keys():
            for o in data['_nodes']:
                node = Node()
                node.deserialize(data=o)
                nodes.append(node)
        self._nodes = nodes

        root_node = None
        if self._root_node_id:
            for node in self._nodes:
                if node.id == self._root_node_id:
                    root_node = node
                    break
        self._root_node = root_node

        metadata = AssemblyMetadata()
        if '_metadata' in data.keys():
            metadata.deserialize(data=data['_metadata'])
        self._metadata = metadata

        self._revision = data['_revision'] if '_revision' in data.keys() else 0

        items = []
        if '_connections' in data.keys():
            for o in data['_connections']:
                item = Connection()
                item.deserialize(data=o)
                items.append(item)
        self._connections = items

        for connection in self._connections:
            input_plug: Plug = None
            output_plug: Plug = None
            for node in self._nodes:
                for plug in node.inputs:
                    if connection.source_id == plug.id:
                        input_plug = plug
                    elif connection.destination_id == plug.id:
                        input_plug = plug

                for plug in node.outputs:
                    if connection.source_id == plug.id:
                        output_plug = plug
                    elif connection.destination_id == plug.id:
                        output_plug = plug

                if input_plug is not None and output_plug is not None:
                    break
            if input_plug is None or output_plug is None:
                continue
            if output_plug not in input_plug.outputs:
                input_plug.outputs.append(output_plug)
            output_plug.input = input_plug

    def connect(self, source: Plug, destination: Plug) -> None:
        for connection in self._connections:
            if connection.source_id == source.id and connection.destination_id == destination.id:
                return
        connection = Connection()
        connection._source_id = source.id
        connection._destination_id = destination.id
        self._connections.append(connection)
        if destination not in source.outputs:
            source.outputs.append(destination)
        destination.input = source

    @property
    def nodes(self) -> typing.List[Node]:
        return self._nodes

    @property
    def metadata(self) -> AssemblyMetadata:
        return self._metadata

    @property
    def root_node(self) -> Node:
        return self._root_node

    @root_node.setter
    def root_node(self, value: Node) -> None:
        self._root_node = value
        self._root_node_id = self._root_node.id if self._root_node else ''

    @property
    def revision(self) -> int:
        return self._revision

    @revision.setter
    def revision(self, value: int) -> None:
        self._revision = value

    @property
    def store_id(self) -> str:
        return self._store_id

    @store_id.setter
    def store_id(self, value: int) -> None:
        if self._store_id is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='store_id',
            old_value=self._store_id,
            new_value=value
        )
        self._store_id = value
        self._notify(notification=notification)


class TargetInstance(GraphEntity):

    @classmethod
    def FromAssembly(cls, assembly: Target) -> 'TargetInstance':
        instance = cls()
        instance._target_id = assembly.id
        instance.target = assembly
        instance.display_name = assembly.display_name
        return instance

    def __init__(self):
        super(TargetInstance, self).__init__()
        self._target_id: str = ''
        self._target: typing.Union[Target, typing.NoReturn] = None
        self._is_setting_target = False

    def serialize(self) -> dict:
        super(TargetInstance, self).serialize()
        output = GraphEntity.serialize(self)
        output['_target_id'] = self._target_id
        output['_inputs'] = []
        output['_outputs'] = []
        return output

    def deserialize(self, data: dict) -> None:
        """
        Does not invoke super on DagNode base class because inputs and outputs are derived from assembly instance.
        """
        data['_inputs'] = []
        data['_outputs'] = []
        GraphEntity.deserialize(self, data=data)
        self._target_id = data['_target_id'] if '_target_id' in data.keys() else ''

    def invalidate(self, plug: 'Plug' = None):
        """
        Invalidate any plug that is a destination of an output plug named plug.name.
        """
        # If a destination is invalidated it is assumed compute will be invoked once a destination endpoint has been found
        do_compute = True
        output: Plug
        destination: Plug
        for output in self.outputs:
            if not plug or output.name == plug.name:
                for destination in output.outputs:
                    destination.invalidate()
                    do_compute = False
        if do_compute:
            self.compute()

    @property
    def target_id(self) -> str:
        return self._target_id

    @property
    def target(self) -> typing.Union[Target, typing.NoReturn]:
        return self._target

    @target.setter
    def target(self, value: typing.Union[Target, typing.NoReturn]) -> None:
        if self._target is value:
            return
        if not self._target_id and value:
            raise Exception('Target ID "" does not match assembly instance "{0}".'.format(value.id))
        if self._target_id and not value:
            raise Exception('Target ID "{0}" does not match assembly instance "None".'.format(self._target_id))
        if self._target_id and value and not self._target_id == value.id:
            raise Exception('Target ID "{0}" does not match assembly instance "{1}".'.format(self._target_id, value.id))

        self._is_setting_target = True

        notification = ChangeNotification(
            item=self,
            property_name='target',
            old_value=self._target,
            new_value=value
        )

        self._target = value

        self._inputs = []
        self._outputs = []
        if self._target:
            node_id_plug = Plug.Create(
                parent=self,
                name='node_id_output',
                display_name='Node Id',
                value_type=Plug.VALUE_TYPE_STRING
            )
            node_id_plug._id = self._target.id
            node_id_plug.value = self._target.id
            self._outputs.append(node_id_plug)
            for node in self._target.nodes:
                for o in node.inputs:
                    plug = Plug(parent=self)
                    plug.deserialize(data=o.serialize())
                    self._inputs.append(plug)
                for o in node.outputs:
                    plug = Plug(parent=self)
                    plug.deserialize(data=o.serialize())
                    self._outputs.append(plug)

        self._is_setting_target = False

        self._notify(notification=notification)

        self.invalidate()


class Operator(Base):

    def __init__(
            self,
            id: str,
            name: str,
            required_inputs: int,
            min_inputs: int,
            max_inputs: int,
            num_outputs: int,
    ):
        super(Operator, self).__init__()
        self._id = id
        self._name: str = name
        self._required_inputs: int = required_inputs
        self._min_inputs: int = min_inputs
        self._max_inputs: int = max_inputs
        self._num_outputs: int = num_outputs
        self._computing: bool = False

    def compute(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        """
        Base class only computes input_plugs. It is assumed that extending class computes output plugs.
        """
        if self._computing:
            return

        self._computing = True

        if len(input_plugs) < self._required_inputs:
            raise Exception('Array of inputs not of required length "{0}". Actual length "{1}".  Operator: "{2}"'.format(self._required_inputs, len(input_plugs), self.__class__.__name__))

        for plug in input_plugs:
            if plug.input:
                if plug.input in input_plugs:
                    print('WARNING: Universal Material Map: Invalid state in compute graph. Compute cancelled.')
                    print('\tInput {0}.{1} is dependent on another input on the same node.'.format(plug.parent.display_name, plug.name))
                    print('\tDependency: {0}.{1}'.format(plug.input.parent.display_name, plug.input.name))
                    print('\tThis is not supported.')
                    print('\tComputations likely to not behave as expected. It is recommended you restart the solution using this data.')
                    self._computing = False
                    return
                if plug.input in output_plugs:
                    print('WARNING: Universal Material Map: Invalid state in compute graph. Compute cancelled.')
                    print('\tInput {0}.{1} is dependent on another output on the same node.'.format(
                        plug.parent.display_name, plug.name))
                    print('\tDependency: {0}.{1}'.format(plug.input.parent.display_name, plug.input.name))
                    print('\tThis is not supported.')
                    print('\tComputations likely to not behave as expected. It is recommended you restart the solution using this data.')
                    self._computing = False
                    return

        for plug in output_plugs:
            if plug.input:
                if plug.input in output_plugs:
                    print('WARNING: Universal Material Map: Invalid state in compute graph. Compute cancelled.')
                    print('\tInput {0}.{1} is dependent on another output on the same node.'.format(
                        plug.parent.display_name, plug.name))
                    print('\tDependency: {0}.{1}'.format(plug.input.parent.display_name, plug.input.name))
                    print('\tThis is not supported.')
                    print('\tComputations likely to not behave as expected. It is recommended you restart the solution using this data.')
                    self._computing = False
                    return

        self._compute_inputs(input_plugs=input_plugs)
        self._compute_outputs(input_plugs=input_plugs, output_plugs=output_plugs)

        self._computing = False

    def _compute_inputs(self, input_plugs: typing.List[Plug]):
        # Compute dependencies
        for plug in input_plugs:
            if not plug.input:
                continue
            if not plug.input.parent:
                continue
            if not plug.input.is_invalid:
                continue
            plug.input.parent.compute()

        # Set computed_value
        for plug in input_plugs:
            if plug.input:
                plug.computed_value = plug.input.computed_value
            else:
                plug.computed_value = plug.value

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        raise NotImplementedError(self.__class__)

    def generate_input(self, parent: 'DagNode', index: int) -> Plug:
        """
        Base class provides method template but does nothing.
        """
        pass

    def generate_output(self, parent: 'DagNode', index: int) -> Plug:
        """
        Base class provides method template but does nothing.
        """
        pass

    def test(self) -> None:
        parent = OperatorInstance()
        inputs = []
        while len(inputs) < self.min_inputs:
            inputs.append(
                self.generate_input(parent=parent, index=len(inputs))
            )
        outputs = []
        while len(outputs) < self.num_outputs:
            outputs.append(
                self.generate_output(parent=parent, index=len(outputs))
            )
        self._prepare_plugs_for_test(input_plugs=inputs, output_plugs=outputs)
        self._perform_test(input_plugs=inputs, output_plugs=outputs)
        self._assert_test(input_plugs=inputs, output_plugs=outputs)

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        pass

    def _perform_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        self.compute(input_plugs=input_plugs, output_plugs=output_plugs)

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        raise NotImplementedError()

    def remove_plug(self, operator_instance: 'OperatorInstance', plug: 'Plug') -> None:
        if not plug.is_removable:
            raise Exception('Plug is not removable')
        notifications = []
        if plug in operator_instance._inputs:
            old_value = operator_instance._inputs[:]
            operator_instance._inputs.remove(plug)
            operator_instance._unsubscribe(notifying=plug)
            notifications.append(
                ChangeNotification(
                    item=operator_instance,
                    property_name='inputs',
                    old_value=old_value,
                    new_value=operator_instance._inputs[:]
                )
            )

        if plug in operator_instance._outputs:
            old_value = operator_instance._outputs[:]
            operator_instance._outputs.remove(plug)
            operator_instance._unsubscribe(notifying=plug)
            notifications.append(
                ChangeNotification(
                    item=operator_instance,
                    property_name='outputs',
                    old_value=old_value,
                    new_value=operator_instance._outputs[:]
                )
            )

        destination: Plug
        for destination in plug.outputs:
            destination.input = None

        for notification in notifications:
            for callback in operator_instance._changed_callbacks.values():
                callback(notification)

    @property
    def name(self) -> str:
        return self._name

    @property
    def min_inputs(self) -> int:
        return self._min_inputs

    @property
    def max_inputs(self) -> int:
        return self._max_inputs

    @property
    def required_inputs(self) -> int:
        return self._required_inputs

    @property
    def num_outputs(self) -> int:
        return self._num_outputs


class GraphOutput(Operator):
    """
    Output resolves to a node id.
    """

    def __init__(self):
        super(GraphOutput, self).__init__(
            id='5f39ab48-5bee-46fe-9a22-0f678013568e',
            name='Graph Output',
            required_inputs=1,
            min_inputs=1,
            max_inputs=1,
            num_outputs=1
        )

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='input_node_id', display_name='Node Id', value_type=Plug.VALUE_TYPE_NODE_ID)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='output_node_id', display_name='Node Id', value_type=Plug.VALUE_TYPE_NODE_ID)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].computed_value = input_plugs[0].computed_value

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        input_plugs[0].computed_value = self.id

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        for output in output_plugs:
            if not output.computed_value == self.id:
                raise Exception('Test failed.')


class OperatorInstance(GraphEntity):

    @classmethod
    def FromOperator(cls, operator: Operator) -> 'OperatorInstance':
        instance = OperatorInstance()
        instance._is_deserializing = True
        instance._operator = operator
        instance._display_name = operator.name
        while len(instance._inputs) < operator.min_inputs:
            instance._inputs.append(
                operator.generate_input(parent=instance, index=len(instance._inputs))
            )
        while len(instance._outputs) < operator.num_outputs:
            instance._outputs.append(
                operator.generate_output(parent=instance, index=len(instance._outputs))
            )

        instance._operator_module = operator.__class__.__module__
        instance._operator_class_name = operator.__class__.__name__

        instance._is_deserializing = False
        instance.invalidate()
        return instance

    def __init__(self):
        super(OperatorInstance, self).__init__()
        self._description: str = ''
        self._operator_module: str = ''
        self._operator_class_name: str = ''
        self._operator: Operator = None
        self._is_deserializing = False

    def serialize(self) -> dict:
        output = super(OperatorInstance, self).serialize()
        output['_description'] = self._description
        output['_operator_module'] = self._operator_module
        output['_operator_class_name'] = self._operator_class_name
        return output

    def deserialize(self, data: dict) -> None:
        self._is_deserializing = True
        super(OperatorInstance, self).deserialize(data=data)

        self._description = data['_description'] if '_description' in data.keys() else ''
        self._operator_module = data['_operator_module'] if '_operator_module' in data.keys() else ''
        self._operator_class_name = data['_operator_class_name'] if '_operator_class_name' in data.keys() else ''
        if not self._operator_module:
            raise Exception('Unexpected data: no valid "operator module" defined')
        if not self._operator_class_name:
            raise Exception('Unexpected data: no valid "operator class name" defined')
        if self._operator_module not in sys.modules.keys():
            importlib.import_module(self._operator_module)
        module_pointer = sys.modules[self._operator_module]
        class_pointer = module_pointer.__dict__[self._operator_class_name]
        self._operator = typing.cast(Operator, class_pointer())

        notifying = []
        while len(self._inputs) < self._operator.min_inputs:
            plug = self._operator.generate_input(parent=self, index=len(self._inputs))
            self._inputs.append(plug)
            notifying.append(plug)

        while len(self._outputs) < self._operator.num_outputs:
            plug = self._operator.generate_output(parent=self, index=len(self._outputs))
            self._outputs.append(plug)
            notifying.append(plug)

        self._is_deserializing = False

        for o in notifying:
            self._subscribe(notifying=o)

        self.invalidate()

    def invalidate(self, plug: 'Plug' = None):
        """
        Because one plug changed we assume any connected plug to any output needs to be invalidated.
        """
        if self._is_deserializing:
            return

        # Set all outputs to invalid
        output: Plug
        for output in self.outputs:
            output._is_invalid = True

        # If a destination is invalidated it is assumed compute will be invoked once a destination endpoint has been found
        do_compute = True
        destination: Plug
        for output in self.outputs:
            for destination in output.outputs:
                destination.invalidate()
                do_compute = False
        if do_compute:
            self.compute()

    def compute(self) -> None:

        if self._operator:
            self._operator.compute(input_plugs=self._inputs, output_plugs=self._outputs)

    def add_input(self) -> Plug:
        if not self.can_add_input:
            raise Exception('Cannot add another input.')
        old_value = self._inputs[:]

        plug = self._operator.generate_input(parent=self, index=len(self._inputs))
        self._inputs.append(plug)
        self._subscribe(notifying=plug)

        notification = ChangeNotification(
            item=self,
            property_name='inputs',
            old_value=old_value,
            new_value=self._inputs[:]
        )
        self._notify(notification=notification)

        for o in self.outputs:
            o.invalidate()

        return plug

    def remove_plug(self, plug: 'Plug') -> None:
        self._operator.remove_plug(operator_instance=self, plug=plug)

    @property
    def operator(self) -> Operator:
        return self._operator

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        if self._description is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='description',
            old_value=self._description,
            new_value=value
        )
        self._description = value
        self._notify(notification=notification)

    @DagNode.can_add_input.getter
    def can_add_input(self) -> bool:
        if self._operator.max_inputs == -1:
            return True
        return len(self._inputs) < self._operator.max_inputs - 1


class StyleInfo(object):

    def __init__(
            self,
            name: str,
            background_color: int,
            border_color: int,
            connection_color: int,
            node_background_color: int,
            footer_icon_filename: str,
    ):
        super(StyleInfo, self).__init__()
        self._name: str = name
        self._background_color: int = background_color
        self._border_color: int = border_color
        self._connection_color: int = connection_color
        self._node_background_color: int = node_background_color
        self._footer_icon_filename: str = footer_icon_filename

    @property
    def name(self) -> str:
        return self._name

    @property
    def background_color(self) -> int:
        return self._background_color

    @property
    def border_color(self) -> int:
        return self._border_color

    @property
    def connection_color(self) -> int:
        return self._connection_color

    @property
    def node_background_color(self) -> int:
        return self._node_background_color

    @property
    def footer_icon_filename(self) -> str:
        return self._footer_icon_filename


class ConversionGraph(Base):
    # STYLE_OUTPUT: StyleInfo = StyleInfo(
    #     name='output',
    #     background_color=0xFF2E2E2E,
    #     border_color=0xFFB97E9C,
    #     connection_color=0xFF80C26F,
    #     node_background_color=0xFF444444,
    #     footer_icon_filename='Material.svg'
    # )
    STYLE_SOURCE_NODE: StyleInfo = StyleInfo(
        name='source_node',
        background_color=0xFF2E2E2E,
        border_color=0xFFE5AAC8,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='Material.svg'
    )
    STYLE_ASSEMBLY_REFERENCE: StyleInfo = StyleInfo(
        name='assembly_reference',
        background_color=0xFF2E2E2E,
        border_color=0xFFB97E9C,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='Material.svg'
    )
    STYLE_OPERATOR_INSTANCE: StyleInfo = StyleInfo(
        name='operator_instance',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='constant_color.svg'
    )

    STYLE_VALUE_RESOLVER: StyleInfo = StyleInfo(
        name='value_resolver',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='value_resolver.svg'
    )

    STYLE_BOOLEAN_SWITCH: StyleInfo = StyleInfo(
        name='boolean_switch',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='boolean_switch.svg'
    )

    STYLE_CONSTANT_BOOLEAN: StyleInfo = StyleInfo(
        name='constant_boolean',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='constant_boolean.svg'
    )

    STYLE_CONSTANT_COLOR: StyleInfo = StyleInfo(
        name='constant_color',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='constant_color.svg'
    )

    STYLE_CONSTANT_FLOAT: StyleInfo = StyleInfo(
        name='constant_float',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='constant_float.svg'
    )

    STYLE_CONSTANT_INTEGER: StyleInfo = StyleInfo(
        name='constant_integer',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='constant_integer.svg'
    )

    STYLE_CONSTANT_STRING: StyleInfo = StyleInfo(
        name='constant_string',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='constant_string.svg'
    )

    STYLE_EQUAL: StyleInfo = StyleInfo(
        name='equal',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='equal.svg'
    )

    STYLE_GREATER_THAN: StyleInfo = StyleInfo(
        name='greater_than',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='greater_than.svg'
    )

    STYLE_LESS_THAN: StyleInfo = StyleInfo(
        name='less_than',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='less_than.svg'
    )

    STYLE_MERGE_RGB: StyleInfo = StyleInfo(
        name='merge_rgb',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='merge_rgb.svg'
    )

    STYLE_NOT: StyleInfo = StyleInfo(
        name='not',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='not.svg'
    )

    STYLE_OR: StyleInfo = StyleInfo(
        name='or',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='or.svg'
    )

    STYLE_SPLIT_RGB: StyleInfo = StyleInfo(
        name='split_rgb',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='split_rgb.svg'
    )

    STYLE_TRANSPARENCY_RESOLVER: StyleInfo = StyleInfo(
        name='transparency_resolver',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='transparency_resolver.svg'
    )

    STYLE_OUTPUT: StyleInfo = StyleInfo(
        name='output',
        background_color=0xFF34302A,
        border_color=0xFFCD923A,
        connection_color=0xFF80C26F,
        node_background_color=0xFF444444,
        footer_icon_filename='output.svg'
    )

    STYLE_INFOS = (
        STYLE_OUTPUT,
        STYLE_SOURCE_NODE,
        STYLE_ASSEMBLY_REFERENCE,
        STYLE_OPERATOR_INSTANCE,
        STYLE_VALUE_RESOLVER,
        STYLE_BOOLEAN_SWITCH,
        STYLE_CONSTANT_BOOLEAN,
        STYLE_CONSTANT_COLOR,
        STYLE_CONSTANT_FLOAT,
        STYLE_CONSTANT_INTEGER,
        STYLE_CONSTANT_STRING,
        STYLE_EQUAL,
        STYLE_GREATER_THAN,
        STYLE_LESS_THAN,
        STYLE_NOT,
        STYLE_OR,
        STYLE_SPLIT_RGB,
        STYLE_TRANSPARENCY_RESOLVER,
        STYLE_MERGE_RGB,
    )

    def __init__(self):
        super(ConversionGraph, self).__init__()
        self._graph_output: OperatorInstance = OperatorInstance.FromOperator(operator=GraphOutput())
        self._target_instances: typing.List[TargetInstance] = []
        self._operator_instances: typing.List[OperatorInstance] = [self._graph_output]
        self._connections: typing.List[Connection] = []
        self._library: Library = None
        self._source_node_id: str = ''
        self._source_node: TargetInstance = None
        self._filename: str = ''
        self._exists_on_disk: bool = False
        self._revision: int = 0

    def _on_notification(self, notification: ChangeNotification) -> None:
        if notification.item == self:
            return
        # Re-broadcast notification
        self._notify(notification=notification)

    def serialize(self) -> dict:
        output = super(ConversionGraph, self).serialize()
        output['_target_instances'] = [o.serialize() for o in self._target_instances]
        output['_operator_instances'] = [o.serialize() for o in self._operator_instances]
        output['_connections'] = [o.serialize() for o in self._connections]
        output['_source_node_id'] = self._source_node_id
        output['_revision'] = self._revision
        return output

    def deserialize(self, data: dict) -> None:
        super(ConversionGraph, self).deserialize(data=data)

        notifications = []

        # _source_node_id
        old = self._source_node_id
        new = data['_source_node_id'] if '_source_node_id' in data.keys() else ''
        if not old == new:
            self._source_node_id = new
            notifications.append(
                ChangeNotification(
                    item=self,
                    property_name='source_node_id',
                    old_value=old,
                    new_value=new
                )
            )

        # _revision
        old = self._revision
        new = data['_revision'] if '_revision' in data.keys() else 0
        if not old == new:
            self._revision = new
            notifications.append(
                ChangeNotification(
                    item=self,
                    property_name='revision',
                    old_value=old,
                    new_value=new
                )
            )

        # _target_instances
        old = self._target_instances[:]

        while len(self._target_instances):
            self._unsubscribe(notifying=self._target_instances.pop())

        items = []
        if '_target_instances' in data.keys():
            for o in data['_target_instances']:
                item = TargetInstance()
                item.deserialize(data=o)
                items.append(item)
        self._target_instances = items

        if not self._target_instances == old:
            notifications.append(
                ChangeNotification(
                    item=self,
                    property_name='target_instances',
                    old_value=old,
                    new_value=self._target_instances
                )
            )

        # _source_node
        old = self._source_node

        source_node = None
        if self._source_node_id:
            items = [o for o in self._target_instances if o.id == self._source_node_id]
            source_node = items[0] if len(items) else None
        self._source_node = source_node

        if not self._source_node == old:
            notifications.append(
                ChangeNotification(
                    item=self,
                    property_name='source_node',
                    old_value=old,
                    new_value=self._source_node
                )
            )

        # _operator_instances
        # _graph_output
        old_operator_instances = self._operator_instances
        old_graph_output = self._graph_output

        items = []
        self._graph_output = None
        if '_operator_instances' in data.keys():
            for o in data['_operator_instances']:
                item = OperatorInstance()
                item.deserialize(data=o)
                items.append(item)
                if isinstance(item.operator, GraphOutput):
                    self._graph_output = item

        if not self._graph_output:
            self._graph_output = OperatorInstance.FromOperator(operator=GraphOutput())
            items.insert(0, self._graph_output)

        self._operator_instances = items

        if not self._operator_instances == old_operator_instances:
            notifications.append(
                ChangeNotification(
                    item=self,
                    property_name='operator_instances',
                    old_value=old_operator_instances,
                    new_value=self._operator_instances
                )
            )

        if not self._graph_output == old_graph_output:
            notifications.append(
                ChangeNotification(
                    item=self,
                    property_name='old_graph_output',
                    old_value=old_operator_instances,
                    new_value=self._graph_output
                )
            )

        items = []
        if '_connections' in data.keys():
            for o in data['_connections']:
                item = Connection()
                item.deserialize(data=o)
                items.append(item)
        self._connections = items

        for o in self._target_instances:
            self._subscribe(notifying=o)
        for o in self._operator_instances:
            self._subscribe(notifying=o)

        for o in notifications:
            self._notify(notification=o)

    def build_dag(self) -> None:
        for connection in self._connections:
            source = self._get_plug(plug_id=connection.source_id)
            destination = self._get_plug(plug_id=connection.destination_id)
            if not source or not destination:
                continue
            if destination not in source.outputs:
                source.outputs.append(destination)
            destination.input = source

    def _get_plug(self, plug_id: str) -> typing.Union[Plug, typing.NoReturn]:
        for assembly_reference in self._target_instances:
            for plug in assembly_reference.inputs:
                if plug.id == plug_id:
                    return plug
            for plug in assembly_reference.outputs:
                if plug.id == plug_id:
                    return plug
        for operator_instance in self._operator_instances:
            for plug in operator_instance.outputs:
                if plug.id == plug_id:
                    return plug
            for plug in operator_instance.inputs:
                if plug.id == plug_id:
                    return plug
        return None

    def add_node(self, node: OperatorInstance) -> None:
        self._operator_instances.append(node)

    def add_connection(self, source: Plug, destination: Plug) -> None:
        connection = Connection()
        connection._source_id = source.id
        connection._destination_id = destination.id
        self._connections.append(connection)
        if destination not in source.outputs:
            source.outputs.append(destination)
        destination.input = source

    def add(self, entity: GraphEntity) -> None:
        if isinstance(entity, TargetInstance):
            if entity in self._target_instances:
                return
            self._target_instances.append(entity)
            self._subscribe(notifying=entity)
            return
        if isinstance(entity, OperatorInstance):
            if entity in self._operator_instances:
                return
            self._operator_instances.append(entity)
            self._subscribe(notifying=entity)
            return
        raise NotImplementedError()

    def can_be_removed(self, entity: GraphEntity) -> bool:
        if not entity:
            return False
        if entity not in self._target_instances and entity not in self._operator_instances:
            return False
        if entity == self._graph_output:
            return False
        return True

    def remove(self, entity: GraphEntity) -> None:
        if not self.can_be_removed(entity=entity):
            raise Exception('Not allowed: entity is not allowed to be deleted.')

        if isinstance(entity, TargetInstance):
            if entity in self._target_instances:
                self._unsubscribe(notifying=entity)
                self._target_instances.remove(entity)
            to_remove = []
            for connection in self._connections:
                if connection.source_id == entity.id or connection.destination_id == entity.id:
                    to_remove.append(connection)
            for connection in to_remove:
                self.remove_connection(connection=connection)
            return

        if isinstance(entity, OperatorInstance):
            if entity in self._operator_instances:
                self._unsubscribe(notifying=entity)
                self._operator_instances.remove(entity)
            to_remove = []
            for connection in self._connections:
                if connection.source_id == entity.id or connection.destination_id == entity.id:
                    to_remove.append(connection)
            for connection in to_remove:
                self.remove_connection(connection=connection)
            return

        raise NotImplementedError()

    def remove_connection(self, connection: Connection) -> None:
        if connection in self._connections:
            self._connections.remove(connection)
        source = self._get_plug(plug_id=connection.source_id)
        destination = self._get_plug(plug_id=connection.destination_id)
        if source and destination:
            if destination in source.outputs:
                source.outputs.remove(destination)
            if destination.input == source:
                destination.input = None

    def get_entity_by_id(self, identifier: str) -> typing.Union[GraphEntity, typing.NoReturn]:
        entities = [entity for entity in self._target_instances if entity.id == identifier]
        if len(entities):
            return entities[0]
        entities = [entity for entity in self._operator_instances if entity.id == identifier]
        if len(entities):
            return entities[0]
        return None

    def get_output_entity(self) -> typing.Union[TargetInstance, typing.NoReturn]:
        """
        Computes the dependency graph and returns the resulting Target reference.

        Make sure relevant source node plug values have been set prior to invoking this method.
        """
        if not self._graph_output:
            return None
        self._graph_output.invalidate()
        assembly_id = self._graph_output.outputs[0].computed_value
        for item in self._target_instances:
            if item.target_id == assembly_id:
                return item
        return None

    def get_object_style_name(self, entity: GraphEntity) -> str:
        if not entity:
            return ''
        # TODO: Style computed output entity
        # if entity == self.get_output_entity():
        #     return ConversionGraph.STYLE_OUTPUT.name
        if entity == self.source_node:
            return ConversionGraph.STYLE_SOURCE_NODE.name
        if isinstance(entity, TargetInstance):
            return ConversionGraph.STYLE_ASSEMBLY_REFERENCE.name
        if isinstance(entity, OperatorInstance):
            if entity.operator:
                if entity.operator.__class__.__name__ == 'ConstantBoolean':
                    return ConversionGraph.STYLE_CONSTANT_BOOLEAN.name
                if entity.operator.__class__.__name__ == 'ConstantColor':
                    return ConversionGraph.STYLE_CONSTANT_COLOR.name
                if entity.operator.__class__.__name__ == 'ConstantFloat':
                    return ConversionGraph.STYLE_CONSTANT_FLOAT.name
                if entity.operator.__class__.__name__ == 'ConstantInteger':
                    return ConversionGraph.STYLE_CONSTANT_INTEGER.name
                if entity.operator.__class__.__name__ == 'ConstantString':
                    return ConversionGraph.STYLE_CONSTANT_STRING.name
                if entity.operator.__class__.__name__ == 'BooleanSwitch':
                    return ConversionGraph.STYLE_BOOLEAN_SWITCH.name
                if entity.operator.__class__.__name__ == 'ValueResolver':
                    return ConversionGraph.STYLE_VALUE_RESOLVER.name
                if entity.operator.__class__.__name__ == 'SplitRGB':
                    return ConversionGraph.STYLE_SPLIT_RGB.name
                if entity.operator.__class__.__name__ == 'MergeRGB':
                    return ConversionGraph.STYLE_MERGE_RGB.name
                if entity.operator.__class__.__name__ == 'LessThan':
                    return ConversionGraph.STYLE_LESS_THAN.name
                if entity.operator.__class__.__name__ == 'GreaterThan':
                    return ConversionGraph.STYLE_GREATER_THAN.name
                if entity.operator.__class__.__name__ == 'Or':
                    return ConversionGraph.STYLE_OR.name
                if entity.operator.__class__.__name__ == 'Equal':
                    return ConversionGraph.STYLE_EQUAL.name
                if entity.operator.__class__.__name__ == 'Not':
                    return ConversionGraph.STYLE_NOT.name
                if entity.operator.__class__.__name__ == 'MayaTransparencyResolver':
                    return ConversionGraph.STYLE_TRANSPARENCY_RESOLVER.name
                if entity.operator.__class__.__name__ == 'GraphOutput':
                    return ConversionGraph.STYLE_OUTPUT.name
            return ConversionGraph.STYLE_OPERATOR_INSTANCE.name
        return ''

    def get_output_targets(self) -> typing.List[TargetInstance]:
        return [o for o in self._target_instances if not o == self._source_node]

    @property
    def target_instances(self) -> typing.List[TargetInstance]:
        return self._target_instances[:]

    @property
    def operator_instances(self) -> typing.List[OperatorInstance]:
        return self._operator_instances[:]

    @property
    def connections(self) -> typing.List[Connection]:
        return self._connections[:]

    @property
    def filename(self) -> str:
        return self._filename

    @filename.setter
    def filename(self, value: str) -> None:
        if self._filename is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='filename',
            old_value=self._filename,
            new_value=value
        )
        self._filename = value
        self._notify(notification=notification)

    @property
    def library(self) -> 'Library':
        return self._library

    @property
    def graph_output(self) -> OperatorInstance:
        return self._graph_output

    @property
    def source_node(self) -> TargetInstance:
        return self._source_node

    @source_node.setter
    def source_node(self, value: TargetInstance) -> None:
        if self._source_node is value:
            return
        node_notification = ChangeNotification(
            item=self,
            property_name='source_node',
            old_value=self._source_node,
            new_value=value
        )
        node_id_notification = ChangeNotification(
            item=self,
            property_name='source_node_id',
            old_value=self._source_node_id,
            new_value=value.id if value else ''
        )

        self._source_node = value
        self._source_node_id = self._source_node.id if self._source_node else ''

        self._notify(notification=node_notification)
        self._notify(notification=node_id_notification)

    @property
    def exists_on_disk(self) -> bool:
        return self._exists_on_disk

    @property
    def revision(self) -> int:
        return self._revision

    @revision.setter
    def revision(self, value: int) -> None:
        if self._revision is value:
            return
        notification = ChangeNotification(
            item=self,
            property_name='revision',
            old_value=self._revision,
            new_value=value
        )
        self._revision = value
        self._notify(notification=notification)


class FileHeader(Serializable):

    @classmethod
    def FromInstance(cls, instance: Serializable) -> 'FileHeader':
        header = cls()
        header._module = instance.__class__.__module__
        header._class_name = instance.__class__.__name__
        return header

    @classmethod
    def FromData(cls, data: dict) -> 'FileHeader':
        if '_module' not in data.keys():
            raise Exception('Unexpected data: key "_module" not in dictionary')
        if '_class_name' not in data.keys():
            raise Exception('Unexpected data: key "_class_name" not in dictionary')
        header = cls()
        header._module = data['_module']
        header._class_name = data['_class_name']
        return header

    def __init__(self):
        super(FileHeader, self).__init__()
        self._module = ''
        self._class_name = ''

    def serialize(self) -> dict:
        output = dict()
        output['_module'] = self._module
        output['_class_name'] = self._class_name
        return output

    @property
    def module(self) -> str:
        return self._module

    @property
    def class_name(self) -> str:
        return self._class_name


class FileUtility(Serializable):

    @classmethod
    def FromInstance(cls, instance: Serializable) -> 'FileUtility':
        utility = cls()
        utility._header = FileHeader.FromInstance(instance=instance)
        utility._content = instance
        return utility

    @classmethod
    def FromData(cls, data: dict) -> 'FileUtility':
        if '_header' not in data.keys():
            raise Exception('Unexpected data: key "_header" not in dictionary')
        if '_content' not in data.keys():
            raise Exception('Unexpected data: key "_content" not in dictionary')
        utility = cls()
        utility._header = FileHeader.FromData(data=data['_header'])

        if utility._header.module not in sys.modules.keys():
            importlib.import_module(utility._header.module)
        module_pointer = sys.modules[utility._header.module]
        class_pointer = module_pointer.__dict__[utility._header.class_name]
        utility._content = class_pointer()
        if isinstance(utility._content, Serializable):
            utility._content.deserialize(data=data['_content'])
        return utility

    def __init__(self):
        super(FileUtility, self).__init__()
        self._header: FileHeader = None
        self._content: Serializable = None

    def serialize(self) -> dict:
        output = dict()
        output['_header'] = self._header.serialize()
        output['_content'] = self._content.serialize()
        return output

    def assert_content_serializable(self):
        data = self.content.serialize()
        self._assert(data=data)

    def _assert(self, data: dict):
        for key, value in data.items():
            if isinstance(value, dict):
                self._assert(data=value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._assert(data=item)
                    else:
                        print(item)
            else:
                print(key, value)

    @property
    def header(self) -> FileHeader:
        return self._header

    @property
    def content(self) -> Serializable:
        return self._content


class Library(Base):

    """
    A Library represents a UMM data set. It can contain any of the following types of files:

        - Settings
        - Conversion Graph
        - Target
        - Conversion Manifest

    A Library is divided into a "core" and a "user" data set.

        "core":

            - Files provided by NVIDIA.
            - Installed and updated by UMM.
            - Adding, editing, and deleting files require running in "Developer Mode".
            - Types:

                - Conversion Graph
                - Target
                - Conversion Manifest

        "user"

            - Files created and updated by user.
            - Types:

                - Conversion Graph
                - Target
                - Conversion Manifest
                    Overrides ./core/Conversion Manifest

    ...or...

        each file header has an attribute: source = core, source = user

        if source == core then it is read-only to users.

        TARGET: problem with that is what if user needs to update an existing target?

            ...why would they?

            ...because they may want to edit property states in the Target... would want their own.

        CONVERSION GRAPH

            ...they could just Save As and make a different one. no problem here. do need to change the 'source' attribute to 'user' though.

        CONVERSION MANIFEST

            2 files

                ConversionManifest.json
                ConversionManifest_user.json (overrides ConversionManifest.json)

                Limitation: User cannot all together remove a manifest item
    """

    @classmethod
    def Create(
            cls,
            library_id: str,
            name: str,
            manifest: IDelegate = None,
            conversion_graph: IDelegate = None,
            target: IDelegate = None,
            settings: IDelegate = None
    ) -> 'Library':
        instance = typing.cast(Library, super(Library, cls).Create())
        instance._id = library_id
        instance._name = name
        instance._manifest = manifest
        instance._conversion_graph = conversion_graph
        instance._target = target
        instance._settings = settings
        return instance

    def __init__(self):
        super(Library, self).__init__()
        self._name: str = ''
        self._manifest: typing.Union[IDelegate, typing.NoReturn] = None
        self._conversion_graph: typing.Union[IDelegate, typing.NoReturn] = None
        self._target: typing.Union[IDelegate, typing.NoReturn] = None
        self._settings: typing.Union[IDelegate, typing.NoReturn] = None

    def serialize(self) -> dict:
        output = super(Library, self).serialize()
        output['_name'] = self._name
        return output

    def deserialize(self, data: dict) -> None:
        super(Library, self).deserialize(data=data)
        self._name = data['_name'] if '_name' in data.keys() else ''

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def manifest(self) -> typing.Union[IDelegate, typing.NoReturn]:
        return self._manifest

    @property
    def conversion_graph(self) -> typing.Union[IDelegate, typing.NoReturn]:
        return self._conversion_graph

    @property
    def target(self) -> typing.Union[IDelegate, typing.NoReturn]:
        return self._target

    @property
    def settings(self) -> typing.Union[IDelegate, typing.NoReturn]:
        return self._settings

    @property
    def is_read_only(self) -> bool:
        return not self._conversion_graph or not self._target or not self._conversion_graph


class Settings(Serializable):

    def __init__(self):
        super(Settings, self).__init__()
        self._libraries: typing.List[Library] = []
        self._store_id = 'Settings.json'
        self._render_contexts: typing.List[str] = []

    def serialize(self) -> dict:
        output = super(Settings, self).serialize()
        output['_libraries'] = [o.serialize() for o in self._libraries]
        output['_render_contexts'] = self._render_contexts
        return output

    def deserialize(self, data: dict) -> None:
        super(Settings, self).deserialize(data=data)
        items = []
        if '_libraries' in data.keys():
            for o in data['_libraries']:
                item = Library()
                item.deserialize(data=o)
                items.append(item)
        self._libraries = items
        self._render_contexts = data['_render_contexts'] if '_render_contexts' in data.keys() else []

    @property
    def libraries(self) -> typing.List[Library]:
        return self._libraries

    @property
    def store_id(self) -> str:
        return self._store_id

    @property
    def render_contexts(self) -> typing.List[str]:
        return self._render_contexts


class ClassInfo(object):

    def __init__(self, display_name: str, class_name: str):
        super(ClassInfo, self).__init__()
        self._display_name = display_name
        self._class_name = class_name

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def class_name(self) -> str:
        return self._class_name


class OmniMDL(object):
    OMNI_GLASS: ClassInfo = ClassInfo(display_name='Omni Glass', class_name='OmniGlass.mdl|OmniGlass')
    OMNI_GLASS_OPACITY: ClassInfo = ClassInfo(display_name='Omni Glass Opacity',
                                              class_name='OmniGlass_Opacity.mdl|OmniGlass_Opacity')
    OMNI_PBR: ClassInfo = ClassInfo(display_name='Omni PBR', class_name='OmniPBR.mdl|OmniPBR')
    OMNI_PBR_CLEAR_COAT: ClassInfo = ClassInfo(display_name='Omni PBR Clear Coat',
                                               class_name='OmniPBR_ClearCoat.mdl|OmniPBR_ClearCoat')
    OMNI_PBR_CLEAR_COAT_OPACITY: ClassInfo = ClassInfo(display_name='Omni PBR Clear Coat Opacity',
                                                       class_name='OmniPBR_ClearCoat_Opacity.mdl|OmniPBR_ClearCoat_Opacity')
    OMNI_PBR_OPACITY = ClassInfo(display_name='Omni PBR Opacity', class_name='OmniPBR_Opacity.mdl|OmniPBR_Opacity')
    OMNI_SURFACE: ClassInfo = ClassInfo(display_name='OmniSurface', class_name='OmniSurface.mdl|OmniSurface')
    OMNI_SURFACE_LITE: ClassInfo = ClassInfo(display_name='OmniSurfaceLite',
                                             class_name='OmniSurfaceLite.mdl|OmniSurfaceLite')
    OMNI_SURFACE_UBER: ClassInfo = ClassInfo(display_name='OmniSurfaceUber',
                                             class_name='OmniSurfaceUber.mdl|OmniSurfaceUber')


class MayaShader(object):
    LAMBERT: ClassInfo = ClassInfo(display_name='Lambert', class_name='lambert')


class ConversionMap(Serializable):

    @classmethod
    def Create(
            cls,
            render_context: str,
            application: str,
            document: ConversionGraph,
    ) -> 'ConversionMap':
        if not isinstance(document, ConversionGraph):
            raise Exception('Argument "document" unexpected class: "{0}"'.format(type(document)))
        instance = cls()
        instance._render_context = render_context
        instance._application = application
        instance._conversion_graph_id = document.id
        instance._conversion_graph = document
        return instance

    def __init__(self):
        super(ConversionMap, self).__init__()
        self._render_context: str = ''
        self._application: str = ''
        self._conversion_graph_id: str = ''
        self._conversion_graph: ConversionGraph = None

    def __eq__(self, other: 'ConversionMap') -> bool:
        if not isinstance(other, ConversionMap):
            return False
        if not self.render_context == other.render_context:
            return False
        if not self.application == other.application:
            return False
        if not self.conversion_graph_id == other.conversion_graph_id:
            return False
        return True

    def serialize(self) -> dict:
        output = super(ConversionMap, self).serialize()
        output['_render_context'] = self._render_context
        output['_application'] = self._application
        output['_conversion_graph_id'] = self._conversion_graph_id
        return output

    def deserialize(self, data: dict) -> None:
        super(ConversionMap, self).deserialize(data=data)
        self._render_context = data['_render_context'] if '_render_context' in data.keys() else ''
        self._application = data['_application'] if '_application' in data.keys() else ''
        self._conversion_graph_id = data['_conversion_graph_id'] if '_conversion_graph_id' in data.keys() else ''
        self._conversion_graph = None

    @property
    def render_context(self) -> str:
        return self._render_context

    @property
    def application(self) -> str:
        return self._application

    @property
    def conversion_graph_id(self) -> str:
        return self._conversion_graph_id

    @property
    def conversion_graph(self) -> ConversionGraph:
        return self._conversion_graph


class ConversionManifest(Serializable):

    def __init__(self):
        super(ConversionManifest, self).__init__()
        self._version_major: int = 100
        self._version_minor: int = 0
        self._conversion_maps: typing.List[ConversionMap] = []
        self._store_id = 'ConversionManifest.json'

    def serialize(self) -> dict:
        output = super(ConversionManifest, self).serialize()
        output['_version_major'] = self._version_major
        output['_version_minor'] = self._version_minor
        output['_conversion_maps'] = [o.serialize() for o in self._conversion_maps]
        return output

    def deserialize(self, data: dict) -> None:
        super(ConversionManifest, self).deserialize(data=data)
        self._version_major = data['_version_major'] if '_version_major' in data.keys() else 100
        self._version_minor = data['_version_minor'] if '_version_minor' in data.keys() else 0
        items = []
        if '_conversion_maps' in data.keys():
            for o in data['_conversion_maps']:
                item = ConversionMap()
                item.deserialize(data=o)
                items.append(item)
        self._conversion_maps = items

    def set_version(self, major: int = 100, minor: int = 0) -> None:
        self._version_major = major
        self._version_minor = minor

    def add(
            self,
            render_context: str,
            application: str,
            document: ConversionGraph,
    ) -> ConversionMap:
        item = ConversionMap.Create(
            render_context=render_context,
            application=application,
            document=document,
        )
        self._conversion_maps.append(item)
        return item

    def remove(self, item: ConversionMap) -> None:
        if item in self._conversion_maps:
            self._conversion_maps.remove(item)

    @property
    def conversion_maps(self) -> typing.List[ConversionMap]:
        return self._conversion_maps[:]

    @property
    def version(self) -> str:
        return '{0}.{1}'.format(self._version_major, self._version_minor)

    @property
    def version_major(self) -> int:
        return self._version_major

    @property
    def version_minor(self) -> int:
        return self._version_minor

    @property
    def store_id(self) -> str:
        return self._store_id

