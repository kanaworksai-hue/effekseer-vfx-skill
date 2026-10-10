# Install the effekseer-vfx toolchain on Windows into EFFEKSEER_VFX_HOME (default %USERPROFILE%\.cache\effekseer-vfx).
# The Windows counterpart of setup.sh; safe to re-run. From cmd, PowerShell or Git Bash:
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File <skill>\scripts\setup.ps1                   full mode (x64 or ARM64)
#   powershell -NoProfile -ExecutionPolicy Bypass -File <skill>\scripts\setup.ps1 --authoring-only  Python packages only
#
# Full mode installs the Python packages, Effekseer Core 1.80.7 and the .NET 9 runtime; `sh setup.sh` from Git Bash
# runs this script. Needs Python 3.11+ (found through the py launcher or PATH) or uv. Exit codes: 0 ok, 1 a download or
# install failed, 2 unknown option, 3 full mode on an unsupported system, 4 no suitable Python.
#
# The Effekseer and .NET archives (~250 MB in full mode) come from the official Effekseer and Microsoft releases and
# are checked against pinned SHA-256 sums; Python packages are pinned by version (requirements.lock.txt), not by hash.
# Nothing is installed outside EFFEKSEER_VFX_HOME. Godot 4 is not installed here. Concurrent runs that share one
# EFFEKSEER_VFX_HOME wait for each other (an exclusive handle on a lock file, released by the kernel when the process
# exits); every download and extraction goes to a private temporary folder first.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Mode = 'full'
foreach ($argument in $args) {
  if ($argument -eq '--authoring-only') { $Mode = 'authoring' }
  else { [Console]::Error.WriteLine("Unknown option: $argument (expected --authoring-only)"); exit 2 }
}
$Scripts = Split-Path -Parent $MyInvocation.MyCommand.Path
$Toolchain = if ($env:EFFEKSEER_VFX_HOME) { $env:EFFEKSEER_VFX_HOME } else { Join-Path $env:USERPROFILE '.cache\effekseer-vfx' }
$CoreUrl = 'https://github.com/effekseer/Effekseer/releases/download/1807/Effekseer1.80.7Win.zip'
$CoreSha256 = '6f059b9cce3a79c5bfe3df9c970cfe62fd72acf130083c7b81832d90f8d1335f'
$DotnetVersion = '9.0.20'
# Microsoft's published SHA-512 sums for these archives (releases.json) are
#   win-x64   6f7241fab7a8003813c3c8a59005e368fe53525e3cf08ab1cc052103f2f422af6bd1b20b838c283283a8a709d52a6aea2379686fe6cb07cc0fa7119f2ef2b2bf
#   win-arm64 9e8a6252d98f37fe035c7c642be479ea8b16db393e357ef248695c3f3cafb0656548d41e2e1a12d24ce62531f8190b48af02adb933bf25d5ecaa2a94415d2fc7
$DotnetSha256 = @{
  'x64'   = '1f645d05f046b5107dd57406f7ef994f76cfc35cc5ef0cd320c8120d49903503'
  'arm64' = '3f8e7af1baa8ec3f1dea2963e90cd67fd73f69d817f70e058d25dda45315f21e'
}

function Say([string]$message) { [Console]::Error.WriteLine($message) }

# Run a native program with its output on stderr (stdout carries only the final doctor JSON); return its exit code.
function Invoke-Native([string]$exe, [string[]]$arguments) {
  $saved = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'  # Windows PowerShell turns native stderr lines into errors under 'Stop'
  try { & $exe @arguments 2>&1 | ForEach-Object { [Console]::Error.WriteLine("$_") } }
  finally { $ErrorActionPreference = $saved }
  return $LASTEXITCODE
}

function Get-Sha256([string]$path) { (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() }

# A verified copy of $url at $target: reuse a verified copy, else download privately, verify, then move into place.
function Get-Verified([string]$url, [string]$sha256, [string]$target) {
  if ((Test-Path -LiteralPath $target) -and (Get-Sha256 $target) -eq $sha256) { return }
  $download = Join-Path $script:WorkDir 'download'
  if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
    if ((Invoke-Native 'curl.exe' @('-sSL', '--fail', '-o', $download, $url)) -ne 0) { throw "Download failed: $url" }
  } else {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $download
  }
  if ((Get-Sha256 $download) -ne $sha256) { Say "Checksum mismatch for $url"; exit 1 }
  Move-Item -Force -LiteralPath $download -Destination $target
}

function Expand-Zip([string]$archive, [string]$destination) {
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  [System.IO.Compression.ZipFile]::ExtractToDirectory($archive, $destination)
}

# Python 3.11+ is required (the pinned numpy, Pillow and pythonnet need it). uv provides one by itself; otherwise use
# the py launcher's newest 3.11+, then python or python3 on PATH (which may be the Microsoft Store stub: it is tested).
function Test-Modern([string]$exe, [string[]]$prefix) {
  $code = Invoke-Native $exe ($prefix + @('-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'))
  return $code -eq 0
}
function Find-Python {
  if (Get-Command py.exe -ErrorAction SilentlyContinue) {
    foreach ($minor in 13, 12, 11) { if (Test-Modern 'py.exe' @("-3.$minor")) { return @('py.exe', "-3.$minor") } }
  }
  foreach ($name in 'python.exe', 'python3.exe') {
    $found = Get-Command $name -ErrorAction SilentlyContinue
    if ($found -and (Test-Modern $found.Source @())) { return @($found.Source) }
  }
  return $null
}

$architecture = $env:PROCESSOR_ARCHITECTURE
if ($env:PROCESSOR_ARCHITEW6432) { $architecture = $env:PROCESSOR_ARCHITEW6432 }  # 32-bit PowerShell on a 64-bit OS
$Rid = switch ($architecture) { 'AMD64' { 'x64' } 'ARM64' { 'arm64' } default { $null } }
if ($Mode -eq 'full' -and -not $Rid) {
  Say "Full mode (EffekseerCore build + Godot review) needs 64-bit Windows (x64 or ARM64); this is $architecture."
  Say "On this system run: powershell -NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`" --authoring-only"
  exit 3
}

New-Item -ItemType Directory -Force -Path (Join-Path $Toolchain 'downloads') | Out-Null
# One setup at a time per toolchain: hold an exclusive handle on a lock file until this script ends.
$lockPath = Join-Path $Toolchain '.setup.lock'
$lock = $null
while (-not $lock) {
  try { $lock = [System.IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None') }
  catch [System.IO.IOException] { Start-Sleep -Milliseconds 500 }
}
$WorkDir = Join-Path $Toolchain ('downloads\.setup.' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $WorkDir | Out-Null
try {
  $venv = Join-Path $Toolchain 'venv'
  $venvPython = Join-Path $venv 'Scripts\python.exe'
  Say "== Python packages -> $venv"
  # An environment from an older Python (or a broken earlier attempt) is replaced, never reused.
  if ((Test-Path -LiteralPath $venv) -and -not ((Test-Path -LiteralPath $venvPython) -and (Test-Modern $venvPython @()))) {
    Say "Replacing ${venv}: it is missing, broken or older than Python 3.11"
    Remove-Item -Recurse -Force -LiteralPath $venv
  }
  $uv = Get-Command uv.exe -ErrorAction SilentlyContinue
  if (-not (Test-Path -LiteralPath $venvPython)) {
    if ($uv) {
      if ((Invoke-Native $uv.Source @('venv', '--python', '3.12', $venv)) -ne 0) { Say 'uv could not create the environment.'; exit 1 }
    } else {
      $python = Find-Python
      if (-not $python) {
        Say 'Python 3.11 or newer is required and none was found.'
        Say 'Install one of them, then run this script again:'
        Say '  uv (manages its own Python):  https://docs.astral.sh/uv/getting-started/installation/'
        Say '  or Python from python.org:    winget install Python.Python.3.12'
        exit 4
      }
      $prefix = @($python | Select-Object -Skip 1)
      if ((Invoke-Native $python[0] ($prefix + @('-m', 'venv', $venv))) -ne 0) { Say 'Creating the environment failed.'; exit 1 }
    }
  }
  $requirements = Join-Path $Scripts 'requirements.lock.txt'
  if ($uv) { $code = Invoke-Native $uv.Source @('pip', 'install', '--python', $venvPython, '-r', $requirements) }
  else { $code = Invoke-Native $venvPython @('-m', 'pip', 'install', '--quiet', '-r', $requirements) }
  if ($code -ne 0) { Say 'Installing the Python packages failed; fix the error above and run this script again (it resumes).'; exit 1 }

  if ($Mode -eq 'full') {
    $effekseer = Join-Path $Toolchain 'effekseer'
    if (-not (Test-Path -LiteralPath (Join-Path $effekseer 'Effekseer1.80.7Win\Tool\bin\EffekseerCore.dll'))) {
      Say '== Effekseer 1.80.7 (official release; only its managed Core assemblies are used)'
      $archive = Join-Path $Toolchain 'downloads\Effekseer1.80.7Win.zip'
      Get-Verified $CoreUrl $CoreSha256 $archive
      $staged = Join-Path $WorkDir 'effekseer'
      Expand-Zip $archive $staged
      if (Test-Path -LiteralPath $effekseer) { Remove-Item -Recurse -Force -LiteralPath $effekseer }
      Move-Item -LiteralPath $staged -Destination $effekseer
    }
    $dotnet = Join-Path $Toolchain 'dotnet'
    if (-not (Test-Path -LiteralPath (Join-Path $dotnet 'dotnet.exe'))) {
      Say "== .NET $DotnetVersion runtime (official Microsoft archive, win-$Rid)"
      $name = "dotnet-runtime-$DotnetVersion-win-$Rid.zip"
      $archive = Join-Path $Toolchain "downloads\$name"
      Get-Verified "https://builds.dotnet.microsoft.com/dotnet/Runtime/$DotnetVersion/$name" $DotnetSha256[$Rid] $archive
      $staged = Join-Path $WorkDir 'dotnet'
      Expand-Zip $archive $staged
      if (Test-Path -LiteralPath $dotnet) { Remove-Item -Recurse -Force -LiteralPath $dotnet }
      Move-Item -LiteralPath $staged -Destination $dotnet
    }
  }
} finally {
  Remove-Item -Recurse -Force -LiteralPath $WorkDir -ErrorAction SilentlyContinue
  $lock.Dispose()
}
& (Join-Path $Scripts 'vfx.cmd') doctor
exit $LASTEXITCODE
