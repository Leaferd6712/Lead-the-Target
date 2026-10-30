"""Construction and tower specifications. No engine dependency."""
from dataclasses import dataclass, field
from math import isfinite
from simulation import Tower
from targeting import Vec2


PADS = (Vec2(462,435), Vec2(270,360), Vec2(660,360), Vec2(755,470),
        Vec2(470,645), Vec2(230,645), Vec2(150,390), Vec2(680,645),
        Vec2(700,155), Vec2(380,155), Vec2(175,155), Vec2(750,340))


@dataclass(frozen=True)
class TowerSpec:
    title: str
    cost: int
    range: float
    shell_speed: float
    reload_time: float
    damage: int
    unlock: int
    description: str


SPECS = {
    "standard": TowerSpec("Sentinel", 90, 390, 240, 1.05, 1, 1,
                          "Balanced shells. Learn to lead moving targets."),
    "heavy": TowerSpec("Heavy cannon", 145, 450, 190, 1.8, 3, 8,
                       "Slow shells, heavy damage. Needs a longer forecast."),
    "tracking": TowerSpec("Tracking turret", 180, 370, 320, .72, 1, 41,
                          "Fast motor and rapid fire for moving targets."),
    "sensor": TowerSpec("Sensor station", 110, 300, 0, 0, 0, 31,
                        "Shares colour input with towers within 300 units."),
}


@dataclass
class Emplacement:
    id: int
    pad: int
    kind: str = "standard"
    level: int = 0
    algorithm: int = 1
    lead: float = .8
    gains: list = field(default_factory=lambda: [8, 0, 0, 0])
    colour: bool = False
    sensor_enabled: bool = True
    priority: str = "First"
    motor: Tower = field(default_factory=Tower, repr=False)
    solution: object = field(default=None, repr=False)
    target_id: int | None = None
    wait: str = "Waiting for observations"

    def __post_init__(self):
        self.motor.position = PADS[self.pad]
        self.apply_gains()

    @property
    def spec(self): return SPECS[self.kind]

    @property
    def radius(self): return self.spec.range + 25*self.level

    @property
    def damage(self): return self.spec.damage + self.level

    @property
    def shell_speed(self): return self.spec.shell_speed + 15*self.level

    @property
    def upgrade_cost(self): return 55 + 45*self.level

    @property
    def refund(self):
        return int(.65*(self.spec.cost + sum(55+45*i for i in range(self.level)) + 80*self.colour))

    def apply_gains(self):
        c = self.motor.controller
        c.kp, c.ki, c.kd, c.kf = self.gains

    def snapshot(self):
        return {k: getattr(self, k) for k in ("id", "pad", "kind", "level", "algorithm",
                "lead", "gains", "colour", "sensor_enabled", "priority")}


def restore_towers(records):
    """Validate untrusted save fields, including finite controller gains."""
    result, pads, ids = [], set(), set()
    for raw in records if isinstance(records, list) else []:
        if not isinstance(raw, dict): continue
        pad, ident = raw.get("pad"), raw.get("id")
        kind = raw.get("kind", "standard")
        if (type(pad) is not int or not 0 <= pad < len(PADS) or pad in pads
                or type(ident) is not int or ident < 1 or ident in ids or kind not in SPECS):
            continue
        def bounded(value, default, high):
            return min(high, max(0, value)) if type(value) in (int,float) and isfinite(value) else default
        gains = raw.get("gains", [8,0,0,0])
        if not isinstance(gains, list) or len(gains) != 4: gains = [8,0,0,0]
        gains = [bounded(v,d,h) for v,d,h in zip(gains,(8,0,0,0),(16,5,2,3))]
        tower = Emplacement(ident, pad, kind, int(bounded(raw.get("level"),0,3)),
                            int(bounded(raw.get("algorithm"),1,4)), bounded(raw.get("lead"),.8,2),
                            gains, raw.get("colour") is True, raw.get("sensor_enabled",True) is True,
                            raw.get("priority") if raw.get("priority") in ("First","Nearest","Strongest") else "First")
        result.append(tower); pads.add(pad); ids.add(ident)
    return result[:len(PADS)]
