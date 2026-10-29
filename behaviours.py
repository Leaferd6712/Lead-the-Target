"""Published tank-class rules shared by physics and sensor-based forecasts.

Sharing rules does not share hidden state. Predictors must supply measured speed
and detected class; a missing class must never call this model on a tank object.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class BehaviourProfile:
    label: str
    symbol: str
    acceleration: float
    speed_cap: float


PROFILES = {
    "blue": BehaviourProfile("Cruiser", "B", 0, 68),
    "red": BehaviourProfile("Booster", "R", 42, 135),
    "gold": BehaviourProfile("Braker", "G", 65, 100),
}
BRAKE_ZONES = ((100, 260), (500, 700), (1200, 1480))


def in_brake_zone(distance):
    return any(low <= distance <= high for low, high in BRAKE_ZONES)


def next_speed(colour, speed, distance, dt):
    if colour == "red":
        return min(PROFILES[colour].speed_cap, speed+PROFILES[colour].acceleration*dt)
    if colour == "gold":
        profile = PROFILES[colour]
        desired = 28 if in_brake_zone(distance) else profile.speed_cap
        return max(0, speed+max(-profile.acceleration*dt,
                               min(profile.acceleration*dt, desired-speed)))
    return speed
