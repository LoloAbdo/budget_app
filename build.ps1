# build.ps1 — package Budget Manager into a standalone Windows executable.
#
#   .\build.ps1            # one-file build  -> dist\BudgetManager.exe
#   .\build.ps1 -OneDir    # one-folder build (faster startup) -> dist\BudgetManager\
#
# Requires PyInstaller (installed automatically below). The resulting app needs
# no Python install on the target machine. User data is stored separately in
# %APPDATA%\BudgetManager, so rebuilding/updating never touches existing data.

param([switch]$OneDir)

$ErrorActionPreference = "Stop"

python -m pip install --upgrade pyinstaller

$mode = if ($OneDir) { "--onedir" } else { "--onefile" }

pyinstaller --noconfirm $mode --windowed `
    --name BudgetManager `
    --icon assets\icon.ico `
    --add-data "assets;assets" `
    --add-data "CHANGELOG.md;." `
    --add-data "CHANGELOG.fr.md;." `
    --add-data "USER_GUIDE.md;." `
    --hidden-import soupsieve `
    --collect-all matplotlib `
    main.py

Write-Host ""
if ($OneDir) {
    Write-Host "Built: dist\BudgetManager\BudgetManager.exe"
} else {
    Write-Host "Built: dist\BudgetManager.exe"
}
