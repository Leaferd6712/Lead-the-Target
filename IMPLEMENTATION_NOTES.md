# Panda3D implementation notes

The current implementation supersedes the earlier pygame renderer and UI. Git
history preserves those files. Runtime dependencies, launcher, screenshots,
tests, assets and release scripts now use Panda3D.

- Ground physics and teaching formulas are retained. Projectiles are non-homing;
  a prediction cannot alter a shell already in flight.
- A campaign level and an academy lesson are separate state. 100 encounters
  reuse one island and three routes. Timing, formations, behaviour and armour
  vary; this release does not claim 100 hand-made terrain maps.
- Each tower owns a motor/controller and configuration. Construction uses 12
  fixed pads. All towers and projectile collisions share the 120 Hz clock.
  Predictions update at 20 Hz to bound the cost of numerical intercept solving.
- Colour data is removed from observations unless a tower has enabled hardware
  or receives an enabled sensor station's coverage. The player seeing a tank's
  colour never grants hidden state to the algorithm.
- Native DirectSlider widgets persist across frames; lead numeric entry,
  plus/minus and keyboard alternatives call the same state update. The first
  fixed-lead academy task selects its required model automatically.
- Calibration telemetry reads the actual Experiment.gains. It cannot report
  unused chosen gains while the experiment isolates a different term.
- UI coordinates scale from 1440x900. Compact mode is a bottom dock. The camera
  renders into the free battlefield region, with inverse viewport transforms
  for picking. Display preferences have a wall-clock rollback timer.
- Profile schema 3 reads the old save without rewriting it. Kill rewards remain
  unbanked until victory. Academy-to-campaign rewards use persisted transfer
  markers and cannot be claimed twice.
- Website and release workflows are separate. Actual built screenshots are
  checked into website/images; release assets are selected from GitHub metadata.

The academy core and its 37 existing evidence gates are retained. New tests cover
campaign completion, sensor gates, construction, banking, relocation, FPS
independence, native slider callbacks, display rollback and actual telemetry.
