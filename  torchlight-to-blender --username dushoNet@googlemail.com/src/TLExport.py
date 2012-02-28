#!BPY

"""
Name: 'OGRE for Torchlight (*.MESH)'
Blender: 2.59 and 2.62
Group: 'Import/Export'
Tooltip: 'Import/Export Torchlight OGRE mesh files'
    
Author: Dusho
"""

__author__ = "Dusho"
__version__ = "0.4 28-Feb-2012"

__bpydoc__ = """\
This script imports Torchlight Ogre models into Blender.

Supported:<br>
    * import/export of basic meshes

Missing:<br>   
    * vertex weights
    * skeletons
    * animations
    * material export
    * vertex color import/export

Known issues:<br>
    * meshes with skeleton info will loose that info (vertex weights, skeleton link, ...)
     
History:<br>
    * v0.4 (28-Feb-2012) - fixing export when no UV data are present
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

SHOW_EXPORT_DUMPS = False

class VertexInfo(object):
    def __init__(self, px,py,pz, nx,ny,nz, u,v):        
        self.px = px
        self.py = py
        self.pz = pz
        self.nx = nx
        self.ny = ny
        self.nz = nz        
        self.u = u
        self.v = v        
        

    '''does not compare ogre_vidx (and position at the moment) [ no need to compare position ]'''
    def __eq__(self, o): 
        if self.nx != o.nx or self.ny != o.ny or self.nz != o.nz: return False 
        elif self.px != o.px or self.py != o.py or self.pz != o.pz: return False
        elif self.u != o.u or self.v != o.v: return False
        return True
    
#    def __hash__(self):
#        return hash(self.px) ^ hash(self.py) ^ hash(self.pz) ^ hash(self.nx) ^ hash(self.ny) ^ hash(self.nz)
#        
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
    texCoordSets = geometry['texcoordsets']
    if texCoordSets>0 and 'uvsets' in geometry:
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
        xVertexBuffer.setAttribute("texture_coords", str(texCoordSets))
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
            xVertex.appendChild(xUVSet)
            
def xSaveSubMeshes(meshData, xDoc, xMesh, hasSharedGeometry):
            
    xSubMeshes = xDoc.createElement("submeshes")
    xMesh.appendChild(xSubMeshes)
    
    for submesh in meshData['submeshes']:
                
        numVerts = len(submesh['geometry']['positions'])
        
        xSubMesh = xDoc.createElement("submesh")
        xSubMesh.setAttribute("material", submesh['material'])
        if hasSharedGeometry:
            xSubMesh.setAttribute("usesharedvertices", "true")
        else:
            xSubMesh.setAttribute("usesharedvertices", "false")
        xSubMesh.setAttribute("use32bitindexes", str(bool(numVerts > 65535)))   
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

def getVertexIndex(vertexInfo, vertexList):
    
    for vIdx, vert in enumerate(vertexList):
        if vertexInfo == vert:
            return vIdx
    
    #not present in list:
    vertexList.append(vertexInfo)
    return len(vertexList)-1

def bCollectMeshData(selectedObjects):
    meshData = {}
    subMeshesData = []
    for ob in selectedObjects:
        subMeshData = {}
        #ob = bpy.types.Object ##
        materialName = ob.name
        #mesh = bpy.types.Mesh ##
        mesh = ob.data     
        
        # first try to collect UV data
        uvData = []
        hasUVData = False
        if mesh.uv_textures.active:
            hasUVData = True
            #uvLayerTofaceUVdata = {}
            for layer in mesh.uv_textures:
                faceIdxToUVdata = {}
                for fidx, uvface in enumerate(layer.data):               
                    faceIdxToUVdata[fidx] = uvface.uv
                #uvData[layer]=faceIdxToUVdata
                uvData.append(faceIdxToUVdata)
                      
        vertexList = []        
        newFaces = []
                
        for fidx, face in enumerate(mesh.faces):
            tris = []
            tris.append( (face.vertices[0], face.vertices[1], face.vertices[2]) )
            if(len(face.vertices)>=4):
                tris.append( (face.vertices[0], face.vertices[2], face.vertices[3]) ) 
            if SHOW_EXPORT_DUMPS:
                    print("_face: "+ str(fidx) + " indices [" + str(list(face.vertices))+ "]")
            for tri in tris:
                newFaceVx = []                        
                for vertex in tri:
                    vxOb = mesh.vertices[vertex]
                    u = 0
                    v = 0
                    if hasUVData:
                        uv = uvData[0][fidx][ list(tri).index(vertex) ] #take 1st layer only
                        u = uv[0]
                        v = uv[1]
                    px = vxOb.co[0]
                    py = vxOb.co[1]
                    pz = vxOb.co[2]
                    nx = vxOb.normal[0] 
                    ny = vxOb.normal[1]
                    nz = vxOb.normal[2]                     
                    if SHOW_EXPORT_DUMPS:
                        print("_vx: "+ str(vertex)+ " co: "+ str([px,py,pz]) +
                              " no: " + str([nx,ny,nz]) +
                              " uv: " + str([u,v]))
                    vert = VertexInfo(px,py,pz,nx,ny,nz,u,v)
                    newVxIdx = getVertexIndex(vert, vertexList)
                    newFaceVx.append(newVxIdx)
                    if SHOW_EXPORT_DUMPS:
                        print("Nvx: "+ str(newVxIdx)+ " co: "+ str([px,py,pz]) +
                              " no: " + str([nx,ny,nz]) +
                              " uv: " + str([u,v]))
                newFaces.append(newFaceVx)
                if SHOW_EXPORT_DUMPS:
                    print("Nface: "+ str(fidx) + " indices [" + str(list(newFaceVx))+ "]")
                  
        # geometry
        geometry = {}
        #vertices = bpy.types.MeshVertices
        #vertices = mesh.vertices
        faces = [] 
        normals = []
        positions = []
        uvTex = []
        
        faces = newFaces
        
        for vxInfo in vertexList:
            positions.append([vxInfo.px, vxInfo.py, vxInfo.pz])
            normals.append([vxInfo.nx, vxInfo.ny, vxInfo.nz])
            uvTex.append([[vxInfo.u, vxInfo.v]])
        
        if SHOW_EXPORT_DUMPS:
            print("uvTex")
            print(uvTex)
        
        geometry['positions'] = positions
        geometry['normals'] = normals
        geometry['texcoordsets'] = len(mesh.uv_textures)
        print("texcoordsets: " + str(len(mesh.uv_textures)))
        if hasUVData:
            geometry['uvsets'] = uvTex
        
        
        subMeshData['material'] = materialName
        subMeshData['faces'] = faces
        subMeshData['geometry'] = geometry
        subMeshesData.append(subMeshData)
        
    meshData['submeshes']=subMeshesData
    
    return meshData

def SaveMesh(filepath):
    
    # go to the object mode
    for ob in bpy.data.objects: 
        bpy.ops.object.mode_set(mode='OBJECT')
            
    # get mesh data from selected objects
    selectedObjects = []
    scn = bpy.context.scene
    for ob in scn.objects:
        if ob.select==True:
            selectedObjects.append(ob)
    
    if len(selectedObjects)==0:
        return -1
  
    blenderMeshData = bCollectMeshData(selectedObjects)
    
    if SHOW_EXPORT_DUMPS:
        dumpFile = filepath + "EDump"    
        fileWr = open(dumpFile, 'w')
        fileWr.write(str(blenderMeshData))    
        fileWr.close() 
    
    xSaveMeshData(blenderMeshData, filepath)
    
    return 1

def save(operator, context, filepath,       
         ogreXMLconverter=None,
         keep_xml=False,):
    
    print("saving...")
    print(str(filepath))
    
    xmlFilepath = filepath + ".xml"
    result = SaveMesh(xmlFilepath)
    
    if result<0:
        print("No objects selected for export.")
        return ('CANCELLED')
    
    if(ogreXMLconverter is not None):
        # use Ogre XML converter  xml -> binary mesh
        os.system('%s "%s"' % (ogreXMLconverter, xmlFilepath))
        
        # remove XML file
        if keep_xml is False:
            os.unlink("%s" % xmlFilepath)        
    
    print("done.")
    
    return {'FINISHED'}

#save(0, bpy.context, "D:\stuff\Torchlight_modding\org_models\box\box_t2.mesh.xml")
