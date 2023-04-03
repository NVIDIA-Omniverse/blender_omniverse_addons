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


# Generic utility functions for Blender

import json
import sys
from timeit import default_timer as timer

import bpy

def do_print(msg):
    # Flush so prints immediately.
    print("\033[93m" + msg + "\033[0m", flush=True)

def do_print_error(msg):
    # Flush so prints immediately.
    print("\033[91m" + msg + "\033[0m", flush=True)

def start_time():
    return timer()

def report_time(start, msg):
    end = timer()
    do_print("Elapsed time for {}: {:.3f}".format(msg, end-start))
    
def print_python_version():
    do_print("Python version: %s.%s" % (sys.version_info.major, sys.version_info.minor))
    
def open_file(inputPath):
    start = timer()
    # Load scene. Clears any existing file before loading
    if inputPath.endswith(tuple([".usd", ".usda", ".usdc"])):
        do_print("Load file: " + inputPath)
        bpy.ops.wm.usd_import(filepath=inputPath)
    elif inputPath.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=inputPath)
    else:
        do_print_error("Unrecognized file, not loaded: " + inputPath)
        return False
    end = timer()
    do_print("Elapsed time to load file: " + "{:.3f}".format(end-start))
    return True

def save_file(outputPath):
    # Save scene. Only writes diffs, so faster than export.
    start = timer()
    do_print("Save file: " + outputPath)
    bpy.ops.wm.usd_export(filepath=outputPath)
    end = timer()
    do_print("Elapsed time to save file: " + "{:.3f}".format(end-start))
    return True

def clear_scene():
    # This seems to be difficult with Blender. Partially working code:
    bpy.ops.wm.read_factory_settings(use_empty=True)

def process_json_config(operation):
    return json.loads(operation) if operation else None

def getVertexCount(occurrences): # returns the vertex count of all current occurrences for threshold testing during recursion
    vertexCount = 0
    for obj in occurrences:
        vertexCount += len(obj.data.vertices)
    return vertexCount

def getFaceCount(occurrences): # returns the face count of all current occurrences for threshold testing during recursion
    faceCount = 0
    for obj in occurrences:
        faceCount += len(obj.data.polygons)
    return faceCount

def printPart(part):
    print("current part being operated on: ", part.name)

def printClearLine():
    LINE_UP = '\033[1A' # command to move up a line in the console
    LINE_CLEAR = '\x1b[2K' # command to clear current line in the console
    print(LINE_UP, end=LINE_CLEAR) # don't want endless print statements
