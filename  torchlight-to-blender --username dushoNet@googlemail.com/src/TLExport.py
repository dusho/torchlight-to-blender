#!BPY

"""
Name: 'OGRE for Torchlight (*.MESH)'
Blender: 2.59
Group: 'Export'
Tooltip: 'Export Torchlight OGRE files'
    
Author: Dusho
"""

__author__ = "Dusho"
__version__ = "0.3 22-Feb-2012"

__bpydoc__ = """\
This script exports Torchlight Ogre models from Blender.

Supported:<br>
    * TODO

Missing:<br>    
    * TODO

Known issues:<br>
    * TODO
     
History:<br>
    * v0.3 (22-Feb-2012) - WIP - started cleaning + using OgreXMLConverter
    * v0.2 (19-Feb-2012) - WIP - working export of geometry and faces
    * v0.1 (18-Feb-2012) - initial 2.59 import code (from .xml)
    * v0.0 (12-Feb-2012) - file created
"""

#from Blender import *
from xml.dom import minidom
import bpy
from mathutils import Vector, Matrix
#import math
import os

def toFmtStr(number):
    #return str("%0.7f" % number)
    return str(round(number, 7))

def xSaveGeometry(geometry, xDoc, xMesh, isShared):
    # I guess positions (vertices) must be there always
    vertices = geometry['positions']
    
    if isShared:
        geometryType = "sharedgeometry"
    else:
        geometryType = "geometry"
    
    isNormals = False
    if 'normals' in geometry:    
        isNormals = True
        normals = geometry['normals']
        
    isTexCoordsSets = False
    if 'texcoordsets' in geometry:
        isTexCoordsSets = True
        uvSets = geometry['uvsets']
    
    xGeometry = xDoc.createElement(geometryType)
    xGeometry.setAttribute("vertexcount", str(len(vertices)))
    xMesh.appendChild(xGeometry)
    
    xVertexBuffer = xDoc.createElement("vertexbuffer")
    xVertexBuffer.setAttribute("positions", "true")
    if isNormals:
        xVertexBuffer.setAttribute("normals", "true")
    if isTexCoordsSets:
        xVertexBuffer.setAttribute("texture_coord_dimensions_0", "2")
        xVertexBuffer.setAttribute("texture_coords", "1")
    xGeometry.appendChild(xVertexBuffer)
    
    for i, vx in enumerate(vertices):
        xVertex = xDoc.createElement("vertex")
        xVertexBuffer.appendChild(xVertex)
        xPosition = xDoc.createElement("position")
        xPosition.setAttribute("x", toFmtStr(vx[0]))
        xPosition.setAttribute("y", toFmtStr(vx[2]))
        xPosition.setAttribute("z", toFmtStr(-vx[1]))
        xVertex.appendChild(xPosition)
        if isNormals:
            xNormal = xDoc.createElement("normal")
            xNormal.setAttribute("x", toFmtStr(normals[i][0]))
            xNormal.setAttribute("y", toFmtStr(normals[i][2]))
            xNormal.setAttribute("z", toFmtStr(-normals[i][1]))
            xVertex.appendChild(xNormal)
        if isTexCoordsSets:
            xUVSet = xDoc.createElement("texcoord")
            xUVSet.setAttribute("u", toFmtStr(uvSets[i][0][0])) # take only 1st set for now
            xUVSet.setAttribute("v", toFmtStr(1.0 - uvSets[i][0][1]))
            #xUVSet.setAttribute("v", str("%0.7f" % (1.0 - uvSets[i][0][1]))) #rounding
            xVertex.appendChild(xUVSet)
            
def xSaveSubMeshes(meshData, xDoc, xMesh, hasSharedGeometry):
    
    xSubMeshes = xDoc.createElement("submeshes")
    xMesh.appendChild(xSubMeshes)
    
    for submesh in meshData['submeshes']:
        
        xSubMesh = xDoc.createElement("submesh")
        xSubMesh.setAttribute("material", submesh['material'])
        if hasSharedGeometry:
            xSubMesh.setAttribute("usesharedvertices", "true")
        else:
            xSubMesh.setAttribute("usesharedvertices", "false")
        xSubMesh.setAttribute("use32bitindexes", "false")   # TODO: not sure about this
        xSubMesh.setAttribute("operationtype", "triangle_list")  
        xSubMeshes.appendChild(xSubMesh)
        # write all faces
        if 'faces' in submesh:
            faces = submesh['faces']
            xFaces = xDoc.createElement("faces")
            xFaces.setAttribute("count", str(len(faces)))
            xSubMesh.appendChild(xFaces)
            for face in faces:
                xFace = xDoc.createElement("face")
                xFace.setAttribute("v1", str(face[0]))
                xFace.setAttribute("v2", str(face[1]))
                xFace.setAttribute("v3", str(face[2]))
                xFaces.appendChild(xFace)
        # if there is geometry per sub mesh
        if 'geometry' in submesh:
            geometry = submesh['geometry']
            xSaveGeometry(geometry, xDoc, xSubMesh, hasSharedGeometry)
    
def xSaveMeshData(meshData, filepath):    
    from xml.dom.minidom import Document
    
    hasSharedGeometry = False
    if 'sharedgeometry' in meshData:
        hasSharedGeometry = True
        
    # Create the minidom document
    xDoc = Document()
    
    xMesh = xDoc.createElement("mesh")
    xDoc.appendChild(xMesh)
    
    if hasSharedGeometry:
        geometry = meshData['sharedgeometry']
        xSaveGeometry(geometry, xDoc, xMesh, hasSharedGeometry)
    
    xSaveSubMeshes(meshData, xDoc, xMesh, hasSharedGeometry)
   
    # Print our newly created XML    
    fileWr = open(filepath, 'w') 
    fileWr.write(xDoc.toprettyxml(indent="    ")) # 4 spaces
    #doc.writexml(fileWr, "  ")
    fileWr.close() 

def bCollectMeshData(selectedObjects):
    meshData = {}
    subMeshesData = []
    for ob in selectedObjects:
        subMeshData = {}
        #ob = bpy.types.Object ##
        materialName = ob.name
        #mesh = bpy.types.Mesh ##
        mesh = ob.data     
        
        uvTex = []
        faces = []   
        fcs = mesh.faces    
        for f in fcs:
            #f = bpy.types.MeshFace ##
            oneFace = []
            for vertexIdx in f.vertices:
                oneFace.append(vertexIdx)
                
            faces.append(oneFace)
            if mesh.uv_textures[0].data:
                faceUV=mesh.uv_textures[0].data[f.index]
                if len(f.vertices)>=3:
                    uvTex.append([[faceUV.uv1[0], faceUV.uv1[1]]]) 
                    uvTex.append([[faceUV.uv2[0], faceUV.uv2[1]]])
                    uvTex.append([[faceUV.uv3[0], faceUV.uv3[1]]])
                if len(f.vertices)==4:
                    uvTex.append([[faceUV.uv4[0], faceUV.uv4[1]]])                              
        
#        uvOfVertex = {}
#        if mesh.uv_textures.active:
#            for layer in mesh.uv_textures:
#                uvOfVertex[layer] = {}
#                for fidx, uvface in enumerate(layer.data):
#                    face = mesh.faces[ fidx ]
#                    for vertex in face.vertices:
#                        if vertex not in uvOfVertex[layer]:
#                            uv = uvface.uv[ list(face.vertices).index(vertex) ]
#                            uvOfVertex[layer][vertex] = [uv[0],uv[1]] 

        uvOfVertex = {}
        if mesh.uv_textures.active:
            for layer in mesh.uv_textures:
                uvOfVertex[layer] = {}
                for fidx, uvface in enumerate(layer.data):
                    face = mesh.faces[ fidx ]
                    for vertex in face.vertices:
                        if vertex not in uvOfVertex[layer]:
                            uv = uvface.uv[ list(face.vertices).index(vertex) ]
                            uvOfVertex[layer][vertex] = [uv[0],uv[1]] 
        
        # geometry
        geometry = {}
        #vertices = bpy.types.MeshVertices
        vertices = mesh.vertices
        normals = []
        positions = []
        
        for v in vertices:
            #v = bpy.types.MeshVertex ##
            #nr = bpy.types.Vec
            positions.append([v.co[0], v.co[1], v.co[2]])
            normals.append([v.normal[0],v.normal[1],v.normal[2]])        
        
        geometry['positions'] = positions
        geometry['normals'] = normals
        geometry['texcoordsets'] = len(mesh.uv_textures)
        geometry['uvsets'] = uvTex
        
        
        subMeshData['material'] = materialName
        subMeshData['faces'] = faces
        subMeshData['geometry'] = geometry
        subMeshesData.append(subMeshData)
        
    meshData['submeshes']=subMeshesData
    
    return meshData

def SaveMesh(filepath):
    
    # get mesh data from selected objects
    selectedObjects = []
    scn = bpy.context.scene
    for ob in scn.objects:
        if ob.select==True:
            selectedObjects.append(ob)
  
    blenderMeshData = bCollectMeshData(selectedObjects)
    
    dumpFile = filepath + "EDump"
    #fileWr = open("D:\stuff\Torchlight_modding\org_models\Shields_03\Shields_03_AAblex.MESH.xml", 'w') 
    fileWr = open(dumpFile, 'w')
    fileWr.write(str(blenderMeshData))
    
    fileWr.close() 
    
    #print(blenderMeshData)
    xSaveMeshData(blenderMeshData, filepath)
    #xSaveMeshData(blenderMeshData, "D:\stuff\Torchlight_modding\org_models\Shields_03\Shields_03_blex.MESH.xml")
    

def save(operator, context, filepath,       
         ogreXMLconverter=None,
         keep_xml=False,):
    
    print("saving...")
    print(str(filepath))
    
    xmlFilepath = filepath + ".xml"
    SaveMesh(xmlFilepath)
    
    if(ogreXMLconverter is not None):
        # use Ogre XML converter  xml -> binary mesh
        os.system('%s "%s"' % (ogreXMLconverter, xmlFilepath))
        
        # remove XML file
        if keep_xml is False:
            os.unlink("%s" % xmlFilepath)        
    
    print("done.")
    
    return {'FINISHED'}

#save(0, bpy.context, "D:\stuff\Torchlight_modding\org_models\box\box_t2.mesh.xml")
