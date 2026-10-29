"""LEAD THE TARGET. Dependency: pygame==2.6.1 (pip install -r requirements.txt).

Run: python main.py. Tests: python -m unittest discover -s tests.
"""
import argparse
import os
from pathlib import Path
import sys
from time import perf_counter
from math import ceil


def main():
    parser = argparse.ArgumentParser(description="Lead the Target: physics and control tower defense")
    parser.add_argument("--headless", action="store_true", help="Use SDL dummy video/audio drivers")
    parser.add_argument("--frames", type=int, default=0, help="Exit after this many frames (verification)")
    parser.add_argument("--screenshot", type=Path, help="Save final logical frame as PNG")
    parser.add_argument("--stage", type=int, choices=range(1, 9), help="Preview a lesson without changing saves")
    parser.add_argument("--autoplay", action="store_true", help="Start the selected lesson with a sensible algorithm")
    parser.add_argument("--benchmark", action="store_true", help="Report measured frame processing time")
    args = parser.parse_args()
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    try:
        import pygame
    except ImportError:
        print("Pygame is required. Run: python -m pip install -r requirements.txt", file=sys.stderr)
        return 1
    from game import Game
    from ui import Interface
    pygame.init()
    try:
        pygame.display.set_caption("Lead the Target | Control Quest 3D")
        clock = pygame.time.Clock()
        preview = bool(args.stage or args.frames or args.headless)
        game = Game(saved={} if preview else None, persist=not preview)
        desktop = pygame.display.get_desktop_sizes()[0]
        desired=game.settings["window"]
        size=(max(800,min(desired[0],desktop[0])),max(600,min(desired[1],desktop[1]-60)))
        if args.headless:size=tuple(desired)
        window = pygame.display.set_mode(size, pygame.RESIZABLE)
        if args.stage:
            game.stage = args.stage-1
            game.currency = 200
            if game.stage >= 4:
                game.upgrades["colour"] = 1
            game.prepare_stage()
        if args.autoplay:
            game.practice = True
            game.algorithm = min(game.unlock, 4)
            game.mode = "ready"
            game.begin_wave()
        ui = Interface(game, window)
        frame = 0
        timings=[]
        while not ui.quit:
            dt = 1/60 if args.headless else clock.tick(60)/1000
            started=perf_counter()
            ui.events(pygame.event.get())
            game.update(dt)
            ui.update(dt)
            ui.draw()
            if args.benchmark:timings.append((perf_counter()-started)*1000)
            frame += 1
            if args.frames and frame >= args.frames:
                break
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(ui.surface, str(args.screenshot))
        if timings:
            timings.sort()
            print(f"Frame processing: mean {sum(timings)/len(timings):.2f} ms; p95 {timings[ceil(len(timings)*.95)-1]:.2f} ms; {len(timings)} frames")
        return 0
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
