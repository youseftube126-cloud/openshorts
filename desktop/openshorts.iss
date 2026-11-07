; Inno Setup script. Built by .github/workflows/build-windows.yml, which first
; assembles the staging folder  dist\OpenShorts  (python\, app\, ffmpeg\).
#define AppName "OpenShorts Studio"
#define AppVersion "0.1.0"

[Setup]
AppId={{6F3C2B1E-8A47-4D55-9C1B-0B5C7E2A91D4}
AppName={#AppName}
AppVersion={#AppVersion}
; Per-user install: the app writes output\ and uploads\ next to its code, which
; a Program Files folder would refuse.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\OpenShorts
DefaultGroupName={#AppName}
OutputDir=..\installer
OutputBaseFilename=OpenShorts-Studio-Setup
Compression=lzma2/fast
SolidCompression=no
DiskSpanning=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\OpenShorts\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\desktop\launcher.py"""; WorkingDir: "{app}\app"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\desktop\launcher.py"""; WorkingDir: "{app}\app"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\desktop\launcher.py"""; WorkingDir: "{app}\app"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
