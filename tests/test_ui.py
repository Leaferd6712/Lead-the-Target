"""Real Panda3D offscreen rendering and DirectGUI command-path regressions."""
import unittest
from app import LeadTheTarget
from domain import Scene


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=LeadTheTarget(offscreen=True,preview=True)

    @classmethod
    def tearDownClass(cls):cls.app.destroy()

    def setUp(self):
        self.app.navigate('title');self.app.prefs['compact']=False
        self.app.ui.signature=None;self.app.ui.refresh()

    def test_all_screens_render(self):
        a=self.app
        for screen in ('title','map','academy_hub','records','campaign','options'):
            a.navigate(screen);a.ui.refresh();a.graphicsEngine.renderFrame()
        a.enter_academy(0);a.ui.refresh();a.answer(a.academy.step.correct);a.ui.refresh()
        self.assertEqual(a.academy.mode,Scene.CONGRATS)

    def test_lead_slider_native_callback_and_numeric_share_state(self):
        a=self.app;a.enter_campaign();a.ui.refresh()
        a.ui.set_slider('lead',1.25)
        self.assertAlmostEqual(a.campaign.selected.lead,1.25)
        slider=a.ui.sliders['lead'];a.ui.refresh()
        self.assertIs(a.ui.sliders['lead'],slider)
        a.adjust_lead(-.05);self.assertAlmostEqual(a.campaign.selected.lead,1.2)

    def test_fixed_lesson_auto_selects_required_model(self):
        a=self.app
        from game import Game
        a.academy=Game({},persist=False);a.enter_academy(0)
        a.answer(a.academy.step.correct);a.continue_academy();a.run_experiment()
        a.academy.trial.finish();a.academy.finish_experiment();a.continue_academy()
        self.assertEqual(a.academy.step.scenario,'fixed');self.assertEqual(a.academy.algorithm,1)
        a.ui.refresh();a.ui.set_slider('lead',.8);a.run_experiment()
        a.academy.trial.finish();a.academy.finish_experiment()
        self.assertEqual(a.academy.mode,Scene.CONGRATS)

    def test_display_settings_roundtrip_and_timeout(self):
        a=self.app;old=dict(a.prefs)
        a.display.apply({'resolution':[1920,1080],'fps':144});self.assertEqual(a.prefs['fps'],144)
        a.display.deadline=0;self.assertTrue(a.display.tick());self.assertEqual(a.prefs,old)

    def test_display_choices_survive_accessibility_and_vsync_changes(self):
        from direct.gui.DirectOptionMenu import DirectOptionMenu
        a=self.app;a.open_options();a.ui.refresh()
        menus=[w for w in a.ui.widgets if isinstance(w,DirectOptionMenu)]
        menus[0].set(menus[0]['items'].index('1600 x 900'))
        menus[2].set(menus[2]['items'].index('144'))
        muted=a.prefs['muted'];a.toggle_pref('muted');a.toggle_display_vsync();a.ui.refresh()
        next(action for button,action,title in a.ui.buttons if title=='APPLY DISPLAY')()
        self.assertEqual(a.prefs['resolution'],[1600,900]);self.assertEqual(a.prefs['fps'],144)
        self.assertEqual(a.prefs['muted'],not muted)
        a.revert_display();a.close_options()

    def test_compact_is_bottom_and_can_expand(self):
        a=self.app;a.enter_campaign();a.toggle_compact();a.ui.refresh()
        self.assertTrue(a.scene.compact)
        slider=a.ui.sliders['lead'];self.assertLess(slider.getZ(),-600)
        a.toggle_compact();a.ui.refresh();self.assertFalse(a.scene.compact)

    def test_contract_cannot_reward_twice(self):
        a=self.app;a.campaign.running=False;a.recovery();a.ui.refresh();bank=a.campaign.credits
        a.answer_contract('wrong');self.assertEqual(a.campaign.credits,bank)
        a.answer_contract(a.contract['answer']);a.answer_contract(a.contract['answer'])
        self.assertEqual(a.campaign.credits,bank+20)

    def test_calibration_displays_the_actual_active_gains(self):
        a=self.app;a.enter_academy(7)
        from experiments import Experiment
        a.academy.trial=Experiment('f_base',a.academy.strategies,4,.8,(8,1,.7,2),True)
        a.academy.mode=Scene.EXPERIMENT;a.ui.refresh()
        self.assertIn('I 0.00',a.ui.labels['actual_gains'].getText())
        self.assertIn('F 0.00',a.ui.labels['actual_gains'].getText())


if __name__=='__main__':unittest.main()
