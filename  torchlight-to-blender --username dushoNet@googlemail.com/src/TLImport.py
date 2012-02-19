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
    * v0.1 (18-Feb-2012) - initial 2.59 import code (from .xml)
"""

"""
Inner data representation:
MESHDATA:
['sharedgeometry']
    ['positions'] - vectors with (x,y,z)
    ['normals'] - vectors with (x,y,z)
    ['vertexcolors'] - vectors with (r,g,b,a)
    ['texcoordsets'] - integer (number of UV sets)
    ['uvsets'] - vectors with (u,v) * number or UV sets for vertex [(u,v)][(u,v)]...
['submeshes'][idx]
        [material] - string (material name)
        [faces] - vectors with faces (v1,v2,v3)
        [geometry] - identical to 'sharedgeometry' data content   
"""

#from Blender import *
from xml.dom import minidom
import bpy
from mathutils import Vector, Matrix
#import math
import os

def xOpenFile(filename):
    xml_file = open(filename)
    #xml_doc = minidom.parse(xml_file)
    try:
        xml_doc = minidom.parse(xml_file)
        output = xml_doc
    except:
        print ("File not valid!")
        output = 'None'
    xml_file.close()
    return output

def xCollectFaceData(facedata):
    faces = []
    for face in facedata.childNodes:
        if face.localName == 'face':
            v1 = int(face.getAttributeNode('v1').value)
            v2 = int(face.getAttributeNode('v2').value)
            v3 = int(face.getAttributeNode('v3').value)
            faces.append([v1,v2,v3])
    
    return faces

def xCollectVertexData(data):
    vertexdata = {}
    vertices = []
    normals = []
    vertexcolors = []
    
    for vb in data.childNodes:
        if vb.localName == 'vertexbuffer':
            if vb.hasAttribute('positions'):
                for vertex in vb.getElementsByTagName('vertex'):
                    for vp in vertex.childNodes:
                        if vp.localName == 'position':
                            x = float(vp.getAttributeNode('x').value)
                            y = -float(vp.getAttributeNode('z').value)
                            z = float(vp.getAttributeNode('y').value)
                            vertices.append([x,y,z])
                vertexdata['positions'] = vertices            
            
            if vb.hasAttribute('normals'):
                for vertex in vb.getElementsByTagName('vertex'):
                    for vn in vertex.childNodes:
                        if vn.localName == 'normal':
                            x = float(vn.getAttributeNode('x').value)
                            y = -float(vn.getAttributeNode('z').value)
                            z = float(vn.getAttributeNode('y').value)
                            normals.append([x,y,z])
                vertexdata['normals'] = normals                
            
            if vb.hasAttribute('colours_diffuse'):
                for vertex in vb.getElementsByTagName('vertex'):
                    for vcd in vertex.childNodes:
                        if vcd.localName == 'colour_diffuse':
                            rgba = vcd.getAttributeNode('value').value
                            r = float(rgba.split()[0])
                            g = float(rgba.split()[1])
                            b = float(rgba.split()[2])
                            a = float(rgba.split()[3])
                            vertexcolors.append([r,g,b,a])
                vertexdata['vertexcolors'] = vertexcolors
            
            if vb.hasAttribute('texture_coord_dimensions_0'):
                texcosets = int(vb.getAttributeNode('texture_coords').value)
                vertexdata['texcoordsets'] = texcosets
                uvcoordset = []
                for vertex in vb.getElementsByTagName('vertex'):
                    uvcoords = []
                    for vt in vertex.childNodes:
                        if vt.localName == 'texcoord':
                            u = float(vt.getAttributeNode('u').value)
                            v = -float(vt.getAttributeNode('v').value)+1.0
                            uvcoords.append([u,v])
                                
                    if len(uvcoords) > 0:
                        uvcoordset.append(uvcoords)
                vertexdata['uvsets'] = uvcoordset                
                        
    return vertexdata

def xCollectMeshData(xmldoc,meshname,Textures,dirname):
    #global has_skeleton
    meshData = {}
    faceslist = []
    OGREObjects = []
    allObjs = []
    isSharedGeometry = False
    sharedGeom = []
        
    if(len(xmldoc.getElementsByTagName('sharedgeometry')) > 0):
        for subnodes in xmldoc.getElementsByTagName('sharedgeometry'):
            meshData['sharedgeometry'] = xCollectVertexData(subnodes)
            
    for submeshes in xmldoc.getElementsByTagName('submeshes'):
        for submesh in submeshes.childNodes:
            if submesh.localName == 'submesh':
                material = str(submesh.getAttributeNode('material').value)
                # to avoid Blender naming limit problems
                #material = GetBlender249Name(material)
                sm = {}
                sm['material']=material
                for subnodes in submesh.childNodes:
                    if subnodes.localName == 'faces':
                        facescount = int(subnodes.getAttributeNode('count').value)
                        #sm.append(xCollectFaceData(subnodes))
                        sm['faces']=xCollectFaceData(subnodes)
                    
                        if len(xCollectFaceData(subnodes)) != facescount:
                            print ("FacesCount doesn't match!")
                            break 
                    
                    if (subnodes.localName == 'geometry'):
                        vertexcount = int(subnodes.getAttributeNode('vertexcount').value)
                        #sm.append(xCollectVertexData(subnodes))
                        sm['geometry']=xCollectVertexData(subnodes)
                                                                   
#                    if subnodes.localName == 'boneassignments':
#                        sm.append(collectBoneAssignments(subnodes))    
#                        sm['boneassignments']=
                        
                OGREObjects.append(sm)
                
    meshData['submeshes']=OGREObjects
    
    return meshData

def xSaveGeometry(geometry, xDoc, xMesh, isShared):
    # I guess positions (vertices) must there always
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
        xPosition.setAttribute("x", str(vx[0]))
        xPosition.setAttribute("y", str(vx[1]))
        xPosition.setAttribute("z", str(vx[2]))
        xVertex.appendChild(xPosition)
        if isNormals:
            xNormal = xDoc.createElement("normal")
            xNormal.setAttribute("x", str(normals[i][0]))
            xNormal.setAttribute("y", str(normals[i][1]))
            xNormal.setAttribute("z", str(normals[i][2]))
            xVertex.appendChild(xNormal)
        if isTexCoordsSets:
            xUVSet = xDoc.createElement("texcoord")
            xUVSet.setAttribute("u", str(uvSets[i][0][0])) # take only 1st set for now
            xUVSet.setAttribute("v", str(uvSets[i][0][1]))
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
                
def CreateMesh(xml_doc, folder, name, materialFile):

    textures = 'None'
    print("collecting mesh data...")
    meshData = xCollectMeshData(xml_doc, name, textures, folder)
    # from collected data create all sub meshes
    subObjs = bCreateSubMeshes(meshData)
    # skin submeshes
    #bSkinMesh(subObjs)
    
    # TODO, place save code here for now
    xSaveMeshData(meshData, "D:\stuff\Torchlight_modding\org_models\Shields_03\Shields_03_ex.MESH.xml")
    
    print(meshData)
    

def bCreateSubMeshes(meshData):
    
    allObjects = []
    submeshes = meshData['submeshes']
    
    for i in range(len(submeshes)):
        subMeshData = submeshes[i]
        aName = subMeshData['material']        
        # Create mesh and object
        me = bpy.data.meshes.new(aName)
        ob = bpy.data.objects.new(aName, me)
        #ob.location = origin
        # Link object to scene
        scn = bpy.context.scene
        scn.objects.link(ob)
        scn.objects.active = ob
        scn.update()
        # check for submesh geometry, or take the shared one
        if 'geometry' in subMeshData.keys():
            geometry = subMeshData['geometry']            
        else:
            geometry = meshData['sharedgeometry']            
          
        verts = geometry['positions']      
        faces = subMeshData['faces']     
        # mesh vertices and faces   
        me.from_pydata(verts, [], faces) 
        # mesh normals
        c = 0
        for v in me.vertices:
            if 'normals' in geometry.keys():
                normals = geometry['normals']
                v.normal = Vector((normals[c][0],normals[c][1],normals[c][2]))
                c+=1
        # smooth        
        for f in me.faces:
            f.use_smooth = True        
        # texture coordinates
        if 'texcoordsets' in geometry:
            for j in range(geometry['texcoordsets']):                
                uvLayer = me.uv_textures.new('UVLayer'+str(j))
                
                me.uv_textures.active = uvLayer
            
                for f in me.faces:    
                    if 'uvsets' in geometry:
                        uvco1sets = geometry['uvsets'][f.vertices[0]]
                        uvco2sets = geometry['uvsets'][f.vertices[1]]
                        uvco3sets = geometry['uvsets'][f.vertices[2]]
                        uvco1 = Vector((uvco1sets[j][0],uvco1sets[j][1]))
                        uvco2 = Vector((uvco2sets[j][0],uvco2sets[j][1]))
                        uvco3 = Vector((uvco3sets[j][0],uvco3sets[j][1]))
                        uvLayer.data[f.index].uv = (uvco1,uvco2,uvco3)
                        
        # vertex colors       
        if 'vertexcolors' in geometry:
            me.vertex_colors = True
        
            vcolors = geometry['vertexcolors']
        
            for f in me.faces:
                for k,v in enumerate(f.v):
                    col = f.col[k]
                    vcol = vcolors[k]
                    col.r = int(vcol[0]*255)
                    col.g = int(vcol[1]*255)
                    col.b = int(vcol[2]*255)
                    col.a = int(vcol[3]*255)
        
        # Update mesh with new data
        me.update(calc_edges=True)
        
        allObjects.append(ob)
        
        return allObjects
        

def load(operator, context, filepath,       
         ):
    
    print("loading...")
    print(str(filepath))
    
    folder = os.path.split(filepath)[0]
    meshfilename = os.path.split(filepath)[1].lower()    
    name = "mesh"
    files = []
    materialFile = "None"
    
    filename = filepath.lower()
    # import the mesh
    if (".mesh" in filename):
        mesh_data = xOpenFile(filename)
        if mesh_data != "None":
            #CreateSkeleton(mesh_data, folder, name)
            CreateMesh(mesh_data, folder, name, materialFile)
    
    print("done")
    return {'FINISHED'}


load(0, bpy.context, "D:\stuff\Torchlight_modding\org_models\Shields_03\Shields_03.MESH.xml")