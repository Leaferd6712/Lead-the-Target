$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$releaseRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'dist\LeadTheTarget'))
$workspaceRoot = [IO.Path]::GetFullPath($PSScriptRoot) + [IO.Path]::DirectorySeparatorChar
if (-not $releaseRoot.StartsWith($workspaceRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Release directory is outside the project.' }
$env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot 'artifacts\pyinstaller-cache'
& '.\.venv\Scripts\python.exe' tools/make_icon.py
$iconPath = Join-Path $PSScriptRoot 'assets\app.ico'
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --windowed --onedir --icon $iconPath --name LeadTheTarget --workpath artifacts/build --specpath artifacts --distpath dist main.py
if ($LASTEXITCODE -ne 0) { throw 'Windows build failed.' }
Copy-Item -LiteralPath README.md,ACCESSIBLE_GUIDE.md,THIRD_PARTY_NOTICES.md,IMPLEMENTATION_NOTES.md -Destination 'dist\LeadTheTarget'
Copy-Item -LiteralPath '.venv\Lib\site-packages\pygame\docs\generated\LGPL.txt' -Destination 'dist\LeadTheTarget\PYGAME-LGPL.txt'
Write-Output 'Build ready: dist\LeadTheTarget\LeadTheTarget.exe. Distribute the entire folder.'
