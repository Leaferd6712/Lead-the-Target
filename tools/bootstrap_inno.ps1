$ErrorActionPreference = 'Stop'
$toolsRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\artifacts\tools'))
New-Item -ItemType Directory -Path $toolsRoot -Force | Out-Null
$headers = @{ 'User-Agent' = 'LeadTheTarget-build' }
$release = Invoke-RestMethod 'https://api.github.com/repos/jrsoftware/issrc/releases/latest' -Headers $headers
$asset = $release.assets | Where-Object { $_.name -match '^innosetup-[0-9.]+-x64.exe$' } | Select-Object -First 1
if (-not $asset) { throw 'Official Inno Setup x64 compiler release was not found.' }
$download = Join-Path $toolsRoot $asset.name
if (-not (Test-Path -LiteralPath $download)) { Invoke-WebRequest $asset.browser_download_url -OutFile $download }
$signature = Get-AuthenticodeSignature -LiteralPath $download
if ($signature.Status -ne 'Valid') { throw "Inno Setup compiler installer signature invalid: $($signature.Status)" }
$compilerRoot = Join-Path $toolsRoot 'InnoSetup'
$process = Start-Process -FilePath $download -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/NOICONS',"/DIR=`"$compilerRoot`"") -PassThru -Wait -WindowStyle Hidden
if ($process.ExitCode -ne 0) { throw "Compiler installation failed: $($process.ExitCode)" }
$compiler = Join-Path $compilerRoot 'ISCC.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw 'Compiler installation did not produce ISCC.exe.' }
if ($env:GITHUB_ENV) { "ISCC_PATH=$compiler" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append }
Write-Output $compiler
