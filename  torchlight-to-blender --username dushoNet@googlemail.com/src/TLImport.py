#!BPY

"""
Name: 'OGRE for Torchlight (*.MESH)'
Blender: 2.59
Group: 'Import'
Tooltip: 'Import Torchlight OGRE files'
    
Author: Dusho
"""

__author__ = "Dusho"
__version__ = "0.2 19-Feb-2012"

__bpydoc__ = """\
This script imports Torchlight Ogre models into Blender.

Supported:<br>
    * TODO

Missing:<br>    
    * TODO

Known issues:<br>
    * TODO
     
History:<br>
    * v0.2 (19-Feb-2012) - WIP - working export of geometry and faces
    * v0.1 (18-Feb-2012) - initial 2.59 import code (from .xml)
    * v0.0 (12-Feb-2012) - file created
"""

"""
When importing: (x)-Blender, (x')-Ogre
vectors: x=x', y=-z', z=y'
UVtex: u=u', v = -v'+1

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
['materials']
    [(matID)]:'texture path'
"""

#from Blender import *
from xml.dom import minidom
import bpy
from mathutils import Vector, Matrix
#import math
import os

# makes sure name doesn't exceeds blender naming limits
# also keeps after name (as Torchlight uses names to identify types -boots, chest, ...- with names)
# TODO: this is not needed for Blender 2.62 and above
def GetValidBlenderName(name):
    newname = name    
    if(len(name) > 20):
        if(name.find("/") >= 0):
            if(name.find("Material") >= 0):
                # replace 'Material' string with only 'Mt'
                newname = name.replace("Material","Mt")
            # check if it's still above 20
            if(len(newname) > 20):
                suffix = newname[newname.find("/"):]
                prefix = newname[0:(21-len(suffix))]
                newname = prefix + suffix
        else:
            newname = name[0:21]            
    if(newname!=name):
        print("WARNING: Name truncated (" + name + " -> " + newname + ")")
            
    return newname

def xOpenFile(filename):
    xml_file = open(filename)    
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
    subMeshData = []
    allObjs = []
    isSharedGeometry = False
    sharedGeom = []
    
    # collect shared geometry    
    if(len(xmldoc.getElementsByTagName('sharedgeometry')) > 0):
        for subnodes in xmldoc.getElementsByTagName('sharedgeometry'):
            meshData['sharedgeometry'] = xCollectVertexData(subnodes)
    # collect submeshes data       
    for submeshes in xmldoc.getElementsByTagName('submeshes'):
        for submesh in submeshes.childNodes:
            if submesh.localName == 'submesh':
                material = str(submesh.getAttributeNode('material').value)
                # to avoid Blender naming limit problems
                material = GetValidBlenderName(material)
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
                        
                subMeshData.append(sm)
                
    meshData['submeshes']=subMeshData
            
    return meshData
# for now just collecting material and texture {[material:texture]}
def xCollectMaterialData(meshData, materialFile, folder):
    try:
        filein = open(materialFile)
    except:
        print ("Material: File", materialFile, "not found!")
        return 'None' 
    data = filein.readlines()
    filein.close()
    MaterialDic = {}
    
    count = 0
    for line in data:
        if "material" in line:
            MaterialName = line.split()[1]
            # to avoid Blender naming limit problems
            MaterialName = GetValidBlenderName(MaterialName)
            MaterialDic[MaterialName] = []
            count = 0
        if "{" in line:
            count += 1
        if  count > 0:
            MaterialDic[MaterialName].append(line)
        if "}" in line:
            count -= 1
    Textures = {}
    #print(MaterialDic)
    for Material in MaterialDic.keys():
        print ("Materialname:", Material)
        for line in MaterialDic[Material]:
            if "texture_unit" in line:
                Textures[Material] = ""
                count = 0
            if "{" in line:
                count+=1
            if (count > 0) and ("texture" in line):
                file = os.path.join(folder, (line.split()[1]))            
                
                if(not os.path.isfile(file)):
                    # just force to use .dds if there isn't file specified in material file
                    file = os.path.join(folder, os.path.splitext((line.split()[1]))[0] + ".dds")
                Textures[Material] += file
                    
            if "}" in line:
                count-=1
    
    # store it into meshData
    meshData['materials']= Textures
    print(Textures)
    #return Textures

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
        xPosition.setAttribute("x", str(vx[0]))
        xPosition.setAttribute("y", str(vx[2]))
        xPosition.setAttribute("z", str(-vx[1]))
        xVertex.appendChild(xPosition)
        if isNormals:
            xNormal = xDoc.createElement("normal")
            xNormal.setAttribute("x", str(normals[i][0]))
            xNormal.setAttribute("y", str(normals[i][2]))
            xNormal.setAttribute("z", str(-normals[i][1]))
            xVertex.appendChild(xNormal)
        if isTexCoordsSets:
            xUVSet = xDoc.createElement("texcoord")
            xUVSet.setAttribute("u", str(uvSets[i][0][0])) # take only 1st set for now
            xUVSet.setAttribute("v", str(1.0 - uvSets[i][0][1]))
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
                
def CreateMesh(xml_doc, folder, name, materialFile):

    textures = 'None'
    print("collecting mesh data...")
    meshData = xCollectMeshData(xml_doc, name, textures, folder)
    
    xCollectMaterialData(meshData, materialFile, folder)
    # from collected data create all sub meshes
    subObjs = bCreateSubMeshes(meshData)
    # skin submeshes
    #bSkinMesh(subObjs)
    
    # TODO, need to retrieve meshData from blender
    # TODO, place save code here for now
    xSaveMeshData(meshData, "D:\stuff\Torchlight_modding\org_models\Shields_03\Shields_03_ex.MESH.xml")
    
    #xSaveMeshData(meshData, "D:\stuff\Torchlight_modding\org_models\Alchemist\Alchemist_ex.MESH.xml")
    #print(meshData)
    

def bCreateSubMeshes(meshData):
    
    allObjects = []
    submeshes = meshData['submeshes']
    
    for i in range(len(submeshes)):
        subMeshData = submeshes[i]
        subMeshName = subMeshData['material']        
        # Create mesh and object
        me = bpy.data.meshes.new(subMeshName)
        ob = bpy.data.objects.new(subMeshName, me)        
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
          
#        # transform raw data (Ogre) into Blender
#        vertices = geometry['positions']      
#        verts = []
#        for vert in vertices:
#            verts.append([vert[0], vert[1], vert[2]])

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
              
        # material for the submesh
        # Create image texture from image.         
        if subMeshName in meshData['materials']:
            realpath = meshData['materials'][subMeshName] # texture path
            tex = bpy.data.textures.new('ColorTex', type = 'IMAGE')
            tex.image = bpy.data.images.load(realpath)
            tex.use_alpha = True
         
        # Create shadeless material and MTex
        mat = bpy.data.materials.new('TexMat')
        mat.use_shadeless = True
        mtex = mat.texture_slots.add()
        mtex.texture = tex
        mtex.texture_coords = 'UV'
        mtex.use_map_color_diffuse = True 
        
        # add material to object
        ob.data.materials.append(mat)
        #print(me.uv_textures[0].data.values()[0].image)       
            
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
                        # this will link image to faces
                        uvLayer.data[f.index].image=tex.image
                        uvLayer.data[f.index].use_image=True
                        
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
        
    # forced view mode with textures
    bpy.context.scene.game_settings.material_mode = 'GLSL'
    areas = bpy.context.screen.areas
    for area in areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.viewport_shade='TEXTURED'
    
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
    
    # get all the filenames in the chosen directory, put in list and sort it
    for filename in os.listdir(folder):
        # we're going to do string comparisons. assume lower case to simplify code
        filename = filename.lower()
        # process .mesh and .skeleton files while skipping .xml files
        if ".skeleton.xml" in filename:
            files.append(os.path.join(folder, filename))
        elif (".mesh.xml" in filename) and (meshfilename in filename):
            print (meshfilename)
            # get the name of the MESH file without extension. Use this base name to name our imported object
            name = filename.split('.')[0]
            # to avoid Blender naming limit problems
            name = GetValidBlenderName(name)
            # put MESH file on top of the file list
            files.insert(0, os.path.join(folder, filename))
        elif ".material" in filename:
            # material file
            materialFile = os.path.join(folder, filename)

    # now that we have a list of files, process them
    filename = files[0]
    
    #filename = filepath.lower()
    # import the mesh
    if (".mesh" in filename):
        mesh_data = xOpenFile(filename)
        if mesh_data != "None":
            #CreateSkeleton(mesh_data, folder, name)
            CreateMesh(mesh_data, folder, name, materialFile)
    
    print("done")
    return {'FINISHED'}
 
#load(0, bpy.context, "D:\stuff\Torchlight_modding\org_models\Alchemist\Alchemist.MESH.xml")
load(0, bpy.context, "D:\stuff\Torchlight_modding\org_models\Shields_03\Shields_03.MESH.xml")