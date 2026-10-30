"""Panda3D audio cues; no mixer dependency and safe with silent/offscreen devices."""
from pathlib import Path
from panda3d.core import Filename


class Audio:
    def __init__(self,base):
        self.sounds={}
        for name in ('shot','hit','win','click'):
            path=Path(__file__).resolve().parent/'assets'/(name+'.wav')
            if path.exists():self.sounds[name]=base.loader.loadSfx(Filename.fromOsSpecific(str(path)).getFullpath())

    def play(self,name,prefs):
        if not prefs.get('muted') and name in self.sounds:
            sound=self.sounds[name];sound.setVolume(prefs.get('volume',.4));sound.play()
