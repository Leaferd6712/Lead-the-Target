"""Campaign simulation: rendering and input belong to the Panda3D application.

120 Hz physics, sampled observations, non-homing shells and per-tower PIDF.
Rewards settle exactly once; quitting combat restarts the unbanked encounter.
"""
from collections import deque
from dataclasses import replace
from math import atan2, radians
from control import wrap_angle
from fortress import Emplacement, PADS, SPECS, restore_towers
from sensors import SensorSuite
from simulation import Tank, swept_impact_time
from targeting import (CurrentPositionStrategy, FixedLeadStrategy, ConstantVelocityStrategy,
                       AdaptiveStrategy, ColourAwareStrategy)
from waves import LEVELS, Route


class Campaign:
    DT = 1/120

    def __init__(self, saved=None):
        saved = saved or {}
        self.level = min(100, max(1, saved.get("level",1)))
        self.credits = saved.get("credits",160)
        self.site = saved.get("site",0)
        self.completed = dict(saved.get("completed",{}))
        self.towers = restore_towers(saved.get("towers",[]))
        if not self.towers: self.towers = [Emplacement(1,0)]
        self.selected_id = self.towers[0].id
        self.message = "Select a build pad to expand your fortress."
        self.routes = [Route(i) for i in range(3)]
        self.strategies = [[CurrentPositionStrategy(), FixedLeadStrategy(), ConstantVelocityStrategy(),
                            AdaptiveStrategy(), ColourAwareStrategy(r)] for r in self.routes]
        self.reset_encounter()

    @property
    def selected(self):
        return next((t for t in self.towers if t.id == self.selected_id), self.towers[0] if self.towers else None)

    @property
    def spec(self): return LEVELS[self.level-1]

    @property
    def unlock(self):
        return 4 if self.level >= 31 else 3 if self.level >= 21 else 2 if self.level >= 5 else 1

    def snapshot(self):
        return {"level":self.level,"credits":self.credits,"site":self.site,
                "completed":self.completed,"towers":[t.snapshot() for t in self.towers]}

    def reset_encounter(self):
        self.running = self.finished = self.success = self.paused = False
        self.time = self.accumulator = 0.
        self.health = 16
        self.spawned = self.shots = self.hits = self.kills = self.leaks = 0
        self.pending_credits = 0
        self.tanks, self.projectiles = [], []
        self.sensors = SensorSuite(True)
        self.events = deque(maxlen=60)
        self.history = deque(maxlen=240)
        self.history_clock = 0.
        for t in self.towers:
            t.motor.reload = 0; t.motor.controller.reset(); t.motor.rate = 0
            t.solution = None; t.target_id = None; t.wait = "Waiting for observations"

    def build(self, kind, pad):
        if kind not in SPECS or not 0 <= pad < len(PADS): return False
        spec = SPECS[kind]
        if self.level < spec.unlock:
            self.message = f"{spec.title} unlocks at level {spec.unlock}."; return False
        if any(t.pad == pad for t in self.towers):
            self.message = "That pad is occupied. Select its tower to configure it."; return False
        if self.credits < spec.cost:
            self.message = "Not enough credits. Complete an academy task or recovery contract."; return False
        self.credits -= spec.cost
        ident = max((t.id for t in self.towers), default=0)+1
        self.towers.append(Emplacement(ident,pad,kind,algorithm=min(2,self.unlock)))
        self.selected_id = ident
        self.message = f"{spec.title} deployed. Select it to adjust targeting."
        return True

    def upgrade(self):
        t = self.selected
        if not t or t.level >= 3:
            self.message = "This tower is fully upgraded."; return False
        if self.credits < t.upgrade_cost:
            self.message = "More credits needed for this upgrade."; return False
        self.credits -= t.upgrade_cost; t.level += 1
        self.message = "Upgrade installed: more range, damage and shell speed."; return True

    def buy_colour(self):
        t = self.selected
        if not t or t.colour: return False
        if self.level < 31:
            self.message = "Campaign colour research opens at level 31. Try it in the academy now."; return False
        if self.credits < 80:
            self.message = "Colour sensor costs 80 credits."; return False
        self.credits -= 80; t.colour = True
        self.message = "Colour input installed: RED / GOLD / BLUE now select different code branches."
        return True

    def sell(self):
        t = self.selected
        if not t or (len(self.towers) == 1 and t.kind != "sensor"):
            self.message = "Keep at least one defending tower."; return False
        if t.kind != "sensor" and not any(o.kind != "sensor" and o.id != t.id for o in self.towers):
            self.message = "Keep at least one defending tower."; return False
        self.credits += t.refund; self.towers.remove(t)
        self.selected_id = self.towers[0].id
        self.message = "Equipment recovered at 65% of its purchase and upgrade cost."
        return True

    def copy_configuration(self):
        source = self.selected
        if not source: return
        for t in self.towers:
            if t.kind == source.kind and t.id != source.id:
                t.algorithm, t.lead, t.gains, t.priority = source.algorithm, source.lead, list(source.gains), source.priority
                t.apply_gains(); t.motor.controller.reacquire()
        self.message = "Targeting and PIDF copied to towers of the same type."

    def start(self):
        if self.running: return
        self.reset_encounter(); self.running = True

    def update(self, dt, speed=1):
        if not self.running or self.paused: return
        self.accumulator += min(.1,dt)*speed
        while self.accumulator+1e-12 >= self.DT and self.running:
            self.tick(); self.accumulator -= self.DT

    def tick(self):
        dt = self.DT; self.time += dt
        while self.spawned < len(self.spec.spawns) and self.spec.spawns[self.spawned].time <= self.time:
            s = self.spec.spawns[self.spawned]
            tank = Tank(self.spawned+1,self.routes[s.entrance],s.colour,s.speed,s.behaviour,s.hp)
            tank.position = tank.previous = tank.path.points[0]
            tank.route_id = s.entrance
            self.tanks.append(tank); self.spawned += 1
            self.events.append(("spawn", tank.position, self.time))
        for tank in self.tanks:
            tank.update(dt)
            if tank.distance >= tank.path.length:
                tank.alive = False; self.health -= max(1,tank.hp); self.leaks += 1
                self.events.append(("leak",tank.position,self.time))
        self.sensors.update(self.tanks,self.time)
        observations = self.sensors.read(self.time)
        by_id = {t.id:t for t in self.tanks if t.alive}
        # Reserve pending damage, not just a boolean, so armour gets enough shells.
        reserved = {}
        for p in self.projectiles:
            if p.age < p.reservation_time+.18:
                reserved[p.target_id] = reserved.get(p.target_id,0)+p.damage
        for t in self.towers:
            t.motor.reload = max(0,t.motor.reload-dt)
            if t.kind == "sensor": continue
            sensed_colour = t.sensor_enabled and (t.colour or any(
                o.kind == "sensor" and o.sensor_enabled and
                (o.motor.position-t.motor.position).length() <= o.radius for o in self.towers))
            candidates = [o for o in observations if o.target_id in by_id and
                          (o.position-t.motor.position).length() <= t.radius and self.sensors.confident(o.target_id)]
            fresh = [o for o in candidates if reserved.get(o.target_id,0) < by_id[o.target_id].hp]
            if fresh: candidates = fresh
            def score(o):
                if t.priority == "Nearest": return -(o.position-t.motor.position).length()
                if t.priority == "Strongest": return by_id[o.target_id].hp
                return -(by_id[o.target_id].path.length-o.progress)
            obs = max(candidates,key=score,default=None)
            desired = t.motor.angle
            if obs:
                if not sensed_colour: obs = replace(obs,colour=None)
                route = by_id[obs.target_id].route_id
                # Aim at 20 Hz; the motor and collision integrator stay at 120 Hz.
                key = (int(self.time*20),obs.target_id,t.algorithm,t.lead,t.shell_speed,sensed_colour)
                if key != getattr(t,'decision_key',None) or t.solution is None:
                    t.solution = self.strategies[route][t.algorithm].aim(t.motor.position,obs,t.shell_speed,t.lead)
                    t.decision_key = key
                if t.target_id != obs.target_id: t.motor.controller.reacquire()
                t.target_id = obs.target_id
                delta = t.solution.point-t.motor.position
                desired = atan2(delta.y,delta.x)
            else: t.target_id = None; t.solution = None
            t.apply_gains()
            controlled = self.level >= 41
            bias = radians(9) if self.level >= 51 else 0
            t.motor.track(desired,dt,controlled,2 if t.kind == "tracking" else min(t.level,2),bias)
            aligned = not controlled or abs(wrap_angle(desired-t.motor.angle)) < radians(2)
            covered = obs is not None and reserved.get(obs.target_id,0) >= by_id[obs.target_id].hp
            t.wait = "No target in range" if not obs else "No reachable intercept" if not t.solution.valid else "Tracking barrel" if not aligned else "Reloading" if t.motor.reload > 0 else "Ready"
            if covered: t.wait = "Enough damage in flight / holding fire"
            if obs and not covered and t.solution.valid and aligned and t.motor.reload <= 0:
                p = t.motor.fire(t.shell_speed,t.damage)
                p.target_id = obs.target_id; p.reservation_time = t.solution.flight_time
                p.tower_id = t.id
                self.projectiles.append(p); self.shots += 1
                reserved[p.target_id] = reserved.get(p.target_id,0)+p.damage
                t.motor.reload = t.spec.reload_time/(1+.15*t.level)
                self.events.append(("shot",t.motor.position,self.time))
        survivors = []
        for p in self.projectiles:
            p.update(dt)
            impacts = [(swept_impact_time(p,tank),tank) for tank in self.tanks if tank.alive]
            impacts = [(f,tank) for f,tank in impacts if f is not None]
            if impacts:
                _, tank = min(impacts,key=lambda pair:pair[0])
                tank.hp -= p.damage; self.hits += 1
                self.events.append(("hit",tank.position,self.time))
                if tank.hp <= 0:
                    tank.alive = False; self.kills += 1; self.pending_credits += 8
            elif p.age < 5 and -100 < p.position.x < 1050 and -100 < p.position.y < 850:
                survivors.append(p)
        self.projectiles = survivors
        self.tanks = [t for t in self.tanks if t.alive]
        self.history_clock += dt
        if self.history_clock >= .05:
            if self.selected: self.history.append((self.time,self.selected.motor.controller.sample))
            self.history_clock = 0
        if self.health <= 0 or (self.spawned == len(self.spec.spawns) and not self.tanks and not self.projectiles):
            self.finish()

    def finish(self):
        if self.finished: return
        self.running = False; self.finished = True; self.success = self.health > 0
        if self.success:
            first = str(self.level) not in self.completed
            self.credits += self.pending_credits+(self.spec.reward if first else self.spec.reward//3)
            self.completed[str(self.level)] = max(self.health,self.completed.get(str(self.level),0))
            self.message = f"Level {self.level} secured! +{self.pending_credits+(self.spec.reward if first else self.spec.reward//3)} credits."
        else:
            self.message = "Fortress overrun. Banked credits and recovered equipment are safe. Relocate troops to rebuild."

    def next_level(self):
        if not self.finished or not self.success: return False
        self.level = min(100,self.level+1)
        self.reset_encounter(); return True

    def relocate(self):
        if self.running: return False
        self.site += 1
        self.credits += sum(t.refund for t in self.towers if t.id != self.towers[0].id)
        starter = self.towers[0]
        if starter.kind == "sensor": starter = Emplacement(starter.id,0)
        starter.pad = self.site % 3
        starter.motor.position = PADS[starter.pad]
        self.towers = [starter]; self.selected_id = starter.id
        self.credits = max(90,self.credits)
        self.reset_encounter()
        self.message = "Troops relocated. Extra equipment salvaged at 65%. One tower redeployed; rebuilding fund guarantees 90 credits."
        return True
