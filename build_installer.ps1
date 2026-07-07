# build_installer.ps1 — build a Windows installer (BudgetManagerSetup.exe).
#
#   .\build_installer.ps1            # build the app + compile the installer
#   .\build_installer.ps1 -SkipBuild # reuse an existing dist\BudgetManager\ build
#
# Produces installer_output\BudgetManagerSetup.exe. Installs Inno Setup and
# PyInstaller automatically if they're missing.

param([switch]$SkipBuild)

$ErrorActionPreference = "Stop"

# ── Ensure Inno Setup ────────────────────────────────────────────────────────
function Find-ISCC {
    $candidates = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

$iscc = Find-ISCC
if (-not $iscc) {
    Write-Host "Installing Inno Setup..."
    winget install --id JRSoftware.InnoSetup -e --accept-source-agreements --accept-package-agreements
    $iscc = Find-ISCC
}
if (-not $iscc) { throw "Could not find ISCC.exe (Inno Setup compiler) after install." }

# ── Build the app (one-folder, for instant startup) ──────────────────────────
if (-not $SkipBuild) {
    python -m pip install --upgrade pyinstaller
    pyinstaller --noconfirm --onedir --windowed `
        --name BudgetManager `
        --icon assets\icon.ico `
        --add-data "assets;assets" `
        --add-data "CHANGELOG.md;." `
        --add-data "CHANGELOG.fr.md;." `
        --collect-all matplotlib `
        main.py
}

# ── Compile the installer with the version from version.py ────────────────────
$ver = (python -c "import version; print(version.__version__)").Trim()
Write-Host "Compiling installer for version $ver ..."
& $iscc "/DMyAppVersion=$ver" installer.iss

Write-Host ""
Write-Host "Installer built: installer_output\BudgetManagerSetup.exe"
