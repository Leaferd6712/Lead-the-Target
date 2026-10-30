# Lead the Target — Fortress / Control Quest

**Runtime pip dependency: `panda3d==1.10.16`. Python 3.12 is the tested version.**

A real 3D tower-defence game built with Panda3D. Tanks keep moving while shells
travel, so aiming at their current position misses. Build a fortress, choose a
prediction model and make the shell meet the target in the future.

Official site: https://leaferd6712.github.io/Lead-the-Target/

Downloads: https://github.com/Leaferd6712/Lead-the-Target/releases/latest

## Three ways to play

- **Python source ZIP:** extract, install Python 3.12, then run the commands below.
- **Portable Windows ZIP:** extract the complete archive and run
  `LeadTheTarget/LeadTheTarget.exe`. Keep `_internal` and all supplied files together.
  Python and the dependencies are bundled; no installation is required.
- **Windows installer EXE:** run `LeadTheTarget-vVERSION-windows-setup.exe`.
  It installs for the current user, creates Start menu shortcuts, optionally adds
  a desktop shortcut and includes an uninstaller. No Python or administrator
  permissions are required. Uninstalling keeps your profile.

These are unsigned independent builds. Verify the release's SHA256SUMS.txt if
needed. Do not disable security software to run a download.

## Run the source

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

`play.bat` also launches the game. On macOS/Linux use `.venv/bin/python`; those
source platforms have not been verified. Windows x64 is the packaged target.

## Playing

Start with **Continue campaign** or visit the **Academy**. The campaign has 100
timed encounters across ten regions. Region patterns include rushes, armour,
staggered attacks, multiple gates, boosts, braking and surprise speed switches.

Select a numbered pad, choose **Build towers**, choose a tower type and click an
empty pad. Sentinels are available immediately; heavy cannons unlock at level 8,
colour hardware and sensor stations at 31, tracking turrets and motor control
at 41. Each tower has independent aim, reload, upgrades and target priority.
Shell reservations coordinate incoming damage between towers. Later regions
introduce motor bias and PIDF challenges.

- **Direct** aims at the current observed position: watch it miss behind a tank.
- **Fixed lead** uses `position + velocity * time`. Drag the native slider, type
  an exact value and press Enter, use the +/- buttons, or press `[` / `]`.
- **Intercept** solves `|r + v*t| = shell_speed*t` for the earliest positive time.
  It unlocks at campaign level 5; Adaptive opens at 21 and Colour aware at 31.
- **Adaptive** estimates acceleration from position samples, using
  `p + v*t + 0.5*a*t*t` over a bounded forecast horizon.
- **Colour aware** branches on sensor data: red boosts, gold brakes in zones,
  blue cruises. A visible colour is not available to code without hardware.

Buy more towers, upgrade, sell at 65% recovery, and copy tuning to towers of the
same type. The base has 16 health. A cleared encounter banks kill credits and
a first-clear bonus; replay bonuses are smaller. Quitting an active attack
restarts it and does not bank pending kill rewards. On defeat, **Relocate troops**
redeploys one tower at a new pad, salvages extra equipment and guarantees a
90-credit rebuilding fund. Repeatable calculation contracts earn 20 credits.
All 12 pads are fixed: roads cannot be blocked. Campaign maps currently reuse
one island with three entrance routes; the ten regions vary encounter rules.

The academy is separate from campaign position: 8 lessons, 37 measured tasks.
It asks for a prediction, records an experiment, compares baselines and rewards
demonstrated success with a congratulations screen. Setting a positive I, D or F
gain alone cannot pass: measured improvement is required. Once-only mastery
rewards also fund the campaign. Academy equipment is deliberately held constant
to isolate one control term; telemetry reports the actual active gains.

The game uses a 120 Hz simulation independent of rendering FPS. Prediction in
campaign combat updates at 20 Hz; sampled sensors update at approximately 8 Hz.
Rendering uses a lit Panda3D scene graph with solid geometry. Projectile physics
is on the ground plane: shell height is decorative, and gravity is not modelled.

## Controls and display

- Mouse: select towers/pads; drag sliders; click numeric values and press Enter.
- Space: pause/resume; C or **Compact mode**: bottom control dock.
- Tab / Enter: focus/activate buttons. Escape: back; it cannot skip mastery.
- Mouse wheel over the field: zoom. Left/right arrows: campaign camera orbit.
- Options: monitor detection, resolution, windowed/borderless/fullscreen,
  30/60/90/120/144/165/240 FPS or uncapped, VSync, larger text, high contrast,
  reduced motion and sound. Confirm display changes within 15 seconds or revert.
  Borderless uses the desktop resolution. VSync/graphics drivers can cap FPS
  below the selected limit. No guaranteed frame rate is implied.

Packaged builds target x64 Windows 10 1809+ / Windows 11, with a graphics driver
supporting Panda3D's OpenGL renderer. Minimum window: 800x600; 1280x800 or greater
is recommended for readability. Minimum RAM/GPU specs have not been benchmarked.

## Saves and troubleshooting

Source runs use `profile3.json` beside the code. Packaged runs use
`%APPDATA%/LeadTheTarget/profile3.json`. Writes are atomic and keep a backup.
The old `save.json` is imported conservatively and preserved. Academy progress,
credits and preferences migrate; a lesson number is never interpreted as a
campaign level. A display choice that fails can be left alone to roll back.

Fully extract the portable archive before launching. Do not move only the EXE.
Update your graphics driver if a graphics window cannot open. Headless verification
uses Panda3D's software renderer and does not verify a particular GPU driver.
Report issues at https://github.com/Leaferd6712/Lead-the-Target/issues.

## Editing and checking

`targeting.py`, `control.py`, `sensors.py`, `simulation.py` are engine independent.
`campaign.py`, `waves.py`, `fortress.py` own campaign rules. `curriculum.py`,
`experiments.py` and `game.py` own academy evidence. `app.py` coordinates scenes,
`scene3d.py` renders, `ui.py` builds DirectGUI, `display.py` applies preferences,
and `profile_store.py` handles the new profile.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe main.py --headless --level 1 --autoplay --frames 160 --screenshot artifacts/smoke.png
.\.venv\Scripts\python.exe tools/check_website.py
```

CLI previews (`--headless`, `--frames`, `--level`, `--stage`) never modify saves.
`--resolution 1920x1080` and `--compact` are useful for layout checks.

## Automated releases and website

See the [deployment guide](https://github.com/Leaferd6712/Lead-the-Target/blob/main/DEPLOYMENT.md). Stable `vMAJOR.MINOR.PATCH` tags run Windows
tests and build all three distributions. A release remains a draft until every
required build and execution check has passed. Website-only changes deploy Pages
without rebuilding the game. Download buttons enable only for a complete stable
release; draft/development builds are excluded. Online leaderboards are not
implemented; current records are local.

MIT game licence. Panda3D, Python, PyInstaller and font notices are described in
THIRD_PARTY_NOTICES.md and bundled with the distributions.
