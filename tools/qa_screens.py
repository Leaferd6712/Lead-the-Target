"""Capture genuine Panda3D screens for visual QA and the official website."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from panda3d.core import Filename
from app import LeadTheTarget
from fortress import Emplacement


def main():
    root=Path(__file__).resolve().parents[1]
    out=root/'website'/'images';out.mkdir(parents=True,exist_ok=True)
    a=LeadTheTarget(offscreen=True,preview=True,resolution=(1600,1000))
    def capture(name):
        a.ui.signature=None;a.ui.refresh();a.sync_scene()
        for _ in range(3):a.graphicsEngine.renderFrame()
        path=out/(name+'.png')
        if not a.win.saveScreenshot(Filename.fromOsSpecific(str(path))):raise RuntimeError(path)
        print(path)
    try:
        c=a.campaign;c.level=34;c.credits=410
        c.towers=[Emplacement(i+1,pad,'heavy' if i==2 else 'standard',1,4,.8,[8,0,0,0],True)
                  for i,pad in enumerate((0,1,2,3,8))]
        a.enter_campaign();c.start()
        for _ in range(120*8):c.tick()
        capture('campaign')
        a.toggle_compact();capture('compact')
        a.toggle_compact();a.enter_academy(0);capture('academy')
        a.open_options();capture('options')
        a.navigate('map');a.map_page=3;capture('campaign-map')
    finally:a.destroy()


if __name__=='__main__':main()
