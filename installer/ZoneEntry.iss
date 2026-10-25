; ZoneEntry installer (Inno Setup 6).
; The GitHub workflow builds it with:  ISCC.exe /DAppVersion=1.1.0 installer\ZoneEntry.iss
; Installs for the CURRENT USER ONLY, so no administrator rights are needed.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6D1C5E0A-3B7B-4E57-9B0B-5A8C2F1D7E42}
AppName=ZoneEntry
AppVersion={#AppVersion}
AppVerName=ZoneEntry {#AppVersion}
AppPublisher=ZoneEntry
DefaultDirName={autopf}\ZoneEntry
DefaultGroupName=ZoneEntry
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=ZoneEntry-Setup
SetupIconFile=..\assets\zoneentry.ico
UninstallDisplayIcon={app}\ZoneEntry.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\ZoneEntry\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\ZoneEntry"; Filename: "{app}\ZoneEntry.exe"
Name: "{autodesktop}\ZoneEntry"; Filename: "{app}\ZoneEntry.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ZoneEntry.exe"; Description: "{cm:LaunchProgram,ZoneEntry}"; Flags: nowait postinstall skipifsilent

; Your lists and saved work live in %APPDATA%\ZoneEntry and are deliberately NOT removed on uninstall.
