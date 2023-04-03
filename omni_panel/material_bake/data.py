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

from .bake_operation import bakestolist

class MasterOperation:

    current_bake_operation = None
    total_bake_operations = 0
    this_bake_operation_num = 0

    orig_UVs_dict = {}
    baked_textures = []
    prepared_mesh_objects = []

    batch_name = ""

    orig_objects = []
    orig_active_object = ""
    orig_sample_count = 0

    @staticmethod
    def clear():

        # Master variables called throughout bake process
        MasterOperation.orig_UVs_dict = {}
        MasterOperation.total_bake_operations = 0
        MasterOperation.current_bake_operation = None
        MasterOperation.this_bake_operation_num = 0
        MasterOperation.prepared_mesh_objects = []
        MasterOperation.baked_textures = []
        MasterOperation.batch_name = ""

        # Variables to reset your scene to what it was before bake.
        MasterOperation.orig_objects = []
        MasterOperation.orig_active_object = ""
        MasterOperation.orig_sample_count = 0

        return True


class BakeOperation:

    #Constants
    PBR = "pbr"

    def __init__(self):

        #Mapping of object name to active UVs
        self.bake_mode = BakeOperation.PBR #So the example in the user prefs will work
        self.bake_objects = []
        self.active_object = None

        #normal
        self.uv_mode = "normal"

        #pbr stuff
        self.pbr_selected_bake_types = []

    def assemble_pbr_bake_list(self):
        self.pbr_selected_bake_types = bakestolist()