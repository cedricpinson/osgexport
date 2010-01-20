# -*- python-indent: 4; coding: iso-8859-1; mode: python -*-
# Copyright (C) 2008 Cedric Pinson, Jeremy Moles
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#  Cedric Pinson <cedric.pinson@plopbyte.net>
#  Jeremy Moles <jeremy@emperorlinux.com>


import Blender
import Blender.Mathutils
import os
from osglog import log


Matrix    = Blender.Mathutils.Matrix
Vector    = Blender.Mathutils.Vector
FLOATPRE  = 5
CONCAT    = lambda s, j="": j.join(str(v) for v in s)
STRFLT    = lambda f: "%%.%df" % FLOATPRE % float(f)
INDENT    = 2


def findNode(name, root):
    if root.name == name:
        return root
    if isinstance(root, Group) is False:
        return None
    for i in root.children:
        found = findNode(name, i)
        if found is not None:
            return found
    return None

def findMaterial(name, root):
    if root.stateset is not None:
        for i in root.stateset.attributes:
            if isinstance(i, Material) is True and i.name == name:
                return i
    if isinstance(root, Geode) is True:
        for i in root.drawables:
            found = findMaterial(name, i)
            if found is not None:
                return found
    if isinstance(root, Group) is True:
        for i in root.children:
            found = findMaterial(name, i)
            if found is not None:
                return found
    return None


class Writer(object):
    instances = {}
    wrote_elements = {}

    def __init__(self, comment = None):
        object.__init__(self)
        self.comment = comment
        self.indent_level = 0
        self.counter = len(Writer.instances)
        Writer.instances[self] = True

    def __repr__(self):
        ret = ""
#        text = self.ascii().replace("\t", "").replace("#", (" " * INDENT)).replace("$", (" " * (INDENT*self.indent_level) ))
        text = Writer.writeInstanceOrUseIt(self).replace("\t", "").replace("#", (" " * INDENT)).replace("$", (" " * (INDENT*self.indent_level) ))
        return ret + text

    def __str__(self):
        return self.__repr__()

    @staticmethod
    def resetWriter():
        Writer.instances = {}
        wrote_elements = {}

    @staticmethod
    def writeInstanceOrUseIt(obj):
        if Writer.wrote_elements.has_key(obj) and obj.shadow_object is not None:
            return obj.shadow_object.ascii()
        Writer.wrote_elements[obj] = True
        return obj.ascii()

class ShadowObject(Writer):
    def __init__(self, *args, **kwargs):
        Writer.__init__(self, *args, **kwargs)
        self.target = args[0]
    
    def ascii(self):
        text = "$Use " + self.target.generateID() + "\n"
        return text


class Object(Writer):
    
    def __init__(self, *args, **kwargs):
        Writer.__init__(self, *args)
        self.shadow_object = ShadowObject(self)
        self.dataVariance = "UNKNOWN"
        self.name = kwargs.get('name', "None")

    def copyFrom(self, obj):
        self.name = obj.name
        self.dataVariance = obj.dataVariance

    def generateID(self):
        return "uniqid_" + self.className() + "_" + str(self.counter)

    def setName(self, name):
        self.name = name

    def className(self):
        return "Object"

    def printContent(self):
        id = self.generateID()
        text = ""
        if id is not None:
            text += "$#UniqueID " + self.generateID() + "\n"
        if self.dataVariance is not "UNKNOWN":
            text += "$#DataVariance " + self.dataVariance + "\n"
        if self.name is not "None":
            text += "$#name \"%s\"\n" % self.name
        return text

class UpdateMatrixTransform(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.stacked_transforms = []

    def className(self):
        return "UpdateMatrixTransform"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text =""
        for s in self.stacked_transforms:
            s.indent_level = self.indent_level + 1
            text += str(s)
        return text

class UpdateMaterial(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)

    def className(self):
        return "UpdateMaterial"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += "$}\n"
        return text

class StackedMatrixElement(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        if self.name == "None":
            self.name = "matrix"
        self.matrix = kwargs.get('matrix', Matrix().resize4x4().identity())

    def className(self):
        return "StackedMatrixElement"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += self.printContent()
        text += "$}\n"
        return text

    def generateID(self):
        return None

    def printContent(self):
        text = "$#Matrix {\n"
        for i in range(0,4):
            text += "$##%s %s %s %s\n" % (STRFLT(self.matrix[i][0]), STRFLT(self.matrix[i][1]),STRFLT(self.matrix[i][2]), STRFLT(self.matrix[i][3]))
        text += "$#}\n"
        return text

class StackedTranslateElement(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.translate = Vector(0,0,0)
        self.name = "translate"

    def className(self):
        return "StackedTranslateElement"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += "$}\n"
        return text

    def generateID(self):
        return None

    def printContent(self):
        text = "$#translate %s %s %s\n" % (STRFLT(self.translate[0]), STRFLT(self.translate[1]),STRFLT(self.translate[2]))
        return text

class StackedScaleElement(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.scale = Vector(1,1,1)
        self.name = "scale"

    def className(self):
        return "StackedScaleElement"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += "$}\n"
        return text

    def generateID(self):
        return None

    def printContent(self):
        text = "$#scale %s %s %s\n" % (STRFLT(self.scale[0]), STRFLT(self.scale[1]),STRFLT(self.scale[2]))
        return text

class StackedRotateAxisElement(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.axis = kwargs.get('axis', Vector(1,0,0))
        self.angle = kwargs.get('angle', 0)

    def className(self):
        return "StackedRotateAxisElement"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += "$}\n"
        return text

    def generateID(self):
        return None

    def printContent(self):
        text = "$#axis %s %s %s\n" % (STRFLT(self.axis[0]), STRFLT(self.axis[1]),STRFLT(self.axis[2]))
        text = "$#angle %s\n" % (STRFLT(self.angle))
        return text

class StackedQuaternionElement(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.quaternion = Matrix().resize4x4().identity().toQuat()
        self.name = "quaternion"

    def className(self):
        return "StackedQuaternionElement"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += "$}\n"
        return text

    def generateID(self):
        return None

    def printContent(self):
        text = "$#quaternion %s %s %s %s\n" % (STRFLT(self.quaternion.x(), STRFLT(self.quaternion.y()),STRFLT(self.quaternion.z()),STRFLT(self.quaternion.w()) ))
        return text

class UpdateBone(UpdateMatrixTransform):
    def __init__(self, *args, **kwargs):
        UpdateMatrixTransform.__init__(self, *args, **kwargs)

    def className(self):
        return "UpdateBone"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += UpdateMatrixTransform.printContent(self)
        text += "$}\n"
        return text


class UpdateSkeleton(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)

    def className(self):
        return "UpdateSkeleton"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += "$}\n"
        return text

class Node(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.cullingActive = "TRUE"
        self.stateset = None
        self.update_callbacks = []

    def className(self):
        return "Node"

    def makeRef(self, refUniqueID):
        self.uniqueID = refUniqueID

    def makeNodeContents(self, name, uniqueID):
        self.name = name
        self.uniqueID = uniqueID

    def ascii(self):
        text = "$Node {\n"
        text += Object.printContent(self)
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = "$#cullingActive " + self.cullingActive  + "\n"
        if self.stateset is not None:
            self.stateset.indent_level = self.indent_level + 1
            text += str(self.stateset)
        if len(self.update_callbacks) > 0:
            text += "$#UpdateCallbacks {\n"
            for i in self.update_callbacks:
                i.indent_level = self.indent_level + 2
                text += str(i)
            text += "$#}\n"
        return text

class Geode(Node):
    def __init__(self, *args, **kwargs):
        Node.__init__(self, *args, **kwargs)
        self.drawables = []

    def setName(self, name):
        self.name = self.className() + name

    def className(self):
        return "Geode"

    def ascii(self):
        text = "$Geode {\n"
        text += Object.printContent(self)
        text += Node.printContent(self)
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = "$#num_drawables %d" % (len(self.drawables))  + "\n"
        for i in self.drawables:
            if i is not None:
                i.indent_level = self.indent_level + 1
                text += str(i)
        return text

class Group(Node):
    def __init__(self, *args, **kwargs):
        Node.__init__(self, *args, **kwargs)
        self.children = []

    def className(self):
        return "Group"

    def ascii(self):
        text = "$Group {\n"
        text += Object.printContent(self)
        text += Node.printContent(self)
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = "$#num_children %d" % (len(self.children)) + "\n"
        for i in self.children:
            i.indent_level = self.indent_level + 1
            text += str(i)
        return text

class MatrixTransform(Group):
    def __init__(self, *args, **kwargs):
        Group.__init__(self, *args, **kwargs)
        self.matrix = Matrix().resize4x4().identity()
    
    def className(self):
        return "MatrixTransform"

    def ascii(self):
        text = "$MatrixTransform {\n"
        text += Object.printContent(self)
        text += Node.printContent(self)
        text += self.printContent()
        text += Group.printContent(self)
        text += "$}\n"
        return text

    def printContent(self):
        text = "$#Matrix {\n"
        for i in range(0,4):
            text += "$##%s %s %s %s\n" % (STRFLT(self.matrix[i][0]), STRFLT(self.matrix[i][1]),STRFLT(self.matrix[i][2]), STRFLT(self.matrix[i][3]))
        text += "$#}\n"
        return text


class StateAttribute(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.update_callbacks = []

    def className(self):
        return "StateAttribute"

    def printContent(self):
        text = Object.printContent(self)
        if len(self.update_callbacks) > 0:
            text += "$#UpdateCallback {\n"
            for i in self.update_callbacks:
                i.indent_level = self.indent_level + 2
                text += str(i)
            text += "$#}\n"
        return text

class StateTextureAttribute(StateAttribute):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.unit = 0

    def className(self):
        return "StateTextureAttribute"

    def printContent(self):
        text = Object.printContent(self)
        return text

class Light(StateAttribute):
    def __init__(self, *args, **kwargs):
        StateAttribute.__init__(self, *args, **kwargs)
        self.light_num = 0
        self.ambient = (0.05, 0.05, 0.05, 1.0)
        self.diffuse = (0.8, 0.8, 0.8, 1.0)
        self.specular = (1.0, 1.0, 1.0, 1.0)
        self.position = (0.0, 0.0, 1.0, 0.0)
        self.direction = (0.0, 0.0, -1.0)
        self.spot_exponent = 0.0
        self.spot_cutoff = 180.0
        self.constant_attenuation = 1.0
        self.linear_attenuation = 0.0
        self.quadratic_attenuation = 0.0

    def className(self):
        return "Light"

    def generateID(self):
        return None

    def ascii(self):
        text = "$%s {\n" % self.className()
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = Object.printContent(self)
        text += "$#light_num %s\n" % self.light_num
        text += "$#ambient %s %s %s %s\n" % (STRFLT(self.ambient[0]), STRFLT(self.ambient[1]), STRFLT(self.ambient[2]), STRFLT(self.ambient[3]))
        text += "$#diffuse %s %s %s %s\n" % (STRFLT(self.diffuse[0]), STRFLT(self.diffuse[1]), STRFLT(self.diffuse[2]), STRFLT(self.diffuse[3]))
        text += "$#specular %s %s %s %s\n" % (STRFLT(self.specular[0]), STRFLT(self.specular[1]), STRFLT(self.specular[2]), STRFLT(self.specular[3]))
        text += "$#position %s %s %s %s\n" % (STRFLT(self.position[0]), STRFLT(self.position[1]), STRFLT(self.position[2]), STRFLT(self.position[3]))

        text += "$#direction %s %s %s\n" % (STRFLT(self.direction[0]), STRFLT(self.direction[1]), STRFLT(self.direction[2]))

        text += "$#constant_attenuation %s\n" % STRFLT(self.constant_attenuation)
        text += "$#linear_attenuation %s\n" % STRFLT(self.linear_attenuation)
        text += "$#quadratic_attenuation %s\n" % STRFLT(self.quadratic_attenuation)

        text += "$#spot_exponent %s\n" % STRFLT(self.spot_exponent)
        text += "$#spot_cutoff %s\n" % STRFLT(self.spot_cutoff)

        return text

class LightSource(Group):
    def __init__(self, *args, **kwargs):
        Group.__init__(self, *args, **kwargs)
        self.light = Light()
        self.cullingActive = "FALSE"

    def className(self):
        return "LightSource"

    def ascii(self):
        text = "$%s {\n" % self.className()
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = Object.printContent(self)
        text += Node.printContent(self)
        if self.light is not None:
            self.light.indent_level = self.indent_level + 1
            text += str(self.light)
        text += Group.printContent(self)
        return text
    

class Texture2D(StateTextureAttribute):
    def __init__(self, *args, **kwargs):
        StateTextureAttribute.__init__(self, *args, **kwargs)
        self.source_image = None
        self.file = "none"
        self.wrap_s = "REPEAT"
        self.wrap_t = "REPEAT"
        self.wrap_r = "REPEAT"
        self.min_filter = "LINEAR_MIPMAP_LINEAR"
        self.mag_filter = "LINEAR"
        self.internalFormatMode = "USE_IMAGE_DATA_FORMAT"

    def className(self):
        return "Texture2D"

    def ascii(self):
        text = "$GL_TEXTURE_2D ON\n"
        text += "$%s {\n" % self.className()
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = StateTextureAttribute.printContent(self)
        text += "$#file \"%s\"\n" % self.file
        text += "$#wrap_s %s\n" % self.wrap_s
        text += "$#wrap_t %s\n" % self.wrap_t
        text += "$#wrap_r %s\n" % self.wrap_r
        text += "$#min_filter %s\n" % self.min_filter
        text += "$#mag_filter %s\n" % self.mag_filter
        text += "$#internalFormatMode %s\n" % self.internalFormatMode
        text += "$#subloadMode OFF\n"
        return text

class Material(StateAttribute):
    def __init__(self, *args, **kwargs):
        StateAttribute.__init__(self, *args, **kwargs)
        self.colormode = "OFF"
        self.emission = (0.0, 0.0, 0.0, 1.0)
        self.ambient = (0.2, 0.2, 0.2, 1.0)
        self.diffuse = (0.8, 0.8, 0.8, 1.0)
        self.specular = (0.0, 0.0, 0.0, 1.0)
        self.shininess = 0.0

    def className(self):
        return "Material"

    def ascii(self):
        text = "$%s {\n" % self.className()
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = StateAttribute.printContent(self)
        text += "$#ColorMode %s\n" % self.colormode
        text += "$#ambientColor %s %s %s %s\n" % (STRFLT(self.ambient[0]), STRFLT(self.ambient[1]), STRFLT(self.ambient[2]), STRFLT(self.ambient[3]))
        text += "$#diffuseColor %s %s %s %s\n" % (STRFLT(self.diffuse[0]), STRFLT(self.diffuse[1]), STRFLT(self.diffuse[2]), STRFLT(self.diffuse[3]))
        text += "$#specularColor %s %s %s %s\n" % (STRFLT(self.specular[0]), STRFLT(self.specular[1]), STRFLT(self.specular[2]), STRFLT(self.specular[3]))
        text += "$#emissionColor %s %s %s %s\n" % (STRFLT(self.emission[0]), STRFLT(self.emission[1]), STRFLT(self.emission[2]), STRFLT(self.emission[3]))
        text += "$#shininess %s\n" % STRFLT(self.shininess)
        return text

class LightModel(StateAttribute):
    def __init__(self, *args, **kwargs):
        StateAttribute.__init__(self, *args, **kwargs)
        self.local_viewer = "FALSE"
        self.color_control = "SEPARATE_SPECULAR_COLOR"
        self.ambient = (0.2, 0.2, 0.2, 1.0)

    def className(self):
        return "LightModel"

    def ascii(self):
        text = "$%s {\n" % self.className()
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = StateAttribute.printContent(self)
        text += "$#ambientIntensity %s %s %s %s\n" % (STRFLT(self.ambient[0]), STRFLT(self.ambient[1]), STRFLT(self.ambient[2]), STRFLT(self.ambient[3]))
        text += "$#colorControl %s\n" % self.color_control
        text += "$#localViewer %s\n" % self.local_viewer
        return text


class StateSet(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.modes = {}
        self.attributes = []
        self.texture_attributes = {}

    def className(self):
        return "StateSet"

    def ascii(self):
        text = "$%s {\n" % self.className()
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = Object.printContent(self)
        for i in self.modes.iteritems():
            if i is not None:
                text += "$#%s %s\n" %i
        for i in self.attributes:
            if i is not None:
                i.indent_level = self.indent_level + 1
                text += str(i)
        for (unit, attributes) in self.texture_attributes.items():
            if attributes is not None and len(attributes) > 0:
                text += "$#textureUnit %s {\n" % unit
                for a in attributes:
                    if a is not None:
                        a.indent_level = self.indent_level + 2
                        text += str(a)
                text += "$#}\n"
        return text

class ShadowVertexArrayObject(Writer):
    def __init__(self, *args, **kwargs):
        Writer.__init__(self)
        self.target = args[0]
        self.binding = None
    
    def ascii(self):
        text = ""
        if self.binding is not None:
            text += "$" + self.binding + "\n"
        text += "$" + self.target.className() + " Use " + self.target.generateID() + "\n"
        return text

class VertexArray(Writer):
    def __init__(self, *args, **kwargs):
        Writer.__init__(self)
        self.array = kwargs.get('array', [])
        self.shadow_object = ShadowVertexArrayObject(self, "Vec3Array")

    def className(self):
        return "VertexArray"

    def generateID(self):
        return self.className() + "_" + str(self.counter)

    def ascii(self):
        text = "$%s UniqueID %s Vec3Array %s\n${\n" % (self.className(), self.generateID(), str(len(self.array)))
        for i in self.array:
                text += "$#%s %s %s\n" % (STRFLT(i[0]), STRFLT(i[1]), STRFLT(i[2]))
        text += "$}\n"
        return text


class NormalArray(VertexArray):
    def __init__(self, *args, **kwargs):
        VertexArray.__init__(self, *args, **kwargs)
        self.shadow_object = ShadowVertexArrayObject(self, "Vec3Array")
        self.shadow_object.binding = "NormalBinding PER_VERTEX"

    def className(self):
        return "NormalArray"

    def ascii(self):
        text = "$NormalBinding PER_VERTEX\n"
        text += "$%s UniqueID %s Vec3Array %s\n${\n" % (self.className(), self.generateID(), len(self.array))
        for i in self.array:
                text += "$#%s %s %s\n" % (STRFLT(i[0]), STRFLT(i[1]), STRFLT(i[2]))
        text += "$}\n"
        return text

class ColorArray(VertexArray):
    def __init__(self, *args, **kwargs):
        VertexArray.__init__(self, *args, **kwargs)
        self.shadow_object = ShadowVertexArrayObject(self, "Vec4Array")
        self.shadow_object.binding = "ColorBinding PER_VERTEX"

    def className(self):
        return "ColorArray"

    def ascii(self):
        text = "$%s UniqueID %s Vec4Array %s\n${\n" % (self.className(), self.generateID(), len(self.array))
        for i in self.array:
                text += "$#%s %s %s %s\n" % (STRFLT(i[0]), STRFLT(i[1]), STRFLT(i[2]), STRFLT(i[3]))
        text += "$}\n"
        return text

class TexCoordArray(VertexArray):
    def __init__(self, *args, **kwargs):
        VertexArray.__init__(self, *args, **kwargs)
        self.index = 0
        self.shadow_object = ShadowVertexArrayObject(self, "Vec2Array")

    def className(self):
        return "TexCoordArray"

    def ascii(self):
        text = "$%s %s UniqueID %s Vec2Array %s\n${\n" % (self.className(), self.index, self.generateID(),  len(self.array))
        for i in self.array:
                text += "$#%s %s\n" % (STRFLT(i[0]), STRFLT(i[1]))
        text += "$}\n"
        return text

class DrawElements(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.indexes = []
        self.type = None
        self.shadow_object = None

    def getSizeArray(self):
        element = "DrawElementsUByte"
        for i in self.indexes:
            if i > 255 and element == "DrawElementsUByte":
                element = "DrawElementsUShort"
            elif i > 65535 and element == "DrawElementsUShort":
                element = "DrawElementsUInt"
                break
        return element

    def ascii(self):
        element = self.getSizeArray()

        text = "$#%s %s %s {\n" % (element, self.type, str(len(self.indexes)))
        n = 1
        if self.type == "TRIANGLES":
            n = 3
        if self.type == "QUADS":
            n = 4

        total = len(self.indexes) / n
        for i in range(0, total):
            text += "$##"
            for a in range(0,n):
                text += "%s " % self.indexes[i*n+a]
            text += "\n"
        text += "$#}\n"
        return text

    def className(self):
        return "DrawElements"
    
class Geometry(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.primitives = []
        self.vertexes = None
        self.normals = None
        self.colors = None
        self.uvs = {}
        self.stateset = None

    def className(self):
        return "Geometry"

    def copyFrom(self, geometry):
        Object.copyFrom(self, geometry)
        self.primitives = geometry.primitives
        self.vertexes = geometry.vertexes
        self.normals = geometry.normals
        self.colors = geometry.colors
        self.uvs = geometry.uvs
        self.stateset = geometry.stateset

    def ascii(self):
        text = "$%s {\n" % self.className()
        text += Object.printContent(self)
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = ""
        if len(self.primitives):
            text += "$#Primitives %s {\n" % (str(len(self.primitives)))
            for i in self.primitives:
                i.indent_level = self.indent_level + 1
                text += str(i)
            text += "$#}\n"
        if self.vertexes:
            self.vertexes.indent_level = self.indent_level + 1
            text += str(self.vertexes)
        if self.normals:
            self.normals.indent_level = self.indent_level + 1
            text += str(self.normals)
        if self.colors:
            self.colors.indent_level = self.indent_level + 1
            text += str(self.colors)
        for i in self.uvs.values():
            if i:
                i.indent_level = self.indent_level + 1
                text += str(i)
        if self.stateset is not None:
            self.stateset.indent_level = self.indent_level + 1
            text += str(self.stateset)
        return text

################################## animation node ######################################
class Bone(MatrixTransform):
    def __init__(self, skeleton = None, bone = None, parent=None, **kwargs):
        MatrixTransform.__init__(self, **kwargs)
        self.dataVariance = "DYNAMIC"
        self.parent = parent
        self.skeleton = skeleton
        self.bone = bone
        self.bone_matrix = {'BONESPACE': Matrix().resize4x4().identity() }

    def buildBoneChildren(self):
        if self.skeleton is None or self.bone is None:
            return
        
        self.setName(self.bone.name)
        update_callback = UpdateBone()
        update_callback.setName(self.name)
        self.update_callbacks.append(update_callback)

        self.bone_matrix['BONESPACE'] = self.bone.matrix['BONESPACE'].copy().resize4x4()

        if self.parent:
            parent_tail = self.parent.bone.tail['BONESPACE'] * self.parent.bone_matrix['BONESPACE'].rotationPart().copy().invert()
            parent_head = self.parent.bone.head['BONESPACE'] * self.parent.bone_matrix['BONESPACE'].rotationPart().copy().invert()

            pos = parent_tail - parent_head + self.bone.head['BONESPACE']

            self.bone_matrix['BONESPACE'][3][0] = pos[0]
            self.bone_matrix['BONESPACE'][3][1] = pos[1]
            self.bone_matrix['BONESPACE'][3][2] = pos[2]
            self.bone_matrix['ARMATURESPACE']   = self.bone_matrix['BONESPACE'] * self.parent.bone_matrix['ARMATURESPACE']

        else:
            pos = self.bone.head['BONESPACE']
            self.bone_matrix['BONESPACE'][3][0] = pos[0]
            self.bone_matrix['BONESPACE'][3][1] = pos[1]
            self.bone_matrix['BONESPACE'][3][2] = pos[2]
            self.bone_matrix['ARMATURESPACE']   = self.bone_matrix['BONESPACE'].copy()

        # add bind matrix in localspace callback
        update_callback.stacked_transforms.append(StackedMatrixElement(name = "bindmatrix", matrix = self.bone_matrix['BONESPACE'].copy()))
        update_callback.stacked_transforms.append(StackedTranslateElement())
        update_callback.stacked_transforms.append(StackedQuaternionElement())
        update_callback.stacked_transforms.append(StackedScaleElement())

        self.matrix = self.bone_matrix['BONESPACE'].copy()

        if not self.bone.hasChildren():
            return

        for boneChild in self.bone.children:
            b = Bone(self.skeleton, boneChild, self)
            self.children.append(b)
            b.buildBoneChildren()

    def collect(self, list):
        list.append(self)
        for boneChild in self.children:
            boneChild.collect(list)

    def className(self):
        return "Bone"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += Node.printContent(self)
        text += self.printContent()
        text += MatrixTransform.printContent(self)
        text += Group.printContent(self)
        text += "$}\n"
        return text

    def printContent(self):
        matrix = self.bone_matrix['ARMATURESPACE'].copy()
        matrix.invert()
        text = "$#InvBindMatrixInSkeletonSpace {\n"
        for i in range(0,4):
            text += "$##%s %s %s %s\n" % (STRFLT(matrix[i][0]), STRFLT(matrix[i][1]),STRFLT(matrix[i][2]), STRFLT(matrix[i][3]))
        text += "$#}\n"
        return text

        matrix = self.matrix['BONESPACE'].copy()
        text = "$#bindQuaternion %s %s %s %s\n" % (
            STRFLT(matrix.toQuat().x),
            STRFLT(matrix.toQuat().y),
            STRFLT(matrix.toQuat().z),
            STRFLT(matrix.toQuat().w)
            )
        text += "$#bindPosition %s %s %s\n" % (
            STRFLT(matrix.translationPart()[0]),
            STRFLT(matrix.translationPart()[1]),
            STRFLT(matrix.translationPart()[2]),
            )
        text += "$#bindScale %s %s %s\n" % (STRFLT(1) ,STRFLT(1) ,STRFLT(1))
        return text


class Skeleton(MatrixTransform):
    def __init__(self, name, matrix):
        MatrixTransform.__init__(self)
        self.boneList = []
        self.matrix = matrix
        self.setName(name)
        self.update_callbacks = []
        self.update_callbacks.append(UpdateSkeleton())

    def collectBones(self):
        self.boneList = []
        for bone in self.children:
            bone.collect(self.boneList)

    def className(self):
        return "Skeleton"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += Node.printContent(self)
        text += MatrixTransform.printContent(self)
        text += Group.printContent(self)
        text += "$}\n"
        return text

class RigGeometry(Geometry):
    def __init__(self, *args, **kwargs):
        Geometry.__init__(self, *args, **kwargs)
        self.groups = {}
        self.dataVariance = "DYNAMIC"
        self.sourcegeometry = None

    def className(self):
        return "RigGeometry"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += self.printContent()
        text += Geometry.printContent(self)
        text += "$}\n"
        return text

    def printContent(self):
        text = ""
        text += "$#num_influences %s\n" % len(self.groups)
        if len(self.groups) > 0:
            for name, grp in self.groups.items():
                grp.indent_level = self.indent_level + 1
                text += str(grp)

        self.sourcegeometry.indent_level = self.indent_level + 1
        text += str(self.sourcegeometry)
        return text

class AnimationManagerBase(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.animations = []

    def className(self):
        return "AnimationManagerBase"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = "$#num_animations %s\n" % len(self.animations)
        for i in self.animations:
            i.indent_level = self.indent_level + 1
            text += str(i)
        return text

class BasicAnimationManager(AnimationManagerBase):
    def __init__(self, *args, **kwargs):
        AnimationManagerBase.__init__(self, *args, **kwargs)

    def className(self):
        return "BasicAnimationManager"

    def ascii(self):
        return AnimationManagerBase.ascii(self)

    def printContent(self):
        return AnimationManagerBase.printContent(self)

class VertexGroup(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.vertexes = []
        self.targetGroupName = "None"

    def className(self):
        return "VertexGroup"

    def generateID(self):
        return "uniqid_" + self.className() + self.targetGroupName

    def ascii(self):
        self.setName(self.targetGroupName)
        text = "$osgAnimation::VertexInfluence \"%s\" %s {\n" % (self.targetGroupName, len(self.vertexes))
        #text += Object.printContent(self)
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = ""
        for i in self.vertexes:
            text += "$#%s %s\n" % (i[0],STRFLT(i[1]))
        return text

class Animation(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.channels = []
    
    def className(self):
        return "Animation"

    def ascii(self):
        text = "$osgAnimation::%s {\n" % self.className()
        text += Object.printContent(self)
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = "$#num_channels %s\n" % len(self.channels)
        for i in self.channels:
            i.indent_level = self.indent_level + 1
            text += str(i)
        return text


class Channel(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)
        self.keys = []
        self.target = "none"
        self.type = "Unknown"

    def generateID(self):
        return None
    
    def className(self):
        return "Channel"

    def ascii(self):
        text = "$%s {\n" % self.type
        text += self.printContent()
        text += "$}\n"
        return text

    def printContent(self):
        text = "$#name \"%s\"\n" % self.name
        text += "$#target \"%s\"\n" % self.target
        text += "$#Keyframes %s {\n" % (len(self.keys))
        for i in self.keys:
            text += "$##key"
            for a in range(0, len(i)):
                text += " %s" % (STRFLT(i[a]))
            text += "\n"
        text += "$#}\n"
        return text
