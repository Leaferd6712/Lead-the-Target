"""Save recovery, migration and transactional banking."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from domain import Scene
from game import Game
from persistence import load_status, save_progress, validate


class SaveTests(unittest.TestCase):
    def test_legacy_migration_retains_economy_without_fabricating_mastery(self):
        old={"stage":5,"currency":321,"upgrades":{"colour":1},"won":False}
        data=validate(old);game=Game(data,persist=False)
        self.assertEqual(game.currency,321)
        self.assertEqual(game.upgrades["colour"],1)
        self.assertEqual(game.stage,0)
        self.assertEqual(game.learning,{})

    def test_corrupt_primary_recovers_previous_good_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"profile.json"
            self.assertTrue(save_progress(0,40,{},path=path))
            self.assertTrue(save_progress(1,80,{},path=path))
            path.write_text("corrupted",encoding="utf-8")
            data,note=load_status(path)
            self.assertEqual(data["currency"],40)
            self.assertIn("backup",note)

    def test_invalid_settings_are_bounded(self):
        data=validate({"schema":2,"stage":0,"currency":40,"settings":{"volume":float('nan'),"window":[-3,999999]},"gains":[99,-1,2,3]})
        self.assertEqual(data["gains"],[16,0,2,3])
        self.assertEqual(data["settings"]["volume"],.4)
        self.assertEqual(data["settings"]["window"],[800,2160])

    def test_active_wave_does_not_bank_temporary_earnings(self):
        game=Game({},persist=False);game.practice=True;game.begin_wave()
        original=game.currency;game.currency+=32
        self.assertEqual(game.snapshot()["currency"],original)

    def test_actual_save_uses_banked_currency_and_practice_keeps_only_settings(self):
        game=Game({},persist=True);game.mode=Scene.PLAYING
        game.currency=72
        with patch("game.save_progress",return_value=True) as writer:
            game.save()
            self.assertEqual(writer.call_args.args[1],40)
            game.mode=Scene.TITLE;game.currency=40;game.enter_sandbox(7)
            game.currency=9999;game.settings["muted"]=True;game.save()
            self.assertEqual(writer.call_args.args[1],40)
            self.assertTrue(writer.call_args.kwargs["settings"]["muted"])

    def test_restart_and_advance_keep_gains_and_required_evidence(self):
        game=Game({},persist=False);game.prepare_stage();game.set_gains((8,1,.3,1))
        game.stage=1;game.prepare_stage()
        self.assertEqual(game.gains(),(8,1,.3,1))
        self.assertFalse(game.advance())

    def test_corrupt_primary_is_preserved_when_starting_over(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"profile.json";path.write_text("broken",encoding="utf-8")
            self.assertTrue(save_progress(0,40,{},path=path))
            self.assertEqual(path.with_suffix(".json.unreadable").read_text(encoding="utf-8"),"broken")
