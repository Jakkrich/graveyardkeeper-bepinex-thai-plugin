param([string]$GameRoot, [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
if (-not $GameRoot) { $GameRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }
$game = (Resolve-Path -LiteralPath $GameRoot).Path
$expected = @{
    'Graveyard Keeper_Data/resources.assets'='215c7981901a4b72d5db717666ba47ad3cc032527c95f58dc39d8af1293a69ca'
    'Graveyard Keeper_Data/Managed/Assembly-CSharp-firstpass.dll'='9dc6def3b7715dd27eeb168ddc0af47e31c6f38d3fbee24bf592899392026498'
    'Graveyard Keeper_Data/Managed/Assembly-CSharp.dll'='e72e4270e4b88dd0a87ca23c9cf1750aec4c4a0fedb40b6d2dae7902fc9c7fd8'
}
foreach ($entry in $expected.GetEnumerator()) {
    $file = Join-Path $game $entry.Key
    if (-not (Test-Path -LiteralPath $file) -or (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { throw "Pristine game required: $($entry.Key). No files changed. Read docs/INSTALL_TH.md." }
}
foreach ($name in @('BepInEx.dll','0Harmony.dll')) { if (-not (Test-Path -LiteralPath (Join-Path $game "BepInEx/core/$name"))) { throw "Missing loader reference $name" } }
$build = Join-Path $PSScriptRoot 'build'
$manifest = Get-Content -LiteralPath (Join-Path $build 'build-manifest.json') -Raw | ConvertFrom-Json
foreach ($entry in $manifest.inputs.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath $entry.Name -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { throw "Stale build input: $($entry.Name)" }
}
foreach ($entry in $manifest.outputs.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $build $entry.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { throw "Build output modified: $($entry.Name)" }
}
if ($CheckOnly) { Write-Host 'PASS: pristine game and build hashes verified. No files changed.'; exit 0 }
if (Get-Process -Name 'Graveyard Keeper' -ErrorAction SilentlyContinue) { throw 'Close Graveyard Keeper before installation.' }
$destination = [IO.Path]::GetFullPath((Join-Path $game 'BepInEx/plugins/GK2Thai'))
$plugins = [IO.Path]::GetFullPath((Join-Path $game 'BepInEx/plugins'))
if ((Split-Path -Parent $destination) -ne $plugins) { throw 'Invalid destination' }
$backupRoot = Join-Path $PSScriptRoot ('backups/install-' + (Get-Date -Format 'yyyyMMdd-HHmmssfff'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$backup = Join-Path $backupRoot 'GK2Thai'
if (Test-Path -LiteralPath $destination) { Move-Item -LiteralPath $destination -Destination $backup }
try {
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    foreach ($name in @('GK2Thai.Plugin.dll','font.ttf')) {
        Copy-Item -LiteralPath (Join-Path $build $name) -Destination (Join-Path $destination $name)
        if ((Get-FileHash -LiteralPath (Join-Path $destination $name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.outputs.$name) { throw "Installed hash mismatch: $name" }
    }
} catch {
    if (Test-Path -LiteralPath $destination) { Move-Item -LiteralPath $destination -Destination (Join-Path $backupRoot 'failed-install') }
    if (Test-Path -LiteralPath $backup) { Move-Item -LiteralPath $backup -Destination $destination }
    throw
}
Write-Host "Installed DLL + font: $destination"
Write-Host "Previous plugin backup: $backupRoot"
