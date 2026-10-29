"""Real headless rendering, input and navigation checks, including compact mode."""
import os
import unittest
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT","1")
try:
    import pygame
except ImportError:
    pygame=None
from domain import Scene


@unittest.skipIf(pygame is None,"Install requirements.txt for UI tests")
class InterfaceTests(unittest.TestCase):
    def setUp(self):
        from game import Game
        from ui import Interface
        pygame.init()
        self.game=Game({},persist=False)
        self.ui=Interface(self.game,pygame.display.set_mode((1280,800)))

    def tearDown(self):pygame.quit()

    def key(self,key,mod=0):
        self.ui.events([pygame.event.Event(pygame.KEYDOWN,key=key,mod=mod)])

    def click_label(self,label):
        self.ui.draw()
        rect=next(b[0] for b in self.ui.buttons if b[3]==label)
        size=self.ui.window.get_size()
        pos=(rect.centerx*size[0]/self.ui.WIDTH,rect.centery*size[1]/self.ui.HEIGHT)
        self.ui.events([pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=pos),
                        pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=pos)])

    def test_all_screens_and_modal_return_paths_render(self):
        g,ui=self.game,self.ui
        ui.draw();g.start_campaign();ui.draw()
        g.answer(g.step.correct);ui.draw()
        self.assertEqual(g.mode,Scene.CONGRATS)
        self.key(pygame.K_ESCAPE)
        self.assertEqual(g.mode,Scene.CONGRATS)
        g.continue_learning();g.run_experiment()
        for _ in range(60):g.update(1/60)
        ui.draw()
        g.trial.finish();g.finish_experiment();ui.draw()
        g.continue_learning()
        for scene in (Scene.OPTIONS,Scene.MAP,Scene.SHOP,Scene.NOTEBOOK):
            original=g.mode;g.open_panel(scene);ui.draw();self.key(pygame.K_ESCAPE)
            self.assertEqual(g.mode,original)
        ui.ask_confirm("Reset?",lambda:None);ui.draw();g.close_panel()
        g.enter_sandbox(7);g.begin_wave()
        for _ in range(300):g.tick(g.STEP)
        ui.draw();g.paused=True;ui.draw()
        g.finish_wave(False);ui.draw()
        g.mode=Scene.VICTORY;ui.draw()

    def test_keyboard_focus_activates_and_does_not_skip_tasks(self):
        g,ui=self.game,self.ui
        g.start_campaign();ui.draw();self.key(pygame.K_TAB)
        self.assertGreaterEqual(ui.focus,0)
        self.assertFalse(g.advance())
        self.click_label("It will miss behind the tank")
        self.assertEqual(g.mode,Scene.CONGRATS)
        self.click_label("Continue")
        self.assertEqual(g.step.id,"observe")

    def test_pointer_slider_records_a_real_change(self):
        g,ui=self.game,self.ui
        g.start_campaign();g.answer(g.step.correct);g.continue_learning()
        g.run_experiment();g.trial.finish();g.finish_experiment();g.continue_learning()
        g.set_algorithm(1);ui.draw()
        rect=ui.sliders["lead"][0]
        ui.events([pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=rect.center),
                   pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=rect.center)])
        self.assertIn("lead",g.runner.changed)
        self.assertAlmostEqual(g.lead,1,places=1)

    def test_exact_numeric_gain_and_focus_loss_pause(self):
        g,ui=self.game,self.ui
        g.enter_sandbox(7);ui.draw();ui.start_numeric(3)
        ui.editing[1]="1.25";self.key(pygame.K_RETURN)
        self.assertEqual(g.gains()[3],1.25)
        g.begin_wave()
        ui.events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        self.assertTrue(g.paused)

    def test_compact_large_text_has_reachable_primary_buttons(self):
        g,ui=self.game,self.ui
        ui.resize((800,600));g.settings["large_text"]=True;g.start_campaign()
        ui.draw()
        for label in ("It will hit","It will miss behind the tank"):
            rect=next(b[0] for b in ui.buttons if b[3]==label)
            self.assertGreater(rect.height,20)
            self.assertTrue(ui.surface.get_rect().contains(rect))
        g.answer(g.step.correct);ui.draw()
        self.assertTrue(any(b[3]=="Continue" for b in ui.buttons))

    def test_queued_double_click_cannot_activate_previous_scene(self):
        g,ui=self.game,self.ui;g.start_campaign();ui.draw()
        rect=next(b[0] for b in ui.buttons if b[3]=="It will miss behind the tank")
        ui.events([pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=rect.center)]*2)
        self.assertEqual(len(g.learning),1)
        self.assertEqual(g.mode,Scene.CONGRATS)


class CameraTests(unittest.TestCase):
    def test_ground_projection_round_trip_for_multiple_views(self):
        from camera import Camera
        for yaw in (0,25,80,-30):
            camera=Camera(yaw=yaw);camera.fit((20,100,850,440))
            for x,y in ((100,258),(462,435),(848,558)):
                projected=camera.project((x,y,12))
                actual=camera.ground_at(projected,12)
                self.assertAlmostEqual(actual[0],x,places=6)
                self.assertAlmostEqual(actual[1],y,places=6)
