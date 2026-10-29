"""Flat-shaded 3D solids with orthographic projection and sorted visible faces.

Pygame rasterizes the projected mesh faces. No OpenGL context is required, so the
same renderer works in packaged builds and deterministic headless screenshot QA.
The flat ground-plane collision model remains in simulation.py.
"""
from math import atan2, cos, sin, pi, degrees
import pygame
from camera import Camera
from geometry import box, cylinder
from targeting import Vec2
from behaviours import BRAKE_ZONES
from control import wrap_angle

CYAN = (98, 241, 250)
AMBER = (255, 204, 75)
WHITE = (249, 246, 255)
TANK_COLOURS = {"blue": (64, 184, 246), "red": (255, 105, 130), "gold": (255, 201, 57)}


class Renderer3D:
    def __init__(self):
        self.camera = Camera()
        self.faces = []
        self.static = None
        self.static_key = None
        self.font = pygame.font.Font(None, 21)

    def mesh(self, mesh, colour):
        vertices, faces = mesh
        projected = [self.camera.project(v) for v in vertices]
        view = self.camera.toward_viewer
        for face in faces:
            a,b,c = [vertices[i] for i in face[:3]]
            u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
            normal = (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            length = max(1e-9, sum(n*n for n in normal)**0.5)
            n = tuple(value/length for value in normal)
            if sum(n[i]*view[i] for i in range(3)) <= 0:
                continue
            light = max(0, n[0]*-.35+n[1]*-.2+n[2]*.91)
            shade = .64+.36*light
            fill = tuple(min(255,int(value*shade)) for value in colour)
            depth = sum(projected[i][2] for i in face)/len(face)
            points = [(projected[i][0],projected[i][1]) for i in face]
            self.faces.append((depth, points, fill))

    def flush(self, surface):
        for _, points, colour in sorted(self.faces, key=lambda f:f[0]):
            pygame.draw.polygon(surface, colour, points)
            pygame.draw.aalines(surface, tuple(max(0,c-13) for c in colour), True, points)
        self.faces.clear()

    def line(self, surface, a, b, colour, width=2, dashed=False):
        p, q = self.camera.project(a), self.camera.project(b)
        if dashed:
            for index in range(0,20,2):
                start = (p[0]+(q[0]-p[0])*index/20, p[1]+(q[1]-p[1])*index/20)
                end = (p[0]+(q[0]-p[0])*(index+1)/20,p[1]+(q[1]-p[1])*(index+1)/20)
                pygame.draw.line(surface, colour, start, end, width)
        else:
            pygame.draw.line(surface, colour, p[:2], q[:2], width)

    def ring(self, surface, position, radius, colour, width=2, height=3):
        points = [self.camera.project((position[0]+radius*cos(i*pi/24),position[1]+radius*sin(i*pi/24),height))[:2]
                  for i in range(49)]
        pygame.draw.lines(surface, colour, False, points, width)

    def tag(self, surface, text, point, colour=WHITE):
        p = self.camera.project(point)
        image = self.font.render(text, True, colour)
        rect = image.get_rect(midbottom=(p[0],p[1]-5))
        pygame.draw.rect(surface, (37,31,67), rect.inflate(10,4), border_radius=5)
        surface.blit(image, rect)

    def terrain(self, surface, rect, path, zones):
        key = (surface.get_size(), tuple(rect), round(self.camera.yaw,2), round(self.camera.elevation,2),round(self.camera.zoom,2), zones)
        if key != self.static_key:
            self.static = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            self.static.set_clip(rect)
            self.mesh(box((460,405,-18),(960,610,18)), (101,155,92))
            self.flush(self.static)
            for x in range(20,940,80):
                for y in range(125,680,80):
                    colour = (106,172,99) if (x+y)//80%2 else (114,182,103)
                    self.mesh(box((x,y,0),(78,78,1)),colour)
            self.flush(self.static)
            for a,b in zip(path.points,path.points[1:]):
                delta = b-a
                centre = (a+b)*.5
                self.mesh(box((centre.x,centre.y,1),(delta.length()+36,48,4),atan2(delta.y,delta.x)),(223,192,130))
            self.flush(self.static)
            if zones:
                for low,high in BRAKE_ZONES:
                    for d in range(low,high,28):
                        p = path.point_at(d)
                        direction = path.direction_at(d)
                        self.mesh(box((p.x,p.y,5.1),(10,43,.5),atan2(direction.y,direction.x)),(255,219,92))
                self.flush(self.static)
            # Little solid pines and stones stay off the road and out of sight lines.
            for x,y in ((180,400),(310,650),(710,170),(750,430),(110,160),(620,650)):
                self.mesh(box((x,y,1),(9,9,22)),(112,72,59))
                self.mesh(cylinder((x,y,18),23,24,5),(53,126,96))
                self.mesh(cylinder((x,y,36),16,20,5),(64,153,107))
            self.flush(self.static)
            self.static_key = key
        surface.blit(self.static,(0,0))

    def tank(self, tank, angle=0, ghost=False):
        x,y = tank.position.tuple()
        colour = (145,243,245) if ghost else TANK_COLOURS[tank.colour]
        # All are real extruded solids, with shared dimensions and flat lighting.
        for offset in (-15,15):
            xx,yy = x-sin(angle)*offset,y+cos(angle)*offset
            self.mesh(box((xx,yy,5),(48,11,10),angle),(61,63,86) if not ghost else (94,174,183))
        self.mesh(box((x,y,12),(40,24,15),angle),colour)
        self.mesh(cylinder((x,y,27),12,9,8),colour)
        self.mesh(box((x+cos(angle)*18,y+sin(angle)*18,30),(35,5,5),angle),colour)

    def tower(self, tower, sensor=False, recoil=0, sensor_enabled=True):
        x,y = tower.position.tuple()
        self.mesh(cylinder((x,y,1),39,13,12),(134,128,168))
        self.mesh(cylinder((x,y,14),29,35,12),(154,143,200))
        self.mesh(box((x,y,49),(46,38,19),tower.angle),(176,150,241))
        a = tower.angle
        self.mesh(box((x+cos(a)*(25-recoil),y+sin(a)*(25-recoil),56),(60,12,12),a),(106,213,224))
        if sensor:
            self.mesh(cylinder((x-9,y-6,68),9,13,6),(111,255,191) if sensor_enabled else (110,112,139))

    def draw(self, surface, rect, game, trial=None, preview=False):
        rect = pygame.Rect(rect)
        self.camera.fit(rect)
        surface.set_clip(rect)
        self.terrain(surface, rect, game.path, game.stage>=3)
        tower = trial.tower if trial else game.tower
        tanks = [trial.tank] if trial else game.tanks
        projectiles = [trial.projectile] if trial and trial.projectile and trial.hit_time is None else [] if trial else game.projectiles
        solution = trial.solution if trial else game.solution
        if str(game.mode) in ("playing","ready") and game.overlay:
            self.ring(surface, tower.position.tuple(), game.RANGE, (157,207,145), 1)
        if not tanks and preview:
            from simulation import Tank
            tank = Tank(1,game.path)
            tank.distance = 300
            tank.position = game.path.point_at(tank.distance)
            tanks = [tank]
        for tank in tanks:
            self.ring(surface,tank.position.tuple(),23,(79,134,80),3,5.2)
            angle = 0 if trial else atan2(game.path.direction_at(tank.distance).y,game.path.direction_at(tank.distance).x)
            self.tank(tank,angle)
        self.tower(tower,bool(game.upgrades["colour"]),4 if game.tower.reload>.98 and not game.settings["reduced_motion"] else 0,game.colour_enabled)
        for shot in projectiles:
            flight = trial.solution.flight_time if trial and trial.solution else max(.1,shot.reservation_time-.12)
            height = 59-30*min(1,shot.age/max(.1,flight))
            self.mesh(cylinder((shot.position.x,shot.position.y,height),4,5,6),AMBER)
            tail = shot.position-shot.velocity.unit()*16
            self.line(surface,(tail.x,tail.y,height),(shot.position.x,shot.position.y,height),AMBER,3)
        self.flush(surface)
        self.ring(surface,game.path.points[-1].tuple(),24,(100,245,204),3,5)
        self.tag(surface,"BASE",(*game.path.points[-1].tuple(),12))
        for tank in tanks:
            self.tag(surface,tank.colour[0].upper()+(" II" if tank.hp>1 else ""),(tank.position.x,tank.position.y,49),TANK_COLOURS[tank.colour])
        if game.overlay:
            if solution and solution.valid:
                p = solution.point
                self.ring(surface,p.tuple(),16,CYAN,2,6)
                self.line(surface,(tower.position.x,tower.position.y,58),(p.x,p.y,6),CYAN,2,True)
                self.tag(surface,f"lead {solution.flight_time:.2f}s",(p.x,p.y,15),CYAN)
                # A translucent-looking wire hull makes the forecast concrete
                # without hiding actual targets behind an opaque second tank.
                vertices,faces=box((p.x,p.y,6),(40,24,20))
                projected=[self.camera.project(v)[:2] for v in vertices]
                for face in faces:
                    pygame.draw.aalines(surface,CYAN,True,[projected[i] for i in face])
            a = trial.desired if trial and trial.tracking else tower.angle
            if trial and trial.tracking:
                self.line(surface,(*tower.position.tuple(),59),(tower.position.x+cos(a)*160,tower.position.y+sin(a)*160,59),CYAN,2,True)
                error=wrap_angle(a-tower.angle)
                arc=[self.camera.project((tower.position.x+cos(tower.angle+error*i/20)*75,
                                           tower.position.y+sin(tower.angle+error*i/20)*75,64))[:2] for i in range(21)]
                pygame.draw.lines(surface,(255,155,174),False,arc,2)
            self.line(surface,(*tower.position.tuple(),59),(tower.position.x+cos(tower.angle)*100,tower.position.y+sin(tower.angle)*100,59),WHITE,3)
            obs = trial.observation if trial and not trial.tracking else game.selected
            if obs:
                end = obs.position+obs.velocity*.5
                self.line(surface,(*obs.position.tuple(),42),(*end.tuple(),42),(125,204,255),3)
                pp,qq = self.camera.project((*obs.position.tuple(),42)),self.camera.project((*end.tuple(),42))
                angle = atan2(qq[1]-pp[1],qq[0]-pp[0])
                pygame.draw.polygon(surface,(125,204,255),[qq[:2],(qq[0]-10*cos(angle-.5),qq[1]-10*sin(angle-.5)),(qq[0]-10*cos(angle+.5),qq[1]-10*sin(angle+.5))])
        if trial and trial.hit_time is not None:
            self.tag(surface,"HIT!",(trial.projectile.position.x,trial.projectile.position.y,65),AMBER)
        for point,life,kind in game.effects:
            colour = (255,232,113) if kind=="hit" else (255,131,146)
            self.ring(surface,point.tuple(),24 if game.settings["reduced_motion"] else 12+(1.2-life)*24,colour,2,12)
        surface.set_clip(None)
