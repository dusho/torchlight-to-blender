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

SHOW_IMPORT_DUMPS = False
# default blender version of script
blender_version = 259

#ogreXMLconverter=None

# makes sure name doesn't exceeds blender naming limits
# also keeps after name (as Torchlight uses names to identify types -boots, chest, ...- with names)
# TODO: this is not needed for Blender 2.62 and above
def GetValidBlenderName(name):
    
    global blender_version
    
    maxChars = 20
    if blender_version>262:
        maxChars = 63
    
    newname = name    
    if(len(name) > maxChars):
        if(name.find("/") >= 0):
            if(name.find("Material") >= 0):
                # replace 'Material' string with only 'Mt'
                newname = name.replace("Material","Mt")
            # check if it's still above 20
            if(len(newname) > maxChars):
                suffix = newname[newname.find("/"):]
                prefix = newname[0:(maxChars+1-len(suffix))]
                newname = prefix + suffix
        else:
            newname = name[0:maxChars+1]            
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

               
def CreateMesh(xml_doc, folder, name, materialFile, filepath):

    textures = 'None'
    print("collecting mesh data...")
    meshData = xCollectMeshData(xml_doc, name, textures, folder)
    
    xCollectMaterialData(meshData, materialFile, folder)
    # from collected data create all sub meshes
    subObjs = bCreateSubMeshes(meshData)
    # skin submeshes
    #bSkinMesh(subObjs)
    
    # temporarily select all imported objects
    for subOb in subObjs:
        subOb.select = True
    
#    # get mesh data from selected objects
#    selectedObjects = []
#    scn = bpy.context.scene
#    for ob in scn.objects:
#        if ob.select==True:
#            selectedObjects.append(ob)
#  


    if SHOW_IMPORT_DUMPS:
        importDump = filepath + "IDump"  
        fileWr = open(importDump, 'w') 
        fileWr.write(str(meshData))    
        fileWr.close() 
    
       

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
            if realpath:
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
                        #uvLayer.data[f.index].use_image=True
                        
        # this probably doesn't work
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
        
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.faces_shade_smooth()
        bpy.ops.object.editmode_toggle()
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
         ogreXMLconverter=None,
         keep_xml=False,):
    
    global blender_version
    
    blender_version = bpy.app.version[0]*100 + bpy.app.version[1]
        
    print("loading...")
    print(str(filepath))
    
    folder = os.path.split(filepath)[0]
    meshfilename = os.path.split(filepath)[1].lower()    
    name = "mesh"
    files = []
    materialFile = "None"
    
    print(ogreXMLconverter)
    if(ogreXMLconverter is not None):
        # convert MESH and SKELETON file to MESH.XML and SKELETON.XML respectively
        for filename in os.listdir(folder):
            # we're going to do string comparisons. assume lower case to simplify code
            filename = os.path.join(folder, filename.lower())
            # process .mesh and .skeleton files while skipping .xml files
            if (".mesh" in filename) and (".xml" not in filename):
                os.system('%s "%s"' % (ogreXMLconverter, filename))
            
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
            CreateMesh(mesh_data, folder, name, materialFile, filepath)
            if not keep_xml:
                # cleanup by deleting the XML file we created
                os.unlink("%s" % filename)
    
    print("done.")
    return {'FINISHED'}
 
#load(0, bpy.context, "D:\stuff\Torchlight_modding\org_models\Alchemist\Alchemist.MESH.xml")
#load(0, bpy.context, "D:\stuff\Torchlight_modding\org_models\Shields_03\Shields_03.MESH.xml")