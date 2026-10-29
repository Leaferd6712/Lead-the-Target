"""Campaign curriculum and just-in-time explanations, kept out of rendering."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Lesson:
    title: str
    subtitle: str
    explanation: tuple[str, ...]
    formula: str
    challenge: str
    count: int
    gap: float
    unlock: int
    min_hits: int
    min_hit_rate: float


LESSONS = (
    Lesson("01 / Aim into the future", "A moving target will not wait for a shell.", (
        "Watch the comparison first: both tanks move at 80 pixels per second. Both shells travel at 240 pixels per second. Only the predicted shot meets its tank.",
        "In the battlefield, DIRECT aims at the current position. Watch two shots miss, then choose FIXED LEAD. Move its time slider until the shell meets the tank.",
        "A reload is the wait between launches. Flight time begins when a shell leaves the barrel. We recalculate the aim at every launch."),
        "future position = position + velocity x lead time",
        "Land 3 hits at 30% accuracy. Try a fixed lead near 0.8 seconds.", 6, 2.8, 1, 3, .30),
    Lesson("02 / One guess is not enough", "Same algorithm. Different speeds and distances.", (
        "This wave alternates slow and fast tanks. A fixed lead is a time guess, not a fixed distance: a faster tank needs more lead distance.",
        "Even the right time guess stops working as range changes. A shell travelling 300 px/s takes 1 second to cover 300 pixels, but only half a second to cover 150.",
        "Change the lead time while the wave is running. Use pause and single-step to compare the predicted cross with the actual shell path."),
        "flight time = travel distance / shell speed",
        "Land 4 hits at 40% accuracy. Adjust lead as tanks approach.", 8, 2.5, 1, 4, .40),
    Lesson("03 / Solve, do not guess", "Find a meeting point in space and time.", (
        "INTERCEPT solves for a time when the shell and tank reach the same point. Select it in the algorithm panel and compare it with fixed lead.",
        "Let r be the tank position minus tower position, v its velocity, and s shell speed. Squaring |r + v*t| = s*t gives a quadratic. The earliest positive root is the first possible meeting time.",
        "The inspector shows the root and lead point. If no positive root exists, the tower waits. Reload still limits how often you can fire."),
        "(v.v - s*s)t*t + 2(r.v)t + r.r = 0",
        "Select INTERCEPT. Land 5 hits at 80% accuracy.", 8, 2.2, 2, 5, .80),
    Lesson("04 / The world changes", "Velocity now is not a promise about later.", (
        "Some tanks boost, brake, or change speed mid-path. Watch the dashed gold road zones. A constant-velocity intercept becomes inaccurate during speed changes.",
        "ADAPTIVE estimates acceleration from successive velocity observations. It uses p + v*t + 0.5*a*t*t for a short horizon, then continues at that forecast speed.",
        "A sudden change after launch can still cause a miss. Refreshing a prediction improves the next shot; it cannot steer a shell already in flight. At corners, the sensor resets its acceleration estimate."),
        "future position = p + v*t + 0.5*a*t*t",
        "Land 5 hits at 60% accuracy. Try ADAPTIVE for speed changes.", 9, 2.5, 3, 5, .60),
    Lesson("05 / Sense, classify, branch", "A new sensor changes what code can know.", (
        "Buy the COLOUR SENSOR in the shop, then select COLOUR AWARE. Without the sensor, colour is None and this strategy falls back to measured acceleration.",
        "BLUE holds its speed. RED boosts by 42 px/s each second up to 135 px/s. GOLD brakes toward 28 px/s in gold road zones and returns toward 100 outside them.",
        "The colour branch forecasts these published rules along the known road. This is a model, not a view into the future. Follow the branch label in the inspector and compare sensor ON and OFF in the shop."),
        "if red: boost; elif gold: brake zones; else: cruise",
        "Use COLOUR AWARE with sensor ON. Land 6 hits at 80% accuracy.", 10, 2.1, 4, 6, .80),
    Lesson("06 / Turn with proportional control", "A correct lead point still needs a tracking turret.", (
        "The turret now has a real motor: finite turning speed and response lag. The green line shows the desired direction, while the bright barrel shows actual rotation.",
        "P multiplies angular error by Kp. A larger error produces a stronger turn. Low P lags behind; high P can oscillate because the motor takes time to respond.",
        "Experiment with P between 1 and 14. Watch error in degrees and turn commands in degrees per second. Every shot follows the actual barrel, even if it has not caught up."),
        "P = Kp * wrap(desired angle - actual angle)",
        "Land 5 hits at 35% accuracy. Try P near 6-8, then compare.", 8, 2.7, 4, 5, .35),
    Lesson("07 / Remember and damp", "Integral removes bias. Derivative controls overshoot.", (
        "A visible +9 deg/s motor bias is now active. P alone needs a persistent opposite error to cancel it. First raise I: it accumulates that error and supplies a correcting command.",
        "Too much I stores excessive correction. Anti-windup stops accumulation into saturation and caps the integral. Reset tuning to clear its memory before a new experiment.",
        "Now raise D. This implementation uses -Kd * measured angular velocity: damping that resists rapid turning. It avoids a derivative kick when the selected target changes, but also slows tracking unless compensated."),
        "I = Ki * sum(error*dt); D = -Kd * filtered turn rate",
        "Land 6 hits at 40% accuracy. Adjust I and D; start P near 6-8.", 10, 2.6, 4, 6, .40),
    Lesson("08 / Anticipate with feedforward", "Bring sensing, prediction and control together.", (
        "F estimates how fast the desired aim direction is moving. It supplies turning effort before tracking error has to build. Try Kf near 1, then compare with F = 0.",
        "P corrects the present error, I remembers persistent error, D damps motion, and F anticipates desired motion. Their sum requests a turn rate; the motor clips that request and responds with lag.",
        "The final wave mixes all tank behaviours. Tune the controller, inspect sensor branches, and buy useful upgrades. After victory, the sandbox lets you replay every lesson with all algorithms unlocked."),
        "turn request = P + I + D + F; F = Kf * desired turn rate",
        "Land 8 hits at 60% accuracy. Tune PIDF, then unlock sandbox.", 12, 2.2, 4, 8, .60),
)

UPGRADES = {
    "colour": ("Colour sensor", (80,), "Reveals class; unlocks colour branches."),
    "sensor": ("Sampling rate", (45, 75), "8 Hz > 13 Hz > 25 Hz observations."),
    "reload": ("Reload mechanism", (50, 85), "1.05 s > 0.86 s > 0.67 s per shot."),
    "shell": ("Shell speed", (55, 90), "240 > 270 > 300 px/s; less flight time."),
    "motor": ("Turret motor", (55, 90), "Higher turn limit and quicker response."),
    "damage": ("Shell damage", (70,), "1 > 2 damage per hit."),
}
