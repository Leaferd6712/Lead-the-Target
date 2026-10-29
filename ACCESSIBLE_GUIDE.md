# Accessible lesson companion

This document contains every guided task and its explanation. It can be read with a screen reader independently of the drawn game interface.

## Lesson 1

### 1. Will this shot hit?

The tank moves right at 80 px/s. A shell aimed at its current position takes time to reach the road. Predict the outcome.

Explanation: During flight, the tank keeps moving. An aim point is a prediction about the future.

Hint: Where will the tank be when the shell gets to the road?

### 2. Watch a direct shot

Run a direct shot. Follow the white ray and amber shell. We will measure their closest distance to the moving tank.

Explanation: This intentional miss is a baseline, not a penalty. Reload is the wait between launches; flight time starts at launch.

Hint: Run the experiment. A miss is the expected result.

### 3. Meet the moving tank

Choose Fixed lead and adjust the lead-time slider. Move the cyan ghost ahead of the tank, then run a shot that actually hits.

Explanation: Future position = position + velocity x time. Both objects must reach the same point together.

Hint: The flight is about 0.78 s. Try lead time near 0.8 s.

### 4. Take it to the field

Land 3 hits at 30% accuracy. Try a fixed lead near 0.8 seconds.

Explanation: Apply the skill in a tower-defense wave. Your base is rebuilt; field upgrades apply. Practice misses were not counted.

Hint: Use the model you just tested. Pause or slow the wave to inspect prediction and barrel tracking.

## Lesson 2

### 1. Calculate flight time

A shell travels 240 pixels at 240 px/s. How long is its flight?

Explanation: Time = distance / speed = 240 / 240 = 1 second. The units cancel to seconds.

Hint: Divide distance by shell speed.

### 2. Turn time into lead

During a 1-second flight, a tank moves at 60 px/s. How far ahead should the aim point move?

Explanation: Lead distance = target speed x flight time = 60 x 1 = 60 pixels.

Hint: 60 pixels each second, for one second.

### 3. A different range

Flight distance is now 360 pixels, shell speed 240 px/s, and tank speed 80 px/s. Choose flight time and lead distance.

Explanation: 360 / 240 = 1.5 s, then 80 x 1.5 = 120 px. One time guess cannot fit every range.

Hint: Find flight time first; multiply by tank speed.

### 4. Take it to the field

Land 4 hits at 40% accuracy. Adjust lead as tanks approach.

Explanation: Apply the skill in a tower-defense wave. Your base is rebuilt; field upgrades apply. Practice misses were not counted.

Hint: Use the model you just tested. Pause or slow the wave to inspect prediction and barrel tracking.

## Lesson 3

### 1. Build the prediction

Which expression predicts constant-velocity motion? p is position, v is velocity, and t is time.

Explanation: Vectors include direction. Add the displacement v*t to the starting position.

Hint: Position plus the distance travelled during flight.

### 2. Solve the meeting time

Choose Intercept and run a shot. It solves |r + v*t| = shell_speed*t for a meeting time.

Explanation: Squaring gives (v.v - s*s)t*t + 2(r.v)t + r.r = 0. Use the earliest positive root, then aim at p + v*t.

Hint: Intercept calculates the time instead of using the slider.

### 3. Choose the first meeting

A fast approaching tank gives two positive meeting times: 0.185 s and 1.667 s. Which intercept should be used first?

Explanation: The earliest positive root is the first reachable meeting. Negative roots describe the past.

Hint: Choose the first meeting in the future.

### 4. Transfer to a faster tank

This tank moves faster. Keep Intercept and hit it without guessing a fixed lead time.

Explanation: A physics-based algorithm recalculates the meeting point from the new velocity.

Hint: Leave Intercept selected and run the changed scenario.

### 5. Take it to the field

Select INTERCEPT. Land 5 hits at 80% accuracy.

Explanation: Apply the skill in a tower-defense wave. Your base is rebuilt; field upgrades apply. Practice misses were not counted.

Hint: Use the model you just tested. Pause or slow the wave to inspect prediction and barrel tracking.

## Lesson 4

### 1. Velocity is not a promise

Choose Intercept and run this accelerating target. Record the miss as your constant-velocity baseline.

Explanation: The velocity measured now changes during flight. Correct algebra can still use the wrong motion model.

Hint: Use Intercept first so we can measure its baseline miss.

### 2. Add changing velocity

Choose Adaptive and repeat the identical experiment. Reduce miss distance and hit the accelerating tank.

Explanation: Future position = p + v*t + 0.5*a*t*t. Adaptive trusts acceleration only over a short horizon.

Hint: Choose Adaptive. Acceleration moves the prediction farther ahead.

### 3. Now the tank slows down

Keep Adaptive and hit a decelerating target. This time acceleration opposes velocity.

Explanation: A slowing tank travels less distance, so it needs less lead. The same formula handles negative acceleration.

Hint: The ghost should be closer than a constant-velocity forecast.

### 4. Know the prediction limit

A tank suddenly changes speed after launch. What can a fresh observation improve?

Explanation: Observations improve the next shot. A non-homing shell cannot change direction after launch.

Hint: These shells have no steering motor.

### 5. Take it to the field

Land 5 hits at 60% accuracy. Try ADAPTIVE for speed changes.

Explanation: Apply the skill in a tower-defense wave. Your base is rebuilt; field upgrades apply. Practice misses were not counted.

Hint: Use the model you just tested. Pause or slow the wave to inspect prediction and barrel tracking.

## Lesson 5

### 1. Install a colour sensor

Open Workshop and install the colour sensor. If already installed, verify it. This lesson funds the required purchase.

Explanation: A sensor adds an input to the code. A colour visible to you is not automatically visible to the targeting algorithm.

Hint: Workshop > Colour sensor. Then return here and verify it.

### 2. Measure with colour OFF

Choose Colour aware, turn colour input OFF, and run the red tank. Observe its fallback branch.

Explanation: Without the sensor, colour is None. The code uses measured motion rather than hidden tank state.

Hint: Switch colour OFF and keep Colour aware selected.

### 3. Run the boost branch

Turn colour input ON. Repeat with Colour aware and hit the red tank using its detected boost model.

Explanation: RED gains 42 px/s each second up to 135 px/s. The sensor identifies a published rule, not future positions.

Hint: Switch colour ON and look for RED > BOOST + SPEED CAP.

### 4. Follow a different branch

Run the gold tank with colour ON. Execute the brake-zone branch and hit the target.

Explanation: GOLD approaches 28 px/s in striped zones and 100 outside. One algorithm selects different code paths.

Hint: Gold needs the brake-zone model, not the red boost rule.

### 5. Explain the condition

Which input selects the colour-aware boost rule?

Explanation: An if/elif branch reacts to a detected class. A fallback remains necessary when a sensor is absent.

Hint: The branch reads the sensor colour value.

### 6. Take it to the field

Use COLOUR AWARE with sensor ON. Land 6 hits at 80% accuracy.

Explanation: Apply the skill in a tower-defense wave. Your base is rebuilt; field upgrades apply. Practice misses were not counted.

Hint: Use the model you just tested. Pause or slow the wave to inspect prediction and barrel tracking.

## Lesson 6

### 1. Measure slow tracking

Run the P=1 baseline. Watch desired direction, actual barrel and angular error. This motor calibration needs no shells.

Explanation: P = Kp * angular error. Low gain produces a weak turn command and a slow response.

Hint: Run the baseline before changing P.

### 2. Improve the response

Raise P and repeat. Reduce RMS error by at least 20% without excessive overshoot. Other terms stay zero.

Explanation: More P speeds the response, but motor lag can cause overshoot. Compare the measured response.

Hint: Try P around 6-8. Very high P can oscillate.

### 3. Explain the stronger turn

If angular error doubles and the motor is not saturated, what happens to P?

Explanation: P is proportional: twice the error requests twice the P contribution. Output limits can clip the total.

Hint: P = gain x error.

### 4. Take it to the field

Land 5 hits at 35% accuracy. Try P near 6-8, then compare.

Explanation: Apply the skill in a tower-defense wave. Your base is rebuilt; field upgrades apply. Practice misses were not counted.

Hint: Use the model you just tested. Pause or slow the wave to inspect prediction and barrel tracking.

## Lesson 7

### 1. Measure persistent bias

Run a fixed-direction test with I=0 and a +9 deg/s motor disturbance. Record the steady error.

Explanation: P alone needs persistent error to cancel a disturbance. Integral remembers that error and builds correction.

Hint: A fixed reference isolates the remaining offset.

### 2. Remove steady error

Raise I and repeat. Reduce mean absolute error over the final two seconds by at least 40%. P stays fixed.

Explanation: I = Ki * accumulated error. Anti-windup prevents unlimited correction when output saturates.

Hint: Try I between 1 and 2. Its correction builds over time.

### 3. Measure overshoot

Run a step-turn with D=0. I is disabled in both damping trials for a fair comparison.

Explanation: The motor can keep moving past the desired angle. We measure the largest overshoot after the turn.

Hint: Observe the peak past the desired direction.

### 4. Damp the motion

Raise D and repeat. Reduce peak overshoot by at least 25% while retaining a useful response.

Explanation: D = -Kd * measured turn rate. Damping resists rapid movement and avoids a setpoint derivative kick.

Hint: Try D around 0.3-0.6. Too much also slows tracking.

### 5. Take it to the field

Land 6 hits at 40% accuracy. Adjust I and D; start P near 6-8.

Explanation: Apply the skill in a tower-defense wave. Your base is rebuilt; field upgrades apply. Practice misses were not counted.

Hint: Use the model you just tested. Pause or slow the wave to inspect prediction and barrel tracking.

## Lesson 8

### 1. Measure tracking lag

Run a moving-reference baseline with F=0. P=8 and D=0.3 stay fixed in both feedforward trials.

Explanation: Feedback reacts after error develops. A moving reference needs continuous turning effort.

Hint: Record a baseline before enabling feedforward.

### 2. Anticipate the turn

Raise F and repeat the same movement. Reduce steady tracking error by at least 30% with other gains fixed.

Explanation: F = Kf * desired turn rate. P corrects, I remembers, D damps and F anticipates. The motor limits their sum.

Hint: Try F near 1. It supplies the desired turning speed before lag builds.

### 3. Choose the anticipating term

Which term supplies effort from desired movement before tracking error develops?

Explanation: Feedforward models what motion requires. Feedback corrects model errors and disturbances.

Hint: The clue is desired movement, rather than measured error.

### 4. Defend with what you learned

Launch the final mixed wave. Land 8 hits at 60% accuracy and protect the base using your sensor and tuned motor.

Explanation: This transfer challenge combines sensing, prediction and control. Field upgrades now apply; calibration trials used fixed equipment.

Hint: Colour aware and P=8, I=1, D=0.3, F=1 are useful starting values. Inspect barrel error if shots miss.
