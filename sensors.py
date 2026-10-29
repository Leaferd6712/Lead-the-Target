"""Sampled sensors. This is the only bridge from tanks to targeting observations."""
from targeting import TargetObservation, Vec2


class SensorSuite:
    def __init__(self, colour=False, level=0):
        self.colour = colour
        self.interval = (0.12, 0.075, 0.04)[level]
        self.last_sample = -1.0
        self.observations = {}
        self.sample_counts = {}

    def update(self, tanks, time):
        active = {tank.id for tank in tanks if tank.alive}
        self.observations = {k: v for k, v in self.observations.items() if k in active}
        self.sample_counts = {k: v for k, v in self.sample_counts.items() if k in active}
        if time-self.last_sample < self.interval:
            return
        for tank in tanks:
            if not tank.alive:
                continue
            previous = self.observations.get(tank.id)
            velocity, acceleration = Vec2(0, 0), Vec2(0, 0)
            if previous is not None:
                dt = time-previous.timestamp
                raw = (tank.position-previous.position)*(1/dt)
                # Avoid interpreting a path corner as sustained acceleration.
                turned = previous.velocity.length() > 1 and raw.unit().dot(previous.velocity.unit()) < 0.8
                velocity = raw if turned or previous.velocity.length() < 1 else previous.velocity*0.2 + raw*0.8
                if not turned and previous.velocity.length() > 1:
                    acceleration = previous.acceleration*0.65 + (velocity-previous.velocity)*(0.35/dt)
                    if acceleration.length() > 65:
                        acceleration = acceleration.unit()*65
            self.observations[tank.id] = TargetObservation(
                tank.id, tank.position, velocity, acceleration, tank.distance, time,
                tank.colour if self.colour else None)
            self.sample_counts[tank.id] = self.sample_counts.get(tank.id, 0)+1
        self.last_sample = time

    def confident(self, target_id):
        return self.sample_counts.get(target_id, 0) >= 2

    def read(self, time):
        # Extrapolate between samples; acceleration still comes from samples only.
        return [TargetObservation(o.target_id, o.position+o.velocity*(time-o.timestamp),
                                  o.velocity, o.acceleration,
                                  o.progress+o.velocity.length()*(time-o.timestamp),
                                  time, o.colour, o.timestamp) for o in self.observations.values()]
