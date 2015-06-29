# The MIT License (MIT)
# 
# Copyright (c) 2014 Don Viszneki <don@codebad.com>
# Copyright (c) 2015 William Shakour <william@willshex.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# This is an import script for Tiled .tmx map files.
#
# based on http://codebad.com/~hdon/import-tmx.py
# using http://pythonhosted.org/tmx/ for parsing
# using https://pypi.python.org/pypi/six
#

bl_info = { 
    "name":         "Import Tiled Map (.tmx)",
    "author":       "William Shakour (william@willshex.com), Don Viszneki (don@codebad.com)",
    "version":      (1, 1, 0), 
    "blender":      (2, 74, 0), 
    "location":     "File > Import > Tiled (.tmx)",
    "description":  "Import a Tiled map (.tmx)",
    "warning":      "Still under development",
    "category":     "Import-Export"}

import bpy, bmesh
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper
import importlib.machinery
import os.path

# Tile UV offset calculator
tileUVOffsets = [(0,-1), (1,-1), (1,0), (0,0)]

level = None

def makeLayerMesh(i, posX, posY, posZ):
    # Create new bmesh
    bm = bmesh.new()
    tmxLayer = level.layers[i]
    tw = level.width
    th = level.height
  
    usedMaterialNames = {}
  
    # usedMaterials.append(bpy.data.materials['import_tmx_material0'])
  
    # Add vertices
    for y in range(th + 1):
        for x in range(tw + 1):
            bm.verts.new().co = (float(x + posX), posY, float(y + posZ))

    bm.verts.index_update()
  
    # Add faces and UVs
    bm.loops.layers.uv.new()
    uvlay = bm.loops.layers.uv.active
    bm.verts.ensure_lookup_table()
  
    for y in range(th):
        for x in range(tw):
            # Construct face
            f = bm.faces.new((
                bm.verts[(y+0)*(tw + 1)+x+0],
                bm.verts[(y+0)*(tw + 1)+x+1],
                bm.verts[(y+1)*(tw + 1)+x+1],
                bm.verts[(y+1)*(tw + 1)+x+0]))
            
            # Assign UVs
            # print ('th = ' + str(th))
            # print ('x,y = ' + str(x) + ',' + str(y))

            tileIDy = th - y - 1 # flip!
            # print('tileIDy = ' + str(tileIDy))
          
            tileID = tmxLayer.tiles[(tileIDy * tw) + x].gid
            # print('tileID = ' + str(tileID))
          
            # Why? Is 0 empty?
            if tileID == 0:
                for iLoop, loop in enumerate(f.loops):
                    loop[uvlay].uv = (0.0, 0.0)
            else:
                tileset = findTileset(tileID);
          
                mName = materialName(tileset)
                usedMaterialNames[mName] = mName

                tsw = int(int(tileset.image.width) / (tileset.tilewidth + tileset.spacing))
                tsh = int(int(tileset.image.height) / (tileset.tileheight + tileset.spacing))
                
                tswf = float(tileset.image.width) / (tileset.tilewidth + tileset.spacing)
                tshf = float(tileset.image.height) / (tileset.tileheight + tileset.spacing)
                
                # print('spacing', tileset.spacing)
                
                for iLoop, loop in enumerate(f.loops):
                    # loop[uvlay].uv = (0.0, 0.0)
                    position = (tileID - tileset.firstgid)
                    tx = position % tsw
                    ty = position // tsw
                    
                    xoffset = tileUVOffsets[iLoop][0]
                    yoffset = tileUVOffsets[iLoop][1]
                    
                    if xoffset > 0:
                        xoffset -= (tileset.spacing * 0.5) / tileset.tilewidth
                    else:
                        xoffset += (tileset.spacing * 0.5) / tileset.tilewidth
                        
                    if yoffset < 0:
                        yoffset += (tileset.spacing * 0.5) / tileset.tileheight
                    else:
                        yoffset -= (tileset.spacing * 0.5) / tileset.tileheight
                    
                    loop[uvlay].uv = (((tx + xoffset) / tswf) 
                    # - (tx * 0.001)
                    ,
                    (((tshf - ty) + yoffset) / tshf)
                    # + (ty * 0.005)
                    )
                    # print (loop[uvlay].uv)
                    # print (tx, ty)
          
    me = bpy.data.meshes.new('gen_' + str(i) + '_' + tmxLayer.name)
    for mName in usedMaterialNames.values():
        me.materials.append(bpy.data.materials.get(mName))
    
    bm.to_mesh(me)
    ob = bpy.data.objects.new(tmxLayer.name, me)
    ob.show_transparent = True
    
    return ob

def findTileset(gid):
    found = None
    for tileset in level.tilesets:
        if (gid >= tileset.firstgid):
            found = tileset
    #if (found != None):
        # print (found.name)
    return found

def materialName(tileset):
    return tileset.name + '_material'

def textureName(tileset):
    return tileset.name + '_texture'

def createTilesetMaterial(i):
    mName = materialName(level.tilesets[i])
    ma = None
    if (bpy.data.materials.get(mName) == None):
        ma = bpy.data.materials.new(mName)
        te = bpy.data.textures.new(textureName(level.tilesets[i]), type='IMAGE')
      
        source = level.tilesets[i].image.source
        # print ('Material image @ ' + source)
      
        im = bpy.data.images.load(source)
        te.image = im
        mt = ma.texture_slots.add()
        mt.texture = te
        mt.texture_coords = 'UV'
        mt.use_map_color_diffuse = True 
        mt.mapping = 'FLAT'
    # else:
       # print ('Material ' + mName + ' already exists')
    
    return ma

class ImportTMX(bpy.types.Operator, ImportHelper):
    bl_idname     = 'import.tmx'
    bl_label      = 'Import Tiled Map (.tmx)'
    bl_options    = {'PRESET'}

    filename_ext = '.tmx'
    filter_glob = StringProperty(default='*.tmx', options={'HIDDEN'})

    filepath = bpy.props.StringProperty(
        name        = 'File Path',
        description = 'Import file path',
        maxlen      = 1024,
        default     = '')

    def execute(self, context):
        global level
        try:
            cwd = os.path.dirname(os.path.realpath(__file__));
            loader = importlib.machinery.SourceFileLoader("six", cwd + "/libs/six.py")
            loader.load_module()
            loader = importlib.machinery.SourceFileLoader("tmx", cwd + "/libs/tmx.py")
            tmx = loader.load_module()
            level = tmx.TileMap.load(self.properties.filepath)
            
            for i in range(len(level.tilesets)):
                createTilesetMaterial(i)
            
            for i in range(len(level.layers)):
                # print (i)
                if (hasattr(level.layers[i], 'tiles')):
                    ob = makeLayerMesh(i, 0.0, -i, 0.0)
                    bpy.context.scene.objects.link(ob)
                    
                    if (not level.layers[i].visible):
                        ob.hide = True
                        ob.hide_render = True
                #else:
                    # print ('Found non tile layer ' + level.layers[i].name)
            
            # print ('Finished')
        finally:
            level = None

        return {'FINISHED'}


def menu_func(self, context):                                                               
    self.layout.operator(ImportTMX.bl_idname, text="Tiled Map (.tmx)")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(menu_func)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func)

if __name__ == '__main__':
    register()