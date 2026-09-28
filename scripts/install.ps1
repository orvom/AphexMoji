<#
    One-liner installer/runner for the AphexMoji Telegram bot.

    Usage (from PowerShell):
        irm https://raw.githubusercontent.com/orvom/AphexMoji/main/scripts/install.ps1 | iex

    Downloads bot/premium_emoji_bot.py from this repo and runs it with Python.
    The bot token is never stored on disk or hardcoded here: it is read from
    the BOT_TOKEN environment variable, or prompted for securely (input is
    masked) if that variable isn't already set.
#>

[CmdletBinding()]
param(
    [string]$Branch = "main",
    [string]$RepoRaw = "https://raw.githubusercontent.com/orvom/AphexMoji"
)

$ErrorActionPreference = "Stop"

function Test-RealPython([string]$cmd) {
    # On Windows, "python"/"python3" can resolve to a Microsoft Store app
    # execution alias stub even when no real interpreter is installed, so
    # existence of the command isn't enough - actually run it and check.
    try {
        $output = & $cmd --version 2>&1
        return ($LASTEXITCODE -eq 0 -and $output -match "Python \d")
    } catch {
        return $false
    }
}

function Get-PythonCommand {
    foreach ($cmd in @("py", "python", "python3")) {
        if ((Get-Command $cmd -ErrorAction SilentlyContinue) -and (Test-RealPython $cmd)) {
            return $cmd
        }
    }
    Write-Error "Python 3 not found. Install it from https://www.python.org/downloads/ (check 'Add python.exe to PATH' during setup), then run this script again."
    exit 1
}

$python = Get-PythonCommand

$installDir = Join-Path $env:TEMP "AphexMoji"
New-Item -ItemType Directory -Force -Path $installDir | Out-Null
$scriptPath = Join-Path $installDir "premium_emoji_bot.py"

$url = "$RepoRaw/$Branch/bot/premium_emoji_bot.py"
Write-Host "Downloading bot script from $url ..."
Invoke-WebRequest -Uri $url -OutFile $scriptPath -UseBasicParsing

if (-not $env:BOT_TOKEN) {
    $secure = Read-Host -Prompt "Enter your Telegram Bot Token" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $env:BOT_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

Write-Host "Starting bot..."
& $python $scriptPath
