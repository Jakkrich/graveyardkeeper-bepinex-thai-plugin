param([switch]$WithPayload)
$ErrorActionPreference = 'Stop'
$mod = Split-Path -Parent $PSScriptRoot
$output = Join-Path $PSScriptRoot 'bin'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$csc = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$files = @((Join-Path $PSScriptRoot 'RuntimeTests.cs'), (Join-Path $mod 'GKThai.Plugin/Runtime/EmbeddedPayload.cs'), (Join-Path $mod 'GKThai.Plugin/Runtime/ThaiGlyphMetrics.cs'))
& $csc /nologo /target:exe ("/out:$output/RuntimeTests.exe") @files
if ($LASTEXITCODE -ne 0) { throw 'Runtime test compilation failed' }
if ($WithPayload) { & "$output/RuntimeTests.exe" (Join-Path $mod 'payload/payload.bin') } else { & "$output/RuntimeTests.exe" }
if ($LASTEXITCODE -ne 0) { throw 'Runtime tests failed' }
