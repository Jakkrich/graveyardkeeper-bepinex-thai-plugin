param([string]$GameRoot)
$ErrorActionPreference = 'Stop'
$mod = Split-Path -Parent $PSScriptRoot
if (-not $GameRoot) { $GameRoot = Split-Path -Parent (Split-Path -Parent $mod) }
$game = (Resolve-Path -LiteralPath $GameRoot).Path
$managed = Join-Path $game 'Graveyard Keeper_Data/Managed'
$pristine = Join-Path $managed 'Assembly-CSharp-firstpass.dll'
if ((Get-FileHash -LiteralPath $pristine -Algorithm SHA256).Hash -ne '9DC6DEF3B7715DD27EEB168DDC0AF47E31C6F38D3FBEE24BF592899392026498') { throw 'Original firstpass hash mismatch' }
$build = Join-Path $mod 'build'
New-Item -ItemType Directory -Force -Path $build | Out-Null
$csc = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$refs = @('mscorlib.dll','System.dll','System.Core.dll','UnityEngine.dll','UnityEngine.CoreModule.dll','UnityEngine.ScreenCaptureModule.dll','UnityEngine.TextRenderingModule.dll') | ForEach-Object { Join-Path $managed $_ }
$refs += $pristine
$refs += Join-Path $game 'BepInEx/core/BepInEx.dll'
$dll = Join-Path $build 'GK2Thai.RuntimeQa.dll'
$compile = @('/nologo','/noconfig','/nostdlib+','/target:library',"/out:$dll") + @($refs | ForEach-Object { '/reference:' + $_ })
$compile += Join-Path $PSScriptRoot 'RuntimeQaProbe.cs'
& $csc @compile
if ($LASTEXITCODE -ne 0) { throw 'QA probe compilation failed' }
Get-FileHash -LiteralPath $dll -Algorithm SHA256
