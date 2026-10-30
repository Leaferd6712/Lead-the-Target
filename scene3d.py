"""Panda3D scene graph: original low-poly geometry, lighting, camera and picking.

Physics uses a flat ground plane; x/y are scaled by 1/20 into 3D x/-y.
Shell height is decorative: this game teaches planar interception, not gravity.
"""
from math import atan2, cos, sin, pi, degrees
from panda3d.core import (AmbientLight, DirectionalLight, Geom, GeomNode,
    GeomTriangles, GeomVertexData, GeomVertexFormat, GeomVertexWriter, LineSegs,
    NodePath, OrthographicLens, Point3, Vec3, Plane, TransparencyAttrib, TextNode)
from geometry import box, cylinder
from fortress import PADS
from waves import Route

TANK_COLOURS = {"blue":(.12,.70,.94,1),"red":(1,.25,.35,1),"gold":(1,.73,.16,1)}


def mesh(parent,name,vertices,faces,colour):
    data = GeomVertexData(name,GeomVertexFormat.getV3n3c4(),Geom.UHStatic)
    v,n,c = (GeomVertexWriter(data,key) for key in ("vertex","normal","color"))
    tris = GeomTriangles(Geom.UHStatic)
    index = 0
    for face in faces:
        a,b,d = (Vec3(*vertices[i]) for i in face[:3])
        normal = (b-a).cross(d-a); normal.normalize()
        for i in face:
            v.addData3(*vertices[i]); n.addData3(normal); c.addData4(*colour)
        for j in range(1,len(face)-1): tris.addVertices(index,index+j,index+j+1)
        index += len(face)
    geom = Geom(data); geom.addPrimitive(tris)
    node = GeomNode(name); node.addGeom(geom)
    return parent.attachNewNode(node)


def block(parent,position,size,colour,name="block"):
    vertices,faces = box(position,size)
    return mesh(parent,name,vertices,faces,colour)


def drum(parent,position,radius,height,colour,sides=12):
    vertices,faces = cylinder(position,radius,height,sides)
    return mesh(parent,"drum",vertices,faces,colour)


def cone(parent,x,y,z,radius,height,colour):
    vertices = [(x+radius*cos(i*pi/3),y+radius*sin(i*pi/3),z) for i in range(6)]+[(x,y,z+height)]
    return mesh(parent,"tree",vertices,[(i,(i+1)%6,6) for i in range(6)],colour)


def line(parent,points,colour=(.3,1,1,1),thickness=2):
    ls = LineSegs(); ls.setColor(*colour); ls.setThickness(thickness)
    ls.moveTo(*points[0])
    for p in points[1:]: ls.drawTo(*p)
    node = parent.attachNewNode(ls.create()); node.setLightOff()
    return node


def world(pos,z=0): return pos.x/20,-pos.y/20,z


class Battlefield:
    def __init__(self,base):
        self.base = base
        self.root = base.render.attachNewNode("battlefield")
        self.static = self.root.attachNewNode("island")
        self.dynamic = self.root.attachNewNode("units")
        self.overlay = self.root.attachNewNode("prediction")
        self.tank_nodes,self.tower_nodes,self.shell_nodes = {},{},{}
        self.camera_angle = 0; self.zoom = 1
        self.compact = False
        self.lens = OrthographicLens(); self.lens.setNearFar(.1,300)
        base.cam.node().setLens(self.lens)
        base.disableMouse(); base.setBackgroundColor(.035,.055,.14,1)
        ambient = AmbientLight("sky"); ambient.setColor((.55,.57,.7,1))
        self.root.setLight(self.root.attachNewNode(ambient))
        sun = DirectionalLight("sun"); sun.setColor((1,.91,.72,1))
        node = self.root.attachNewNode(sun); node.setHpr(-35,-55,0); self.root.setLight(node)
        self.make_terrain()
        self.resize()

    def resize(self):
        # Render into the actual free battlefield area, above the bottom dock.
        # UI scaling is independent; changing resolution never changes picking.
        region = self.base.cam.node().getDisplayRegion(0)
        left,right,bottom,top = (.015,.985,.345,.78) if self.compact else (.015,.695,.285,.78)
        region.setDimensions(left,right,bottom,top)
        aspect = self.base.getAspectRatio()*(right-left)/(top-bottom)
        film_height = 29 if self.compact else 31
        self.lens.setFilmSize(film_height*aspect/self.zoom,film_height/self.zoom)
        focus_x,focus_y = 23,-18
        a = self.camera_angle
        self.base.camera.setPos(focus_x+45*sin(a),focus_y-45*cos(a),49)
        self.base.camera.lookAt(focus_x,focus_y,0)

    def make_terrain(self):
        s = self.static
        block(s,(23,-18,-2.1),(95,90,.4),(.035,.26,.36,1),"water")
        block(s,(23,-18,-1.6),(49,38,1.5),(.20,.24,.36,1),"island-rock")
        block(s,(23,-18,-.15),(48,37,.15),(.16,.43,.32,1),"grass")
        seen = set()
        for route in (Route(0),Route(1),Route(2)):
            for a,b in zip(route.points,route.points[1:]):
                key = tuple(sorted((a.tuple(),b.tuple())))
                if key in seen: continue
                seen.add(key)
                x,y = (a.x+b.x)/40,-(a.y+b.y)/40
                block(s,(x,y,.015),(abs(b.x-a.x)/20+1.65,abs(b.y-a.y)/20+1.65,.07),(.64,.56,.39,1),"road")
        for i in range(9):
            block(s,(8+i*1.1,-12.9,.095),(.3,1.55,.02),(.95,.75,.25,1))
        for i,p in enumerate(PADS):
            x,y,_ = world(p)
            drum(s,(x,y,.04),1.22,.15,(.24,.28,.43,1),8)
            ring = [(x+1.05*cos(j*pi/4),y+1.05*sin(j*pi/4),.23) for j in range(9)]
            line(s,ring,(.33,.81,.81,1),2)
            label = TextNode(f"pad-{i}"); label.setText(str(i+1)); label.setAlign(TextNode.ACenter)
            label.setTextColor(.8,1,1,1)
            n = s.attachNewNode(label); n.setScale(.46); n.setPos(x,y-.5,.28); n.setP(-90); n.setLightOff()
        # Low-poly foliage and stone props stay outside the build pads and roads.
        for x,y in ((2,-3),(10,-3),(22,-3),(33,-3),(45,-3),(46,-16),(1,-21),(42,-35),(35,-35)):
            drum(s,(x,y,0),.18,1,(.35,.20,.16,1),6)
            cone(s,x,y,.8,1.1,2.3,(.13,.56,.31,1))
            cone(s,x,y,1.7,.85,1.8,(.23,.73,.36,1))
        self.base_node = s.attachNewNode("fortress")
        block(self.base_node,(4.4,-33,0),(3.5,2.2,1.2),(.35,.29,.52,1))
        for x in (3.1,5.7):
            drum(self.base_node,(x,-33,0),.65,2,(.49,.42,.68,1),8)
            cone(self.base_node,x,-33,2,.8,1,(.54,.24,.74,1))
        block(self.base_node,(4.4,-32.9,1.2),(1.3,.8,1.5),(.6,.48,.78,1))
        block(self.base_node,(4.4,-32.95,2.7),(.12,.12,1),(.9,.85,.6,1))
        block(self.base_node,(4.9,-32.95,3.2),(1,.05,.5),(1,.73,.18,1))

    def tower_model(self,tower):
        root = self.dynamic.attachNewNode("tower")
        drum(root,(0,0,.2),.88,.45,(.22,.24,.38,1),8)
        drum(root,(0,0,.65),.68,1.1,(.50,.39,.74,1),8)
        rotating = root.attachNewNode("turret")
        if getattr(tower,"kind","") == "sensor":
            drum(rotating,(0,0,1.7),.75,.18,(.24,.94,.7,1),8)
            block(rotating,(0,0,1.8),(.1,.1,1),(.6,1,1,1))
        else:
            drum(rotating,(0,0,1.75),.77,.4,(.38,.70,.82,1),8)
            block(rotating,(.85,0,1.84),(1.8,.28,.3),(.89,.94,1,1),"barrel")
            block(rotating,(1.7,0,1.79),(.35,.4,.4),(.25,.31,.44,1))
        return root,rotating

    def tank_model(self,colour):
        root = self.dynamic.attachNewNode("tank")
        for y in (-.48,.48):
            block(root,(0,y,.12),(1.65,.30,.45),(.12,.17,.25,1),"tracks")
        c = TANK_COLOURS.get(colour,TANK_COLOURS["blue"])
        block(root,(0,0,.35),(1.55,.8,.5),c)
        drum(root,(0,0,.85),.43,.28,c,8)
        block(root,(.55,0,.96),(1.1,.13,.15),(.9,.93,.98,1))
        # Symbols make classes distinguishable without colour vision.
        text = TextNode("class"); text.setText({"blue":"B","red":"R","gold":"G"}.get(colour,"?")); text.setAlign(TextNode.ACenter)
        n = root.attachNewNode(text); n.setPos(-.2,0,1.2); n.setScale(.40); n.setBillboardPointEye(); n.setLightOff()
        return root

    def sync(self,towers,tanks,shells,selected=None,solution=None,history=(),trial=None,show_overlay=True,build_pad=None):
        ids = {t.id for t in towers}
        for ident in list(self.tower_nodes):
            if ident not in ids:
                self.tower_nodes.pop(ident)[0].removeNode()
        for t in towers:
            if t.id not in self.tower_nodes: self.tower_nodes[t.id] = self.tower_model(t)
            root,rot = self.tower_nodes[t.id]
            motor = t.motor if hasattr(t,"motor") else t
            root.setPos(*world(motor.position)); rot.setH(degrees(-motor.angle))
            if hasattr(t,"level"): root.setScale(1+.06*t.level)
        ids = {t.id for t in tanks}
        for ident in list(self.tank_nodes):
            if ident not in ids: self.tank_nodes.pop(ident).removeNode()
        for t in tanks:
            if t.id not in self.tank_nodes: self.tank_nodes[t.id] = self.tank_model(t.colour)
            root = self.tank_nodes[t.id]; root.setPos(*world(t.position))
            direction = t.position-t.previous
            if direction.length()>.001: root.setH(-degrees(atan2(direction.y,direction.x)))
        ids = {id(p) for p in shells}
        for ident in list(self.shell_nodes):
            if ident not in ids: self.shell_nodes.pop(ident).removeNode()
        for p in shells:
            if id(p) not in self.shell_nodes:
                self.shell_nodes[id(p)] = drum(self.dynamic,(0,0,0),.12,.24,(1,.80,.24,1),6)
                self.shell_nodes[id(p)].setLightOff()
            self.shell_nodes[id(p)].setPos(*world(p.position,1.2))
        self.overlay.removeNode(); self.overlay = self.root.attachNewNode("prediction")
        if build_pad is not None:
            p = PADS[build_pad]; x,y,_ = world(p)
            line(self.overlay,[(x+1.35*cos(i*pi/16),y+1.35*sin(i*pi/16),.4) for i in range(33)],(1,.8,.2,1),4)
        if not show_overlay or selected is None: return
        motor = selected.motor if hasattr(selected,"motor") else selected
        x,y,z = world(motor.position,.3)
        radius = getattr(selected,"radius",530)/20
        line(self.overlay,[(x+radius*cos(i*pi/32),y+radius*sin(i*pi/32),z) for i in range(65)],(.40,.80,1,.7),1)
        sol = solution or getattr(selected,"solution",None)
        if sol and sol.valid:
            px,py,_ = world(sol.point,.6)
            line(self.overlay,[(x,y,1.8),(px,py,.6)],(.25,1,.88,1),2)
            line(self.overlay,[(px-.55,py,.6),(px+.55,py,.6)],(.4,1,1,1),3)
            line(self.overlay,[(px,py-.55,.6),(px,py+.55,.6)],(.4,1,1,1),3)
            v,f = box((px,py,.25),(1.6,.9,.7))
            ghost = mesh(self.overlay,"ghost",v,f,(.3,1,1,.25))
            ghost.setTransparency(TransparencyAttrib.MAlpha); ghost.setLightOff(); ghost.setDepthWrite(False)
        if trial and trial.tracking:
            p = motor.position
            line(self.overlay,[world(p,2),world(p+type(p)(cos(trial.desired),sin(trial.desired))*220,2)],(.5,1,.3,1),3)

    def clear_units(self):
        for nodes in self.tower_nodes.values(): nodes[0].removeNode()
        for node in list(self.tank_nodes.values())+list(self.shell_nodes.values()): node.removeNode()
        self.tank_nodes.clear(); self.tower_nodes.clear(); self.shell_nodes.clear()

    def pick_pad(self,mouse):
        # Mouse coordinates cover the window; the lens covers its display region.
        region = self.base.cam.node().getDisplayRegion(0)
        mx,my = (mouse.x+1)/2,(mouse.y+1)/2
        l,r,b,t = region.getLeft(),region.getRight(),region.getBottom(),region.getTop()
        if not l<=mx<=r or not b<=my<=t:return None
        from panda3d.core import Point2
        mouse = Point2(2*(mx-l)/(r-l)-1,2*(my-b)/(t-b)-1)
        near,far = Point3(),Point3()
        if not self.lens.extrude(mouse,near,far): return None
        near = self.base.render.getRelativePoint(self.base.cam,near)
        far = self.base.render.getRelativePoint(self.base.cam,far)
        hit = Point3()
        if not Plane(Vec3(0,0,1),Point3(0,0,.2)).intersectsLine(hit,near,far): return None
        distances = [(abs(p.x/20-hit.x)**2+abs(-p.y/20-hit.y)**2,i) for i,p in enumerate(PADS)]
        distance,index = min(distances)
        return index if distance < 2.0 else None
