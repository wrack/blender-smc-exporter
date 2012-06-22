#  ***** GPL LICENSE BLOCK *****
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#  All rights reserved.
#  ***** GPL LICENSE BLOCK *****
# by Eric Depta

bl_info = {
    "name": "Export Sauerbraten (.smc)",
    "author": "Wrack",
    "version": (1, 0),
    "blender": (2, 6, 0),
    "api": 42615,
    "location": "File > Export > Sauerbraten (.smc)",
    "description": "Export Selected Mesh to Sauerbraten",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.5/Py/"\
        "Scripts/Import-Export/PC2_Pointcache_export",
    "tracker_url": "https://projects.blender.org/tracker/index.php?"\
        "func=detail&aid=24703",
    "category": "Import-Export"}

"""
-- Export Sauerbraten v0.0.1 --<br> 
"""

import bpy
from bpy.props import *
import mathutils, math
from bpy_extras.io_utils import ExportHelper
from sys import stdout

class Grid:
    def __init__(self):
        self.density = []
        self.dim = [0,0,0]
        self.gridstep = 0
        self.center = None
        self.progress = ["|","/","-","\\"]
        
    def boundMesh(self, mesh, longestRow):
        ## boundings ##
        minX = mesh.vertices[0].co[0]
        maxX = minX
        minY = mesh.vertices[0].co[1]
        maxY = minY
        minZ = mesh.vertices[0].co[2]
        maxZ = minZ
        for v in mesh.vertices: 
            minX = min(minX,v.co[0])
            maxX = max(maxX,v.co[0])
            minY = min(minY,v.co[1])
            maxY = max(maxY,v.co[1])
            minZ = min(minZ,v.co[2])
            maxZ = max(maxZ,v.co[2])
            
        dimBox = [math.copysign(maxX, 0) + math.copysign(minX, 0), math.copysign(maxY, 0) + math.copysign(minY, 0), math.copysign(maxZ, 0) + math.copysign(minZ, 0)]
        
        ## calc grid vals##
        self.gridstep = max(dimBox) / longestRow
        self.dim = [math.ceil(dimBox[0]/self.gridstep), math.ceil(dimBox[1]/self.gridstep), math.ceil(dimBox[2]/self.gridstep)]
        self.center = mathutils.Vector( (math.copysign(minX, 0), math.copysign(minY, 0), math.copysign(minZ, 0)) )
        
    def solve(self, obj, mesh, useExpPIM, pbar):
        i = 0
        total = (self.dim[0]+1) * (self.dim[1]+1) * (self.dim[2]+1)
        for xc in range(self.dim[0]+1):
            self.density.append([])
            for yc in range(self.dim[1]+1):
                self.density[xc].append([])
                for zc in range(self.dim[2]+1):
                    p = mathutils.Vector((xc*self.gridstep, yc*self.gridstep, zc*self.gridstep)) - self.center
                    location, normal, index = obj.closest_point_on_mesh(p)
                    d = self.distancePoints(p, location)
                    
                    if useExpPIM:
                        if self.pointInsideMeshExp(mesh,p,index):
                            d = d * -1
                    else:
                        if self.pointInsideMesh(p,obj):
                             d = d * -1
                    
                    self.density[xc][yc].append(d)
                    i += 1
                    
                    pcnt = int(round((i/total) * 100,0))
                    pbar = pcnt
                    stdout.write("\rsolve: %d%%" %pcnt + " " + self.progress[i%4])
                    
        stdout.write("\n")

    def pointInsideMeshExp(self,mesh,p,index):
        inside = True
        for i in range(3):
            v = mesh.vertices[mesh.faces[index].vertices[i]]
            pn = p.dot(v.normal)
            tn = v.co.dot(v.normal)
            if pn >= tn or abs(pn-tn)<0.0000001:
                inside = False
                break
        return inside
    
    def pointInsideMesh(self,point,ob):
        axes = [ mathutils.Vector((1,0,0)) , mathutils.Vector((0,1,0)), mathutils.Vector((0,0,1))  ]
        outside = False
        for axis in axes:
            orig = point
            count = 0
            lasthit = None
            lasthiti = -1
            lasthitcnt = 0
            dx = 0.00001
            while True:
                location,normal,index = ob.ray_cast(orig,orig+axis*10000.0)
                if index == -1: break
                if lasthit == location or lasthiti == index:
                    lasthitcnt += 1
                    orig = location + axis*(dx*lasthitcnt)
                else:
                    lasthit = location
                    lasthiti = index
                    count += 1
                    lasthitcnt = 0
                    ## 0.01 need to be a calculated value but which 
                    orig = location + axis*dx
                
            if count%2 == 0:
                outside = True
                break
        return not outside
    
    def toStr(self, gridPower, file):
        gridSizes = [1,2,4,8,16,32,64,128,256,512,1024,2048,4096] ## faster than facultation
        csize = gridSizes[gridPower]
        
        i = 0
        total = self.dim[0] * self.dim[1] * self.dim[2]
        for xc in range(self.dim[0]):
            for yc in range(self.dim[1]):
                for zc in range(self.dim[2]):
                    if (self.density[xc][yc][zc]<0 or self.density[xc+1][yc][zc]<0 or self.density[xc+1][yc+1][zc]<0 or self.density[xc][yc+1][zc]<0 or self.density[xc][yc][zc+1]<0 or self.density[xc+1][yc][zc+1]<0 or self.density[xc+1][yc+1][zc+1]<0 or self.density[xc][yc+1][zc+1]<0 ):
                        out = ""
                        out += '%d %d %d ' % ((xc * csize), (yc * csize), (zc * csize)) + '%d ' % csize
                        out += '%s ' % self.density[xc][yc][zc]
                        out += '%s ' % self.density[xc+1][yc][zc]
                        out += '%s ' % self.density[xc+1][yc+1][zc]
                        out += '%s ' % self.density[xc][yc+1][zc]
                        out += '%s ' % self.density[xc][yc][zc+1]
                        out += '%s ' % self.density[xc+1][yc][zc+1]
                        out += '%s ' % self.density[xc+1][yc+1][zc+1]
                        out += '%s'  % self.density[xc][yc+1][zc+1]
                        out += '\n'
                        file.write(bytes(out,'ASCII'))
                        
                    i += 1
                    pcnt = int(round((i/total) * 100,0))
                    stdout.write("\rwrite: %d%%" %pcnt + " " + self.progress[i%4])
        stdout.write("\n")
        
    def distancePoints(self, p1, p2):
        return math.sqrt(math.pow(p2[0]-p1[0],2)+math.pow(p2[1]-p1[1],2)+math.pow(p2[2]-p1[2],2))

class Export_smc(bpy.types.Operator, ExportHelper):
    '''Exports the active Object as a .smc file.'''
    
    bl_idname = "export_shape.smc"
    bl_label = "Export Sauerbraten (.smc)"
    filename_ext = ".smc"
    
    gridPower = IntProperty(name='Grid Power',
            description='Cubes Grid Power',
            default=4,
            soft_max=12,
            soft_min=0
            )
    
    longestRow = IntProperty(name='Cube Count',
            description='Count of the Cubes on the longest',
            default=2,
            soft_min=1
            )
    
    useExpPIM = BoolProperty(name='Experimental PIM',
            description='Use experimental point in mesh function',
            default=False,
            )
    
    progress_bar = 1
    
    def execute(self, context):
        print("---- Sauerbraten Exporter ----")
        props = self.properties
        obj = context.active_object
        scn = context.scene
        
        if not obj:
            error("No Object Selected")
            return {'FINISHED'}
        
        mesh = obj.to_mesh(scn, True, 'PREVIEW')
        if not mesh:
            error("Not a Mesh")
            return {'FINISHED'}
        
        ## smc file format ##
        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, '.smc')
        
        ## make grid from mesh ##
        grid = Grid()
        grid.boundMesh(mesh, props.longestRow) 
        grid.solve(obj,mesh,props.useExpPIM,self.progress_bar)
        ##print("solved")
        
        ## write output file ##
        out = open(filepath, "wb")
        grid.toStr(props.gridPower,out)
        out.close()
        
        print("done")
        
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(Export_smc.bl_idname, text="Sauerbraten (.smc)")

def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_export.append(menu_func)
    #bpy.types.VIEW3D_PT_tools_objectmode.prepend(menu_func)

def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_export.remove(menu_func)
    #bpy.types.VIEW3D_PT_tools_objectmode.remove(menu_func)
 
if __name__ == "__main__":
    register()
