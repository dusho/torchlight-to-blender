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

# <pep8-80 compliant>

"""
Name: 'OGRE for Torchlight (*.MESH)'
Blender: 2.59
Group: 'Import'
Tooltip: 'Import Torchlight OGRE files'
    
Author: Dusho
"""

__author__ = "Dusho"
__version__ = "0.0 12-Feb-2012"

__bpydoc__ = """\
This script imports Torchlight Ogre models into Blender.

Supported:<br>
    * TODO

Missing:<br>    
    * TODO

Known issues:<br>
    * TODO
     
History:<br>
    * v0.0 (12-Feb-2012) - file created
    * v0.1 (18-Feb-2012) - got Blender add-on scheme working
"""

bl_info = {
    "name": "Torchlight MESH format",
    "author": "Dusho",
    "blender": (2, 5, 9),
    "api": 35622,
    "location": "File > Import-Export",
    "description": ("Import-Export Torchlight Model, Import MESH, UV's, "
                    "materials and textures"),
    "warning": "",
    "wiki_url": (""),
    "tracker_url": "",
    "support": 'OFFICIAL',
    "category": "Import-Export"}

if "bpy" in locals():
    import imp
    if "TLImport" in locals():
        imp.reload(TLImport)
    if "TLExport" in locals():
        imp.reload(TLExport)


import bpy
from bpy.props import (BoolProperty,
                       FloatProperty,
                       StringProperty,
                       EnumProperty,
                       )
from bpy_extras.io_utils import (ExportHelper,
                                 ImportHelper,
                                 path_reference_mode,
                                 axis_conversion,
                                 )


class ImportTL(bpy.types.Operator, ImportHelper):
    '''Load a Torchlight MESH File'''
    bl_idname = "import_scene.mesh"
    bl_label = "Import MESH"
    bl_options = {'PRESET'}

    filename_ext = ".mesh"
#    
    filter_glob = StringProperty(
            default="*.mesh;*.MESH",
            options={'HIDDEN'},
            )


    def execute(self, context):
        # print("Selected: " + context.active_object.name)
        from . import TLImport

        keywords = self.as_keywords(ignore=("filter_glob",))

        return TLImport.load(self, context, **keywords)

    def draw(self, context):
        layout = self.layout
       


class ExportTL(bpy.types.Operator, ExportHelper):
    '''Export a Torchlight MESH File'''

    bl_idname = "export_scene.mesh"
    bl_label = 'Export MESH'
    bl_options = {'PRESET'}

    filename_ext = ".mesh"
    filter_glob = StringProperty(
            default="*.mesh;*.MESH",
            options={'HIDDEN'},
            )
#

    def execute(self, context):
        from . import TLExport
        from mathutils import Matrix
        
        keywords = self.as_keywords(ignore=("check_existing", "filter_glob"))
               
        return TLExport.save(self, context, **keywords)       


def menu_func_import(self, context):
    self.layout.operator(ImportTL.bl_idname, text="Torchlight (.mesh)")


def menu_func_export(self, context):
    self.layout.operator(ExportTL.bl_idname, text="Torchlight (.mesh)")


def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_import.append(menu_func_import)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_import.remove(menu_func_import)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()
