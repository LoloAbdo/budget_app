; installer.iss — Inno Setup script for Budget Manager.
;
; Builds a single BudgetManagerSetup.exe that installs the app per-user
; (no admin prompt), adds Start Menu + optional desktop shortcuts, and
; registers an uninstaller. Compile with build_installer.ps1, which passes
; the version from version.py:  ISCC /DMyAppVersion=1.0.1 installer.iss
;
; The app stores its data in %APPDATA%\BudgetManager, so installing into a
; read-only program location is fine — user data lives elsewhere and survives
; uninstall/reinstall/update.

#define MyAppName "Budget Manager"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "LoloAbdo"
#define MyAppExeName "BudgetManager.exe"

[Setup]
; A stable unique ID so upgrades replace the previous install instead of stacking.
AppId={{7E2D9C84-5A31-4B6E-9F2A-1C8D3E4F5A6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Per-user install -> no UAC/admin prompt.
PrivilegesRequired=lowest
OutputDir=installer_output
OutputBaseFilename=BudgetManagerSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french";  MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Package the one-folder PyInstaller build (dist\BudgetManager\).
Source: "dist\BudgetManager\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";              Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}";    Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";        Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; No skipifsilent: the in-app auto-updater runs this installer with /SILENT and
; relies on this entry to relaunch the app once the new files are in place.
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall
