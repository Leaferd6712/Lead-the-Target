"""Tiny generated arcade cues; gracefully silent without an audio device."""
from array import array
from math import sin, pi
import pygame


class Audio:
    def __init__(self):
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():pygame.mixer.init(frequency=22050,size=-16,channels=1)
            rate,_,channels=pygame.mixer.get_init()
            for name,freq,duration in (("shot",360,.055),("hit",680,.11),("win",880,.24),("click",510,.045)):
                values=array('h')
                for i in range(int(rate*duration)):
                    envelope=(1-i/(rate*duration))**2
                    sample=int(6000*envelope*sin(2*pi*freq*i/rate))
                    values.extend([sample]*channels)
                self.sounds[name]=pygame.mixer.Sound(buffer=values)
        except pygame.error:
            self.sounds={}

    def play(self,name,settings):
        if not settings["muted"] and name in self.sounds:
            sound=self.sounds[name]
            sound.set_volume(settings["volume"])
            sound.play()
