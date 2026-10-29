"""Controlled, reproducible experiments. Measurements come from simulated motion.

Calibration intentionally fixes shell/motor equipment to isolate one variable.
The same predictor and PIDF classes are used in the field and in these trials.
"""
from dataclasses import dataclass
from math import atan2, cos, sin, degrees, radians, sqrt
from control import wrap_angle
from domain import TrialMetrics
from simulation import Path, Tank, Tower, swept_hit, Projectile
from sensors import SensorSuite
from targeting import Vec2, TargetObservation


def calibration_gains(kind, chosen):
    if kind == "p_base": return (1, 0, 0, 0)
    if kind == "p_tune": return (chosen[0], 0, 0, 0)
    if kind.startswith("i_"): return (8, chosen[1] if kind.endswith("tune") else 0, 0, 0)
    if kind.startswith("d_"): return (10, 0, chosen[2] if kind.endswith("tune") else 0, 0)
    if kind.startswith("f_"): return (8, 0, 0.3, chosen[3] if kind.endswith("tune") else 0)
    return tuple(chosen)


class Experiment:
    DT = 1/120

    def __init__(self, kind, strategies, algorithm, lead, gains, colour_enabled):
        self.kind, self.algorithm, self.lead = kind, algorithm, lead
        self.path = Path()
        self.time, self.accumulator = 0.0, 0.0
        self.done = False
        self.tracking = kind.startswith(("p_", "i_", "d_", "f_"))
        self.duration = 10.0 if kind.startswith("i_") else 6.0 if self.tracking else 2.0
        self.tower = Tower()
        self.tower.position = Vec2(462, 435)
        self.tower.angle = 0.0
        self.gains = calibration_gains(kind, gains)
        self.tower.controller.kp, self.tower.controller.ki, self.tower.controller.kd, self.tower.controller.kf = self.gains
        self.metrics = TrialMetrics(kind, algorithm=algorithm, gains=self.gains)
        self.desired = 0.0
        self.bias = radians(9) if kind.startswith("i_") else 0
        self.tank = Tank(1, self.path)
        self.projectile = None
        self.solution = None
        self.hit_time = None
        self.samples = []
        self.metrics.miss_distance = 9999
        self._colour_model = kind.startswith("colour_")
        if self.tracking:
            self.tank.position = self.tower.position+Vec2(200, 0)
        else:
            self._setup_ballistic(strategies, colour_enabled)

    def motion(self, t):
        velocity = 110 if self.kind in ("fast", "decelerate") else 80
        acceleration = 55 if self.kind.startswith("accel_") else -55 if self.kind == "decelerate" else 0
        return Vec2(462+velocity*t+0.5*acceleration*t*t, 258)

    def _setup_ballistic(self, strategies, colour_enabled):
        if self._colour_model:
            colour = "gold" if self.kind == "colour_gold" else "red"
            behaviour = "brake" if colour == "gold" else "boost"
            self.tank = Tank(1, self.path, colour, 100 if colour == "gold" else 45, behaviour)
            self.tank.distance = 80
            self.tank.position = self.tank.previous = self.path.point_at(80)
            sensor = SensorSuite(colour_enabled)
            for index in range(73):
                self.tank.update(self.DT)
                sensor.update([self.tank], index*self.DT)
            obs = sensor.read(72*self.DT)[0]
        else:
            self.tank.position = self.tank.previous = self.motion(0)
            # Estimate v and a from three *past* position samples; no future state
            # crosses the observation boundary. Acceleration correction aligns v
            # with the sample time rather than the centre of its difference interval.
            h = 0.1
            p0, p1, p2 = self.motion(0), self.motion(-h), self.motion(-2*h)
            acceleration = (p0-p1*2+p2)*(1/(h*h))
            velocity = (p0-p1)*(1/h)+acceleration*(h/2)
            obs = TargetObservation(1, p0, velocity, acceleration, 398, 0)
        self.observation = obs
        self.solution = strategies[self.algorithm].aim(self.tower.position, obs, 240, self.lead)
        self.metrics.branch = self.solution.branch
        if self.solution.valid:
            offset = self.solution.point-self.tower.position
            self.tower.angle = atan2(offset.y, offset.x)
            self.projectile = self.tower.fire(240, 1)
            self.metrics.flight_time = offset.length()/240

    def update(self, real_dt):
        self.accumulator += min(0.1, real_dt)
        while self.accumulator >= self.DT and not self.done:
            self.tick()
            self.accumulator -= self.DT

    def tick(self):
        dt = self.DT
        self.time += dt
        if self.tracking:
            if self.kind.startswith("i_"):
                self.desired = 0
            elif self.kind.startswith("f_"):
                self.desired = wrap_angle(0.55*self.time)
            else:
                self.desired = 0 if self.time < 0.5 else 0.9
            self.tower.track(self.desired, dt, True, 0, self.bias)
            self.tank.position = self.tower.position+Vec2(cos(self.desired), sin(self.desired))*200
            sample = self.tower.controller.sample
            self.samples.append((self.time, sample, self.tower.rate, self.desired, self.tower.angle))
        else:
            self.tank.previous = self.tank.position
            if self._colour_model:
                self.tank.update(dt)
            else:
                self.tank.position = self.motion(self.time)
            if self.projectile and self.hit_time is None:
                self.projectile.update(dt)
                r0 = self.projectile.previous-self.tank.previous
                r1 = self.projectile.position-self.tank.position
                delta = r1-r0
                frac = max(0, min(1, -r0.dot(delta)/max(1e-9, delta.dot(delta))))
                self.metrics.miss_distance = min(self.metrics.miss_distance, (r0+delta*frac).length())
                if swept_hit(self.projectile, self.tank):
                    self.metrics.hit = True
                    self.hit_time = self.time
        if self.time+1e-8 >= self.duration:
            self.done = True
            if self.tracking:
                errors = [abs(degrees(wrap_angle(desired-angle))) for _, _, _, desired, angle in self.samples]
                late = errors[-240:]
                self.metrics.rms_error = sqrt(sum(e*e for e in errors)/len(errors))
                self.metrics.steady_error = sum(late)/len(late)
                self.metrics.overshoot = (max(0, max(degrees(a-0.9) for t, _, _, _, a in self.samples if t >= 0.5))
                                          if self.kind.startswith(("p_", "d_")) else 0)
                self.metrics.samples = self.samples

    def finish(self):
        """Deterministic test/benchmark helper; UI uses update() to animate."""
        while not self.done:
            self.tick()
        return self.metrics
