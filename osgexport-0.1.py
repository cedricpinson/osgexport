#!BPY
""" Registration info for Blender menus: <- these words are ignored
Name: 'OpenSceneGraph (.osg)'
Blender: 246
Group: 'Export'
Tip: 'Export to OpenSceneGraph (.osg) format.'
"""

__author__ = "Cedric Pinson, Ruben Lopez"
__url__ = ("Project homepage, http://www.plopbyte.net/")
__version__ = "0.1"
__email__ = "mornifle@plopbyte.net"
__bpydoc__ = """\

Description: Exports a ASCII OpenSceneGraph file from a Blender scene.

"""
#######################################################################
# Copyright (C) 2008 Cedric Pinson <mornifle@plopbyte.net>
#
# This script is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# You can read the GNU General Public License at http://www.gnu.org
#
#######################################################################
# Copyright (C) 2002-2006 Ruben Lopez <ryu@gpul.org>
#
# This script is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# You can read the GNU General Public License at http://www.gnu.org
#
# Description:
# This script allows you to model in blender and export your models for
# use in realtime OSG applications.
#
# Start this script with ALT+P
#
# Check README.txt for details
#
#######################################################################

import Blender
from Blender import Scene, Object, Window
from Blender import BGL
from Blender.BGL import *
from Blender import Draw
from Blender.Draw import *
from Blender import NMesh
from Blender import Types, Ipo
from math import sin, cos, pi
from sys import exit


def defaultKeyRegistryOSG():
    keys = dict()
    keys['path'] = "./output.osg"
    keys['do_ambient'] = 0
    keys['ambient_ratio'] = 0.5
    keys['do_texmat'] = 0
    keys['color1'] = (.7,.7,.7)
    keys['color2'] = (.3,.3,.3)
    return keys

#######################################################################
######### Class OSG: Allows creating the different OSG nodes ##########
#######################################################################
class OSG:

    def __init__(self, *args, **kwargs):
        self.registry = kwargs.get("osg",defaultKeyRegistryOSG())


    def makeRef(self, refUniqueID):
        return ["  Use %s" % refUniqueID.replace(" ","_")]

#######################################################################
    def makeNodeContents(self, name, uniqueID):
        text = ["  UniqueID \"%s\"" % (uniqueID.replace(" ","_")),
                "  DataVariance DYNAMIC",
                "  name \"%s\"" % (name),
                "  cullingActive TRUE"]
        return text

#######################################################################
    def makeGroupContents(self, name, uniqueID, children):
        text = self.makeNodeContents(name, uniqueID)
        text.append("  num_children %d" % (len(children)))
        for child in children:
            text = text + child
        return text

#######################################################################
    def makeGroup(self, name, uniqueID, children):
        text = ["Group {"]
        text = text + self.makeGroupContents(name, uniqueID, children)
        text.append("}")
        return text

#######################################################################
    def makeSwitch(self, name, uniqueID, children, values):
        text = ["Switch {",
                "  ValueList {"]
        text = text + values
        text.append("  }")
        text = text + self.makeGroupContents(name, uniqueID, children)
        text.append("}")
        return text

#######################################################################
    def makeSequence(self, name, uniqueID, children, times, loopMode):
        text = ["Sequence {",
                "  frameTime {"]
        text = text + times
        text.append("  }")

        text.append("  interval %s 0 %s" % (loopMode, (len(children)-1)))
        text.append("  duration 1 -1")
        text.append("  mode START")

        text = text + self.makeGroupContents(name, uniqueID, children)
        text.append("}")
        return text

#######################################################################
    def makeMatrixTransform(self, name, uniqueID, children, matrix):
        text = ["MatrixTransform {",
                "  StateSet { 0xba1 ON }",
                "  Matrix {",
                "    DataVariance DYNAMIC",
                "    %s %s %s %s" % (matrix[0][0], matrix[0][1],
                                     matrix[0][2], matrix[0][3]),
                "    %s %s %s %s" % (matrix[1][0], matrix[1][1],
                                     matrix[1][2], matrix[1][3]),
                "    %s %s %s %s" % (matrix[2][0], matrix[2][1],
                                     matrix[2][2], matrix[2][3]),
                "    %s %s %s %s" % (matrix[3][0], matrix[3][1],
                                     matrix[3][2], matrix[3][3]),
                "  }"]
        text = text + self.makeGroupContents(name, uniqueID, children)
        text.append("}")
        return text
#######################################################################
    def makeAnimationPathTransform(self, name, uniqueID, children, animCallback):
        text = ["MatrixTransform {",
                "  StateSet { 0xba1 ON }",
                "  UpdateCallbacks {"]
        text = text + animCallback
        text.append("  }")
        text = text + self.makeGroupContents(name, uniqueID, children)
        text.append("}")
        return text

#######################################################################
    def makeMaterial(self, material):
        text=[]
        text.append("      Material {")
        text.append("        DataVariance STATIC")
        text.append("        ColorMode OFF")
        text.append("        diffuseColor %s %s %s %s" % (material.R,\
                                                          material.G,\
                                                          material.B,\
                                                          material.alpha))
        # Blender doesn't have a concept of Ambient color in its lighting model
        # or user interface, but it's often important for OSG/OpenGL rendering.
        # If we just omit it, OSG will use default Ambient (grey).  This gives the
        # user a chance to assume that Ambient is a reduced brightness version of Diffuse.
        if self.registry['do_ambient'] == 1:
            ratio = d['ambient_ratio']
            text.append("        ambientColor %s %s %s %s" % (material.R * ratio,\
                                                                material.G * ratio,\
                                                                material.B * ratio,\
                                                                1))
        text.append("        specularColor %s %s %s %s" % (material.specCol[0],\
                                                                 material.specCol[1],\
                                                                 material.specCol[2],\
                                                                 1))
        text.append("        emissionColor %s %s %s %s" % (material.R*material.emit,\
                                                                 material.G*material.emit,\
                                                                 material.B*material.emit,\
                                                                 1))
        text.append("        shininess %s" % str((material.getHardness()-1) / 255.0 * 128))
        text.append("      }")
        return text

#######################################################################
    def makeTexture(self, texture):
        text=["      textureUnit 0 {",
              "        GL_TEXTURE_2D ON",
              "        Texture2D {",
              "          DataVariance STATIC",
              "          file \"%s\"" % texture,
              "          wrap_s REPEAT",
              "          wrap_t REPEAT",
              "          wrap_r CLAMP",
              "          min_filter LINEAR_MIPMAP_LINEAR",
              "          mag_filter LINEAR",
              "          maxAnisotropy 1",
              "          internalFormatMode USE_IMAGE_DATA_FORMAT",
              "        }",
              "      }"]
        # Textured surfaces also need a material, so that they can be lit.
        # Without a material, OpenGL can't know how to light it.  These values
        # are exposed in the exporter UI to let the user choose what works best
        # for their needs.
        if self.registry['do_texmat'] == 1:
            text.append("      Material {")
            text.append("        DataVariance STATIC")
            text.append("        ColorMode OFF")
            text.append("        diffuseColor %.3f %.3f %.3f 1" % self.registry['color1'])
            text.append("        ambientColor %.3f %.3f %.3f 1" % self.registry['color2'])
            text.append("      }")
        return text

#######################################################################
    def makeStateSet(self, uniqueID, texture, materials):
        if (len(materials) and materials[0].alpha < 1.0):
            hint="TRANSPARENT_BIN"
            blend="ON"
        else:
            hint="OPAQUE_BIN"
            blend="OFF"

        text = ["    StateSet {",
                "      UniqueID %s" % uniqueID.replace(" ","_"),
                "      DataVariance STATIC",
                "      rendering_hint %s" % hint,
                "      GL_BLEND %s" % blend]
        if len(materials):
            text = text + self.makeMaterial(materials[0])
        if texture:
            text = text + self.makeTexture(texture)
        text.append("    }")
        return text

#######################################################################
    def makeGeode(self, name, uniqueID, vertices, faces, stateSet, hasTcoords):
        text=["Geode {"];
        text = text + self.makeNodeContents(name, uniqueID)
        text.append("  num_drawables 1")
        text.append("  Geometry {")
        text = text + stateSet

        [result,mapping] = self.calcVertices(faces,vertices,hasTcoords)
        self.vertexMapping = (result, mapping)
        text = text + self.makeVertices(vertices, result)
        text = text + self.makeFaces(faces, result, mapping, hasTcoords)
        text.append("  }")
        text.append("}")
        return text

#######################################################################
    def compVertices(self, face1, vert1, face2, vert2):
        if (not face1.smooth) or (not face2.smooth): return 0
        if (len(face1.uv) != len(face2.uv)): return 0
        if (len(face1.col) != len(face2.col)): return 0

        if (len(face1.uv) == len(face1.v)):
            if face1.uv[vert1][0] != face2.uv[vert2][0]: return 0
            if face1.uv[vert1][1] != face2.uv[vert2][1]: return 0
        if (len(face1.col) == len(face1.v)):
            if face1.col[vert1].r != face2.col[vert2].r: return 0
            if face1.col[vert1].g != face2.col[vert2].g: return 0
            if face1.col[vert1].b != face2.col[vert2].b: return 0
            if face1.col[vert1].a != face2.col[vert2].a: return 0
        return 1

    # Calculates OSG vertices based on blender vertices and blender faces.
    # duplicates vertices that have different per-face properties
#######################################################################
    def calcVertices(self, faces, vertices, hasTcoords):
        result=[] # list of osg vertices
        mapping=[] # internal map, to find duplicates
        mapping_result=[] # resulting mapping [face][vertex] -> osg_vertex index
        for v in vertices:
            mapping.append([])

        curf=0
        vreal=0
        for face in faces:
            curv=0
            local_map = [] # osg indexes for each vertex
            for vertex in face.v:
                vindex = vertex.index
                found=0
                for f in mapping[vindex]:
                    if self.compVertices(face, curv, faces[f[0]], f[1]) == 1:
                        found=1
                        mapping[vindex].append([curf, curv, f[2]])
                        local_map.append(f[2])
                        break
                if found == 0:
                    mapping[vindex].append([curf, curv, vreal])
                    local_map.append(vreal)
                    if face.smooth: result.append([vindex, vertices[vindex].no])
                    else: result.append([vindex, face.no])
                    vreal = vreal + 1
                curv = curv + 1
            curf = curf + 1
            mapping_result.append(local_map)
        return [result,mapping_result]

#######################################################################
    def makeVertices(self, vertices, osg_vertices_normals):
        text=[]
        text.append("    VertexArray %s {" % len(osg_vertices_normals))
        for vertex_normal in osg_vertices_normals:
            coord=vertices[vertex_normal[0]].co
            text.append("      %s %s %s" %
                            (coord[0], coord[1], coord[2]))
        text.append("    }")
        text.append("    NormalBinding PER_VERTEX")
        text.append("    NormalArray %s {" % len(osg_vertices_normals))
        for vertex_normal in osg_vertices_normals:
            ncoord=vertex_normal[1]
            text.append("      %s %s %s" %
                            (ncoord[0], ncoord[1], ncoord[2]))
        text.append("    }")
        return text

#######################################################################
    def makeFaces(self, faces, vertices_osg, mapping, hasTcoords):
        if (len(faces) == 0):
            print "Probabily you were in edit mode when running the script, some object will be missing"
            return []
        text=[]
        nlin=0
        ntri=0
        nquad=0
        # counting number of lines, triangles and quads
        for face in faces:
            nv=len(face.v)
            if nv == 2:
                nlin = nlin + 1
            elif nv == 3:
                ntri = ntri + 1
            elif nv == 4:
                nquad = nquad + 1
            else:
                print "Se ignora una cara de %s vertices" % nv

        # counting number of primitives (one for lines, one for triangles and one for quads)
        numprims=0
        if (nlin > 0):
            numprims = numprims + 1
        if (ntri > 0):
            numprims = numprims + 1
        if (nquad > 0):
            numprims = numprims + 1

        # Now we write each primitive
        text.append("    PrimitiveSets %s {" % numprims)
        if nlin > 0:
            text.append("      DrawElementsUInt LINES %s {" % nlin)
            nface=0
            for face in faces:
              vlist=face.v
              nv=len(vlist)
              if nv == 2:
                  text.append("        %s %s" % (mapping[nface][0],mapping[nface][1]))
              nface = nface + 1
            text.append("      }")
        if ntri > 0:
            text.append("      DrawElementsUInt TRIANGLES %s {" % ntri)
            nface=0
            for face in faces:
              vlist=face.v
              nv=len(vlist)
              if nv == 3:
                  text.append("        %s %s %s" % (mapping[nface][0],mapping[nface][1],mapping[nface][2]))
              nface = nface + 1
            text.append("      }")
        if nquad > 0:
            text.append("      DrawElementsUInt QUADS %s {" % nquad)
            nface=0
            for face in faces:
              vlist=face.v
              nv=len(vlist)
              if nv == 4:
                  text.append("        %s %s %s %s" % (mapping[nface][0],mapping[nface][1],mapping[nface][2],mapping[nface][3]))
              nface = nface + 1
            text.append("      }")
        text.append("    }")

        if hasTcoords:
            text.append("    TexCoordArray 0 Vec2Array %s {" % len(vertices_osg))
            # Calculating per-vertex texture coordinates
            tc=[]
            for v in vertices_osg:
              tc.append( (0,0) )

            curface=0
            for face in faces:
                curv=0
                if (len(face.uv) == len(face.v)):
                    for vertex in face.v:
                        if (curv < 4):
                            tc[ mapping[curface][curv] ] = face.uv[curv]
                        curv = curv + 1
                curface = curface + 1

            for t in tc:
                text.append("      %s %s" % (t[0], t[1]))
            text.append("    }")

        if faces[0].col:
            text.append("    ColorBinding PER_VERTEX")
            text.append("    ColorArray Vec4Array %s {" % len(vertices_osg))
            # Calculating per-vertex colors
            vc=[]
            for v in vertices_osg:
              vc.append( NMesh.Col(0,0,0,0) )

            curface=0
            for face in faces:
                curv=0
                if (len(face.col) >= len(face.v)):
                    for vertex in face.v:
                        if (curv < 4):
                            vc[ mapping[curface][curv] ] = face.col[curv]
                        curv = curv + 1
                else:
                    print "%s aren't enough colors for %s vertices in one face!" % (len(face.col), len(face.v))
                curface = curface + 1

            for c in vc:
                text.append("      %s %s %s %s" %
                                    (c.r/255.0, c.g/255.0, c.b/255.0, c.a/255.0))
            text.append("    }")
        return text

#######################################################################
    def writeNode(self, node, file):
        for i in node:
            file.write("%s\n"%i)

#######################################################################
#######################################################################
#######################################################################
class Animation:
    def __init__(self, defpos, defrot, defscale, fps):
        self.points = {}
        self.defpoint=[defpos[0], defpos[1], defpos[2], defrot[0], defrot[1], defrot[2], defscale[0], defscale[1], defscale[2]]
        self.fps = fps

#######################################################################
    def add(self, type, tval, val):
        if self.points.has_key(tval):
            cpoint=self.points[tval]
        else:
            cpoint=[0,0,0,0,0,0,0,0,0]
            cpoint[0:9]=self.defpoint
        cpoint[type]=val
        self.points[tval]=cpoint
#######################################################################
    def makeCallback(self):
        text=[]
        text.append("        AnimationPathCallback {")
        text.append("            DataVariance DYNAMIC")
        text.append("            AnimationPath {")
        text.append("                DataVariance DYNAMIC")
        text.append("                LoopMode LOOP")
        text.append("                ControlPoints {")

        for p in self.points.keys():
            # Calculating euler -> quaternion
            # Blender has one unit for each 10 degrees
            heading=self.points[p][5]*pi/18
            pitch=self.points[p][4]*pi/18
            roll=self.points[p][3]*pi/18
            c1=cos(heading/2)
            c2=cos(pitch/2)
            c3=cos(roll/2)
            s1=sin(heading/2)
            s2=sin(pitch/2)
            s3=sin(roll/2)
            w=c1*c2*c3+s1*s2*s3
            x=c1*c2*s3-s1*s2*c3
            y=c1*s2*c3+s1*c2*s3
            z=s1*c2*c3-c1*s2*s3
            text.append("                    %s %s %s %s %s %s %s %s %s %s %s" %
                (p/self.fps,self.points[p][0], self.points[p][1], self.points[p][2],
                 x,y,z,w,
                 self.points[p][6], self.points[p][7], self.points[p][8]))

        text.append("                }")
        text.append("            }")
        text.append("        }")
        return text

#######################################################################
#######################################################################
#######################################################################
class OSGExport:
    scene = None
    strLoopMode = None

#######################################################################
    def __init__(self, filename, daScene, loopMode, meshAnim, fps, objects, **kwargs):
        self.file = open(filename, "w")
        self.scene = daScene
        self.doStaticAnimation = 0
        self.doMeshAnimation = 0
        self.doAnimationPath = 0

        self.mFrameStart = daScene.getRenderingContext().startFrame()
        self.mFrameEnd = daScene.getRenderingContext().endFrame()
        self.mFrameCount = self.mFrameEnd - self.mFrameStart + 1
        self.objects = []
        self.fps = fps
        self.osg = OSG( **kwargs)
        # Use only meshes
        for object in objects:
            if (object.getType() == 'Mesh') or (object.getType() == 'Empty'):
                self.objects.append(object)

        if loopMode == 2:
            self.strLoopMode = "SWING"
        else:
            self.strLoopMode = "LOOP"

        if meshAnim == 1:
            self.doAnimationPath = 1
        if meshAnim == 2:
            self.doStaticAnimation = 1
        if meshAnim == 3:
            self.doMeshAnimation = 1

# A Function to indicate whether the specified object
# should (1) use a per-frame mesh object, or (0) a single mesh
# for the entire animation.
#######################################################################
    def doMeshAnim(self, object):
        if self.doMeshAnimation == 0:
            return 0
        if object.getType() != "Mesh":
            return 0
        parent = object.getParent()
        if not parent:
            return 0
        if not parent.getType() == "Armature":
            return 0
        return 1
        
    

#######################################################################
    def isSupported(self, object):
        return (object.getType() == 'Mesh' or object.getType() == 'Empty')

#######################################################################
    def export(self):
        if self.doAnimationPath:
            root = self.exportPaths()
        else:
            root = self.exportFrames()
	Window.DrawProgressBar( 0.0, "Writing file")
        self.osg.writeNode(root,self.file)
        self.file.close()

#######################################################################
    def exportPaths(self):
        roots = []
	curObj = 1
	Window.DrawProgressBar( 0.0, "Exporting scene")
        for object in self.objects:
	    Window.DrawProgressBar( curObj*(1.0/len(self.objects)), "Exporting objects %d/%d" % (curObj,len(self.objects)))
            if (not object.getParent()) or (not self.isSupported(object.getParent())):
                roots.append(self.recursePaths(object))
	    curObj+=1
        return self.osg.makeGroup("Blender root", "BlenderRoot", roots)

#######################################################################
    def createGeode(self, object, uniqueID):
        mesh=object.getData()
        # Find a texture and create the stateset
        texture = None
        for f in mesh.faces:
            print f.image
            if f.image != None:
                #texture = f.image.name;brea
                texture = Blender.sys.expandpath(f.image.filename).replace(" ","_");break #access to the full pathnam
                #texture = Blender.sys.basename(f.image.filename);break #access to the filenam
        stateSet = self.osg.makeStateSet(object.getName()+"_stateset", texture, mesh.materials)
        # Create the geode
        return self.osg.makeGeode(object.getName()+"_geode",
                                  uniqueID,
                                  mesh.verts, mesh.faces,
                                  stateSet, (texture != None))

#######################################################################
    def recursePaths(self, object):
        # Calculate the matrix of this object
        if not object.getParent():
            matrix = object.getMatrix()
        else:
            parentInverse = object.getParent().getInverseMatrix()
            accumulated = object.getMatrix()
            # Trick to create a new Matrix
            matrix = object.getInverseMatrix()
            self.multMatrixes(parentInverse, accumulated, matrix)

        # Create my children
        children=[]
        if object.getType() == 'Mesh':
            children.append(self.createGeode(object,object.getName()+"_geode"))
        for ob in self.objects:
            if ob.getParent():
                if (ob.getParent().getName() == object.getName()):
                    #then ob is a child of this object.
                    children.append(self.recursePaths(ob))
        # Create an animation or a plain matrix transform depending on IPO
        if object.ipo:
            animation = self.processAnimation(object.ipo, object.loc, object.rot, object.size)
            return self.osg.makeAnimationPathTransform(object.getName(), object.getName(), children, animation)
        else:
            return self.osg.makeMatrixTransform(object.getName(), object.getName(), children, matrix)

#######################################################################
    def exportFrames(self):
        children=[]
        times=[]
        if self.fps==1:
            delay="1"
        else:
            delay = "0.%03d" % (1000/self.fps)
        i = self.scene.getRenderingContext().startFrame()
        frameCount = self.scene.getRenderingContext().endFrame() - i + 1
        #self.writeSequenceHeader(frameCount, self.fps)
	Window.DrawProgressBar( 0.0, "Exporting frames")
        while i<=self.scene.getRenderingContext().endFrame():
	    Window.DrawProgressBar( (i-self.scene.getRenderingContext().startFrame())*(1.0/frameCount), "Exporting frame %d" % i)
            self.scene.getRenderingContext().currentFrame(i)
            self.scene.update(1)
            Window.RedrawAll()
            children.append(self.composeFrame(i))
            times.append(delay)
            i = i + 1
        return self.osg.makeSequence("Frames",
                                     "__Frames_sequence",
                                     children,
                                     times,
                                     self.strLoopMode)

#######################################################################
    def composeFrame(self, frame):
        children=[]
        for object in self.objects:
            if (not object.getParent()) or (not self.isSupported(object.getParent())):
                children.append(self.recurseFrame(object, frame))
        return self.osg.makeGroup("frame%d"%frame, "frame%d"%frame,children)

#######################################################################
    def recurseFrame(self, object, frame):
        # Calculate the matrix of this object
        if not object.getParent():
            matrix = object.getMatrix()
        else:
            parentInverse = object.getParent().getInverseMatrix()
            accumulated = object.getMatrix()
            # Trick to create a new Matrix
            matrix = object.getInverseMatrix()
            self.multMatrixes(parentInverse, accumulated, matrix)

        children=[]
        # My mesh
        if object.getType() == 'Mesh':
            if self.doMeshAnim(object):
                children.append(self.createGeode(object, "%s.%s" % (object.getName(), frame)))
            else:
                if frame > 1:
                    children.append(self.osg.makeRef(object.getName()+"_geode"))
                else:
                    children.append(self.createGeode(object, object.getName()+"_geode"))
        # My children
        for ob in self.objects:
            if ob.getParent():
                if (ob.getParent().getName() == object.getName()):
                    #then ob is a child of this object.
                    children.append(self.recurseFrame(ob,frame))
        return self.osg.makeMatrixTransform(object.getName(), object.getName(), children, matrix)

#######################################################################
    def multMatrixes(self, matrixA, matrixB, matrixR):
        for y in (0,1,2,3):
            for x in (0,1,2,3):
                matrixR[y][x] =( matrixA[0][x] * matrixB[y][0] +
                                 matrixA[1][x] * matrixB[y][1] +
                                 matrixA[2][x] * matrixB[y][2] +
                                 matrixA[3][x] * matrixB[y][3]
                               )
        
#######################################################################
    def processAnimation(self, ipo, defpos, defrot, defscale):
        anim=Animation(defpos,defrot,defscale, self.fps)
        curves = ipo.getCurves()
        for curve in curves:
          if curve.getName() == "LocX":
            for bp in curve.getPoints():
              anim.add(0,bp.pt[0],bp.pt[1])
          elif curve.getName() == "LocY":
            for bp in curve.getPoints():
              anim.add(1,bp.pt[0],bp.pt[1])
          elif curve.getName() == "LocZ":
            for bp in curve.getPoints():
              anim.add(2,bp.pt[0],bp.pt[1])
          elif curve.getName() == "RotX":
            for bp in curve.getPoints():
              anim.add(3,bp.pt[0],bp.pt[1])
          elif curve.getName() == "RotY":
            for bp in curve.getPoints():
              anim.add(4,bp.pt[0],bp.pt[1])
          elif curve.getName() == "RotZ":
            for bp in curve.getPoints():
              anim.add(5,bp.pt[0],bp.pt[1])
          elif curve.getName() == "SizeX":
            for bp in curve.getPoints():
              anim.add(6,bp.pt[0],bp.pt[1])
          elif curve.getName() == "SizeY":
            for bp in curve.getPoints():
              anim.add(7,bp.pt[0],bp.pt[1])
          elif curve.getName() == "SizeZ":
            for bp in curve.getPoints():
              anim.add(8,bp.pt[0],bp.pt[1])
        return anim.makeCallback()


#######################################################################
#######################################################################
#######################################################################
#Main script
if __name__ == "__main__":
    # If the user wants to run in "batch" mode, assume that ParseArgs
    # will correctly set atkconf data and go.
    if osg.ParseArgs(sys.argv):
        OpenSceneGraphExport(osg.osgconf.FILENAME)
        Blender.Quit()

    # Otherwise, let the atkcgui module take over.
    else:
        # do it yourself
        pass
