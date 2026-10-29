"""PIDF turret tracking, independent of rendering. Internal angles are radians."""
from dataclasses import dataclass
from math import pi


def clamp(value, low, high):
    return max(low, min(high, value))


def wrap_angle(angle):
    return (angle + pi) % (2 * pi) - pi


@dataclass(frozen=True)
class ControlSample:
    error: float = 0
    p: float = 0
    i: float = 0
    d: float = 0
    f: float = 0
    requested: float = 0
    output: float = 0


class PIDFController:
    def __init__(self):
        self.kp, self.ki, self.kd, self.kf = 4.0, 0.0, 0.0, 0.0
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.filtered_rate = 0.0
        self.last_desired = None
        self.sample = ControlSample()

    def reacquire(self):
        """A new target is a reference jump, not continuous feedforward motion."""
        self.last_desired = None

    def update(self, desired, measured, measured_rate, dt, limit, bias=0.0):
        if dt <= 0:
            return self.sample
        error = wrap_angle(desired - measured)
        desired_rate = 0 if self.last_desired is None else clamp(
            wrap_angle(desired-self.last_desired)/dt, -limit, limit)
        self.last_desired = desired
        self.filtered_rate += dt/(0.06+dt) * (measured_rate-self.filtered_rate)
        p = self.kp * error
        d = -self.kd * self.filtered_rate
        f = self.kf * desired_rate
        proposed = clamp(self.integral + error*dt, -1.5, 1.5)
        requested = p + self.ki*proposed + d + f
        # Conditional integration: don't wind further into an output limit.
        if abs(requested + bias) <= limit or error*(requested+bias) < 0:
            self.integral = proposed
        i = self.ki * self.integral
        requested = p + i + d + f
        self.sample = ControlSample(error, p, i, d, f, requested,
                                    clamp(requested, -limit, limit))
        return self.sample
