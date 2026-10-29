"""Reusable solid meshes. Flat-shaded polygons remain independent of physics."""
from math import cos, sin, pi


BOX_VERTICES = ((-.5,-.5,0),(.5,-.5,0),(.5,.5,0),(-.5,.5,0),
                (-.5,-.5,1),(.5,-.5,1),(.5,.5,1),(-.5,.5,1))
BOX_FACES = ((4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(3,2,1,0))


def box(center, size, angle=0):
    c, s = cos(angle), sin(angle)
    vertices = []
    for vx, vy, vz in BOX_VERTICES:
        x, y = vx*size[0], vy*size[1]
        vertices.append((center[0]+x*c-y*s, center[1]+x*s+y*c, center[2]+vz*size[2]))
    return vertices, BOX_FACES


CYLINDER_CACHE = {}


def cylinder(center, radius, height, sides=12):
    if sides not in CYLINDER_CACHE:
        vertices = [(cos(i*2*pi/sides), sin(i*2*pi/sides), z) for z in (0,1) for i in range(sides)]
        faces = [tuple(range(sides, 2*sides))]
        faces += [(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
        CYLINDER_CACHE[sides] = vertices, faces
    vertices, faces = CYLINDER_CACHE[sides]
    return [(center[0]+x*radius, center[1]+y*radius, center[2]+z*height) for x,y,z in vertices], faces
