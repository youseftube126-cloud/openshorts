; Inno Setup script. Built by .github/workflows/build-windows.yml, which first
; assembles the staging folder  dist\VexxoClip  (python\, app\, ffmpeg\).
#define AppName "Vexxo Clip"
#define AppVersion "0.1.0"

[Setup]
; New AppId: Vexxo Clip installs next to (not over) the old OpenShorts Studio build.
AppId={{B7D1E4A2-3C58-4F19-A6E2-5D0C9F8B7A31}
AppPublisher=Vexxo
AppName={#AppName}
AppVersion={#AppVersion}
; Per-user install: the app writes output\ and uploads\ next to its code, which
; a Program Files folder would refuse.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\VexxoClip
DefaultGroupName={#AppName}
OutputDir=..\installer
OutputBaseFilename=Vexxo-Clip-Setup
SetupIconFile=..\dist\VexxoClip\app\desktop\vexxo.ico
UninstallDisplayIcon={app}\app\desktop\vexxo.ico
WizardStyle=modern
; ultra + solid shrinks the installer ~15% vs lzma2/fast; the build just takes a few minutes longer.
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
DiskSpanning=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\VexxoClip\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\desktop\launcher.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\desktop\vexxo.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\desktop\launcher.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\desktop\vexxo.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\desktop\launcher.py"""; WorkingDir: "{app}\app"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
