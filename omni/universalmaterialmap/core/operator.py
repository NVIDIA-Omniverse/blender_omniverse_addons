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

from .data import Operator, Plug, DagNode, OperatorInstance
from . import util


class ConstantFloat(Operator):

    def __init__(self):
        super(ConstantFloat, self).__init__(
            id='293c38db-c9b3-4b37-ab02-c4ff6052bcb6',
            name='Constant Float',
            required_inputs=0,
            min_inputs=0,
            max_inputs=0,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].computed_value = output_plugs[0].value if output_plugs[0].value else 0.0

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='value',
                display_name='Float',
                value_type=Plug.VALUE_TYPE_FLOAT,
                editable=True
            )
            plug.value = 0.0
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].value = len(self.id) * 0.3

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        for output in output_plugs:
            if not output.computed_value == len(self.id) * 0.3:
                raise Exception('Test failed.')


class ConstantInteger(Operator):

    def __init__(self):
        super(ConstantInteger, self).__init__(
            id='293c38db-c9b3-4b37-ab02-c4ff6052bcb7',
            name='Constant Integer',
            required_inputs=0,
            min_inputs=0,
            max_inputs=0,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].computed_value = output_plugs[0].value if output_plugs[0].value else 0

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='value',
                display_name='Integer',
                value_type=Plug.VALUE_TYPE_INTEGER,
                editable=True
            )
            plug.value = 0
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].value = len(self.id)

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        for output in output_plugs:
            if not output.computed_value == len(self.id):
                raise Exception('Test failed.')


class ConstantBoolean(Operator):

    def __init__(self):
        super(ConstantBoolean, self).__init__(
            id='293c38db-c9b3-4b37-ab02-c4ff6052bcb8',
            name='Constant Boolean',
            required_inputs=0,
            min_inputs=0,
            max_inputs=0,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].computed_value = output_plugs[0].value if output_plugs[0].value else False

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='value',
                display_name='Boolean',
                value_type=Plug.VALUE_TYPE_BOOLEAN,
                editable=True
            )
            plug.value = True
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].value = False

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        for output in output_plugs:
            if output.computed_value:
                raise Exception('Test failed.')


class ConstantString(Operator):

    def __init__(self):
        super(ConstantString, self).__init__(
            id='cb169ec0-5ddb-45eb-98d1-5d09f1ca759g',
            name='Constant String',
            required_inputs=0,
            min_inputs=0,
            max_inputs=0,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].computed_value = output_plugs[0].value if output_plugs[0].value else ''
        # print('ConstantString._compute_outputs(): output_plugs[0].computed_value', output_plugs[0].computed_value)

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='value',
                display_name='String',
                value_type=Plug.VALUE_TYPE_STRING,
                editable=True
            )
            plug.value = ''
            plug.default_value = ''
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].value = self.id

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        for output in output_plugs:
            if not output.computed_value == self.id:
                raise Exception('Test failed.')


class ConstantRGB(Operator):

    def __init__(self):
        super(ConstantRGB, self).__init__(
            id='60f21797-dd62-4b06-9721-53882aa42e81',
            name='Constant RGB',
            required_inputs=0,
            min_inputs=0,
            max_inputs=0,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].computed_value = output_plugs[0].value if output_plugs[0].value else (0, 0, 0)

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='value',
                display_name='Color',
                value_type=Plug.VALUE_TYPE_VECTOR3,
                editable=True
            )
            plug.value = (0, 0, 0)
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].value = (0.1, 0.2, 0.3)

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        for output in output_plugs:
            if not output.computed_value == (0.1, 0.2, 0.3):
                raise Exception('Test failed.')


class ConstantRGBA(Operator):

    def __init__(self):
        super(ConstantRGBA, self).__init__(
            id='0ab39d82-5862-4332-af7a-329200ae1d14',
            name='Constant RGBA',
            required_inputs=0,
            min_inputs=0,
            max_inputs=0,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].computed_value = output_plugs[0].value if output_plugs[0].value else (0, 0, 0, 0)

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='value',
                display_name='Color',
                value_type=Plug.VALUE_TYPE_VECTOR4,
                editable=True
            )
            plug.value = (0, 0, 0, 1)
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].value = (0.1, 0.2, 0.3, 0.4)

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        for output in output_plugs:
            if not output.computed_value == (0.1, 0.2, 0.3, 0.4):
                raise Exception('Test failed.')


class BooleanSwitch(Operator):

    """
    Outputs the value of input 2 if input 1 is TRUE. Otherwise input 3 will be output.
    Input 1 must be a boolean.
    Input 2 and 3 can be of any value type.
    """

    def __init__(self):
        super(BooleanSwitch, self).__init__(
            id='a628ab13-f19f-45b3-81cf-6824dd6e7b5d',
            name='Boolean Switch',
            required_inputs=3,
            min_inputs=3,
            max_inputs=3,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        debug = False
        value = None

        if debug:
            print('BooleanSwitch')
            print('\tinput_plugs[0].input:', input_plugs[0].input)
        if input_plugs[0].input is not None:
            if debug:
                print('\tinput_plugs[0].input.computed_value:', input_plugs[0].input.computed_value)
                print('\tinput_plugs[1].input:', input_plugs[1].input)
                if input_plugs[1].input is not None:
                    print('\tinput_plugs[1].input.computed_value:', input_plugs[1].input.computed_value)
                print('\tinput_plugs[2].input:', input_plugs[2].input)
                if input_plugs[2].input is not None:
                    print('\tinput_plugs[2].input.computed_value:', input_plugs[2].input.computed_value)
            if input_plugs[0].input.computed_value:
                value = input_plugs[1].input.computed_value if input_plugs[1].input is not None else False
            else:
                value = input_plugs[2].input.computed_value if input_plugs[2].input is not None else False
        elif debug:
            print('\tskipping evaluating inputs')
        if debug:
            print('\tvalue:', value)
            print('\toutput_plugs[0].computed_value is value', output_plugs[0].computed_value is value)
        output_plugs[0].computed_value = value if value is not None else False

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(parent=parent, name='input_boolean', display_name='Boolean', value_type=Plug.VALUE_TYPE_BOOLEAN)
            plug.value = False
            return plug
        if index == 1:
            return Plug.Create(parent=parent, name='on_true', display_name='True Output', value_type=Plug.VALUE_TYPE_ANY)
        if index == 2:
            return Plug.Create(parent=parent, name='on_false', display_name='False Output', value_type=Plug.VALUE_TYPE_ANY)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(parent=parent, name='output', display_name='Output', value_type=Plug.VALUE_TYPE_ANY)
            plug.value = False
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantBoolean())
        fake.outputs[0].value = True
        input_plugs[0].input = fake.outputs[0]

        fake = OperatorInstance.FromOperator(operator=ConstantString())
        fake.outputs[0].value = 'Input 1 value'
        input_plugs[1].input = fake.outputs[0]

        fake = OperatorInstance.FromOperator(operator=ConstantString())
        fake.outputs[0].value = 'Input 2 value'
        input_plugs[2].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        for output in output_plugs:
            if not output.computed_value == 'Input 1 value':
                raise Exception('Test failed.')


class SplitRGB(Operator):

    def __init__(self):
        super(SplitRGB, self).__init__(
            id='1cbcf8c6-328c-49b6-b4fc-d16fd78d4868',
            name='Split RGB',
            required_inputs=1,
            min_inputs=1,
            max_inputs=1,
            num_outputs=3
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if input_plugs[0].input is None:
            output_plugs[0].computed_value = 0
            output_plugs[1].computed_value = 0
            output_plugs[2].computed_value = 0
        else:
            value = input_plugs[0].input.computed_value

            try:
                test = iter(value)
                is_iterable = True
            except TypeError:
                is_iterable = False

            if is_iterable and len(value) == 3:
                output_plugs[0].computed_value = value[0]
                output_plugs[1].computed_value = value[1]
                output_plugs[2].computed_value = value[2]
            else:
                output_plugs[0].computed_value = output_plugs[0].default_value
                output_plugs[1].computed_value = output_plugs[1].default_value
                output_plugs[2].computed_value = output_plugs[2].default_value

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='input_rgb', display_name='RGB', value_type=Plug.VALUE_TYPE_VECTOR3)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='red',
                display_name='Red',
                value_type=Plug.VALUE_TYPE_FLOAT,
                editable=False
            )
            plug.value = 0
            return plug
        if index == 1:
            plug = Plug.Create(
                parent=parent,
                name='green',
                display_name='Green',
                value_type=Plug.VALUE_TYPE_FLOAT,
                editable=False
            )
            plug.value = 0
            return plug
        if index == 2:
            plug = Plug.Create(
                parent=parent,
                name='blue',
                display_name='Blue',
                value_type=Plug.VALUE_TYPE_FLOAT,
                editable=False
            )
            plug.value = 0
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantRGB())
        fake.outputs[0].value = (0.1, 0.2, 0.3)
        input_plugs[0].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value == 0.1:
            raise Exception('Test failed.')
        if not output_plugs[1].computed_value == 0.2:
            raise Exception('Test failed.')
        if not output_plugs[2].computed_value == 0.3:
            raise Exception('Test failed.')


class MergeRGB(Operator):

    def __init__(self):
        super(MergeRGB, self).__init__(
            id='1cbcf8c6-328d-49b6-b4fc-d16fd78d4868',
            name='Merge RGB',
            required_inputs=3,
            min_inputs=3,
            max_inputs=3,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        rgb = [0.0, 0.0, 0.0]

        for i in range(3):
            if input_plugs[i].input is not None:
                assumed_value_type = input_plugs[i].input.value_type
                if util.to_plug_value_type(value=input_plugs[i].input.computed_value, assumed_value_type=assumed_value_type) == Plug.VALUE_TYPE_FLOAT:
                    rgb[i] = input_plugs[i].input.computed_value

        output_plugs[0].computed_value = tuple(rgb)

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='input_r', display_name='R', value_type=Plug.VALUE_TYPE_FLOAT)
        if index == 1:
            return Plug.Create(parent=parent, name='input_g', display_name='G', value_type=Plug.VALUE_TYPE_FLOAT)
        if index == 2:
            return Plug.Create(parent=parent, name='input_B', display_name='B', value_type=Plug.VALUE_TYPE_FLOAT)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='rgb',
                display_name='RGB',
                value_type=Plug.VALUE_TYPE_VECTOR3,
                editable=False
            )
            plug.value = (0, 0, 0)
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantFloat())
        fake.outputs[0].value = 0.1
        input_plugs[0].input = fake.outputs[0]

        fake = OperatorInstance.FromOperator(operator=ConstantFloat())
        fake.outputs[0].value = 0.2
        input_plugs[1].input = fake.outputs[0]

        fake = OperatorInstance.FromOperator(operator=ConstantFloat())
        fake.outputs[0].value = 0.3
        input_plugs[2].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value == (0.1, 0.2, 0.3):
            raise Exception('Test failed.')


class SplitRGBA(Operator):

    def __init__(self):
        super(SplitRGBA, self).__init__(
            id='2c48e13c-2b58-48b9-a3b6-5f977c402b2e',
            name='Split RGBA',
            required_inputs=1,
            min_inputs=1,
            max_inputs=1,
            num_outputs=4
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if input_plugs[0].input is None:
            output_plugs[0].computed_value = 0
            output_plugs[1].computed_value = 0
            output_plugs[2].computed_value = 0
            output_plugs[3].computed_value = 0
            return

        value = input_plugs[0].input.computed_value

        try:
            test = iter(value)
            is_iterable = True
        except TypeError:
            is_iterable = False

        if is_iterable and len(value) == 4:
            output_plugs[0].computed_value = value[0]
            output_plugs[1].computed_value = value[1]
            output_plugs[2].computed_value = value[2]
            output_plugs[3].computed_value = value[3]
        else:
            output_plugs[0].computed_value = output_plugs[0].default_value
            output_plugs[1].computed_value = output_plugs[1].default_value
            output_plugs[2].computed_value = output_plugs[2].default_value
            output_plugs[3].computed_value = output_plugs[3].default_value

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='input_rgba', display_name='RGBA', value_type=Plug.VALUE_TYPE_VECTOR4)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='red',
                display_name='Red',
                value_type=Plug.VALUE_TYPE_FLOAT,
                editable=False
            )
            plug.value = 0
            return plug
        if index == 1:
            plug = Plug.Create(
                parent=parent,
                name='green',
                display_name='Green',
                value_type=Plug.VALUE_TYPE_FLOAT,
                editable=False
            )
            plug.value = 0
            return plug
        if index == 2:
            plug = Plug.Create(
                parent=parent,
                name='blue',
                display_name='Blue',
                value_type=Plug.VALUE_TYPE_FLOAT,
                editable=False
            )
            plug.value = 0
            return plug
        if index == 3:
            plug = Plug.Create(
                parent=parent,
                name='alpha',
                display_name='Alpha',
                value_type=Plug.VALUE_TYPE_FLOAT,
                editable=False
            )
            plug.value = 0
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantRGB())
        fake.outputs[0].value = (0.1, 0.2, 0.3, 0.4)
        input_plugs[0].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value == 0.1:
            raise Exception('Test failed.')
        if not output_plugs[1].computed_value == 0.2:
            raise Exception('Test failed.')
        if not output_plugs[2].computed_value == 0.3:
            raise Exception('Test failed.')
        if not output_plugs[3].computed_value == 0.4:
            raise Exception('Test failed.')


class MergeRGBA(Operator):

    def __init__(self):
        super(MergeRGBA, self).__init__(
            id='92e57f3d-8514-4786-a4ed-2767139a15eb',
            name='Merge RGBA',
            required_inputs=4,
            min_inputs=4,
            max_inputs=4,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        rgba = [0.0, 0.0, 0.0, 0.0]

        for i in range(4):
            if input_plugs[i].input is not None:
                assumed_value_type = input_plugs[i].input.value_type
                if util.to_plug_value_type(value=input_plugs[i].input.computed_value, assumed_value_type=assumed_value_type) == Plug.VALUE_TYPE_FLOAT:
                    rgba[i] = input_plugs[i].input.computed_value

        output_plugs[0].computed_value = tuple(rgba)

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='input_r', display_name='R', value_type=Plug.VALUE_TYPE_FLOAT)
        if index == 1:
            return Plug.Create(parent=parent, name='input_g', display_name='G', value_type=Plug.VALUE_TYPE_FLOAT)
        if index == 2:
            return Plug.Create(parent=parent, name='input_b', display_name='B', value_type=Plug.VALUE_TYPE_FLOAT)
        if index == 3:
            return Plug.Create(parent=parent, name='input_a', display_name='A', value_type=Plug.VALUE_TYPE_FLOAT)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='rgba',
                display_name='RGBA',
                value_type=Plug.VALUE_TYPE_VECTOR3,
                editable=False
            )
            plug.value = (0, 0, 0, 0)
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantFloat())
        fake.outputs[0].value = 0.1
        input_plugs[0].input = fake.outputs[0]

        fake = OperatorInstance.FromOperator(operator=ConstantFloat())
        fake.outputs[0].value = 0.2
        input_plugs[1].input = fake.outputs[0]

        fake = OperatorInstance.FromOperator(operator=ConstantFloat())
        fake.outputs[0].value = 0.3
        input_plugs[2].input = fake.outputs[0]

        fake = OperatorInstance.FromOperator(operator=ConstantFloat())
        fake.outputs[0].value = 0.4
        input_plugs[3].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value == (0.1, 0.2, 0.3, 0.4):
            raise Exception('Test failed.')


class LessThan(Operator):

    def __init__(self):
        super(LessThan, self).__init__(
            id='996df9bd-08d5-451b-a67c-80d0de7fba32',
            name='Less Than',
            required_inputs=2,
            min_inputs=2,
            max_inputs=2,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if input_plugs[0].input is None or input_plugs[1].input is None:
            for output in output_plugs:
                output.computed_value = False
            return

        value = input_plugs[0].input.computed_value
        compare = input_plugs[1].input.computed_value

        result = False
        try:
            result = value < compare
        except Exception as error:
            print('WARNING: Universal Material Map: '
                  'unable to compare if "{0}" is less than "{1}". '
                  'Setting output to "{2}".'.format(
                value,
                compare,
                result
            ))

        output_plugs[0].computed_value = result

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='value', display_name='Value', value_type=Plug.VALUE_TYPE_FLOAT)
        if index == 1:
            return Plug.Create(parent=parent, name='comparison', display_name='Comparison', value_type=Plug.VALUE_TYPE_FLOAT)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='output', display_name='Is Less Than', value_type=Plug.VALUE_TYPE_BOOLEAN)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantFloat())
        fake.outputs[0].value = 0.1
        input_plugs[0].input = fake.outputs[0]

        fake = OperatorInstance.FromOperator(operator=ConstantFloat())
        fake.outputs[0].value = 0.2
        input_plugs[1].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value:
            raise Exception('Test failed.')


class GreaterThan(Operator):

    def __init__(self):
        super(GreaterThan, self).__init__(
            id='1e751c3a-f6cd-43a2-aa72-22cb9d82ad19',
            name='Greater Than',
            required_inputs=2,
            min_inputs=2,
            max_inputs=2,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if input_plugs[0].input is None or input_plugs[1].input is None:
            output_plugs[0].computed_value = False
            return

        value = input_plugs[0].input.computed_value
        compare = input_plugs[1].input.computed_value

        result = False
        try:
            result = value > compare
        except Exception as error:
            print('WARNING: Universal Material Map: '
                  'unable to compare if "{0}" is greater than "{1}". '
                  'Setting output to "{2}".'.format(
                value,
                compare,
                result
            ))

        output_plugs[0].computed_value = result

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='value', display_name='Value', value_type=Plug.VALUE_TYPE_FLOAT)
        if index == 1:
            return Plug.Create(parent=parent, name='comparison', display_name='Comparison', value_type=Plug.VALUE_TYPE_FLOAT)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='output', display_name='Is Greater Than', value_type=Plug.VALUE_TYPE_BOOLEAN)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantFloat())
        fake.outputs[0].value = 0.1
        input_plugs[0].input = fake.outputs[0]

        fake = OperatorInstance.FromOperator(operator=ConstantFloat())
        fake.outputs[0].value = 0.2
        input_plugs[1].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if output_plugs[0].computed_value:
            raise Exception('Test failed.')


class Or(Operator):

    def __init__(self):
        super(Or, self).__init__(
            id='d0288faf-cb2e-4765-8923-1a368b45f62c',
            name='Or',
            required_inputs=2,
            min_inputs=2,
            max_inputs=2,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if input_plugs[0].input is None and input_plugs[1].input is None:
            output_plugs[0].computed_value = False
            return

        value_1 = input_plugs[0].input.computed_value if input_plugs[0].input else False
        value_2 = input_plugs[1].input.computed_value if input_plugs[1].input else False

        if value_1 is None and value_2 is None:
            output_plugs[0].computed_value = False
            return
        if value_1 is None:
            output_plugs[0].computed_value = True if value_2 else False
            return
        if value_2 is None:
            output_plugs[0].computed_value = True if value_1 else False
            return
        output_plugs[0].computed_value = value_1 or value_2

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='value_1', display_name='Value 1', value_type=Plug.VALUE_TYPE_ANY)
        if index == 1:
            return Plug.Create(parent=parent, name='value_2', display_name='Value 2', value_type=Plug.VALUE_TYPE_ANY)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='output', display_name='Is True', value_type=Plug.VALUE_TYPE_BOOLEAN)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantBoolean())
        fake.outputs[0].value = True
        input_plugs[0].input = fake.outputs[0]

        fake = OperatorInstance.FromOperator(operator=ConstantBoolean())
        fake.outputs[0].value = False
        input_plugs[1].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value:
            raise Exception('Test failed.')


class And(Operator):

    def __init__(self):
        super(And, self).__init__(
            id='9c5e4fb9-9948-4075-a7d6-ae9bc04e25b5',
            name='And',
            required_inputs=2,
            min_inputs=2,
            max_inputs=2,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if input_plugs[0].input is None and input_plugs[1].input is None:
            output_plugs[0].computed_value = False
            return

        value_1 = input_plugs[0].input.computed_value if input_plugs[0].input else False
        value_2 = input_plugs[1].input.computed_value if input_plugs[1].input else False

        if value_1 is None and value_2 is None:
            output_plugs[0].computed_value = False
            return
        if value_1 is None:
            output_plugs[0].computed_value = True if value_2 else False
            return
        if value_2 is None:
            output_plugs[0].computed_value = True if value_1 else False
            return
        output_plugs[0].computed_value = value_1 and value_2

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='value_1', display_name='Value 1', value_type=Plug.VALUE_TYPE_ANY)
        if index == 1:
            return Plug.Create(parent=parent, name='value_2', display_name='Value 2', value_type=Plug.VALUE_TYPE_ANY)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='output', display_name='Is True', value_type=Plug.VALUE_TYPE_BOOLEAN)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantBoolean())
        fake.outputs[0].value = True
        input_plugs[0].input = fake.outputs[0]

        fake = OperatorInstance.FromOperator(operator=ConstantBoolean())
        fake.outputs[0].value = True
        input_plugs[1].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value:
            raise Exception('Test failed.')


class Equal(Operator):

    def __init__(self):
        super(Equal, self).__init__(
            id='fb353972-aebd-4d32-8231-f644f75d322c',
            name='Equal',
            required_inputs=2,
            min_inputs=2,
            max_inputs=2,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if input_plugs[0].input is None and input_plugs[1].input is None:
            output_plugs[0].computed_value = True
            return

        if input_plugs[0].input is None or input_plugs[1].input is None:
            output_plugs[0].computed_value = False
            return

        value_1 = input_plugs[0].input.computed_value
        value_2 = input_plugs[1].input.computed_value

        if value_1 is None and value_2 is None:
            output_plugs[0].computed_value = True
            return
        if value_1 is None or value_2 is None:
            output_plugs[0].computed_value = False
            return

        result = False
        try:
            result = value_1 == value_2
        except Exception as error:
            print('WARNING: Universal Material Map: '
                  'unable to compare if "{0}" is equal to "{1}". '
                  'Setting output to "{2}".'.format(
                value_1,
                value_2,
                result
            ))

        output_plugs[0].computed_value = result

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='value_1', display_name='Value 1', value_type=Plug.VALUE_TYPE_ANY)
        if index == 1:
            return Plug.Create(parent=parent, name='value_1', display_name='Value 2', value_type=Plug.VALUE_TYPE_ANY)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='output', display_name='Are Equal', value_type=Plug.VALUE_TYPE_BOOLEAN)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantString())
        fake.outputs[0].value = self.id
        input_plugs[0].input = fake.outputs[0]

        fake = OperatorInstance.FromOperator(operator=ConstantString())
        fake.outputs[0].value = self.id
        input_plugs[1].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value:
            raise Exception('Test failed.')


class Not(Operator):

    def __init__(self):
        super(Not, self).__init__(
            id='7b8b67df-ce2e-445c-98b7-36ea695c77e3',
            name='Not',
            required_inputs=1,
            min_inputs=1,
            max_inputs=1,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if input_plugs[0].input is None:
            output_plugs[0].computed_value = False
            return

        value_1 = input_plugs[0].input.computed_value

        if value_1 is None:
            output_plugs[0].computed_value = False
            return
        output_plugs[0].computed_value = not value_1

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='value', display_name='Boolean', value_type=Plug.VALUE_TYPE_BOOLEAN)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='output', display_name='Boolean', value_type=Plug.VALUE_TYPE_BOOLEAN)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantBoolean())
        fake.outputs[0].value = False
        input_plugs[0].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value:
            raise Exception('Test failed.')


class ValueTest(Operator):

    def __init__(self):
        super(ValueTest, self).__init__(
            id='2899f66b-2e8d-467b-98d1-5f590cf98e7a',
            name='Value Test',
            required_inputs=1,
            min_inputs=1,
            max_inputs=1,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if input_plugs[0].input is None:
            output_plugs[0].computed_value = None
            return
        output_plugs[0].computed_value = input_plugs[0].input.computed_value

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='input', display_name='Input', value_type=Plug.VALUE_TYPE_ANY)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='output', display_name='Output', value_type=Plug.VALUE_TYPE_ANY)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantInteger())
        fake.outputs[0].value = 10
        input_plugs[0].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value == 10:
            raise Exception('Test failed.')


class ValueResolver(Operator):

    def __init__(self):
        super(ValueResolver, self).__init__(
            id='74306cd0-b668-4a92-9e15-7b23486bd89a',
            name='Value Resolver',
            required_inputs=8,
            min_inputs=8,
            max_inputs=8,
            num_outputs=7
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        assumed_value_type = input_plugs[0].input.value_type if input_plugs[0].input else input_plugs[0].value_type
        computed_value = input_plugs[0].input.computed_value if input_plugs[0].input else False
        value_type = util.to_plug_value_type(value=computed_value, assumed_value_type=assumed_value_type)

        if value_type == Plug.VALUE_TYPE_BOOLEAN:
            output_plugs[0].computed_value = computed_value
        else:
            output_plugs[0].computed_value = input_plugs[1].computed_value

        if value_type == Plug.VALUE_TYPE_VECTOR3:
            output_plugs[1].computed_value = computed_value
        else:
            output_plugs[1].computed_value = input_plugs[2].computed_value

        if value_type == Plug.VALUE_TYPE_FLOAT:
            output_plugs[2].computed_value = computed_value
        else:
            output_plugs[2].computed_value = input_plugs[3].computed_value

        if value_type == Plug.VALUE_TYPE_INTEGER:
            output_plugs[3].computed_value = computed_value
        else:
            output_plugs[3].computed_value = input_plugs[4].computed_value

        if value_type == Plug.VALUE_TYPE_STRING:
            output_plugs[4].computed_value = computed_value
        else:
            output_plugs[4].computed_value = input_plugs[5].computed_value

        if value_type == Plug.VALUE_TYPE_VECTOR4:
            output_plugs[5].computed_value = computed_value
        else:
            output_plugs[5].computed_value = input_plugs[6].computed_value

        if value_type == Plug.VALUE_TYPE_LIST:
            output_plugs[6].computed_value = computed_value
        else:
            output_plugs[6].computed_value = input_plugs[7].computed_value

        for index, input_plug in enumerate(input_plugs):
            if index == 0:
                continue
            input_plug.is_editable = not input_plug.input

        for output_plug in output_plugs:
            output_plug.is_editable = False

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='input', display_name='Input', value_type=Plug.VALUE_TYPE_ANY)
        if index == 1:
            plug = Plug.Create(
                parent=parent,
                name='boolean',
                display_name='Boolean',
                value_type=Plug.VALUE_TYPE_BOOLEAN,
                editable=True,
            )
            plug.value = False
            return plug
        if index == 2:
            plug = Plug.Create(
                parent=parent,
                name='color',
                display_name='Color',
                value_type=Plug.VALUE_TYPE_VECTOR3,
                editable=True,
            )
            plug.value = (0, 0, 0)
            return plug
        if index == 3:
            plug = Plug.Create(
                parent=parent,
                name='float',
                display_name='Float',
                value_type=Plug.VALUE_TYPE_FLOAT,
                editable=True,
            )
            plug.value = 0
            return plug
        if index == 4:
            plug = Plug.Create(
                parent=parent,
                name='integer',
                display_name='Integer',
                value_type=Plug.VALUE_TYPE_INTEGER,
                editable=True,
            )
            plug.value = 0
            return plug
        if index == 5:
            plug = Plug.Create(
                parent=parent,
                name='string',
                display_name='String',
                value_type=Plug.VALUE_TYPE_STRING,
                editable=True,
            )
            plug.value = ''
            return plug
        if index == 6:
            plug = Plug.Create(
                parent=parent,
                name='rgba',
                display_name='RGBA',
                value_type=Plug.VALUE_TYPE_VECTOR4,
                editable=True,
            )
            plug.value = (0, 0, 0, 1)
            return plug
        if index == 7:
            plug = Plug.Create(
                parent=parent,
                name='list',
                display_name='List',
                value_type=Plug.VALUE_TYPE_LIST,
                editable=False,
            )
            plug.value = []
            return plug
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='boolean',
                display_name='Boolean',
                value_type=Plug.VALUE_TYPE_BOOLEAN,
                editable=False,
            )
            plug.value = False
            return plug
        if index == 1:
            plug = Plug.Create(
                parent=parent,
                name='color',
                display_name='Color',
                value_type=Plug.VALUE_TYPE_VECTOR3,
                editable=False,
            )
            plug.value = (0, 0, 0)
            return plug
        if index == 2:
            plug = Plug.Create(
                parent=parent,
                name='float',
                display_name='Float',
                value_type=Plug.VALUE_TYPE_FLOAT,
                editable=False,
            )
            plug.value = 0
            return plug
        if index == 3:
            plug = Plug.Create(
                parent=parent,
                name='integer',
                display_name='Integer',
                value_type=Plug.VALUE_TYPE_INTEGER,
                editable=False,
            )
            plug.value = 0
            return plug
        if index == 4:
            plug = Plug.Create(
                parent=parent,
                name='string',
                display_name='String',
                value_type=Plug.VALUE_TYPE_STRING,
                editable=False,
            )
            plug.value = ''
            return plug
        if index == 5:
            plug = Plug.Create(
                parent=parent,
                name='rgba',
                display_name='RGBA',
                value_type=Plug.VALUE_TYPE_VECTOR4,
                editable=False,
            )
            plug.value = (0, 0, 0, 1)
            return plug
        if index == 6:
            plug = Plug.Create(
                parent=parent,
                name='list',
                display_name='List',
                value_type=Plug.VALUE_TYPE_LIST,
                editable=False,
            )
            plug.value = []
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantInteger())
        fake.outputs[0].value = 10
        input_plugs[0].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[3].computed_value == 10:
            raise Exception('Test failed.')


class MayaTransparencyResolver(Operator):

    """
    Specialty operator based on Maya transparency attribute.
    If the input is of type string - and is not an empty string - then the output will be TRUE.
    If the input is a tripple float - and any value is greater than zero - then the output will also be TRUE.
    In all other cases the output will be FALSE.
    """

    def __init__(self):
        super(MayaTransparencyResolver, self).__init__(
            id='2b523832-ac84-4051-9064-6046121dcd48',
            name='Maya Transparency Resolver',
            required_inputs=1,
            min_inputs=1,
            max_inputs=1,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        is_transparent = False
        assumed_value_type = input_plugs[0].input.value_type if input_plugs[0].input else input_plugs[0].value_type
        computed_value = input_plugs[0].input.computed_value if input_plugs[0].input else False
        value_type = util.to_plug_value_type(value=computed_value, assumed_value_type=assumed_value_type)

        if value_type == Plug.VALUE_TYPE_STRING:
            is_transparent = not computed_value == ''
        elif value_type == Plug.VALUE_TYPE_VECTOR3:
            for value in computed_value:
                if value > 0:
                    is_transparent = True
                    break
        elif value_type == Plug.VALUE_TYPE_FLOAT:
            is_transparent = computed_value > 0

        output_plugs[0].computed_value = is_transparent

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='input', display_name='Input', value_type=Plug.VALUE_TYPE_ANY)
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='is_transparent',
                display_name='Is Transparent',
                value_type=Plug.VALUE_TYPE_BOOLEAN,
            )
            plug.value = False
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        fake = OperatorInstance.FromOperator(operator=ConstantRGB())
        fake.outputs[0].value = (0.5, 0.5, 0.5)
        input_plugs[0].input = fake.outputs[0]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value:
            raise Exception('Test failed.')


class ListGenerator(Operator):

    def __init__(self):
        super(ListGenerator, self).__init__(
            id='a410f7a0-280a-451f-a26c-faf9a8e302b4',
            name='List Generator',
            required_inputs=0,
            min_inputs=0,
            max_inputs=-1,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output = []
        for input_plug in input_plugs:
            output.append(input_plug.computed_value)
        output_plugs[0].computed_value = output

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        return Plug.Create(
            parent=parent,
            name='[{0}]'.format(index),
            display_name='[{0}]'.format(index),
            value_type=Plug.VALUE_TYPE_ANY,
            editable=False,
            is_removable=True,
        )

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='list', display_name='list', value_type=Plug.VALUE_TYPE_LIST)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def remove_plug(self, operator_instance: 'OperatorInstance', plug: 'Plug') -> None:
        super(ListGenerator, self).remove_plug(operator_instance=operator_instance, plug=plug)
        for index, plug in enumerate(operator_instance.inputs):
            plug.name = '[{0}]'.format(index)
            plug.display_name = '[{0}]'.format(index)
        for plug in operator_instance.outputs:
            plug.invalidate()

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        pass

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        pass


class ListIndex(Operator):

    def __init__(self):
        super(ListIndex, self).__init__(
            id='e4a81506-fb6b-4729-8273-f68e97f5bc6b',
            name='List Index',
            required_inputs=2,
            min_inputs=2,
            max_inputs=2,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        try:
            test = iter(input_plugs[0].computed_value)
            index = input_plugs[1].computed_value
            if 0 <= index < len(input_plugs[0].computed_value):
                output_plugs[0].computed_value = input_plugs[0].computed_value[index]
            else:
                output_plugs[0].computed_value = None
        except TypeError:
            output_plugs[0].computed_value = None

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='list', display_name='List', value_type=Plug.VALUE_TYPE_LIST)
        if index == 1:
            plug = Plug.Create(
                parent=parent,
                name='index',
                display_name='Index',
                value_type=Plug.VALUE_TYPE_INTEGER,
                editable=True
            )
            plug.computed_value = 0
            return plug
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='output', display_name='Output', value_type=Plug.VALUE_TYPE_ANY)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        input_plugs[0].value = ['hello', 'world']
        input_plugs[1].value = 1

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value == 'world':
            raise Exception('Test failed.')


class MDLColorSpace(Operator):

    def __init__(self):
        super(MDLColorSpace, self).__init__(
            id='cf0b97c8-fb55-4cf3-8afc-23ebd4a0a6c7',
            name='MDL Color Space',
            required_inputs=0,
            min_inputs=0,
            max_inputs=0,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].computed_value = output_plugs[0].value if output_plugs[0].value else 'auto'

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='color_space',
                display_name='Color Space',
                value_type=Plug.VALUE_TYPE_ENUM,
                editable=True
            )
            plug.enum_values = ['auto', 'raw', 'sRGB']
            plug.default_value = 'auto'
            plug.value = 'auto'
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output_plugs[0].value = output_plugs[0].enum_values[2]

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value == output_plugs[0].enum_values[2]:
            raise Exception('Test failed.')


class MDLTextureResolver(Operator):

    def __init__(self):
        super(MDLTextureResolver, self).__init__(
            id='af766adb-cf54-4a8b-a598-44b04fbcf630',
            name='MDL Texture Resolver',
            required_inputs=2,
            min_inputs=2,
            max_inputs=2,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        filepath = input_plugs[0].input.computed_value if input_plugs[0].input else ''
        value_type = util.to_plug_value_type(value=filepath, assumed_value_type=Plug.VALUE_TYPE_STRING)
        filepath = filepath if value_type == Plug.VALUE_TYPE_STRING else ''

        colorspace = input_plugs[1].computed_value

        output_plugs[0].computed_value = [filepath, colorspace]

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='input', display_name='Input', value_type=Plug.VALUE_TYPE_STRING)
        if index == 1:
            plug = Plug.Create(
                parent=parent,
                name='color_space',
                display_name='Color Space',
                value_type=Plug.VALUE_TYPE_ENUM,
                editable=True
            )
            plug.enum_values = ['auto', 'raw', 'sRGB']
            plug.default_value = 'auto'
            plug.value = 'auto'
            return plug
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='list',
                display_name='List',
                value_type=Plug.VALUE_TYPE_LIST,
                editable=False,
            )
            plug.default_value = ['', 'auto']
            plug.value = ['', 'auto']
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        input_plugs[0].value = 'c:/folder/color.png'
        input_plugs[1].value = 'raw'

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[3].computed_value == ['c:/folder/color.png', 'raw']:
            raise Exception('Test failed.')


class SplitTextureData(Operator):

    def __init__(self):
        super(SplitTextureData, self).__init__(
            id='6a411798-434c-4ad4-b464-0bd2e78cdcec',
            name='Split Texture Data',
            required_inputs=1,
            min_inputs=1,
            max_inputs=1,
            num_outputs=2
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        is_valid_input = False
        try:
            value = input_plugs[0].computed_value
            test = iter(value)
            if len(value) == 2:
                if sys.version_info.major < 3:
                    if isinstance(value[0], basestring) and isinstance(value[1], basestring):
                        is_valid_input = True
                else:
                    if isinstance(value[0], str) and isinstance(value[1], str):
                        is_valid_input = True
        except TypeError:
            pass

        if is_valid_input:
            output_plugs[0].computed_value = value[0]
            output_plugs[1].computed_value = value[1]
        else:
            output_plugs[0].computed_value = ''
            output_plugs[1].computed_value = 'auto'

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(parent=parent, name='list', display_name='List', value_type=Plug.VALUE_TYPE_LIST)
            plug.default_value = ['', 'auto']
            plug.computed_value = ['', 'auto']
            return plug
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(parent=parent, name='texture_path', display_name='Texture Path', value_type=Plug.VALUE_TYPE_STRING)
            plug.default_value = ''
            plug.computed_value = ''
            return plug
        if index == 1:
            plug = Plug.Create(parent=parent, name='color_space', display_name='Color Space', value_type=Plug.VALUE_TYPE_STRING)
            plug.default_value = 'auto'
            plug.computed_value = 'auto'
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        input_plugs[0].computed_value = ['hello.png', 'world']

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value == 'hello.png':
            raise Exception('Test failed.')
        if not output_plugs[1].computed_value == 'world':
            raise Exception('Test failed.')


class Multiply(Operator):

    def __init__(self):
        super(Multiply, self).__init__(
            id='0f5c9828-f582-48aa-b055-c12b91e692a7',
            name='Multiply',
            required_inputs=0,
            min_inputs=2,
            max_inputs=-1,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        values = []
        for input_plug in input_plugs:
            if isinstance(input_plug.computed_value, int):
                values.append(input_plug.computed_value)
                continue
            if isinstance(input_plug.computed_value, float):
                values.append(input_plug.computed_value)

        if len(values) < 2:
            output_plugs[0].computed_value = 0
        else:
            product = 1.0
            for o in values:
                product *= o
            output_plugs[0].computed_value = product

        for input_plug in input_plugs:
            input_plug.is_editable = not input_plug.input

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        plug = Plug.Create(
            parent=parent,
            name='[{0}]'.format(index),
            display_name='[{0}]'.format(index),
            value_type=Plug.VALUE_TYPE_FLOAT,
            editable=True,
            is_removable=index > 1,
        )
        plug.default_value = 1.0
        plug.value = 1.0
        plug.computed_value = 1.0
        return plug

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='product', display_name='product', value_type=Plug.VALUE_TYPE_FLOAT)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def remove_plug(self, operator_instance: 'OperatorInstance', plug: 'Plug') -> None:
        super(Multiply, self).remove_plug(operator_instance=operator_instance, plug=plug)
        for index, plug in enumerate(operator_instance.inputs):
            plug.name = '[{0}]'.format(index)
            plug.display_name = '[{0}]'.format(index)
        for plug in operator_instance.outputs:
            plug.invalidate()

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        input_plugs[0].computed_value = 2
        input_plugs[1].computed_value = 2

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value == 4:
            raise Exception('Test failed.')


class ColorSpaceResolver(Operator):

    MAPPING = {
        'MDL|auto|Blender': 'sRGB',
        'MDL|srgb|Blender': 'sRGB',
        'MDL|raw|Blender': 'Raw',
        'Blender|filmic log|MDL': 'raw',
        'Blender|linear|MDL': 'raw',
        'Blender|linear aces|MDL': 'raw',
        'Blender|non-color|MDL': 'raw',
        'Blender|raw|MDL': 'raw',
        'Blender|srgb|MDL': 'sRGB',
        'Blender|xyz|MDL': 'raw',
    }

    DEFAULT = {
        'Blender': 'Linear',
        'MDL': 'auto',
    }

    def __init__(self):
        super(ColorSpaceResolver, self).__init__(
            id='c159df8f-a0a2-4300-b897-e8eaa689a901',
            name='Color Space Resolver',
            required_inputs=3,
            min_inputs=3,
            max_inputs=3,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        color_space = input_plugs[0].computed_value.lower()
        from_color_space = input_plugs[1].computed_value
        to_color_space = input_plugs[2].computed_value
        key = '{0}|{1}|{2}'.format(
            from_color_space,
            color_space,
            to_color_space
        )
        if key in ColorSpaceResolver.MAPPING:
            output_plugs[0].computed_value = ColorSpaceResolver.MAPPING[key]
        else:
            output_plugs[0].computed_value = ColorSpaceResolver.DEFAULT[to_color_space]

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='color_space',
                display_name='Color Space',
                value_type=Plug.VALUE_TYPE_STRING,
                editable=False,
                is_removable=False,
            )
            plug.default_value = ''
            plug.computed_value = ''
            return plug

        if index == 1:
            plug = Plug.Create(
                parent=parent,
                name='from_color_space',
                display_name='From',
                value_type=Plug.VALUE_TYPE_ENUM,
                editable=True
            )
            plug.enum_values = ['MDL', 'Blender']
            plug.default_value = 'MDL'
            plug.computed_value = 'MDL'
            return plug

        if index == 2:
            plug = Plug.Create(
                parent=parent,
                name='to_color_space',
                display_name='To',
                value_type=Plug.VALUE_TYPE_ENUM,
                editable=True
            )
            plug.enum_values = ['Blender', 'MDL']
            plug.default_value = 'Blender'
            plug.computed_value = 'Blender'
            return plug

        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(
                parent=parent,
                name='color_space',
                display_name='Color Space',
                value_type=Plug.VALUE_TYPE_STRING,
                editable=False
            )
            plug.default_value = ''
            plug.computed_value = ''
            return plug
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        raise NotImplementedError()

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value == output_plugs[0].enum_values[2]:
            raise Exception('Test failed.')


class Add(Operator):

    def __init__(self):
        super(Add, self).__init__(
            id='f2818669-5454-4599-8792-2cb09f055bf9',
            name='Add',
            required_inputs=0,
            min_inputs=2,
            max_inputs=-1,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output = 0
        for input_plug in input_plugs:
            try:
                output += input_plug.computed_value
            except:
                pass
        output_plugs[0].computed_value = output

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        plug = Plug.Create(
            parent=parent,
            name='[{0}]'.format(index),
            display_name='[{0}]'.format(index),
            value_type=Plug.VALUE_TYPE_FLOAT,
            editable=True,
            is_removable=True,
        )
        plug.default_value = 0.0
        plug.computed_value = 0.0
        return plug

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='sum', display_name='sum', value_type=Plug.VALUE_TYPE_FLOAT)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def remove_plug(self, operator_instance: 'OperatorInstance', plug: 'Plug') -> None:
        super(Add, self).remove_plug(operator_instance=operator_instance, plug=plug)
        for index, plug in enumerate(operator_instance.inputs):
            plug.name = '[{0}]'.format(index)
            plug.display_name = '[{0}]'.format(index)
        for plug in operator_instance.outputs:
            plug.invalidate()

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        pass

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        pass


class Subtract(Operator):

    def __init__(self):
        super(Subtract, self).__init__(
            id='15f523f3-4e94-43a5-8306-92d07cbfa48c',
            name='Subtract',
            required_inputs=0,
            min_inputs=2,
            max_inputs=-1,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        output = None
        for input_plug in input_plugs:
            try:
                if output is None:
                    output = input_plug.computed_value
                else:
                    output -= input_plug.computed_value
            except:
                pass
        output_plugs[0].computed_value = output

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        plug = Plug.Create(
            parent=parent,
            name='[{0}]'.format(index),
            display_name='[{0}]'.format(index),
            value_type=Plug.VALUE_TYPE_FLOAT,
            editable=True,
            is_removable=True,
        )
        plug.default_value = 0.0
        plug.computed_value = 0.0
        return plug

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='difference', display_name='difference', value_type=Plug.VALUE_TYPE_FLOAT)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def remove_plug(self, operator_instance: 'OperatorInstance', plug: 'Plug') -> None:
        super(Subtract, self).remove_plug(operator_instance=operator_instance, plug=plug)
        for index, plug in enumerate(operator_instance.inputs):
            plug.name = '[{0}]'.format(index)
            plug.display_name = '[{0}]'.format(index)
        for plug in operator_instance.outputs:
            plug.invalidate()

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        pass

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        pass


class Remap(Operator):

    def __init__(self):
        super(Remap, self).__init__(
            id='2405c02a-facc-47a6-80ef-d35d959b0cd4',
            name='Remap',
            required_inputs=5,
            min_inputs=5,
            max_inputs=5,
            num_outputs=1
        )

    def _compute_outputs(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        result = 0.0

        old_value = input_plugs[0].computed_value

        try:
            test = iter(old_value)
            is_iterable = True
        except TypeError:
            is_iterable = False

        if not is_iterable:
            try:
                old_min = input_plugs[1].computed_value
                old_max = input_plugs[2].computed_value
                new_min = input_plugs[3].computed_value
                new_max = input_plugs[4].computed_value
                result = ((old_value - old_min) / (old_max - old_min)) * (new_max - new_min) + new_min
            except:
                pass
        else:
            result = []
            for o in old_value:
                try:
                    old_min = input_plugs[1].computed_value
                    old_max = input_plugs[2].computed_value
                    new_min = input_plugs[3].computed_value
                    new_max = input_plugs[4].computed_value
                    result.append(((o - old_min) / (old_max - old_min)) * (new_max - new_min) + new_min)
                except:
                    pass

        output_plugs[0].computed_value = result

    def generate_input(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            plug = Plug.Create(parent=parent, name='value', display_name='Value', value_type=Plug.VALUE_TYPE_ANY)
            plug.default_value = 0
            plug.computed_value = 0
            return plug
        if index == 1:
            plug = Plug.Create(parent=parent, name='old_min', display_name='Old Min', value_type=Plug.VALUE_TYPE_FLOAT)
            plug.is_editable = True
            plug.default_value = 0
            plug.computed_value = 0
            return plug
        if index == 2:
            plug = Plug.Create(parent=parent, name='old_max', display_name='Old Max', value_type=Plug.VALUE_TYPE_FLOAT)
            plug.is_editable = True
            plug.default_value = 1
            plug.computed_value = 1
            return plug
        if index == 3:
            plug = Plug.Create(parent=parent, name='new_min', display_name='New Min', value_type=Plug.VALUE_TYPE_FLOAT)
            plug.is_editable = True
            plug.default_value = 0
            plug.computed_value = 0
            return plug
        if index == 4:
            plug = Plug.Create(parent=parent, name='new_max', display_name='New Max', value_type=Plug.VALUE_TYPE_FLOAT)
            plug.is_editable = True
            plug.default_value = 10
            plug.computed_value = 10
            return plug
        raise Exception('Input index "{0}" not supported.'.format(index))

    def generate_output(self, parent: DagNode, index: int) -> Plug:
        if index == 0:
            return Plug.Create(parent=parent, name='remapped_value', display_name='Remapped Value', value_type=Plug.VALUE_TYPE_FLOAT)
        raise Exception('Output index "{0}" not supported.'.format(index))

    def _prepare_plugs_for_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        input_plugs[0].computed_value = 0.5
        input_plugs[1].computed_value = 0
        input_plugs[2].computed_value = 1
        input_plugs[3].computed_value = 1
        input_plugs[4].computed_value = 0

    def _assert_test(self, input_plugs: typing.List[Plug], output_plugs: typing.List[Plug]):
        if not output_plugs[0].computed_value == 0.5:
            raise Exception('Test failed.')