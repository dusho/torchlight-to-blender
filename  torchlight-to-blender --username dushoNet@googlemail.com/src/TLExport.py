#!BPY

"""
Name: 'OGRE for Torchlight (*.MESH)'
Blender: 2.59
Group: 'Export'
Tooltip: 'Export Torchlight OGRE files'
    
Author: Dusho
"""

__author__ = "Dusho"
__version__ = "0.0 12-Feb-2012"

__bpydoc__ = """\
This script exports Torchlight Ogre models from Blender.

Supported:<br>
    * TODO

Missing:<br>    
    * TODO

Known issues:<br>
    * TODO
     
History:<br>
    * v0.0 (12-Feb-2012) - file created
"""

def save(operator, context, filepath,       
         ):
    
    print("saving...")
    print(str(filepath))
    
    return {'FINISHED'}
