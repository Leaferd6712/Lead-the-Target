"""Orthographic camera for a real 3D scene. World coordinates: x, ground-y, height."""
from dataclasses import dataclass
from math import sin, cos, radians


@dataclass
class Camera:
    yaw: float = 25
    elevation: float = 40
    zoom: float = 1
    scale: float = 1
    cx: float = 0
    cy: float = 0
    target: tuple = (460, 400, 0)

    def fit(self, rect):
        x, y, width, height = rect
        a, e = radians(self.yaw), radians(self.elevation)
        projected_width = 960*abs(cos(a))+600*abs(sin(a))
        projected_height = (960*abs(sin(a))+600*abs(cos(a)))*sin(e)+100*cos(e)
        self.scale = min((width-40)/projected_width, (height-32)/projected_height)*self.zoom
        self.cx, self.cy = x+width/2, y+height/2+22

    def project(self, point):
        x, y, z = (point[i]-self.target[i] for i in range(3))
        a, e = radians(self.yaw), radians(self.elevation)
        horizontal = x*cos(a)-y*sin(a)
        down = (x*sin(a)+y*cos(a))*sin(e)-z*cos(e)
        depth = (x*sin(a)+y*cos(a))*cos(e)+z*sin(e)
        return (self.cx+horizontal*self.scale, self.cy+down*self.scale, depth)

    def ground_at(self, screen, height=0):
        """Inverse projection onto a known-height plane, used for markers/picking."""
        a, e = radians(self.yaw), radians(self.elevation)
        u = (screen[0]-self.cx)/self.scale
        v = ((screen[1]-self.cy)/self.scale+(height-self.target[2])*cos(e))/sin(e)
        return (self.target[0]+u*cos(a)+v*sin(a), self.target[1]-u*sin(a)+v*cos(a))

    @property
    def toward_viewer(self):
        a, e = radians(self.yaw), radians(self.elevation)
        return sin(a)*cos(e), cos(a)*cos(e), sin(e)

    def reset(self):
        self.yaw, self.elevation, self.zoom = 25, 40, 1
