param([string]$Version = (Get-Content (Join-Path $PSScriptRoot 'VERSION')).Trim(), [string]$Iscc = '')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not $Iscc) {
    $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($compiler) { $Iscc = $compiler.Source }
    else {
        foreach ($candidate in @('C:\Program Files (x86)\Inno Setup 6\ISCC.exe','C:\Program Files\Inno Setup 7\ISCC.exe','C:\Program Files (x86)\Inno Setup 7\ISCC.exe')) {
            if (Test-Path -LiteralPath $candidate) { $Iscc = $candidate; break }
        }
    }
}
if (-not $Iscc) { throw 'Install Inno Setup from https://jrsoftware.org/isdl.php or pass -Iscc path\ISCC.exe.' }
$python = if (Test-Path '.venv\Scripts\python.exe') { '.\.venv\Scripts\python.exe' } else { 'python' }
& $python tools/package.py --version $Version --iscc $Iscc
if ($LASTEXITCODE -ne 0) { throw 'Release build or verification failed.' }
