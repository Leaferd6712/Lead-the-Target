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

GitHub Actions, public downloads and deployed Pages are verified after the
publication run; the corresponding results are appended here once available.

Limits: no fresh-player study, physical mouse/DPI test across all displays, clean
Windows VM without developer tools, exhaustive GPU/monitor-mode matrix, macOS or
Linux package verification, or online leaderboard service. Source and portable
execution checks on a development host do not prove every clean-machine setup.
The build is unsigned. No minimum hardware performance specification is claimed.
