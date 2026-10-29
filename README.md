# Lead the Target — Control Quest

**Runtime pip dependency: `pygame==2.6.1`. Python 3.11 or 3.12.**

**Optional build dependency: `pyinstaller==6.16.0` (`requirements-build.txt`).**

A colourful geometric 3D tower-defense game that teaches prediction, sensing and
PIDF control through **37 evidence-checked tasks across eight lessons**. The UI
uses chunky purple panels, turquoise controls, gold stars and explicit completion
screens inspired by the supplied arcade UI references.

## Play

Windows packaged build: open `dist/LeadTheTarget/LeadTheTarget.exe`. Keep the whole
`LeadTheTarget` folder together; Python and pip are not needed for that build.

Source build: double-click `play.bat` after installation, or run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

On macOS/Linux use `python3`, `.venv/bin/python`, and the same requirements/main.py.
No image downloads, accounts, network services or OpenGL drivers are needed.

## How learning works

The loop is **predict → run → observe measured evidence → congratulations → defend**.
Each lesson ends with a tower-defense transfer wave. Baseline experiment misses
do not count against combat accuracy. Reading a page or moving a slider cannot
award a skill: the required experiment must actually finish and meet its criterion.

- Make predictions and answer concrete time/distance/formula questions.
- Choose a model with the **Aim** dropdown or keys **1–5**.
- Adjust fixed lead with its slider or **[ / ]**, then run the experiment.
- Later, change the current P/I/D/F term and compare measured error/overshoot.
- The current task, hint and feedback remain visible in the coaching rail.
- **Congratulations** records the measurement and awards ten coins exactly once.
  Select **Continue** to acknowledge it and move on.
- After each lesson's experiments, launch its defense wave. Kills earn eight coins;
  a clear awards thirty-five. Required sensor funding is guaranteed and explained.
- **Workshop** previews upgrade effects. Calibration equipment is fixed to keep
  comparisons fair; upgrades apply in field waves and Free play.
- **Notes** holds your discoveries, results and replayable experiments.
- **Free play** unlocks all algorithms and grants 999 coins without modifying
  campaign mastery or banking its currency.

A failed field restores its starting currency. Replay retains your tuning and all
completed guided tasks. The base is rebuilt to sixteen health between field lessons.
Each leaked tank costs two health. Success requires the displayed hit count and
accuracy goal, calculated after all shots resolve. The motor has a two-degree
alignment interlock: bad tracking delays firing; shells always follow the actual
barrel and cannot steer after launch.

## Eight lessons

1. **Predict ahead:** observe direct aim missing, then adjust a fixed lead to hit.
2. **Time and distance:** calculate flight time and lead, then solve a changed range.
3. **Intercept:** select the future-position expression, solve the meeting time,
   choose its earliest positive root and hit a faster target.
4. **Acceleration:** measure a constant-velocity miss, improve it with acceleration,
   then handle deceleration and identify post-launch prediction limits.
5. **Colour sensing:** install the sensor, compare OFF/ON, execute red and gold
   branches and explain which input selects the branch.
6. **P:** compare P=1 with your tune, reducing RMS tracking error by at least 20%.
7. **I, then D:** reduce steady bias error by 40%, then overshoot by 25% in separate
   controlled comparisons. A slider value alone is insufficient.
8. **F:** reduce steady moving-reference error by 30%, explain feedforward, then
   complete the mixed final wave with all prior evidence recorded.

Useful calibration starting points: P around 6–8; I around 1–2; D around 0.3–0.6;
F around 1. The baseline and tuning trials explicitly hold other terms/equipment
constant. Your field tuning is preserved as lessons advance.

## Controls and accessibility

- **Mouse:** buttons and sliders. Click an enabled gain value for exact numeric entry.
- **Tab / Shift+Tab:** focus visible controls; **Enter** activates.
- **Arrow keys:** adjust an editable slider; gain fields also accept typed values.
- **1–5:** select an unlocked algorithm. **[ / ]:** fixed lead in 0.05s steps.
- **Space / Escape:** pause/resume an experiment or wave when a button is not focused.
- **Period:** advance one 1/120s simulation tick while paused.
- **H:** explanation; **V:** overlays; **F11:** fullscreen/windowed.
- **Mouse wheel / PageUp / PageDown:** scroll long coaching text or notebook entries.
- **Free play camera:** wheel over the battlefield zooms; right-drag orbits.
  **Camera** resets it. Guided cameras remain fixed for clear comparisons.
- **Options:** sound/mute, volume, reduced motion, larger text and high contrast.
- Losing focus/minimizing automatically pauses active simulation.

The interface uses symbols and labels as well as colour. It has a compact layout
for 800×600 windows and larger-text scrolling. A screen reader cannot infer drawn
pygame text; [ACCESSIBLE_GUIDE.md](ACCESSIBLE_GUIDE.md) provides the complete task
and explanation text as a normal document. Notifications occupy a reserved band
and do not cover buttons. New campaign asks before replacing a save.

## Saves and migration

Source runs save `save.json` beside the sources. The packaged Windows build uses
`%APPDATA%/LeadTheTarget/progress.json`. Saves include step evidence, acknowledgments,
once-only rewards, tuning, lead, algorithm, campaign economy and display options.
Writes are atomic, the previous good file becomes `.bak`, and an unreadable file
is preserved as `.unreadable` when starting again. A backup is recovered with an
explicit notice. Errors leave progress in the current session rather than crashing.

Old version-1 saves keep credits/upgrades but begin the guided sequence at lesson
one, since an old wave clear is not evidence that a skill was demonstrated. The
original file is backed up at the first write. To move a source save into the
packaged build, close the game and copy `save.json` to the packaged save location,
renaming it `progress.json`.

## Physics and rendering

The battlefield contains actual solid 3D meshes: extruded boxes, cylinders,
flat-shaded terrain/road, towers and tanks. `camera.py` projects their vertices
orthographically; `renderer3d.py` sorts visible faces and rasterizes them in pygame.
Static terrain and UI art are cached. No GPU context is needed for headless tests.

Gameplay uses a flat ground plane measured in pixels and seconds. Decorative mesh
height does not add gravity or alter the interception problem. This keeps simple
physics clear before any future vertical-ballistics extension. The mathematical
launch origin is the tower pivot and every predictor uses that same origin.

For constant velocity, solve `|r + v*t| = s*t`:

```text
r = target_position - tower_position
(v.v - s*s)t*t + 2(r.v)t + r.r = 0
lead_point = target_position + v*t
```

Select the earliest positive root; handle the equal-speed linear case separately.
Adaptive uses `p + v*t + 0.5*a*t*t` briefly, then continues at its forecast velocity.
Its bounded numerical solver reports when no intercept is found within four seconds.
Sampled sensors estimate motion from positions; colour stays `None` when absent or
disabled. Colour rules are shared published profiles, not access to future state.

```text
P = Kp * wrapped angular error
I = Ki * accumulated error
D = -Kd * filtered measured turn rate
F = Kf * desired turn rate
request = P + I + D + F
```

The motor has lag, speed limits, anti-windup and an explicitly applied bias.
Feedforward suppresses reference jumps on target reacquisition. Desired/actual
direction and live error are graphed beside the scene; term contributions, clipped
request and actual motor output remain visible. Collision uses earliest swept
contact, with shot provenance and pending/resolved outcomes recorded separately.

## Source layout

- `curriculum.py`: task definitions, evidence gates, mastery and acknowledgments.
- `experiments.py`: controlled ballistic and motor calibration simulations.
- `game.py`: campaign, wave scheduling, economy and typed scene transitions.
- `domain.py`: scene router, learner events, trial metrics and shot records.
- `targeting.py`: editable strategy classes and intercept solvers; no drawing.
- `sensors.py`, `behaviours.py`: sampled observations and published motion profiles.
- `control.py`, `simulation.py`: PIDF, motor response, tanks, shells, collision.
- `camera.py`, `geometry.py`, `renderer3d.py`: geometric 3D presentation.
- `theme.py`, `ui.py`, `audio.py`: UI art, responsive input and generated audio cues.
- `persistence.py`: validation, migration, backup and atomic writes.
- `tests/`: numerical, full-journey, navigation, save, projection and UI checks.

## Verify and build

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py --headless --stage 1 --frames 120 --benchmark --screenshot artifacts/quest.png
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build.ps1
```

`--stage 1` through `--stage 8` preview a guided lesson without altering saves.
`--autoplay` runs a Free play wave; it cannot award mastery. `--frames N` exits after
N frames. `--headless` uses deterministic SDL dummy video/audio. `--benchmark`
reports measured frame-processing mean/p95, excluding frame-rate throttling.
The tests include a complete 37-checkpoint learner journey and negative checks
that P-only tuning, final settings or scene changes cannot fabricate mastery.
Automated checks establish reproducible behaviour, not human learning outcomes;
classroom/first-time-player validation remains valuable.
