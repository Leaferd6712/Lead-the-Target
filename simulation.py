"""World physics and entities. No pygame imports; all times are in seconds."""
from dataclasses import dataclass, field
from math import atan2, cos, sin, exp, radians
from targeting import Vec2
from control import PIDFController, clamp, wrap_angle
from behaviours import in_brake_zone, next_speed


class Path:
    def __init__(self):
        self.points = [Vec2(64, 258), Vec2(848, 258), Vec2(848, 558),
                       Vec2(88, 558), Vec2(88, 630)]
        self.lengths = [(b-a).length() for a, b in zip(self.points, self.points[1:])]
        self.length = sum(self.lengths)

    def point_at(self, distance):
        distance = max(0, distance)
        for a, b, length in zip(self.points, self.points[1:], self.lengths):
            if distance <= length:
                return a + (b-a)*(distance/length)
            distance -= length
        return self.points[-1]

    def direction_at(self, distance):
        return (self.point_at(min(self.length, distance+0.2))-
                self.point_at(max(0, distance-0.2))).unit()

    @staticmethod
    def in_brake_zone(distance):
        return in_brake_zone(distance)


@dataclass
class Tank:
    id: int
    path: Path
    colour: str = "blue"
    speed: float = 65
    behaviour: str = "constant"
    hp: int = 1
    distance: float = 0
    alive: bool = True
    position: Vec2 = field(default_factory=lambda: Vec2(64, 258))
    previous: Vec2 = field(default_factory=lambda: Vec2(64, 258))
    age: float = 0

    def update(self, dt):
        self.previous = self.position
        self.age += dt
        if self.behaviour == "boost":
            self.speed = next_speed("red", self.speed, self.distance, dt)
        elif self.behaviour == "brake":
            self.speed = next_speed("gold", self.speed, self.distance, dt)
        elif self.behaviour == "switch":
            self.speed = 145 if 95 <= self.distance < 240 or 400 <= self.distance < 600 else 48
        self.distance += self.speed*dt
        self.position = self.path.point_at(self.distance)


@dataclass
class Projectile:
    position: Vec2
    velocity: Vec2
    damage: int = 1
    age: float = 0
    previous: Vec2 | None = None
    target_id: int | None = None
    reservation_time: float = 0
    record_id: int = 0

    def update(self, dt):
        self.previous = self.position
        self.position = self.position + self.velocity*dt
        self.age += dt


def swept_impact_time(projectile, tank, radius=12):
    """Earliest contact fraction in [0,1], or None. Relative swept circles."""
    r0 = projectile.previous-tank.previous
    r1 = projectile.position-tank.position
    delta = r1-r0
    c = r0.dot(r0)-radius*radius
    if c <= 0:
        return 0.0
    a = delta.dot(delta)
    b = 2*r0.dot(delta)
    discriminant = b*b-4*a*c
    if a < 1e-12 or discriminant < 0:
        return None
    t = (-b-discriminant**0.5)/(2*a)
    return t if 0 <= t <= 1 else None


def swept_hit(projectile, tank, radius=12):
    return swept_impact_time(projectile, tank, radius) is not None


class Tower:
    def __init__(self):
        self.position = Vec2(462, 435)
        self.angle = -1.5708
        self.rate = 0.0
        self.reload = 0.0
        self.controller = PIDFController()

    def track(self, desired, dt, controlled, motor_level, bias=0):
        if not controlled:
            self.angle = desired
            self.rate = 0
            return
        limit = radians(115 + 35*motor_level)
        sample = self.controller.update(desired, self.angle, self.rate, dt, limit, bias)
        # First-order actuator lag makes aggressive tuning visibly oscillate.
        demand = clamp(sample.output+bias, -limit, limit)
        self.rate += (demand-self.rate)*(1-exp(-dt/(0.22-0.04*motor_level)))
        self.angle = wrap_angle(self.angle + self.rate*dt)

    def fire(self, speed, damage):
        direction = Vec2(cos(self.angle), sin(self.angle))
        # The mathematical launch origin is the tower pivot. The barrel is visual.
        return Projectile(self.position, direction*speed, damage)


class Demonstration:
    """Identical crossing geometry, two strategies, repeatable without base damage."""
    def __init__(self):
        from targeting import solve_constant_velocity_intercept
        self.time = 0.0
        self.origin = Vec2(0, 180)
        self.start = Vec2(0, 0)
        self.velocity = Vec2(80, 0)
        self.speed = 240
        self.intercept_time = solve_constant_velocity_intercept(
            self.origin, self.start, self.velocity, self.speed)
        lead = self.start+self.velocity*self.intercept_time
        self.direct_velocity = (self.start-self.origin).unit()*self.speed
        self.lead_velocity = (lead-self.origin).unit()*self.speed

    def update(self, dt):
        self.time = min(2.4, self.time+dt)
