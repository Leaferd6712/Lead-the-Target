"""Monitor-aware display configuration and timed rollback, independent of GUI."""
from copy import deepcopy
from time import monotonic
from panda3d.core import ClockObject, WindowProperties, loadPrcFileData
from profile_store import RESOLUTIONS, settings


class DisplayManager:
    def __init__(self,base,prefs,offscreen=False):
        self.base,self.prefs,self.offscreen = base,prefs,offscreen
        self.pending = None
        self.deadline = 0
        self.desktop = (base.pipe.getDisplayWidth(),base.pipe.getDisplayHeight())
        if min(self.desktop) <= 0: self.desktop = (1920,1080)
        self.configure_clock()

    @property
    def resolutions(self):
        available = [r for r in RESOLUTIONS if r[0]<=self.desktop[0] and r[1]<=self.desktop[1]]
        if self.desktop not in available and min(self.desktop)>=600: available.append(self.desktop)
        current = tuple(self.prefs["resolution"])
        if current not in available: available.append(current)
        return sorted(set(available))

    def configure_clock(self):
        clock = ClockObject.getGlobalClock()
        fps = self.prefs["fps"]
        clock.setMode(ClockObject.MLimited if fps else ClockObject.MNormal)
        if fps: clock.setFrameRate(fps)
        # Panda's renderer observes this config variable; a driver can override it.
        loadPrcFileData("display-options",f"sync-video {'true' if self.prefs['vsync'] else 'false'}")

    def request(self):
        if self.offscreen: return
        mode = self.prefs["display_mode"]
        w,h = self.prefs["resolution"]
        if mode == "Borderless": w,h = self.desktop
        elif mode == "Windowed":
            w,h = min(w,self.desktop[0]),min(h,max(600,self.desktop[1]-70))
        props = WindowProperties()
        props.setFullscreen(mode == "Fullscreen")
        props.setUndecorated(mode == "Borderless")
        props.setSize(w,h)
        props.setOrigin(0,0) if mode == "Borderless" else props.setOrigin(-2,-2)
        self.base.win.requestProperties(props)

    def apply(self,chosen):
        if self.pending is not None: self.revert()
        self.pending = deepcopy(self.prefs)
        self.prefs.update(settings({**self.prefs,**chosen}))
        self.request(); self.configure_clock()
        self.deadline = monotonic()+15

    def confirm(self): self.pending = None

    def revert(self):
        if self.pending is None: return
        old,self.pending = self.pending,None
        self.prefs.clear(); self.prefs.update(old)
        self.request(); self.configure_clock()

    def tick(self):
        if self.pending is not None and monotonic() >= self.deadline:
            self.revert(); return True
        return False

    @property
    def remaining(self): return max(0,int(self.deadline-monotonic()+.999))
