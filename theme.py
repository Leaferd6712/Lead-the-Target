"""Chunky arcade UI inspired by the supplied purple/stone/tropical references."""
import pygame
from math import sin, cos, pi

BG = (30, 22, 65)
PANEL = (76, 66, 111)
INK = (36, 29, 60)
EDGE = (146, 134, 188)
TEXT = (255, 250, 239)
MUTED = (220, 214, 238)
GOLD = (255, 202, 62)
TEAL = (64, 218, 216)
GREEN = (113, 231, 140)
RED = (255, 134, 153)
BLUE = (113, 198, 255)
TERMS = (TEAL, GOLD, BLUE, (218, 165, 255))


def set_contrast(enabled):
    global PANEL, EDGE, INK
    PANEL = (47,37,78) if enabled else (76,66,111)
    EDGE = (230,221,255) if enabled else (146,134,188)
    INK = (15,10,29) if enabled else (36,29,60)


def star(surface, center, radius, colour=GOLD):
    points = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius*.46
        angle = -pi/2+i*pi/5
        points.append((center[0]+cos(angle)*r,center[1]+sin(angle)*r))
    pygame.draw.polygon(surface,(116,67,55),[(x,y+3) for x,y in points])
    pygame.draw.polygon(surface,colour,points)
    pygame.draw.aalines(surface,(255,232,140),True,points)


def icon(surface, name, center, colour=TEXT, size=15):
    x,y=center;r=size/2
    if name=="play":pygame.draw.polygon(surface,colour,[(x-r*.6,y-r),(x+r,y),(x-r*.6,y+r)])
    elif name=="pause":
        for dx in (-5,3):pygame.draw.rect(surface,colour,(x+dx,y-r,4,size),border_radius=1)
    elif name=="lock":
        pygame.draw.rect(surface,colour,(x-r,y,2*r,r+2),border_radius=2)
        pygame.draw.arc(surface,colour,(x-r*.65,y-r-2,r*1.3,r*1.5),0,pi,2)
    elif name=="shop":
        pygame.draw.rect(surface,colour,(x-r,y-r*.3,size,size*.9),2,border_radius=2)
        pygame.draw.arc(surface,colour,(x-r*.5,y-r,r,r),0,pi,2)
    elif name=="menu":
        for dy in (-5,0,5):pygame.draw.line(surface,colour,(x-r,y+dy),(x+r,y+dy),2)
    elif name=="note":
        pygame.draw.rect(surface,colour,(x-r,y-r,size,size),2,border_radius=2)
        for dy in (-3,2):pygame.draw.line(surface,colour,(x-r+3,y+dy),(x+r-3,y+dy),1)
    elif name=="sensor":
        pygame.draw.polygon(surface,colour,[(x,y-r),(x+r,y),(x,y+r),(x-r,y)],2)


def app_icon():
    image=pygame.Surface((256,256),pygame.SRCALPHA)
    pygame.draw.rect(image,(55,36,104),image.get_rect(),border_radius=48)
    pygame.draw.rect(image,(151,114,221),(7,7,242,242),5,border_radius=44)
    pygame.draw.ellipse(image,(118,105,156),(42,137,151,64))
    pygame.draw.rect(image,(158,133,210),(42,113,151,60))
    pygame.draw.ellipse(image,(188,162,239),(42,84,151,62))
    pygame.draw.line(image,(75,221,226),(119,106),(207,46),24)
    star(image,(67,58),25)
    return image


def panel(surface, rect, accent=False, foliage=False):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, (17,13,40),rect.move(0,5),border_radius=16)
    pygame.draw.rect(surface, EDGE,rect,border_radius=16)
    pygame.draw.rect(surface,PANEL,rect.inflate(-6,-6),border_radius=13)
    pygame.draw.line(surface,(171,156,209),(rect.left+18,rect.top+5),(rect.right-18,rect.top+5),2)
    if accent:
        pygame.draw.rect(surface,INK,(rect.left+14,rect.top+14,rect.width-28,8),border_radius=4)
    if foliage:
        for side in (-1,1):
            x = rect.centerx+side*(rect.width/2-25)
            for i in range(3):
                y = rect.top+10+i*10
                points = [(x,y+16),(x+side*5,y-5),(x+side*(36+i*4),y-26-i*3),(x+side*22,y+6)]
                pygame.draw.polygon(surface,(71,160+i*12,100),points)
                pygame.draw.line(surface,(119,206,128),(x,y+14),(x+side*(32+i*4),y-22-i*3),1)


class ButtonArt:
    def __init__(self):
        self.cache = {}

    def get(self, size, style, hover=False, pressed=False, disabled=False):
        key = tuple(size),style,hover,pressed,disabled
        if key in self.cache:return self.cache[key]
        colours = {"gold":((255,218,79),(239,145,45)), "aqua":((101,235,235),(27,148,178)),
                   "purple":((154,110,224),(100,67,167)), "red":((255,165,161),(198,76,115)),
                   "green":((146,241,151),(53,163,120)), "stone":((111,104,147),(73,66,109))}
        top,bottom = colours.get(style,colours["stone"])
        if disabled:top,bottom=(89,83,113),(64,58,85)
        elif hover:top=tuple(min(255,c+18) for c in top)
        width,height = map(int,size)
        art=pygame.Surface((width,height),pygame.SRCALPHA)
        pygame.draw.rect(art,(25,18,48),(0,4,width,height-4),border_radius=10)
        face = pygame.Surface((width-4,height-6),pygame.SRCALPHA)
        for y in range(face.get_height()):
            fraction=y/max(1,face.get_height()-1)
            colour=tuple(int(a+(b-a)*fraction) for a,b in zip(top,bottom))
            pygame.draw.line(face,colour,(0,y),(face.get_width(),y))
        mask=pygame.Surface(face.get_size(),pygame.SRCALPHA)
        pygame.draw.rect(mask,(255,255,255,255),mask.get_rect(),border_radius=8)
        face.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MIN)
        art.blit(face,(2,4 if pressed else 1))
        pygame.draw.rect(art,tuple(min(255,c+28) for c in top),(2,2,width-4,height-7),2,border_radius=8)
        if len(self.cache)>256:self.cache.clear()
        self.cache[key]=art
        return art
