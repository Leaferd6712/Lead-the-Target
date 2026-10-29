"""Reproducible visual QA without changing campaign saves."""
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ["SDL_VIDEODRIVER"]="dummy"
os.environ["SDL_AUDIODRIVER"]="dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"]="1"
import pygame
from game import Game
from ui import Interface
from domain import Scene


def main():
    pygame.init()
    out=Path(__file__).resolve().parents[1]/"artifacts"/"v2"
    out.mkdir(parents=True,exist_ok=True)
    game=Game({},persist=False)
    ui=Interface(game,pygame.display.set_mode((1280,800)))
    def capture(name):
        ui.update(1/60);ui.draw();pygame.image.save(ui.surface,str(out/(name+".png")))
    capture("title")
    game.start_campaign();capture("first-task")
    game.answer("It will hit");capture("incorrect-feedback")
    game.answer(game.step.correct);capture("congratulations")
    game.continue_learning();game.run_experiment()
    for _ in range(105):game.trial.tick()
    capture("direct-miss")
    game.trial.finish();game.finish_experiment();game.continue_learning()
    game.set_algorithm(1);game.set_lead(.8);capture("lead-preview")
    game.run_experiment();game.trial.finish();game.finish_experiment();capture("measured-success")
    game.currency=200;game.open_shop();capture("workshop");game.close_panel()
    game.open_panel(Scene.MAP);capture("skill-map");game.close_panel()
    game.open_panel(Scene.NOTEBOOK);capture("notebook");game.close_panel()
    game.open_panel(Scene.OPTIONS);capture("options");game.close_panel()
    game.stage=5;game.prepare_stage();game.run_experiment()
    for _ in range(300):game.trial.tick()
    capture("pid-live")
    game.enter_sandbox(7);game.set_gains((8,1.5,.4,1));game.begin_wave()
    for _ in range(120*7):game.tick(game.STEP)
    capture("defense")
    game.start_campaign();ui.resize((800,600));game.settings["large_text"]=True
    capture("compact-large-text")
    pygame.quit()
    print("Saved 14 verification screens in",out)


if __name__=="__main__":main()
