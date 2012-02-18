#!BPY

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
"""

#from Blender import *
#from xml.dom import minidom
import bpy
#import math
#import os

def xLoadVertexData(data):
    vertexData = {}    
    return vertexData

def Import():
    print("TEST12324324AAA")
    return

def load(operator, context, filepath,       
         ):
    
    print("loading...")
    print(str(filepath))
    
    return {'FINISHED'}


#load(0, bpy.context, "D:\stuff\Torchlight_modding\org_models\Shields_03\Shields_03.MESH.xml")