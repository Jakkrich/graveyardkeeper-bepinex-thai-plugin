param(
    [string]$GameRoot,
    [switch]$BuildPayload
)
$ErrorActionPreference = 'Stop'
if (-not $GameRoot) { $GameRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }
$game = (Resolve-Path -LiteralPath $GameRoot).Path
$managed = Join-Path $game 'Graveyard Keeper_Data/Managed'
$pristine = Join-Path $managed 'Assembly-CSharp-firstpass.dll'
if ((Get-FileHash -LiteralPath $pristine -Algorithm SHA256).Hash -ne '9DC6DEF3B7715DD27EEB168DDC0AF47E31C6F38D3FBEE24BF592899392026498') { throw 'Original firstpass hash mismatch' }
if ($BuildPayload) {
    & python (Join-Path $PSScriptRoot 'tools/build_payload.py') --game-root $game
    if ($LASTEXITCODE -ne 0) { throw 'Payload build failed' }
}
$payload = Join-Path $PSScriptRoot 'payload'
$build = Join-Path $PSScriptRoot 'build'
New-Item -ItemType Directory -Force -Path $build | Out-Null
$metadata = Get-Content -LiteralPath (Join-Path $payload 'metadata.json') -Raw | ConvertFrom-Json
foreach ($entry in @(@('translations/th.csv','master_sha256'),@('config/gk1-font.json','config_sha256'))) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $entry[0]) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $metadata.($entry[1])) { throw 'Payload is stale; run -BuildPayload' }
}
$hashes = @{}
foreach ($name in @('font.ttf','payload.bin','glyphs.png')) { $hashes[$name] = (Get-FileHash -LiteralPath (Join-Path $payload $name) -Algorithm SHA256).Hash.ToLowerInvariant() }
if ($hashes['font.ttf'] -ne $metadata.font_sha256 -or $hashes['payload.bin'] -ne $metadata.payload_sha256) { throw 'Payload/font differs from metadata; rebuild payload' }
$constants = 'namespace GKThai.Plugin.Runtime { internal static class BuildConstants { internal const string FontHash = "' + $hashes['font.ttf'] + '"; internal const string PayloadHash = "' + $hashes['payload.bin'] + '"; internal const string GlyphHash = "' + $hashes['glyphs.png'] + '"; } }'
[IO.File]::WriteAllText((Join-Path $build 'BuildConstants.cs'), $constants, (New-Object Text.UTF8Encoding($false)))
$csc = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$refs = @('mscorlib.dll','System.dll','System.Core.dll','UnityEngine.dll','UnityEngine.CoreModule.dll','UnityEngine.ImageConversionModule.dll','UnityEngine.TextRenderingModule.dll') | ForEach-Object { Join-Path $managed $_ }
$refs += $pristine
$refs += @('BepInEx.dll','0Harmony.dll') | ForEach-Object { Join-Path $game "BepInEx/core/$_" }
$dll = Join-Path $build 'GKThai.Plugin.dll'
$argsCsc = @('/nologo','/noconfig','/nostdlib+','/target:library',"/out:$dll") + @($refs | ForEach-Object { '/reference:' + $_ })
$argsCsc += @('payload.bin','glyphs.png','metadata.json') | ForEach-Object { '/resource:' + (Join-Path $payload $_) + ',GKThai.' + $_ }
$argsCsc += @(Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'GKThai.Plugin') -Recurse -Filter '*.cs' | ForEach-Object FullName)
$argsCsc += (Join-Path $build 'BuildConstants.cs')
& $csc @argsCsc
if ($LASTEXITCODE -ne 0) { throw 'Plugin compilation failed' }
Copy-Item -LiteralPath (Join-Path $payload 'font.ttf') -Destination (Join-Path $build 'font.ttf') -Force
$inputs = @{}
$watched = @($refs) + @(Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'GKThai.Plugin') -Recurse -Filter '*.cs' | ForEach-Object FullName) + @($PSCommandPath)
$watched += @(Get-ChildItem -LiteralPath $payload -File | ForEach-Object FullName)
$watched += @('translations/th.csv','config/gk1-font.json','.local/font.ttf') | ForEach-Object { Join-Path $PSScriptRoot $_ }
foreach ($path in $watched) { $inputs[[IO.Path]::GetFullPath($path)] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
$outputs = @{}
foreach ($name in @('GKThai.Plugin.dll','font.ttf')) { $outputs[$name] = (Get-FileHash -LiteralPath (Join-Path $build $name) -Algorithm SHA256).Hash.ToLowerInvariant() }
$manifest = @{ game='Graveyard Keeper 1'; version='0.1.0'; inputs=$inputs; outputs=$outputs; runtime_qa='See docs/QA_TH.md'; baseline=$metadata.baseline_sha256 }
[IO.File]::WriteAllText((Join-Path $build 'build-manifest.json'), ($manifest | ConvertTo-Json -Depth 8), (New-Object Text.UTF8Encoding($false)))
Get-FileHash -Algorithm SHA256 -LiteralPath $dll, (Join-Path $build 'font.ttf')
