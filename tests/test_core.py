"""Deterministic checks of the physics, controllers and learning progression."""
import json
import math
from pathlib import Path
import tempfile
import unittest

from control import PIDFController, wrap_angle
from game import Game
from persistence import load_progress, save_progress
from sensors import SensorSuite
from simulation import Demonstration, Path as Road, Projectile, Tank, swept_hit
from targeting import (Vec2, TargetObservation, ConstantVelocityStrategy,
                       ColourAwareStrategy, solve_constant_velocity_intercept,
                       solve_predicted_intercept)


def run_wave(stage, algorithm, kp=8, upgrades=None):
    game = Game({}, persist=False)
    game.practice = True
    game.stage = stage
    game.upgrades["colour"] = int(stage >= 4)
    if upgrades:
        game.upgrades.update(upgrades)
    game.prepare_stage()
    game.algorithm = algorithm
    if algorithm == 1:
        game.set_lead(.8)
    game.tower.controller.kp = kp
    game.begin_wave()
    for _ in range(120*110):
        if game.mode != "playing":
            break
        game.tick(game.STEP)
    return game


class PredictionTests(unittest.TestCase):
    def test_stationary_target(self):
        self.assertAlmostEqual(solve_constant_velocity_intercept(
            Vec2(0, 0), Vec2(300, 0), Vec2(0, 0), 100), 3)

    def test_equal_speed_linear_case(self):
        self.assertAlmostEqual(solve_constant_velocity_intercept(
            Vec2(0, 0), Vec2(100, 0), Vec2(-100, 0), 100), 0.5)

    def test_unreachable_target(self):
        self.assertIsNone(solve_constant_velocity_intercept(
            Vec2(0, 0), Vec2(100, 0), Vec2(200, 0), 100))
        self.assertIsNone(solve_constant_velocity_intercept(
            Vec2(0, 0), Vec2(100, 0), Vec2(100, 0), 100))

    def test_intercept_residuals(self):
        for velocity in (Vec2(20, 30), Vec2(-50, 5), Vec2(0, 100)):
            r = Vec2(230, 130)
            t = solve_constant_velocity_intercept(Vec2(0, 0), r, velocity, 240)
            self.assertAlmostEqual((r+velocity*t).length(), 240*t, places=6)

    def test_bounded_nonlinear_solver(self):
        forecast = lambda t: Vec2(100+10*t*t, 0)
        t = solve_predicted_intercept(Vec2(0, 0), 150, forecast)
        self.assertAlmostEqual(forecast(t).length(), 150*t, places=5)
        self.assertIsNone(solve_predicted_intercept(Vec2(0, 0), 0, forecast))

    def test_repeatable_comparison(self):
        demo = Demonstration()
        # Closest approach of direct shot and moving target still misses by >50px.
        relative_velocity = demo.direct_velocity-demo.velocity
        r = demo.origin-demo.start
        closest_time = -r.dot(relative_velocity)/relative_velocity.dot(relative_velocity)
        self.assertGreater((r+relative_velocity*closest_time).length(), 50)
        tank = demo.start+demo.velocity*demo.intercept_time
        shell = demo.origin+demo.lead_velocity*demo.intercept_time
        self.assertLess((tank-shell).length(), 1e-6)

    def test_path_boundaries_and_turn(self):
        road = Road()
        self.assertEqual(road.point_at(-10), road.points[0])
        self.assertEqual(road.point_at(road.length+50), road.points[-1])
        self.assertEqual(road.point_at(784+100), Vec2(848, 358))

    def test_swept_collision(self):
        tank = Tank(1, Road())
        tank.position = tank.previous = Vec2(50, 100)
        projectile = Projectile(Vec2(100, 100), Vec2(1000, 0), previous=Vec2(0, 100))
        self.assertTrue(swept_hit(projectile, tank))
        tank.position = tank.previous = Vec2(50, 125)
        self.assertFalse(swept_hit(projectile, tank))


class SensorTests(unittest.TestCase):
    def test_sensor_gates_colour(self):
        tank = Tank(1, Road(), colour="red")
        hidden, visible = SensorSuite(), SensorSuite(colour=True)
        hidden.update([tank], 0)
        visible.update([tank], 0)
        self.assertIsNone(hidden.read(0)[0].colour)
        self.assertEqual(visible.read(0)[0].colour, "red")

    def test_velocity_is_measured_not_read_from_tank(self):
        tank = Tank(1, Road(), speed=999)
        sensor = SensorSuite()
        sensor.update([tank], 0)
        self.assertEqual(sensor.read(0)[0].velocity, Vec2(0, 0))
        tank.position += Vec2(10, 0)
        sensor.update([tank], 0.2)
        self.assertAlmostEqual(sensor.read(0.2)[0].velocity.x, 50)

    def test_colour_branches_and_fallback(self):
        road = Road()
        strategy = ColourAwareStrategy(road)
        results = []
        for colour in (None, "red", "gold", "blue"):
            obs = TargetObservation(1, road.point_at(110), Vec2(80, 0), Vec2(0, 0), 110, 0, colour)
            result = strategy.aim(Vec2(462, 435), obs, 240)
            self.assertTrue(result.valid)
            results.append(result)
        self.assertEqual(len({r.branch for r in results}), 4)
        self.assertNotAlmostEqual(results[1].point.x, results[2].point.x)


class ControllerTests(unittest.TestCase):
    def test_shortest_rotation(self):
        self.assertAlmostEqual(math.degrees(wrap_angle(math.radians(-358))), 2)

    def test_terms_and_saturation(self):
        controller = PIDFController()
        controller.kp, controller.ki, controller.kd, controller.kf = 2, 1, 0.5, 1
        sample = controller.update(0.2, 0, 0.1, 0.1, 2)
        self.assertAlmostEqual(sample.p, 0.4)
        self.assertGreater(sample.i, 0)
        self.assertLess(sample.d, 0)
        self.assertEqual(sample.f, 0)
        sample = controller.update(0.3, 0, 0.1, 0.1, 2)
        self.assertAlmostEqual(sample.f, 1)
        self.assertAlmostEqual(sample.requested, sample.p+sample.i+sample.d+sample.f)
        sample = controller.update(3, 0, 0, 0.1, 0.2)
        self.assertLessEqual(abs(sample.output), 0.2)

    def test_anti_windup_and_reset(self):
        controller = PIDFController()
        controller.ki = 2
        for _ in range(1000):
            controller.update(2, 0, 0, 0.01, 0.1)
        self.assertAlmostEqual(controller.integral, 0)
        controller.reset()
        self.assertEqual(controller.sample.error, 0)
        self.assertIsNone(controller.last_desired)

    def test_integral_rejects_static_motor_bias(self):
        def settle(ki):
            c = PIDFController()
            c.kp, c.ki = 4, ki
            angle = rate = 0.0
            for _ in range(120*30):
                dt = 1/120
                sample = c.update(0, angle, rate, dt, 2, 0.15)
                rate += (sample.output+0.15-rate)*(1-math.exp(-dt/0.22))
                angle = wrap_angle(angle+rate*dt)
            return abs(angle)
        self.assertLess(settle(1), settle(0)*0.02)


class CampaignTests(unittest.TestCase):
    def test_every_lesson_can_be_completed(self):
        for stage, strategy in enumerate((1, 1, 2, 3, 4, 4, 4, 4)):
            with self.subTest(stage=stage+1):
                game = run_wave(stage, strategy)
                self.assertEqual(game.mode, "result")
                self.assertTrue(game.success)
                self.assertGreater(game.health, 0)
                self.assertLess(game.time, 60)

    def test_current_position_fails_predictive_targeting_succeeds(self):
        direct, intercept = run_wave(2, 0), run_wave(2, 2)
        self.assertFalse(direct.success)
        self.assertTrue(intercept.success)
        self.assertGreater(intercept.hits/intercept.shots, 0.9)
        self.assertLess(direct.hits/direct.shots, 0.2)

    def test_fixed_lead_breaks_under_changing_motion(self):
        fixed, adaptive = run_wave(3, 1), run_wave(3, 3)
        self.assertFalse(fixed.success)
        self.assertTrue(adaptive.success)
        self.assertGreater(adaptive.hits/adaptive.shots, fixed.hits/fixed.shots)

    def test_sensor_required_upgrade_cannot_softlock(self):
        game = Game({}, persist=False)
        game.practice = True
        game.stage, game.currency = 4, 0
        game.prepare_stage()
        self.assertGreaterEqual(game.currency, 80)
        game.mode = "ready"
        game.begin_wave()
        self.assertEqual(game.mode, "shop")
        game.buy("colour")
        self.assertEqual(game.upgrades["colour"], 1)
        self.assertTrue(game.sensors.colour)

    def test_retry_rolls_back_wave_rewards_and_retains_tuning(self):
        game = run_wave(2, 2)
        original = game.checkpoint[0]
        game.tower.controller.kp = 7
        game.retry()
        self.assertEqual(game.currency, original)
        self.assertEqual(game.tower.controller.kp, 7)
        self.assertEqual(game.hits, 0)

    def test_fixed_timestep_frame_rate_independence(self):
        games = []
        for fps in (30, 60, 120):
            game = Game({}, persist=False)
            game.practice = True
            game.stage, game.algorithm = 2, 2
            game.prepare_stage()
            game.begin_wave()
            for _ in range(fps*5):
                game.update(1/fps)
            games.append(game)
        self.assertEqual({g.shots for g in games}, {games[0].shots})
        self.assertEqual({g.hits for g in games}, {games[0].hits})
        self.assertLess(max(g.time for g in games)-min(g.time for g in games), 0.009)


class PersistenceTests(unittest.TestCase):
    def test_round_trip_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"save.json"
            self.assertTrue(save_progress(4, 92, {"colour": 1}, path=path))
            self.assertEqual(load_progress(path)["currency"], 92)
            path.write_text(json.dumps({"stage": True}), encoding="utf-8")
            self.assertEqual(load_progress(path), {})
            path.write_text("broken", encoding="utf-8")
            self.assertEqual(load_progress(path), {})


if __name__ == "__main__":
    unittest.main()
