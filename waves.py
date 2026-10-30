"""One hundred deterministic encounters, with explicit, inspectable spawn times.

Changing a formation changes its timing and entrance, not the physics engine.
Distances are simulation units (shown as pixels in the original academy).
"""
from dataclasses import dataclass
from simulation import Path
from targeting import Vec2


REGIONS = ("Emerald Outpost", "Split Front", "Copper Canyon", "Chromatic Grove",
           "Motor Mesa", "Bias Barrens", "Anticipation Ridge", "Storm Crossing",
           "Obsidian Siege", "The Last Citadel")
FORMATIONS = ("First contact", "Scout patrol", "Staggered advance", "Rush hour",
              "Slow armour", "Double pulse", "Flanking party", "Speed trap",
              "Mixed convoy", "Region siege")


class Route(Path):
    def __init__(self, entrance=0):
        super().__init__()
        if entrance == 1:
            self.points = [Vec2(848, 75), Vec2(848, 258), Vec2(848, 558),
                           Vec2(88, 558), Vec2(88, 630)]
        elif entrance == 2:
            self.points = [Vec2(64, 75), Vec2(64, 258), Vec2(848, 258),
                           Vec2(848, 558), Vec2(88, 558), Vec2(88, 630)]
        self.lengths = [(b-a).length() for a, b in zip(self.points, self.points[1:])]
        self.length = sum(self.lengths)


@dataclass(frozen=True)
class Spawn:
    time: float
    entrance: int
    colour: str
    speed: float
    behaviour: str
    hp: int


@dataclass(frozen=True)
class Encounter:
    number: int
    region: str
    title: str
    briefing: str
    spawns: tuple[Spawn, ...]
    reward: int


def encounter(number):
    if type(number) is not int or not 1 <= number <= 100:
        raise ValueError("Campaign levels run from 1 to 100")
    region, formation = divmod(number-1, 10)
    count = 5 + region*2 + formation//2
    if formation == 9:
        count += 5
    events = []
    for i in range(count):
        # Pulses and flank attacks have deliberate pauses; no random spawn timer.
        gap = 2.8 if region == 0 else max(.85, 2.5-region*.14)
        time = 2+i*gap + (4 if formation in (5, 9) and i >= count//2 else 0)
        if formation == 3:
            time = 2+i*max(.8, gap*.6)
        entrance = (i+formation) % min(3, 1+region//1) if number >= 11 else 0
        colour, behaviour = "blue", "constant"
        speed = (65, 80, 55, 105, 45, 80, 70, 100, 65, 90)[formation]
        if region >= 1 and i % 2:
            speed += 25
        if region >= 2 and i % 3 == 0:
            colour, behaviour, speed = "red", "boost", 45
        if region >= 2 and i % 3 == 1:
            colour, behaviour, speed = "gold", "brake", 100
        if region >= 7 and i % 4 == 3:
            colour, behaviour = "blue", "switch"
        hp = 1+region//2 + (1 if formation in (4, 9) and region > 0 else 0)
        events.append(Spawn(round(time, 3), entrance, colour, speed, behaviour, hp))
    events.sort(key=lambda s: s.time)
    concept = ("Lead the tank: shots take time to travel. Build a second tower when ready.",
               "Watch the attack schedule: more than one entrance is active.",
               "Boosting and braking break a fixed time guess. Try Adaptive.",
               "Install a colour sensor. RED boosts, GOLD brakes, BLUE cruises.",
               "Turret motors now have lag. P turns angular error into motor effort.",
               "A +9 deg/s motor bias needs I. D damps rapid turning and overshoot.",
               "F follows the desired turn rate before tracking error builds.",
               "Surprise speed changes cannot be known before the next sample.",
               "Coordinate tower priorities, coverage and shell reservations.",
               "Combine accurate prediction, PIDF and overlapping fortress coverage.")[region]
    return Encounter(number, REGIONS[region], FORMATIONS[formation], concept,
                     tuple(events), 55+region*12+(35 if formation == 9 else 0))


LEVELS = tuple(encounter(i) for i in range(1, 101))
