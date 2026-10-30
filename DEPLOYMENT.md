# Development, releases and Pages

Repository: https://github.com/Leaferd6712/Lead-the-Target (main)

Site: https://leaferd6712.github.io/Lead-the-Target/

## Build locally on Windows

Use Python 3.12 and `pip install -r requirements-build.txt`. Install Inno Setup
from its official site or run `tools/bootstrap_inno.ps1` (downloads the official
signed compiler installer and verifies its Authenticode signature). Then:

```powershell
./build.ps1 -Version 2.0.0 -Iscc artifacts/tools/InnoSetup/ISCC.exe
```

`tools/package.py` fails on a failed test, missing asset, smoke launch, installer
operation or output. It creates a source ZIP, PyInstaller onedir portable ZIP,
Inno Setup installer and SHA256SUMS.txt under `release/`. It extracts/runs the
source, launches the bundled EXE with PATH limited to System32, silently installs
to an isolated QA folder, launches the installed app and uninstalls it.
Evidence lives in `artifacts/release-qa/`. The test also checks bundled fonts/audio
and Start menu shortcut creation/removal. Test installations retain profile data.

The compiler helper pins Inno Setup 7.1.1 (non-commercial compiler licence) and
installs per-user build tools; it does not disable UAC or
modify security settings. Distribution installers use `PrivilegesRequired=lowest`.
Keep the complete portable directory: the EXE deliberately is not a one-file
self-extracting executable.

## Publish

1. Make changes on a branch, run checks and merge without rewriting history.
2. Update VERSION and RELEASE_NOTES.md for a stable release.
3. Commit, push, create a new `vMAJOR.MINOR.PATCH` tag and push that tag. Never move
   an existing public tag to repair a build; commit the fix and use a new version.
4. `.github/workflows/release.yml` validates tag/VERSION, caches pip, runs tests,
   builds Windows packages and verifies execution. It uploads QA artifacts even
   on failure. Only the successful job creates a draft with the complete assets,
   then publishes it as latest. A failed build creates no public release.
5. Manual execution takes an **existing stable tag**, so release provenance is
   identical. If a release already exists, publication fails rather than replacing
   assets. Resolve a partial draft explicitly; do not silently clobber a release.

No long-lived secret is needed: Actions uses its scoped GITHUB_TOKEN. Release
job has contents:write; Pages uses pages:write and id-token:write. Other jobs have
read-only access. Branch protection, if configured by the owner, still applies.

## Pages

Set repository Pages publishing to **GitHub Actions**. `pages.yml` deploys only
website changes on main, manual requests, and successful release-workflow
completions. The website is plain HTML/CSS/JS with locally served fonts.

The download script requests GitHub's latest stable release and requires all
three exact, non-empty, uploaded assets before enabling any download button.
Drafts/prereleases are excluded. A deployment-time metadata snapshot is a fallback
for anonymous API outages/rate limits; the normal request fetches the current
release. A successful release triggers a fresh Pages deployment to update that
fallback. A failed build is never advertised as a release. No invented URLs are
used when downloads are unavailable; the release-history link stays usable.

## Verification limits

Offscreen screenshots and automated simulation prove executable code paths and
layout state. They do not replace fresh-player usability studies, physical mouse
dragging on every Windows DPI setting, every GPU/monitor mode, or a clean Windows
computer with no developer tools installed. Bundled execution tests remove Python
from PATH, but are run on build/development hosts. Code signing and online
leaderboards are not included. See VERIFICATION.md for execution evidence.

To recheck public release bytes, run `python tools/verify_downloads.py --tag v2.0.3`
on Windows. It downloads the release, validates checksums, creates a clean source
environment and tests the downloaded portable and installer distributions. To
check the live responsive site, install the optional developer tool
`playwright==1.56.0`, run `python -m playwright install chromium`, then run
`python tools/browser_qa.py https://leaferd6712.github.io/Lead-the-Target/ --live --tag v2.0.3`.
