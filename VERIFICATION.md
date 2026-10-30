# Execution evidence

Local verification on 30 October 2026, Windows 11 x64 / Python 3.12:

- 56 automated tests passed, covering original physics, all academy evidence
  gates, profile migration, multi-tower construction, 100 encounters, sensor
  branches, reward settlement, relocation, FPS independence and DirectGUI.
- Actual Panda3D OpenGL window launched and produced a valid screenshot.
- Offscreen source launch/render passed. Genuine screenshots were reviewed in
  normal and compact layouts; viewport transforms were adjusted to keep the
  island above the bottom dock.
- Complete local packaging passed: extracted source launched; portable Windows
  EXE launched with Python removed from PATH; installer installed into an isolated
  folder, installed game launched, and uninstaller removed the executable.
  Assets and licences are included. Evidence: artifacts/release-qa (not committed).
- Chromium browser checks passed at 1440x1000, 768x1024 and 390x844, checking
  horizontal overflow, loaded imagery, JavaScript errors and incomplete-release
  disabled states. Screenshots were visually inspected.

The earned-budget campaign test passed all 100 levels without granting currency
or bypassing equipment/model unlocks. GitHub regression runs and the initial
Pages deployment passed. The public site passed the same three responsive checks.

The first release job correctly blocked publication: its new shortcut test found
that Inno Setup ignores /GROUP when DisableProgramGroupPage is enabled. The
installer now exposes the Start menu folder page, permitting an isolated QA group.
The failed v2.0.0 tag is preserved; the corrected release uses v2.0.1.
Public release/download results are appended after the corrected run.

The corrected v2.0.1 release workflow completed successfully:
https://github.com/Leaferd6712/Lead-the-Target/actions/runs/40981088820

A final interaction check reproduced an Options draft bug: choosing a resolution,
then changing an accessibility preference, discarded the pending display choice.
The v2.0.2 patch keeps a persistent display draft and applies only display fields,
preserving immediate accessibility changes. The new DirectGUI callback regression
passes. The public-download verification helper checks released bytes and runs
the source in a fresh virtual environment, the portable EXE with a minimal PATH,
and the installed application with shortcut/uninstall checks.

The v2.0.2 workflow caught a test assumption: its display test requested a
resolution larger than the CI runner's detected monitor. The test now chooses
from detected resolutions and was repeated with a 1024x768 monitor simulation.
No v2.0.2 release was published. A further replay check reproduced an advanced
algorithm menu crash when returning to level 1. The v2.0.3 correction retains
earned technology across replays and bounds restored menu selections. Focused
replay, construction and display regressions passed before tagging.

Limits: no fresh-player study, physical mouse/DPI test across all displays, clean
Windows VM without developer tools, exhaustive GPU/monitor-mode matrix, macOS or
Linux package verification, or online leaderboard service. Source and portable
execution checks on a development host do not prove every clean-machine setup.
The build is unsigned. No minimum hardware performance specification is claimed.

## Final published result: v2.0.3

- Repository: https://github.com/Leaferd6712/Lead-the-Target
- Website: https://leaferd6712.github.io/Lead-the-Target/
- Release: https://github.com/Leaferd6712/Lead-the-Target/releases/tag/v2.0.3
- Final regression workflow passed:
  https://github.com/Leaferd6712/Lead-the-Target/actions/runs/40982232064
- Release workflow passed **59 tests**, built all three distributions and
  execution-tested source, portable EXE, installation, shortcuts and uninstall:
  https://github.com/Leaferd6712/Lead-the-Target/actions/runs/40982236288
- The post-release Pages deployment passed:
  https://github.com/Leaferd6712/Lead-the-Target/actions/runs/40982617164
- All three public release assets and SHA256SUMS.txt were downloaded from the
  actual GitHub release. Every file matched its checksum. The downloaded source
  ran in a newly created virtual environment containing only its runtime
  dependency. The downloaded portable EXE ran with Python removed from PATH,
  using both offscreen software rendering and a real Windows OpenGL window.
- The downloaded installer installed to an isolated test directory, created its
  Start menu shortcut, launched, and uninstalled the game and shortcut. The log
  reports user privileges None, administrative install mode No, HKCU registration.
- Live Chromium checks passed at 1440x1000, 768x1024 and 390x844. All three
  download links were checked against **v2.0.3**, not just filename suffixes.
  The deployed release.json fallback was independently checked as v2.0.3.
- Local execution evidence is under artifacts/download-qa and artifacts/website;
  these generated files and clean test environments are excluded from Git.

Reproduce the final public checks from a development checkout:

```powershell
python tools/verify_downloads.py --tag v2.0.3
python tools/browser_qa.py https://leaferd6712.github.io/Lead-the-Target/ --live --tag v2.0.3
```

The browser check uses the optional development tool Playwright 1.56.0 plus its
Chromium runtime. Neither is a game runtime dependency. The limitations listed
above still apply; a clean Windows VM and the full hardware/DPI matrix were not
available, and no manual mouse walkthrough or learner study is claimed.
