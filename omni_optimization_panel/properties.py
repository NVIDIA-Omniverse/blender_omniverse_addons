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


from typing import *
from bpy.props import *
import bpy

class optimizeProperties(bpy.types.PropertyGroup):
    # PROPERTIES
    
    operation: EnumProperty(
        name="Operation",
        items= [ ('modify', 'MODIFY', 'run modify'),
        ('fixMesh', 'FIX MESH', 'run fix Mesh'),
        ('uv', 'UV UNWRAP', "run uv"),
        ('chop', 'CHOP', 'run chop')],
        description= "Choose the operation to run on the scene",
        default = 'modify'
    )

    print_attributes: BoolProperty(
        name ="Print Attributes",
        description = "Print attributes used at the begging of operation",
        default = False
    )

class modProperties(bpy.types.PropertyGroup):
    # PROPERTIES

    selected_only: BoolProperty(
        name ="Use Selected Only",
        description = "Operate on selected objects only",
        default = False
    )

    apply_mod: BoolProperty(
        name ="Apply Modifier",
        description = "Apply modifier after adding",
        default = True
    )
    
    fix_bad_mesh: BoolProperty(
        name ="Fix Bad Mesh",
        description = "Remove zero area faces and zero length edges",
        default = False
    )

    dissolve_threshold: FloatProperty(
        name="Dissolve Threshold",
        description = "Threshold value used with Fix Bad Mesh",
        default=0.08,
        min=0,
        max=50
    )

    merge_vertex: BoolProperty(
        name ="Merge Vertex",
        description = "Merge vertices by distance",
        default = False
    )

    merge_threshold: FloatProperty(
        name="Merge Threshold",
        description = "Distance value used with merge vertex",
        default=0.01,
        min=0,
        max=50
    )

    remove_existing_sharp: BoolProperty(
        name ="Remove Existing Sharp",
        description = "Remove existing sharp edges from meshes. This helps sometimes after fixing bad meshes",
        default = True
    )

    fix_normals: BoolProperty(
        name ="Fix Normals",
        description = "Remove existing custom split normals",
        default = False
    )

    create_new_custom_normals: BoolProperty(
        name ="Create New Custom Normals",
        description = "Create new custom split normals",
        default = False
    )

    # Some common modifier names for reference:'DECIMATE''REMESH''NODES''SUBSURF''SOLIDIFY''ARRAY''BEVEL'
    modifier: EnumProperty(
        name="Modifier",
        items= [ ('DECIMATE', 'Decimate', 'decimate geometry'),
        ('REMESH', 'Remesh', 'remesh geometry'),
        ('NODES', 'Nodes', 'add geometry node mod'),
        ('FIX', 'Fix Mesh', "fix mesh")],
        description= "Choose the modifier to apply to geometry",
        default = 'DECIMATE'
    )

    # TODO: Implement this modifier stack properly. would allow for multiple modifiers to be queued and run at once
    # use_modifier_stack: BoolProperty(
    #     name ="Use Modifier Stack",
    #     description = "use stack of modifiers instead of a single modifier",
    #     default = False
    # )
    
    # modifier_stack: CollectionProperty(
    #     type= optimizeProperties,
    #     name="Modifiers",
    #     description= "list of modifiers to be used",
    #     default = [["DECIMATE", "COLLAPSE", 0.5]]
    # )

    decimate_type: EnumProperty(
        items= [ ('COLLAPSE','collapse',"collapse geometry"), 
        ('UNSUBDIV','unSubdivide',"un subdivide geometry"),
        ('DISSOLVE','planar',"dissolve geometry")],
        description = "Choose which type of decimation to perform.",
        default = "COLLAPSE"
    )

    ratio: FloatProperty(
        name="Ratio",
        default=0.5,
        min=0.0,
        max=1.0
    )

    iterations: IntProperty(
        name="Iterations",
        default=2,
        min=0,
        max=50
    )

    angle: FloatProperty(
        name="Angle",
        default=15.0,
        min=0.0,
        max=180.0
    )

    remesh_type: EnumProperty(
        items= [ ('BLOCKS','blocks',"collapse geometry"), 
        ('SMOOTH','smooth',"un subdivide geometry"),
        ('SHARP','sharp',"un subdivide geometry"),
        ('VOXEL','voxel',"dissolve geometry")],
        description = "Choose which type of remesh to perform.",
        default = "VOXEL"
    )
    
    oDepth: IntProperty(
        name="Octree Depth",
        default=4,
        min=1,
        max=8
    )

    voxel_size: FloatProperty(
        name="Voxel Size",
        default=0.1,
        min=0.01,
        max=2.0
    )

    geo_type: EnumProperty(
        items= [ ('GeometryNodeConvexHull','convex hull',"basic convex hull"), 
        ('GeometryNodeBoundBox','bounding box',"basic bounding box"),
        ('GeometryNodeSubdivisionSurface','subdiv',"subdivide geometry")],
        description = "Choose which type of geo node tree to add",
        default = "GeometryNodeBoundBox"
    )
        
    geo_attribute: IntProperty(
        name="Attribute",
        description = "Additional attribute used for certain geo nodes",
        default=2,
        min=0,
        max=8
    )

class uvProperties(bpy.types.PropertyGroup):
    # PROPERTIES

    selected_only: BoolProperty(
        name ="Use Selected Only",
        description = "Operate on selected objects only",
        default = False
    )

    unwrap_type: EnumProperty(
        items= [ ('Cube','cube project',"basic convex hull"), 
        ('Sphere','sphere project',"subdivide geometry"),
        ('Cylinder','cylinder project',"dissolve geometry"),
        ('Smart','smart project',"basic bounding box")],
        description = "Choose which type of unwrap process to use.",
        default = "Cube"
    )

    scale_to_bounds: BoolProperty(
        name ="Scale To Bounds",
        description = "Scale UVs to 2D bounds",
        default = False
    )

    clip_to_bounds: BoolProperty(
        name ="Clip To Bounds",
        description = "Clip UVs to 2D bounds",
        default = False
    )
    
    use_set_size: BoolProperty(
        name ="Use Set Size",
        description = "Use a defined UV size for all objects",
        default = False
    )

    set_size : FloatProperty(
        name="Set Size",
        default=2.0,
        min=0.01,
        max=100.0
    )
    
    print_updated_results: BoolProperty(
        name ="Print Updated Results",
        description = "Print updated results to console",
        default = True
    )

class OmniSceneOptChopPropertiesMixin:
    selected_only: BoolProperty(
        name="Split Selected Only",
        description="Operate on selected objects only",
        default=False
    )

    print_updated_results: BoolProperty(
        name="Print Updated Results",
        description="Print updated results to console",
        default=True
    )

    cut_meshes: BoolProperty(
        name="Cut Meshes",
        description="Cut meshes",
        default=True
    )

    merge: BoolProperty(
        name="Merge",
        description="Merge split chunks after splitting is complete",
        default=False
    )

    create_bounds: BoolProperty(
        name="Create Boundary Objects",
        description="Add generated boundary objects to scene",
        default=False
    )

    max_depth: IntProperty(
        name="Max Depth",
        description="Maximum recursion depth",
        default=8,
        min=0,
        max=32
    )

    max_vertices: IntProperty(
        name="Max Vertices",
        description="Maximum vertices allowed per block",
        default=10000,
        min=0,
        max=1000000
    )
    min_box_size: FloatProperty(
        name="Min Box Size",
        description="Minimum dimension for a chunk to be created",
        default=1,
        min=0,
        max=10000
    )

    def attributes(self) -> Dict:
        return dict(
            merge=self.merge,
            cut_meshes=self.cut_meshes,
            max_vertices=self.max_vertices,
            min_box_size=self.min_box_size,
            max_depth=self.max_depth,
            print_updated_results=self.print_updated_results,
            create_bounds=self.create_bounds,
            selected_only=self.selected_only
        )

    def set_attributes(self, attributes:Dict):
        for attr, value in attributes.items():
            if hasattr(self, attr):
                setattr(self, attr, value)
            else:
                raise ValueError(f"OmniSceneOptChopPropertiesMixin: invalid attribute for set {attr}")


class chopProperties(bpy.types.PropertyGroup, OmniSceneOptChopPropertiesMixin):
    pass
