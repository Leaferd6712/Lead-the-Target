"""Evidence-based curriculum. Page navigation cannot award mastery."""
from dataclasses import dataclass
from lessons import LESSONS


@dataclass(frozen=True)
class LessonStep:
    id: str
    title: str
    task: str
    why: str
    kind: str
    scenario: str = ""
    options: tuple = ()
    correct: str = ""
    hint: str = ""


STEPS = (
    (
        LessonStep("predict", "Will this shot hit?", "The tank moves right at 80 px/s. A shell aimed at its current position takes time to reach the road. Predict the outcome.", "During flight, the tank keeps moving. An aim point is a prediction about the future.", "choice", options=("It will hit", "It will miss behind the tank"), correct="It will miss behind the tank", hint="Where will the tank be when the shell gets to the road?"),
        LessonStep("observe", "Watch a direct shot", "Run a direct shot. Follow the white ray and amber shell. We will measure their closest distance to the moving tank.", "This intentional miss is a baseline, not a penalty. Reload is the wait between launches; flight time starts at launch.", "trial", "direct", hint="Run the experiment. A miss is the expected result."),
        LessonStep("lead", "Meet the moving tank", "Choose Fixed lead and adjust the lead-time slider. Move the cyan ghost ahead of the tank, then run a shot that actually hits.", "Future position = position + velocity x time. Both objects must reach the same point together.", "trial", "fixed", hint="The flight is about 0.78 s. Try lead time near 0.8 s."),
    ),
    (
        LessonStep("time", "Calculate flight time", "A shell travels 240 pixels at 240 px/s. How long is its flight?", "Time = distance / speed = 240 / 240 = 1 second. The units cancel to seconds.", "choice", options=("0.5 seconds", "1 second", "2 seconds"), correct="1 second", hint="Divide distance by shell speed."),
        LessonStep("distance", "Turn time into lead", "During a 1-second flight, a tank moves at 60 px/s. How far ahead should the aim point move?", "Lead distance = target speed x flight time = 60 x 1 = 60 pixels.", "choice", options=("30 pixels", "60 pixels", "240 pixels"), correct="60 pixels", hint="60 pixels each second, for one second."),
        LessonStep("transfer", "A different range", "Flight distance is now 360 pixels, shell speed 240 px/s, and tank speed 80 px/s. Choose flight time and lead distance.", "360 / 240 = 1.5 s, then 80 x 1.5 = 120 px. One time guess cannot fit every range.", "choice", options=("1 s and 80 px", "1.5 s and 120 px", "2 s and 160 px"), correct="1.5 s and 120 px", hint="Find flight time first; multiply by tank speed."),
    ),
    (
        LessonStep("formula", "Build the prediction", "Which expression predicts constant-velocity motion? p is position, v is velocity, and t is time.", "Vectors include direction. Add the displacement v*t to the starting position.", "choice", options=("p + v * t", "p - v / t", "v + p * t"), correct="p + v * t", hint="Position plus the distance travelled during flight."),
        LessonStep("solve", "Solve the meeting time", "Choose Intercept and run a shot. It solves |r + v*t| = shell_speed*t for a meeting time.", "Squaring gives (v.v - s*s)t*t + 2(r.v)t + r.r = 0. Use the earliest positive root, then aim at p + v*t.", "trial", "intercept", hint="Intercept calculates the time instead of using the slider."),
        LessonStep("root", "Choose the first meeting", "A fast approaching tank gives two positive meeting times: 0.185 s and 1.667 s. Which intercept should be used first?", "The earliest positive root is the first reachable meeting. Negative roots describe the past.", "choice", options=("0.185 seconds", "1.667 seconds", "Always the larger root"), correct="0.185 seconds", hint="Choose the first meeting in the future."),
        LessonStep("faster", "Transfer to a faster tank", "This tank moves faster. Keep Intercept and hit it without guessing a fixed lead time.", "A physics-based algorithm recalculates the meeting point from the new velocity.", "trial", "fast", hint="Leave Intercept selected and run the changed scenario."),
    ),
    (
        LessonStep("cv_baseline", "Velocity is not a promise", "Choose Intercept and run this accelerating target. Record the miss as your constant-velocity baseline.", "The velocity measured now changes during flight. Correct algebra can still use the wrong motion model.", "trial", "accel_cv", hint="Use Intercept first so we can measure its baseline miss."),
        LessonStep("acceleration", "Add changing velocity", "Choose Adaptive and repeat the identical experiment. Reduce miss distance and hit the accelerating tank.", "Future position = p + v*t + 0.5*a*t*t. Adaptive trusts acceleration only over a short horizon.", "trial", "accel_adaptive", hint="Choose Adaptive. Acceleration moves the prediction farther ahead."),
        LessonStep("brake", "Now the tank slows down", "Keep Adaptive and hit a decelerating target. This time acceleration opposes velocity.", "A slowing tank travels less distance, so it needs less lead. The same formula handles negative acceleration.", "trial", "decelerate", hint="The ghost should be closer than a constant-velocity forecast."),
        LessonStep("limits", "Know the prediction limit", "A tank suddenly changes speed after launch. What can a fresh observation improve?", "Observations improve the next shot. A non-homing shell cannot change direction after launch.", "choice", options=("The next shot's aim", "The shell already in flight", "The past observation"), correct="The next shot's aim", hint="These shells have no steering motor."),
    ),
    (
        LessonStep("purchase", "Install a colour sensor", "Open Workshop and install the colour sensor. If already installed, verify it. This lesson funds the required purchase.", "A sensor adds an input to the code. A colour visible to you is not automatically visible to the targeting algorithm.", "purchase", hint="Workshop > Colour sensor. Then return here and verify it."),
        LessonStep("off", "Measure with colour OFF", "Choose Colour aware, turn colour input OFF, and run the red tank. Observe its fallback branch.", "Without the sensor, colour is None. The code uses measured motion rather than hidden tank state.", "trial", "colour_off", hint="Switch colour OFF and keep Colour aware selected."),
        LessonStep("on", "Run the boost branch", "Turn colour input ON. Repeat with Colour aware and hit the red tank using its detected boost model.", "RED gains 42 px/s each second up to 135 px/s. The sensor identifies a published rule, not future positions.", "trial", "colour_on", hint="Switch colour ON and look for RED > BOOST + SPEED CAP."),
        LessonStep("gold", "Follow a different branch", "Run the gold tank with colour ON. Execute the brake-zone branch and hit the target.", "GOLD approaches 28 px/s in striped zones and 100 outside. One algorithm selects different code paths.", "trial", "colour_gold", hint="Gold needs the brake-zone model, not the red boost rule."),
        LessonStep("classify", "Explain the condition", "Which input selects the colour-aware boost rule?", "An if/elif branch reacts to a detected class. A fallback remains necessary when a sensor is absent.", "choice", options=("Detected colour is RED", "The tank looks big", "Reload timer is zero"), correct="Detected colour is RED", hint="The branch reads the sensor colour value."),
    ),
    (
        LessonStep("p_base", "Measure slow tracking", "Run the P=1 baseline. Watch desired direction, actual barrel and angular error. This motor calibration needs no shells.", "P = Kp * angular error. Low gain produces a weak turn command and a slow response.", "trial", "p_base", hint="Run the baseline before changing P."),
        LessonStep("p_tune", "Improve the response", "Raise P and repeat. Reduce RMS error by at least 20% without excessive overshoot. Other terms stay zero.", "More P speeds the response, but motor lag can cause overshoot. Compare the measured response.", "trial", "p_tune", hint="Try P around 6-8. Very high P can oscillate."),
        LessonStep("meaning", "Explain the stronger turn", "If angular error doubles and the motor is not saturated, what happens to P?", "P is proportional: twice the error requests twice the P contribution. Output limits can clip the total.", "choice", options=("P contribution doubles", "P becomes zero", "Integral memory resets"), correct="P contribution doubles", hint="P = gain x error."),
    ),
    (
        LessonStep("i_base", "Measure persistent bias", "Run a fixed-direction test with I=0 and a +9 deg/s motor disturbance. Record the steady error.", "P alone needs persistent error to cancel a disturbance. Integral remembers that error and builds correction.", "trial", "i_base", hint="A fixed reference isolates the remaining offset."),
        LessonStep("i_tune", "Remove steady error", "Raise I and repeat. Reduce mean absolute error over the final two seconds by at least 40%. P stays fixed.", "I = Ki * accumulated error. Anti-windup prevents unlimited correction when output saturates.", "trial", "i_tune", hint="Try I between 1 and 2. Its correction builds over time."),
        LessonStep("d_base", "Measure overshoot", "Run a step-turn with D=0. I is disabled in both damping trials for a fair comparison.", "The motor can keep moving past the desired angle. We measure the largest overshoot after the turn.", "trial", "d_base", hint="Observe the peak past the desired direction."),
        LessonStep("d_tune", "Damp the motion", "Raise D and repeat. Reduce peak overshoot by at least 25% while retaining a useful response.", "D = -Kd * measured turn rate. Damping resists rapid movement and avoids a setpoint derivative kick.", "trial", "d_tune", hint="Try D around 0.3-0.6. Too much also slows tracking."),
    ),
    (
        LessonStep("f_base", "Measure tracking lag", "Run a moving-reference baseline with F=0. P=8 and D=0.3 stay fixed in both feedforward trials.", "Feedback reacts after error develops. A moving reference needs continuous turning effort.", "trial", "f_base", hint="Record a baseline before enabling feedforward."),
        LessonStep("f_tune", "Anticipate the turn", "Raise F and repeat the same movement. Reduce steady tracking error by at least 30% with other gains fixed.", "F = Kf * desired turn rate. P corrects, I remembers, D damps and F anticipates. The motor limits their sum.", "trial", "f_tune", hint="Try F near 1. It supplies the desired turning speed before lag builds."),
        LessonStep("explain", "Choose the anticipating term", "Which term supplies effort from desired movement before tracking error develops?", "Feedforward models what motion requires. Feedback corrects model errors and disturbances.", "choice", options=("F: feedforward", "I: accumulated error", "D: motion damping"), correct="F: feedforward", hint="The clue is desired movement, rather than measured error."),
        LessonStep("defend", "Defend with what you learned", "Launch the final mixed wave. Land 8 hits at 60% accuracy and protect the base using your sensor and tuned motor.", "This transfer challenge combines sensing, prediction and control. Field upgrades now apply; calibration trials used fixed equipment.", "wave", hint="Colour aware and P=8, I=1, D=0.3, F=1 are useful starting values. Inspect barrel error if shots miss."),
    ),
)


STEPS = tuple(steps + (LessonStep("field", "Take it to the field", LESSONS[index].challenge,
    "Apply the skill in a tower-defense wave. Your base is rebuilt; field upgrades apply. Practice misses were not counted.",
    "wave", hint="Use the model you just tested. Pause or slow the wave to inspect prediction and barrel tracking."),)
    if index < 7 else steps for index, steps in enumerate(STEPS))


class LessonRunner:
    def __init__(self, stage, records):
        self.stage, self.records = stage, records
        self.pending = next((k for k, v in records.items() if k.startswith(f"{stage}:") and not v.get("acknowledged", True)), None)
        self.feedback = ""
        self.attempts = 0
        self.changed = set()

    @property
    def steps(self):
        return STEPS[self.stage]

    def key(self, step):
        return f"{self.stage}:{step.id}"

    @property
    def step(self):
        return next((s for s in self.steps if self.key(s) not in self.records), None)

    @property
    def complete(self):
        return self.step is None

    def evidence_for(self, id):
        return self.records.get(f"{self.stage}:{id}", {}).get("evidence", {})

    def fail(self, message):
        self.attempts += 1
        self.feedback = message
        return False

    def award(self, evidence):
        step = self.step
        if step is None or self.pending:
            return False
        self.records[self.key(step)] = {"title": step.title, "why": step.why,
                                       "evidence": evidence, "acknowledged": False}
        self.pending = self.key(step)
        self.feedback = ""
        self.attempts = 0
        self.changed.clear()
        return True

    def answer(self, answer):
        step = self.step
        if not step or step.kind != "choice":
            return self.fail("Complete the current experiment first.")
        if answer != step.correct:
            return self.fail("Not yet. "+step.hint)
        return self.award({"answer": answer, "reason": step.why})

    def assess(self, metrics):
        step = self.step
        if step is None or step.kind != "trial" or metrics.kind != step.scenario:
            return self.fail("Run the experiment for the current task.")
        kind = metrics.kind
        if kind == "direct":
            passed = not metrics.hit and metrics.miss_distance > 12
        elif kind == "fixed":
            passed = metrics.algorithm == 1 and metrics.hit and "lead" in self.changed
        elif kind in ("intercept", "fast"):
            passed = metrics.algorithm == 2 and metrics.hit
        elif kind == "accel_cv":
            passed = metrics.algorithm == 2 and not metrics.hit
        elif kind == "accel_adaptive":
            base = self.evidence_for("cv_baseline").get("miss_distance", 0)
            passed = metrics.algorithm == 3 and metrics.hit and metrics.miss_distance < base*0.65
        elif kind == "decelerate":
            passed = metrics.algorithm == 3 and metrics.hit
        elif kind == "colour_off":
            passed = metrics.algorithm == 4 and metrics.branch.startswith("NO COLOUR")
        elif kind in ("colour_on", "colour_gold"):
            expected = "RED" if kind == "colour_on" else "GOLD"
            passed = metrics.algorithm == 4 and metrics.hit and metrics.branch.startswith(expected)
        elif kind.endswith("_base"):
            passed = len(metrics.samples) >= 500
        else:
            metric, baseline, fraction, gain = {
                "p_tune": ("rms_error", "p_base", 0.8, 0),
                "i_tune": ("steady_error", "i_base", 0.6, 1),
                "d_tune": ("overshoot", "d_base", 0.75, 2),
                "f_tune": ("steady_error", "f_base", 0.7, 3),
            }[kind]
            before = self.evidence_for(baseline).get(metric, 0)
            passed = (getattr(metrics, metric) < before*fraction and metrics.gains[gain] > 0
                      and "pidf"[gain] in self.changed and metrics.overshoot < 45)
            if kind == "d_tune":
                passed = passed and metrics.rms_error < 35
        if not passed:
            detail = (f"Closest miss: {metrics.miss_distance:.1f} px. " if not metrics.samples else
                      f"RMS {metrics.rms_error:.2f}; steady {metrics.steady_error:.2f}; overshoot {metrics.overshoot:.2f} deg. ")
            return self.fail(detail+step.hint)
        return self.award(metrics.evidence())

    def acknowledge(self):
        if self.pending in self.records:
            self.records[self.pending]["acknowledged"] = True
        self.pending = None
        self.changed.clear()
