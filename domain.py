"""Shared state and evidence. No graphics or input dependencies."""
from dataclasses import dataclass, field
from enum import StrEnum


class Scene(StrEnum):
    TITLE = "title"
    COACH = "coach"
    EXPERIMENT = "experiment"
    CONGRATS = "congrats"
    READY = "ready"
    PLAYING = "playing"
    RESULT = "result"
    SHOP = "shop"
    MAP = "map"
    NOTEBOOK = "notebook"
    OPTIONS = "options"
    CONFIRM = "confirm"
    VICTORY = "victory"


class SceneRouter:
    """Return destinations belong to one navigation owner, never to a widget."""
    def __init__(self):
        self.scene = Scene.TITLE
        self.stack = []

    def go(self, scene):
        self.scene = Scene(scene)
        self.stack.clear()

    def open(self, scene):
        self.stack.append(self.scene)
        self.scene = Scene(scene)

    def close(self):
        self.scene = self.stack.pop() if self.stack else Scene.COACH


@dataclass(frozen=True)
class LessonEvent:
    kind: str
    time: float
    data: dict = field(default_factory=dict)


@dataclass
class ShotRecord:
    id: int
    target_id: int
    algorithm: int
    gains: tuple
    launched_at: float
    aim: tuple
    branch: str
    outcome: str = "pending"
    miss_distance: float = 9999.0
    resolved_at: float | None = None
    hit_target: int | None = None


@dataclass
class TrialMetrics:
    kind: str
    algorithm: int = 0
    hit: bool = False
    miss_distance: float = 0
    flight_time: float = 0
    rms_error: float = 0
    steady_error: float = 0
    overshoot: float = 0
    branch: str = ""
    gains: tuple = (4, 0, 0, 0)
    samples: list = field(default_factory=list)

    def evidence(self):
        """Only bounded, JSON-friendly summary data belongs in the save file."""
        values = {key: value for key, value in vars(self).items() if key != "samples"}
        # Default zero fields are not measurements. A ballistic hit must never
        # congratulate the player for a fabricated zero-degree motor error.
        if not self.samples:
            for key in ("rms_error", "steady_error", "overshoot"):
                values.pop(key)
        else:
            for key in ("hit", "miss_distance", "flight_time", "branch"):
                values.pop(key)
        return values
