"""Campaign, guided experiments and field combat. No pygame drawing calls."""
from collections import deque
from copy import deepcopy
from math import atan2, radians
from control import wrap_angle
from curriculum import LessonRunner, STEPS
from domain import Scene, SceneRouter, LessonEvent, ShotRecord
from experiments import Experiment
from lessons import LESSONS, UPGRADES
from targeting import (CurrentPositionStrategy, FixedLeadStrategy, ConstantVelocityStrategy,
                           AdaptiveStrategy, ColourAwareStrategy, TargetSelector, Vec2)
from simulation import Path, Tank, Tower, swept_impact_time
from sensors import SensorSuite
from persistence import load_status, save_progress, DEFAULT_SETTINGS


class Game:
    STEP = 1/120
    RANGE = 530

    def __init__(self, saved=None, persist=True):
        self.persist = persist
        self.saved, self.save_note = load_status() if saved is None else (deepcopy(saved), "")
        self.router = SceneRouter()
        self.settings = {**DEFAULT_SETTINGS, **self.saved.get("settings", {})}
        self.stage = self.saved.get("stage", 0)
        self.currency = self.saved.get("currency", 40)
        self.upgrades = {k: self.saved.get("upgrades", {}).get(k, 0) for k in UPGRADES}
        self.learning = deepcopy(self.saved.get("learning", {}))
        self.completion = deepcopy(self.saved.get("completion", {}))
        self.won = self.saved.get("won", False)
        if self.saved.get("legacy"):
            self.stage, self.won = 0, False
        self.sandbox = False
        self.practice = False
        self.path = Path()
        self.strategies = [CurrentPositionStrategy(), FixedLeadStrategy(), ConstantVelocityStrategy(),
                           AdaptiveStrategy(), ColourAwareStrategy(self.path)]
        self.algorithm = self.saved.get("algorithm", 0)
        self.lead = self.saved.get("lead", 0.3)
        self.tuning = tuple(self.saved.get("gains", (4, 0, 0, 0)))
        self.speed, self.overlay, self.colour_enabled = 1.0, True, True
        self.toast, self.toast_time = "", 0
        self.events = deque(maxlen=240)
        self.runner = LessonRunner(self.stage, self.learning)
        self.trial = None
        self.last_trial = None
        self.replay_trial = False
        self.replay_title = "Experiment replay"
        self.reset_world()
        self.checkpoint = (self.currency, dict(self.upgrades))

    @property
    def mode(self): return self.router.scene

    @mode.setter
    def mode(self, value): self.router.go(value)

    @property
    def lesson(self): return LESSONS[self.stage]

    @property
    def unlock(self): return 4 if self.practice else self.lesson.unlock

    @property
    def controlled(self): return self.stage >= 5

    @property
    def shell_speed(self): return 240+30*self.upgrades["shell"]

    @property
    def bias(self): return radians(9) if self.stage >= 6 else 0

    @property
    def step(self): return self.runner.step

    def emit(self, event_kind, **data):
        self.events.append(LessonEvent(event_kind, self.time, data))

    def reset_world(self):
        self.tanks, self.projectiles, self.effects = [], [], []
        self.tower = Tower()
        self.set_gains(self.tuning)
        self.sensors = SensorSuite(bool(self.upgrades["colour"] and self.colour_enabled), self.upgrades["sensor"])
        self.selector = TargetSelector()
        self.time = self.accumulator = self.spawn_clock = 0.0
        self.spawned = self.shots = self.hits = self.kills = self.leaks = self.earned = 0
        self.health = 16
        self.solution = self.selected = None
        self.history = deque(maxlen=360)
        self.history_clock = 0.0
        self.paused = False
        self.success = False
        self.result_hint = ""
        self.records = []
        self.last_target = None
        self.wait_reason = "Waiting for observation"
        self.wave_finished = False
        self.hold_angle = self.tower.angle

    def notify(self, message):
        self.toast, self.toast_time = message, 7

    def snapshot(self):
        banked = self.checkpoint[0] if self.mode == Scene.PLAYING else self.currency
        return {"schema": 2, "stage": self.stage, "currency": banked,
                "upgrades": dict(self.upgrades), "won": self.won,
                "learning": deepcopy(self.learning), "completion": deepcopy(self.completion),
                "algorithm": self.algorithm, "lead": self.lead, "gains": list(self.gains()),
                "settings": deepcopy(self.settings)}

    def save(self):
        if self.practice:
            # Preferences apply everywhere; practice economy and mastery do not.
            self.saved["settings"] = deepcopy(self.settings)
        else:
            self.saved = self.snapshot()
        if self.persist:
            data = dict(self.saved)
            profile = dict(self.saved)
            for k in ("schema", "stage", "currency", "upgrades", "won"):
                data.pop(k, None)
            if not save_progress(profile.get("stage",0), profile.get("currency",40), profile.get("upgrades",{}), profile.get("won",False), **data):
                self.save_note = "Save unavailable. Progress remains in this session; check folder permissions."
                self.notify(self.save_note)

    def start_campaign(self, new=False):
        if self.practice:
            self.__init__(self.saved, self.persist)
        if new:
            settings = dict(self.settings)
            self.__init__({}, self.persist)
            self.settings = settings
        self.prepare_stage()

    def prepare_stage(self):
        self.tuning = self.gains()
        self.algorithm = min(self.algorithm, self.unlock)
        self.reset_world()
        self.trial = None
        self.runner = LessonRunner(self.stage, self.learning)
        if self.stage == 4 and not self.upgrades["colour"] and self.currency < 80:
            grant = 80-self.currency
            self.currency += grant
            self.notify(f"Sensor research grant: +{grant} credits. Your base is rebuilt for each field lesson.")
        self.mode = Scene.READY if self.practice else Scene.CONGRATS if self.runner.pending else Scene.COACH
        if self.completion.get(str(self.stage)) and not self.runner.pending:
            self.mode = Scene.CONGRATS
        if self.won and self.runner.complete and not self.runner.pending and not self.practice:
            self.mode = Scene.VICTORY
        self.save()

    def open_shop(self):
        self.router.open(Scene.SHOP)

    def open_panel(self, scene):
        self.router.open(scene)

    def close_panel(self):
        self.router.close()
        self.save()

    def answer(self, value):
        if self.mode != Scene.COACH or self.practice or self.runner.pending:
            return
        self.emit("answer", value=value)
        if self.runner.answer(value): self.complete_step()

    def complete_step(self):
        key = self.runner.pending
        if not key:
            return
        record = self.learning[key]
        record["evidence"].update({"lead": self.lead, "colour_enabled": self.colour_enabled})
        if not record.get("rewarded"):
            self.currency += 10
            record["rewarded"] = True
        self.emit("step_completed", step=key)
        self.mode = Scene.CONGRATS
        self.save()

    def continue_learning(self):
        if self.mode != Scene.CONGRATS:
            return
        self.runner.acknowledge()
        if self.runner.complete:
            self.advance()
        else:
            self.mode = Scene.COACH
            self.save()

    def verify_sensor(self):
        if self.step and self.step.kind == "purchase" and self.upgrades["colour"]:
            tank = Tank(1, self.path, colour="red")
            sensor = SensorSuite(True)
            sensor.update([tank], 0)
            if sensor.read(0)[0].colour == "red":
                self.runner.award({"sensor": "colour", "observed": "red"})
                self.complete_step()
        else:
            self.runner.fail("Install the colour sensor in Workshop, then return to verify it.")

    def run_experiment(self):
        step = self.step
        if self.mode != Scene.COACH or step is None or step.kind != "trial" or self.runner.pending:
            return
        self.trial = Experiment(step.scenario, self.strategies, self.algorithm, self.lead,
                                self.gains(), bool(self.upgrades["colour"] and self.colour_enabled))
        self.last_trial = (step.scenario, self.algorithm, self.lead, self.gains(), bool(self.upgrades["colour"] and self.colour_enabled))
        self.replay_trial = False
        self.mode = Scene.EXPERIMENT
        self.paused = False
        self.emit("trial_started", scenario=step.scenario, gains=self.trial.gains)

    def replay(self):
        if self.last_trial is None:
            self.notify("Complete a measured experiment to replay your solution.")
            return
        kind, algorithm, lead, gains, colour = self.last_trial
        self.trial = Experiment(kind, self.strategies, algorithm, lead, gains, colour)
        self.replay_trial = True
        self.router.open(Scene.EXPERIMENT)
        self.paused = False

    def review_record(self, key):
        evidence = self.learning.get(key, {}).get("evidence", {})
        if "kind" not in evidence:
            return
        self.trial = Experiment(evidence["kind"], self.strategies, evidence.get("algorithm", 0),
                                evidence.get("lead", .8), evidence.get("gains", (4,0,0,0)),
                                evidence.get("colour_enabled", True))
        self.replay_trial = True
        self.replay_title = self.learning[key].get("title", "Experiment replay")
        self.router.open(Scene.EXPERIMENT)
        self.paused = False

    def finish_experiment(self):
        self.emit("trial_resolved", **self.trial.metrics.evidence())
        if self.replay_trial:
            self.router.close()
        elif self.runner.assess(self.trial.metrics):
            self.complete_step()
        else:
            self.mode = Scene.COACH
        self.save()

    def begin_wave(self):
        if not self.practice and (self.step is None or self.step.kind != "wave" or self.runner.pending):
            self.notify("Finish the current guided task first. Free play is available from the lesson map.")
            return False
        if self.stage == 4 and not self.upgrades["colour"]:
            self.open_shop()
            self.notify("Install the colour sensor, then return to launch.")
            return False
        self.checkpoint = (self.currency, dict(self.upgrades))
        self.mode = Scene.PLAYING
        self.accumulator = 0
        return True

    def retry(self):
        if self.mode not in (Scene.RESULT, Scene.PLAYING):
            return
        self.currency, upgrades = self.checkpoint
        self.upgrades = dict(upgrades)
        self.tuning = self.gains()
        self.reset_world()
        self.mode = Scene.READY if self.practice else Scene.COACH
        self.notify("Field reset; tuning kept. Guided evidence stays completed.")

    def advance(self):
        if not self.practice and (not self.runner.complete or self.runner.pending):
            self.notify("Demonstrate each task and acknowledge its result before continuing.")
            return False
        if self.stage == 7:
            if not self.practice:
                self.won = True
                self.save()
            self.mode = Scene.VICTORY
        else:
            self.stage += 1
            self.prepare_stage()
        return True

    def enter_sandbox(self, stage=0):
        if not self.practice:
            self.save()
        self.practice = self.sandbox = True
        self.stage, self.currency = stage, 999
        self.upgrades["colour"] = 1
        self.algorithm = 4
        self.prepare_stage()

    def go_menu(self):
        if self.mode == Scene.PLAYING:
            self.retry()
        self.save()
        self.mode = Scene.TITLE

    def gains(self):
        if not hasattr(self, "tower"):
            return self.tuning
        c = self.tower.controller
        return c.kp, c.ki, c.kd, c.kf

    def set_gains(self, values):
        values = tuple(max(0, min(v, high)) for v, high in zip(values, (16, 5, 2, 3)))
        self.tuning = values
        if hasattr(self, "tower"):
            c = self.tower.controller
            c.kp, c.ki, c.kd, c.kf = values

    def change_gain(self, index, value):
        values = list(self.gains())
        values[index] = value
        self.set_gains(values)
        self.runner.changed.add("pidf"[index])
        self.emit("gain_changed", term="PIDF"[index], value=value)

    def set_lead(self, value):
        self.lead = max(0, min(2, value))
        self.runner.changed.add("lead")
        self.emit("lead_changed", value=self.lead)

    def set_algorithm(self, index):
        if not 0 <= index <= self.unlock:
            self.notify("This algorithm opens in a later lesson. Free play unlocks every model.")
            return
        if index != self.algorithm:
            self.algorithm = index
            self.tower.controller.reacquire()
            self.emit("algorithm_changed", index=index)

    def toggle_colour(self):
        self.colour_enabled = not self.colour_enabled
        self.sensors = SensorSuite(bool(self.upgrades["colour"] and self.colour_enabled), self.upgrades["sensor"])
        self.emit("sensor_changed", enabled=self.sensors.colour)

    def buy(self, key):
        if self.mode != Scene.SHOP:
            return
        if not self.practice and self.step and self.step.kind != "wave" and key != "colour":
            self.notify("Calibration equipment stays fixed. Field upgrades apply in the final wave or free play.")
            return
        name, prices, _ = UPGRADES[key]
        level = self.upgrades[key]
        if level >= len(prices): self.notify("Fully upgraded.")
        elif self.currency < prices[level]: self.notify("Not enough credits. Guided tasks each award 10 credits.")
        else:
            self.currency -= prices[level]
            self.upgrades[key] += 1
            self.sensors = SensorSuite(bool(self.upgrades["colour"] and self.colour_enabled), self.upgrades["sensor"])
            self.emit("purchased", upgrade=key)
            self.notify(name+" installed.")
            self.save()

    def spawn(self):
        n = self.spawned
        colour, behaviour, speed = "blue", "constant", 65
        if self.stage in (1, 2): speed = (48, 95)[n % 2]
        elif self.stage == 3:
            colour, behaviour, speed = (("red", "boost", 35), ("gold", "brake", 100), ("blue", "switch", 48))[n % 3]
        elif self.stage >= 4:
            colour, behaviour, speed = (("blue", "constant", 68), ("red", "boost", 35), ("gold", "brake", 100))[n % 3]
        hp = 2 if self.stage == 7 and n % 3 == 0 else 1
        self.tanks.append(Tank(n+1, self.path, colour, speed, behaviour, hp))
        self.spawned += 1

    def update(self, real_dt):
        self.toast_time = max(0, self.toast_time-real_dt)
        if self.mode == Scene.EXPERIMENT and self.trial and not self.paused:
            self.trial.update(real_dt*self.speed)
            if self.trial.done: self.finish_experiment()
            return
        if self.mode != Scene.PLAYING or self.paused:
            return
        self.accumulator += min(real_dt, 0.1)*self.speed
        while self.accumulator >= self.STEP and self.mode == Scene.PLAYING:
            self.tick(self.STEP)
            self.accumulator -= self.STEP

    def tick(self, dt):
        if self.wave_finished:
            return
        self.time += dt
        self.spawn_clock -= dt
        if self.spawned < self.lesson.count and self.spawn_clock <= 0:
            self.spawn()
            self.spawn_clock += self.lesson.gap
        for tank in self.tanks:
            tank.update(dt)
            if tank.distance >= self.path.length:
                tank.alive = False
                self.health -= 2
                self.leaks += 1
                self.effects.append([tank.position, 0.7, "leak"])
                self.emit("leak", target=tank.id)
        self.tanks = [t for t in self.tanks if t.alive]
        self.sensors.update(self.tanks, self.time)
        observations = self.sensors.read(self.time)
        candidates = []
        solutions = {}
        for obs in observations:
            if (obs.position-self.tower.position).length() <= self.RANGE:
                solution = self.strategies[self.algorithm].aim(self.tower.position, obs, self.shell_speed, self.lead)
                if solution.valid:
                    candidates.append(obs)
                    solutions[obs.target_id] = solution
        # Prefer tanks without a pending shell; keep steady tracking otherwise.
        reserved_ids = {p.target_id for p in self.projectiles if p.age < p.reservation_time}
        unreserved = [o for o in candidates if o.target_id not in reserved_ids]
        self.selected = self.selector.choose(unreserved or candidates, self.tower.position, self.RANGE)
        self.solution = solutions.get(self.selected.target_id) if self.selected else None
        current_id = self.selected.target_id if self.selected else None
        if current_id != self.last_target:
            self.tower.controller.reacquire()
            self.last_target = current_id
        desired = self.hold_angle
        if self.solution:
            offset = self.solution.point-self.tower.position
            desired = atan2(offset.y, offset.x)
            self.hold_angle = desired
        self.tower.track(desired, dt, self.controlled, self.upgrades["motor"], self.bias)
        self.tower.reload = max(0, self.tower.reload-dt)
        ready = self.selected and self.sensors.confident(self.selected.target_id)
        reserved = current_id in reserved_ids
        # A real gun interlock waits for the barrel to enter a small aim window.
        # It never steers a shell. Poor control still delays fire and causes leaks.
        # Calibration trials measure tracking independently of this field policy.
        aligned = not self.controlled or abs(wrap_angle(desired-self.tower.angle)) <= radians(2)
        self.wait_reason = ("No intercept found within 4s / range" if not self.solution else
                            "Collecting position samples" if not ready else "Reloading" if self.tower.reload > 0 else
                            "Shell already en route" if reserved else "Aligning barrel (2 deg window)" if not aligned else "Firing")
        if self.solution and ready and aligned and not reserved and self.tower.reload <= 0:
            shot = self.tower.fire(self.shell_speed, 1+self.upgrades["damage"])
            shot.target_id = current_id
            shot.reservation_time = (self.solution.point-self.tower.position).length()/self.shell_speed+0.12
            shot.record_id = len(self.records)
            self.records.append(ShotRecord(shot.record_id, current_id, self.algorithm, self.gains(), self.time,
                                           self.solution.point.tuple(), self.solution.branch))
            self.projectiles.append(shot)
            self.tower.reload = 1.05-0.19*self.upgrades["reload"]
            self.shots += 1
            self.emit("shot", target=current_id, record=shot.record_id)
        surviving = []
        for shot in self.projectiles:
            shot.update(dt)
            record = self.records[shot.record_id]
            target = next((t for t in self.tanks if t.id == record.target_id), None)
            if target:
                record.miss_distance = min(record.miss_distance, (shot.position-target.position).length())
            contacts = [(fraction, t) for t in self.tanks if t.alive
                        if (fraction := swept_impact_time(shot, t)) is not None]
            if contacts:
                _, hit = min(contacts, key=lambda pair: pair[0])
                hit.hp -= shot.damage
                self.hits += 1
                record.outcome, record.hit_target, record.resolved_at = "hit", hit.id, self.time
                self.effects.append([hit.position, 0.45, "hit"])
                self.emit("hit", target=hit.id, intended=record.target_id)
                if hit.hp <= 0:
                    hit.alive = False
                    self.kills += 1
                    self.currency += 8
                    self.earned += 8
            elif shot.age < 4 and -40 < shot.position.x < 950 and 70 < shot.position.y < 700:
                surviving.append(shot)
            else:
                record.outcome, record.resolved_at = "miss", self.time
                self.effects.append([Vec2(*record.aim), 1.2, "miss"])
                self.emit("miss", target=record.target_id, separation=record.miss_distance)
        self.projectiles = surviving
        self.tanks = [t for t in self.tanks if t.alive]
        for effect in self.effects: effect[1] -= dt
        self.effects = [e for e in self.effects if e[1] > 0]
        self.history_clock += dt
        if self.history_clock >= 1/30:
            self.history.append((self.time, self.tower.controller.sample, self.tower.rate, desired, self.tower.angle))
            self.history_clock = 0
        if self.health <= 0:
            for p in self.projectiles:
                self.records[p.record_id].outcome = "cancelled"
            self.projectiles.clear()
            self.finish_wave(False)
        elif self.spawned == self.lesson.count and not self.tanks and not self.projectiles:
            required = self.lesson
            valid_model = (self.stage != 2 or all(r.algorithm == 2 for r in self.records if r.outcome == "hit"))
            valid_model = valid_model and (self.stage != 4 or all(r.algorithm == 4 and not r.branch.startswith("NO COLOUR") for r in self.records if r.outcome == "hit"))
            self.finish_wave(self.hits >= required.min_hits and self.hits/max(1,self.shots) >= required.min_hit_rate and (self.practice or valid_model))

    def finish_wave(self, success):
        if self.wave_finished:
            return
        self.wave_finished = True
        self.success = success
        self.paused = False
        self.result_hint = ("Field secured. Your measured skills worked together." if success else
                            "Compare the aim cross and actual barrel. Resolved shots determine accuracy; replay keeps your tuning.")
        if not success:
            self.currency = self.checkpoint[0]
            self.earned = 0
        if success:
            key = str(self.stage)
            if self.practice or not self.completion.get(key):
                self.currency += 35
                self.earned += 35
            if not self.practice:
                self.completion[key] = {"hits": self.hits, "shots": self.shots, "rewarded": True}
                if self.step and self.step.kind == "wave":
                    self.runner.award({"hits": self.hits, "shots": self.shots, "gains": self.gains()})
                    self.complete_step()
                else:
                    self.mode = Scene.RESULT
                self.save()
                return
        self.mode = Scene.RESULT
