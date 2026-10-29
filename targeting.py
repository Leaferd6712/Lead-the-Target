"""Editable prediction algorithms. Units: pixels and seconds; no pygame dependency.

Try changing a Strategy.aim method, then restart the game to compare results.
Algorithms receive observations, never the simulation's hidden tank state.
"""
from dataclasses import dataclass
from math import hypot, sqrt, isfinite
from typing import Protocol
from behaviours import next_speed


@dataclass(frozen=True)
class Vec2:
    x: float
    y: float

    def __add__(self, other):
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, value):
        return Vec2(self.x * value, self.y * value)

    __rmul__ = __mul__

    def dot(self, other):
        return self.x * other.x + self.y * other.y

    def length(self):
        return hypot(self.x, self.y)

    def unit(self):
        length = self.length()
        return self * (1 / length) if length > 1e-9 else Vec2(0, 0)

    def tuple(self):
        return self.x, self.y


@dataclass(frozen=True)
class TargetObservation:
    target_id: int
    position: Vec2
    velocity: Vec2
    acceleration: Vec2
    progress: float
    timestamp: float
    colour: str | None = None
    sample_time: float | None = None


@dataclass(frozen=True)
class AimSolution:
    point: Vec2
    flight_time: float
    valid: bool
    branch: str


class TargetingStrategy(Protocol):
    name: str
    pseudocode: tuple

    def aim(self, origin: Vec2, obs: TargetObservation, speed: float,
            lead: float = 0.8) -> AimSolution: ...


def solve_constant_velocity_intercept(origin, position, velocity, shell_speed):
    """Solve |r + v*t| = speed*t; select the earliest strictly positive root.

    The stable q form avoids cancellation when the quadratic roots differ greatly.
    None means a shell at this speed cannot catch the predicted motion.
    """
    if shell_speed <= 0:
        return None
    r = position - origin
    a = velocity.dot(velocity) - shell_speed * shell_speed
    b = 2 * r.dot(velocity)
    c = r.dot(r)
    if c < 1e-12:
        return 0.0
    if abs(a) < 1e-8:
        return -c / b if b < -1e-9 else None
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return None
    root = sqrt(discriminant)
    q = -0.5 * (b + (root if b >= 0 else -root))
    candidates = [q / a]
    if abs(q) > 1e-12:
        candidates.append(c / q)
    positive = [t for t in candidates if t > 0 and isfinite(t)]
    return min(positive) if positive else None


def predict_motion(position, velocity, acceleration, time):
    return position + velocity * time + acceleration * (0.5 * time * time)


def solve_predicted_intercept(origin, speed, forecast, horizon=4.0):
    """Bracket the earliest crossing of forecast distance and shell distance.

    Bounded sampling plus bisection is predictable and handles nonlinear forecasts.
    A tangent root can be missed; this intentionally returns no solution rather
    than inventing one. The UI identifies this as a finite-horizon forecast.
    """
    if speed <= 0:
        return None
    left = 0.0
    for index in range(1, 161):
        right = horizon * index / 160
        if (forecast(right) - origin).length() - speed * right <= 0:
            for _ in range(28):
                mid = (left + right) / 2
                if (forecast(mid) - origin).length() > speed * mid:
                    left = mid
                else:
                    right = mid
            return right
        left = right
    return None


class CurrentPositionStrategy:
    name = "Direct"
    pseudocode = ("aim = observed.position", "fire toward aim", "# tank moves while shell travels")

    def aim(self, origin, obs, speed, lead=0.8):
        return AimSolution(obs.position, (obs.position-origin).length()/speed,
                           True, "POSITION ONLY")


class FixedLeadStrategy:
    name = "Fixed lead"
    pseudocode = ("t = lead_slider", "aim = position + velocity * t", "# one t cannot fit every distance")

    def aim(self, origin, obs, speed, lead=0.8):
        return AimSolution(obs.position + obs.velocity * lead, lead, True, "FIXED TIME")


class ConstantVelocityStrategy:
    name = "Intercept"
    pseudocode = ("r = position - tower", "solve |r + velocity*t| = shell_speed*t",
                  "t = earliest positive root", "aim = position + velocity*t")

    def aim(self, origin, obs, speed, lead=0.8):
        time = solve_constant_velocity_intercept(origin, obs.position, obs.velocity, speed)
        return AimSolution(obs.position if time is None else obs.position + obs.velocity*time,
                           time or 0, time is not None, "CONSTANT VELOCITY")


class AdaptiveStrategy:
    name = "Adaptive"
    pseudocode = ("v = estimate from position samples", "a = filtered change in velocity",
                  "forecast = p + v*t + 0.5*a*t*t", "solve distance(forecast) = shell_speed*t")

    def forecast(self, obs, time):
        # Acceleration is only trusted briefly: extrapolating indefinitely explodes.
        h = min(time, 0.7)
        v = obs.velocity + obs.acceleration*h
        return predict_motion(obs.position, obs.velocity, obs.acceleration, h) + v*(time-h)

    def aim(self, origin, obs, speed, lead=0.8):
        forecast = lambda t: self.forecast(obs, t)
        time = solve_predicted_intercept(origin, speed, forecast)
        return AimSolution(forecast(time) if time is not None else obs.position,
                           time or 0, time is not None, "MEASURED ACCELERATION")


class ColourAwareStrategy(AdaptiveStrategy):
    name = "Colour aware"
    pseudocode = ("if colour is None: use measured motion", "elif colour == RED: model boost + cap",
                  "elif colour == GOLD: model brake zones", "else: model constant speed",
                  "advance forecast along known path", "solve distance(forecast) = speed*t")

    def __init__(self, path):
        self.path = path
        self._cache = {}

    def aim(self, origin, obs, speed, lead=0.8):
        if obs.colour is None:
            solution = super().aim(origin, obs, speed, lead)
            return AimSolution(solution.point, solution.flight_time, solution.valid,
                               "NO COLOUR > MEASURED MOTION")
        # Precompute a short trajectory once, then interpolate during root finding.
        # This avoids integrating a full forecast again at every root-search step.
        forecast = self.trajectory(obs)
        time = solve_predicted_intercept(origin, speed, forecast)
        branch = {"red": "RED > BOOST + SPEED CAP", "gold": "GOLD > BRAKE-ZONE MODEL",
                  "blue": "BLUE > CONSTANT SPEED"}[obs.colour]
        return AimSolution(forecast(time) if time is not None else obs.position,
                           time or 0, time is not None, branch)

    def forecast(self, obs, time):
        if obs.colour is None:
            return super().forecast(obs, time)
        return self.trajectory(obs)(time)

    def trajectory(self, obs):
        # Cache only identical observed states. Launch-time extrapolation still
        # updates the prediction; it never reuses a stale aim across observations.
        age = max(0, obs.timestamp-obs.sample_time) if obs.sample_time is not None else 0
        anchor = obs.progress-obs.velocity.length()*age
        key = (obs.target_id, obs.sample_time, round(anchor,5), obs.velocity.x, obs.velocity.y, obs.colour)
        dt = 0.025
        if key in self._cache:
            distances = self._cache[key]
        else:
            distances = [anchor]
            velocity = obs.velocity.length()
            for _ in range(170):
                velocity = next_speed(obs.colour, velocity, distances[-1], dt)
                distances.append(distances[-1]+velocity*dt)
            if len(self._cache) > 64:self._cache.clear()
            self._cache[key] = distances

        def forecast(time):
            time += age
            index = min(len(distances)-2, max(0, int(time/dt)))
            fraction = min(1, max(0, time/dt-index))
            distance = distances[index]*(1-fraction)+distances[index+1]*fraction
            return self.path.point_at(distance)

        return forecast


class TargetSelector:
    """Keep a reachable target to prevent controller thrashing between enemies."""
    def __init__(self):
        self.current_id = None

    def choose(self, observations, origin, radius):
        reachable = [o for o in observations if (o.position-origin).length() <= radius]
        retained = next((o for o in reachable if o.target_id == self.current_id), None)
        selected = retained or max(reachable, key=lambda o: o.progress, default=None)
        self.current_id = selected.target_id if selected else None
        return selected
