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

import bpy

class bgbake_ops():
    bgops_list = []
    bgops_list_last = []
    bgops_list_finished = []


def remove_dead():
    
    #Remove dead processes from current list
    for p in bgbake_ops.bgops_list:
        if p[0].poll() == 0:
            
            bgbake_ops.bgops_list_finished.append(p)
            bgbake_ops.bgops_list.remove(p)
    
    return 1 #1 second timer
    
bpy.app.timers.register(remove_dead, persistent=True)
