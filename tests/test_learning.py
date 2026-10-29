"""Progression regressions and a complete learner journey using real simulations."""
import unittest
from curriculum import LessonRunner, STEPS
from domain import Scene, TrialMetrics
from experiments import Experiment
from game import Game
from targeting import Vec2


def perform_trial(game):
    kind = game.step.scenario
    if kind in ("direct",):game.set_algorithm(0)
    elif kind == "fixed":
        game.set_algorithm(1)
        game.set_lead(.8)
    elif kind in ("intercept", "fast", "accel_cv"):game.set_algorithm(2)
    elif kind in ("accel_adaptive", "decelerate"):game.set_algorithm(3)
    elif kind.startswith("colour_"):
        game.set_algorithm(4)
        if game.colour_enabled != (kind != "colour_off"):game.toggle_colour()
    elif kind.endswith("tune"):
        index = "pidf".index(kind[0])
        game.change_gain(index,(8,1.5,.4,1)[index])
    game.run_experiment()
    game.trial.finish()
    game.finish_experiment()


class LearningTests(unittest.TestCase):
    def test_complete_campaign_requires_and_records_all_tasks(self):
        game=Game({},persist=False)
        game.start_campaign()
        completed=[]
        for _ in range(180):
            if game.mode == Scene.VICTORY:break
            if game.mode == Scene.CONGRATS:
                completed.append(game.runner.pending)
                game.continue_learning()
                continue
            self.assertEqual(game.mode,Scene.COACH)
            step=game.step
            if step.kind == "choice":game.answer(step.correct)
            elif step.kind == "purchase":
                game.open_shop();game.buy("colour");game.close_panel();game.verify_sensor()
            elif step.kind == "trial":
                perform_trial(game)
                self.assertEqual(game.mode,Scene.CONGRATS,(step.id,game.runner.feedback))
            elif step.kind == "wave":
                game.set_algorithm((1,1,2,3,4,4,4,4)[game.stage])
                game.begin_wave()
                for _ in range(120*100):
                    if game.mode != Scene.PLAYING:break
                    game.tick(game.STEP)
                self.assertTrue(game.success,(game.stage,game.hits,game.shots))
        self.assertEqual(game.mode,Scene.VICTORY)
        self.assertTrue(game.won)
        self.assertEqual(len(game.learning),sum(map(len,STEPS)))
        self.assertEqual(len(completed),len(set(completed)))
        self.assertTrue(all(v["acknowledged"] for v in game.learning.values()))

    def test_page_navigation_or_final_settings_cannot_advance(self):
        game=Game({},persist=False)
        game.prepare_stage()
        self.assertFalse(game.advance())
        self.assertFalse(game.begin_wave())
        game.set_gains((8,1,.3,1))
        self.assertEqual(len(game.learning),0)
        game.answer("It will hit")
        self.assertEqual(len(game.learning),0)
        self.assertIn("Not yet",game.runner.feedback)

    def test_congratulations_is_explicit_and_reward_once_only(self):
        game=Game({},persist=False);game.prepare_stage()
        currency=game.currency
        game.answer(game.step.correct)
        self.assertEqual(game.mode,Scene.CONGRATS)
        self.assertEqual(game.currency,currency+10)
        game.complete_step()
        self.assertEqual(game.currency,currency+10)
        game.answer("anything")
        self.assertEqual(len(game.learning),1)
        game.continue_learning()
        self.assertEqual(game.step.id,"observe")

    def test_pidf_cannot_award_positive_term_without_measured_improvement(self):
        game=Game({},persist=False)
        for stage,base_kind,tune_kind,term in ((6,"i_base","i_tune",1),(6,"d_base","d_tune",2),(7,"f_base","f_tune",3)):
            records={}
            runner=LessonRunner(stage,records)
            # Complete earlier tasks only for arranging the test at its baseline.
            while runner.step.scenario != base_kind:
                runner.award({});runner.acknowledge()
            base=Experiment(base_kind,game.strategies,4,.8,(8,0,0,0),True).finish()
            self.assertTrue(runner.assess(base));runner.acknowledge()
            tune=Experiment(tune_kind,game.strategies,4,.8,(8,0,0,0),True).finish()
            runner.changed.add("pidf"[term])
            self.assertFalse(runner.assess(tune))
            self.assertNotIn(runner.key(runner.step),records)

    def test_acceleration_trial_has_distinct_outcomes(self):
        game=Game({},persist=False)
        cv=Experiment("accel_cv",game.strategies,2,.8,(4,0,0,0),False).finish()
        adaptive=Experiment("accel_adaptive",game.strategies,3,.8,(4,0,0,0),False).finish()
        self.assertFalse(cv.hit)
        self.assertTrue(adaptive.hit)
        self.assertLess(adaptive.miss_distance,cv.miss_distance*.65)
        self.assertNotIn("rms_error",adaptive.evidence())

    def test_shop_navigation_never_returns_to_stale_result(self):
        game=Game({},persist=False)
        game.practice=True;game.stage=3;game.prepare_stage()
        game.mode=Scene.RESULT;game.success=True
        game.open_shop();game.close_panel()
        game.stage=4;game.prepare_stage()
        game.upgrades["colour"]=0
        game.mode=Scene.READY
        self.assertFalse(game.begin_wave())
        self.assertEqual(game.mode,Scene.SHOP)
        game.currency=80;game.buy("colour");game.close_panel()
        self.assertEqual(game.mode,Scene.READY)
        self.assertFalse(game.success)
        game.practice=False
        self.assertFalse(game.advance())

    def test_gain_retention_and_resume_pending_congratulations(self):
        game=Game({},persist=False);game.prepare_stage()
        game.set_gains((8,1,.3,1));game.answer(game.step.correct)
        resumed=Game(game.saved,persist=False);resumed.start_campaign()
        self.assertEqual(resumed.mode,Scene.CONGRATS)
        self.assertEqual(resumed.gains(),(8,1,.3,1))
        resumed.continue_learning()
        self.assertEqual(resumed.step.id,"observe")

    def test_stationary_target_is_valid_and_fires(self):
        game=Game({},persist=False);game.practice=True;game.spawn()
        game.tanks[0].speed=0;game.spawned=game.lesson.count;game.mode=Scene.PLAYING
        for _ in range(120*3):game.tick(game.STEP)
        self.assertGreater(game.shots,0)

    def test_shot_resolution_precedes_wave_report_and_rewards_are_idempotent(self):
        game=Game({},persist=False);game.practice=True;game.begin_wave()
        game.spawned=game.lesson.count;game.tanks=[]
        shot=game.tower.fire(240,1);shot.record_id=0
        from domain import ShotRecord
        game.records=[ShotRecord(0,1,0,game.gains(),0,(200,200),"test")]
        game.projectiles=[shot];game.tick(game.STEP)
        self.assertEqual(game.mode,Scene.PLAYING)
        game.projectiles=[];game.finish_wave(True)
        currency=game.currency;game.finish_wave(True)
        self.assertEqual(game.currency,currency)

    def test_practice_never_saves_its_credits_or_mastery(self):
        game=Game({},persist=False);game.prepare_stage()
        saved=game.snapshot();game.enter_sandbox(7)
        game.currency=10000;game.save();game.start_campaign()
        self.assertEqual(game.currency,saved["currency"])
        self.assertFalse(game.practice)
