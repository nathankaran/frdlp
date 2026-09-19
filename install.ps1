$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2

$Repository = if ($env:FRDLP_REPOSITORY) {
    $env:FRDLP_REPOSITORY
} else {
    "nathankaran/yt-dlp_frontend"
}
$SourceUrl = if ($env:FRDLP_SOURCE_URL) {
    $env:FRDLP_SOURCE_URL
} else {
    "https://github.com/$Repository/archive/refs/heads/main.zip"
}

$script:PythonExe = $null
$script:PythonPrefix = @()
if ($env:FRDLP_PYTHON) {
    $script:PythonExe = $env:FRDLP_PYTHON
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $script:PythonExe = (Get-Command python).Source
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $script:PythonExe = (Get-Command py).Source
    $script:PythonPrefix = @("-3")
} else {
    throw "frdlp requires Python 3.10 or newer."
}

function Invoke-FRDLPPython {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    $CommandArguments = @($script:PythonPrefix) + $Arguments
    & $script:PythonExe @CommandArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

Invoke-FRDLPPython -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or
    -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    throw "frdlp requires FFmpeg and ffprobe on PATH. Install FFmpeg and retry."
}

$InstallHome = if ($env:FRDLP_HOME) {
    $env:FRDLP_HOME
} else {
    Join-Path $env:LOCALAPPDATA "frdlp"
}
$BinDir = if ($env:FRDLP_BIN_DIR) {
    $env:FRDLP_BIN_DIR
} else {
    Join-Path $InstallHome "bin"
}
$VenvDir = Join-Path $InstallHome "venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$Launcher = Join-Path $BinDir "frdlp.cmd"

New-Item -ItemType Directory -Force -Path $InstallHome, $BinDir | Out-Null
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating frdlp environment in $VenvDir"
    Invoke-FRDLPPython -m venv $VenvDir
}

Write-Host "Installing frdlp from $SourceUrl"
& $VenvPython -m pip install --disable-pip-version-check --upgrade $SourceUrl
if ($LASTEXITCODE -ne 0) {
    throw "Installing frdlp failed with exit code $LASTEXITCODE."
}

$LauncherContents = "@`"$VenvDir\Scripts\frdlp.exe`" %*"
Set-Content -Path $Launcher -Value $LauncherContents -Encoding ASCII

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($null -eq $UserPath) {
    $UserPath = ""
}
$PathEntries = @($UserPath -split ";" | Where-Object { $_ })
if ($PathEntries -notcontains $BinDir) {
    $NewUserPath = if ($UserPath) { "$UserPath;$BinDir" } else { $BinDir }
    [Environment]::SetEnvironmentVariable("Path", $NewUserPath, "User")
    Write-Host "Added $BinDir to your user PATH. Open a new terminal before running frdlp."
}
$env:Path = "$BinDir;$env:Path"

Write-Host ""
Write-Host "frdlp installed successfully: $Launcher"
Write-Host 'Run: frdlp C:\Downloads "video-link" mp4'

