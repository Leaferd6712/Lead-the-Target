"""Dependency: panda3d==1.10.16. Install: python -m pip install -r requirements.txt.

Run: python main.py. Tests: python -m unittest discover -s tests.
"""
import argparse
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description='Lead the Target / Panda3D fortress control')
    parser.add_argument('--headless',action='store_true',help='Offscreen software rendering; no profile changes')
    parser.add_argument('--frames',type=int,default=0,help='Exit after a measured number of frames')
    parser.add_argument('--screenshot',type=Path)
    parser.add_argument('--level',type=int,choices=range(1,101),help='Preview campaign level without saving')
    parser.add_argument('--stage',type=int,choices=range(1,9),help='Preview academy lesson without saving')
    parser.add_argument('--autoplay',action='store_true',help='Start a preview attack')
    parser.add_argument('--compact',action='store_true')
    parser.add_argument('--resolution',default=None,help='WIDTHxHEIGHT, for example 1920x1080')
    args=parser.parse_args()
    resolution=None
    if args.resolution:
        try:
            resolution=tuple(int(v) for v in args.resolution.lower().split('x'))
            if len(resolution)!=2 or not 800<=resolution[0]<=3840 or not 600<=resolution[1]<=2160:raise ValueError()
        except ValueError:parser.error('Resolution must be WIDTHxHEIGHT within 800x600 to 3840x2160.')
    try:from app import LeadTheTarget
    except ImportError as error:
        print(f'Missing dependency: {error}. Run python -m pip install -r requirements.txt');return 1
    app=LeadTheTarget(offscreen=args.headless,preview=bool(args.headless or args.frames or args.level or args.stage),resolution=resolution)
    try:
        if args.compact:app.prefs['compact']=True;app.scene.compact=True;app.scene.resize()
        if args.level:app.enter_campaign(args.level)
        if args.stage:app.enter_academy(args.stage-1)
        if args.autoplay:
            if args.stage:
                app.academy.enter_sandbox(args.stage-1);app.screen='academy';app.academy.begin_wave()
            else:
                app.enter_campaign(args.level or 1)
                c=app.campaign;c.credits=2000
                for pad in (1,2,3):c.build('standard',pad)
                for t in c.towers:t.algorithm=min(c.unlock,4)
                c.start()
        if args.frames:
            for _ in range(args.frames):app.taskMgr.step()
        else:app.run()
        if args.screenshot:
            from panda3d.core import Filename
            args.screenshot.parent.mkdir(parents=True,exist_ok=True)
            app.graphicsEngine.renderFrame()
            if not app.win.saveScreenshot(Filename.fromOsSpecific(str(args.screenshot.resolve()))):
                raise RuntimeError(f'Could not write screenshot: {args.screenshot}')
        return 0
    finally:app.destroy()


if __name__=='__main__':raise SystemExit(main())
