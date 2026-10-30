"""Campaign coverage, construction, settlement, profiles and frame independence."""
import tempfile
from pathlib import Path
import unittest
from campaign import Campaign
from fortress import Emplacement, PADS, restore_towers
from profile_store import load, save, validate, DEFAULTS
from waves import LEVELS


def run(c):
    c.start()
    for _ in range(120*160):
        if not c.running:break
        c.tick()
    return c


class CampaignTests(unittest.TestCase):
    def test_first_level_sensible_default_is_winnable(self):
        c=run(Campaign())
        self.assertTrue(c.success);self.assertEqual(c.kills,5);self.assertGreater(c.hits,0)

    def test_direct_misses_predictive_interception_succeeds(self):
        games=[]
        for algorithm in (0,2):
            c=Campaign();c.level=5;c.towers[0].algorithm=algorithm;run(c);games.append(c)
        self.assertLess(games[0].hits/max(1,games[0].shots),.3)
        self.assertGreater(games[1].hits/max(1,games[1].shots),.75)

    def test_all_100_levels_complete_with_earned_campaign_budget(self):
        c=Campaign()
        for n in range(1,101):
            with self.subTest(level=n):
                # Spend only earned credits; respect all build/model unlocks.
                for pad in range(len(PADS)):
                    if not any(t.pad==pad for t in c.towers) and c.credits>=90:
                        c.build('standard',pad)
                for t in c.towers:
                    c.selected_id=t.id;t.algorithm=c.unlock;t.gains=[8,1.5,.3,1]
                    if n>=31 and not t.colour and c.credits>=80:c.buy_colour()
                    while t.level<3 and c.credits>=t.upgrade_cost:c.upgrade()
                run(c)
                self.assertTrue(c.finished);self.assertTrue(c.success,(n,c.health,c.kills,c.shots))
                self.assertGreaterEqual(c.credits,0)
                if n<100:self.assertTrue(c.next_level())

    def test_spawns_sorted_varied_and_multiple_entrances(self):
        self.assertEqual(len(LEVELS),100)
        for level in LEVELS:
            self.assertEqual(list(level.spawns),sorted(level.spawns,key=lambda s:s.time))
        self.assertEqual(len({s.entrance for s in LEVELS[0].spawns}),1)
        self.assertGreater(len({s.entrance for s in LEVELS[20].spawns}),1)
        self.assertEqual({s.behaviour for s in LEVELS[99].spawns},{'constant','boost','brake','switch'})

    def test_build_placement_cost_unlock_and_independent_settings(self):
        c=Campaign();before=c.credits
        self.assertTrue(c.build('standard',1));self.assertEqual(c.credits,before-90)
        self.assertFalse(c.build('standard',1));self.assertFalse(c.build('heavy',2))
        c.selected.lead=1.2;self.assertEqual(c.towers[0].lead,.8)
        c.copy_configuration();self.assertEqual(c.towers[0].lead,1.2)

    def test_replay_preserves_technology_and_unlocked_towers(self):
        c=Campaign();c.completed={'50':16};c.level=1;c.credits=400
        self.assertEqual(c.unlock,4);self.assertTrue(c.build('tracking',1))
        self.assertTrue(c.buy_colour())

    def test_rewards_idempotent_and_loss_does_not_bank_kills(self):
        c=run(Campaign());bank=c.credits;c.finish();self.assertEqual(c.credits,bank)
        c=Campaign();c.start();c.pending_credits=40;c.health=0;c.finish()
        self.assertEqual(c.credits,160)

    def test_relocate_cannot_bankrupt_or_remove_all_defenders(self):
        c=Campaign();c.credits=0;c.health=0;c.finished=True
        self.assertTrue(c.relocate());self.assertGreaterEqual(c.credits,90);self.assertEqual(len(c.towers),1)
        self.assertFalse(c.sell())

    def test_colour_sensor_changes_actual_branch(self):
        c=Campaign();c.level=31;c.credits=200;c.selected.algorithm=4
        self.assertTrue(c.buy_colour());c.start()
        for _ in range(120*4):c.tick()
        self.assertIsNotNone(c.selected.solution)
        self.assertNotIn('NO COLOUR',c.selected.solution.branch)
        c.selected.sensor_enabled=False
        for _ in range(5):c.tick()
        self.assertIn('NO COLOUR',c.selected.solution.branch)

    def test_simulation_independent_of_render_fps(self):
        outcomes=[]
        for fps in (30,60,144,240):
            c=Campaign();c.start()
            for _ in range(fps*10):c.update(1/fps)
            outcomes.append((c.shots,c.hits,round(c.time,5)))
        self.assertEqual(len(set(outcomes)),1)

    def test_profile_roundtrip_and_invalid_towers(self):
        c=Campaign();c.build('standard',1)
        profile={'schema':3,'campaign':c.snapshot(),'academy':{},'settings':DEFAULTS,'records':{}}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'profile3.json';self.assertTrue(save(profile,path))
            result,note=load(path);self.assertEqual(len(result['campaign']['towers']),2)
            self.assertEqual(result['campaign']['level'],1)
        self.assertEqual(restore_towers([{'id':1,'pad':False}]),[])
        self.assertEqual(validate({'schema':3,'campaign':{'level':float('nan')},'settings':{'fps':999}})['settings']['fps'],60)


if __name__=='__main__':unittest.main()
