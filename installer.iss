; ============================================================
; Macro Recorder Pro — Inno Setup Installer Script
; ============================================================
; Produces a single "MacroRecorderPro_Setup.exe" installer.
;
; Prerequisites:
;   1. Build the app first:  pyinstaller MouseMacro.spec --clean
;   2. Compile this script:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
;      Or open installer.iss in Inno Setup GUI and press Ctrl+F9.
;
; Output: dist\MacroRecorderPro_Setup.exe
; ============================================================

[Setup]
AppName=Macro Recorder Pro
AppVersion=2.0.0
AppPublisher=Macro Recorder Pro
AppPublisherURL=https://github.com/macro-recorder-pro
DefaultDirName={autopf}\MacroRecorderPro
DefaultGroupName=Macro Recorder Pro
UninstallDisplayIcon={app}\MacroRecorderPro.exe
OutputDir=dist
OutputBaseFilename=MacroRecorderPro_Setup
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";  Description: "Create a &desktop shortcut";  GroupDescription: "Additional shortcuts:"
Name: "startupicon";  Description: "Start with &Windows";         GroupDescription: "Additional shortcuts:"

[Files]
; Main executable
Source: "dist\MacroRecorderPro.exe"; DestDir: "{app}"; Flags: ignoreversion

; Assets folder (icon used at runtime for window titlebar)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

; Macros storage folder (create empty dir so the app has somewhere to save)
Source: "storage\macros\*"; DestDir: "{app}\storage\macros"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist uninsneveruninstall

[Dirs]
; Ensure the macros folder exists even if empty
Name: "{app}\storage\macros"; Flags: uninsneveruninstall

[Icons]
; Start Menu
Name: "{group}\Macro Recorder Pro";           Filename: "{app}\MacroRecorderPro.exe"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Uninstall Macro Recorder Pro"; Filename: "{uninstallexe}"

; Desktop shortcut (optional task)
Name: "{userdesktop}\Macro Recorder Pro"; Filename: "{app}\MacroRecorderPro.exe"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

; Startup folder (optional task — launches on Windows login)
Name: "{userstartup}\Macro Recorder Pro"; Filename: "{app}\MacroRecorderPro.exe"; Tasks: startupicon

[Run]
; Offer to launch after install
Filename: "{app}\MacroRecorderPro.exe"; Description: "Launch Macro Recorder Pro"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up any leftover cache files (but NOT user macros — those are uninsneveruninstall)
Type: filesandordirs; Name: "{app}\__pycache__"
