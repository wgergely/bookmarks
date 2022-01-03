; The installer script takes care of deploying Bookmarks and sets
; BOOKMARKS_ROOT environment variable to point to the
; install root. This is used by the Maya Pluging to load the python dependencies
; shipped with Bookmarks.

#define MyAppName "Bookmarks"
#define MyAppVersion "0.5.0"
#define MyAppPublisher "Gergely Wootsch"
#define MyAppURL "http://github.com/wgergely/bookmarks"
#define MyAppExeName "bookmarks.exe"
#define MyAppExeDName "bookmarks_d.exe"


[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{43C00B91-E185-48A1-9FF0-0A90F0AB831C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}

ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
DisableDirPage=false
DisableProgramGroupPage=false
; The [Icons] "quicklaunchicon" entry uses {userappdata} but its [Tasks] entry has a proper IsAdminInstallMode Check.
UsedUserAreasWarning=no
; Uncomment the following line to run in non administrative install mode (install for current user only.)
PrivilegesRequired=lowest
OutputDir={#SourcePath}..\..\launcher-installer


ChangesEnvironment=yes
ChangesAssociations=yes

OutputBaseFilename={#MyAppName}_setup_{#MyAppVersion}
SetupIconFile={#SourcePath}..\..\bookmarks\bookmarks\rsc\icon.ico

;Compression
;https://stackoverflow.com/questions/40447498/best-compression-settings-in-inno-setup-compiler
SolidCompression=no
Compression=lzma2/ultra64
LZMAUseSeparateProcess=yes
LZMADictionarySize=65536
LZMANumFastBytes=64

WizardStyle=modern
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=
VersionInfoTextVersion=
VersionInfoCopyright={#MyAppPublisher}
VersionInfoProductName=
VersionInfoProductVersion=
AppCopyright={#MyAppPublisher}
ShowLanguageDialog=no
WizardImageFile={#SourcePath}WIZMODERNIMAGE.BMP
WizardImageBackColor=clGray
WizardSmallImageFile={#SourcePath}WIZMODERNSMALLIMAGE.BMP
UsePreviousGroup=false
UninstallDisplayIcon={#SourcePath}..\..\bookmarks\bookmarks\rsc\icon.ico
UninstallDisplayName={#MyAppName}

[Languages]
Name: english; MessagesFile: compiler:Default.isl

[installDelete]
Type: filesandordirs; Name: {app}

[Tasks]
Name: desktopicon; Description: {cm:CreateDesktopIcon}; GroupDescription: {cm:AdditionalIcons}; Flags: unchecked
Name: quicklaunchicon; Description: {cm:CreateQuickLaunchIcon}; GroupDescription: {cm:AdditionalIcons}; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Components]
Name: standalone; Description: {#MyAppName} Standalone; Types: full compact custom; Flags: fixed;
Name: maya; Description: {#MyAppName}: Maya Plugin; Types: full; Check: DirExists(ExpandConstant('{userdocs}\maya'))

[Files]
; Main contents
Source: "{#SourcePath}..\..\launcher-install\*"; DestDir: "{app}"; Components: standalone; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
; Maya plugin -- mBookmarks.py
Source:  "{#SourcePath}..\..\launcher-install\shared\{#MyAppName}\maya\plugin.py"; DestName: "{#MyAppName}Maya.py"; DestDir: {userdocs}\maya\plug-ins; Components: maya; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
; Example templates
Source:  "{#SourcePath}..\bookmarks\rsc\templates\Asset.zip"; DestDir: "{localappdata}\{#MyAppName}\asset_templates"; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
Source:  "{#SourcePath}..\bookmarks\rsc\templates\Job.zip"; DestDir: "{localappdata}\{#MyAppName}\job_templates"; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify


[Registry]
; Used by the DCC plugins and the standalone executable to locate the install dir
Root: HKCU; Subkey: "Environment"; \
    ValueType: expandsz; ValueName: "BOOKMARKS_ROOT"; ValueData: "{app}";

; Extension
Root: HKCU; Subkey: "Software\Classes\.bfav"; ValueData: "{#MyAppName}"; Flags: uninsdeletevalue; ValueType: string;  ValueName: ""
Root: HKCU; Subkey: "Software\Classes\{#MyAppName}"; ValueData: "Program {#MyAppName}";  Flags: uninsdeletekey; ValueType: string;  ValueName: ""
Root: HKCU; Subkey: "Software\Classes\{#MyAppName}\DefaultIcon"; ValueData: "{app}\{#MyAppExeName},0"; ValueType: string;  ValueName: ""

; Install path
Root: HKCU; Subkey: "Software\{#MyAppName}\{#MyAppName}";  ValueData: "{app}\{#MyAppExeName}";  ValueType: string;  ValueName: "installpath"
Root: HKCU; Subkey: "Software\{#MyAppName}\{#MyAppExeDName}";  ValueData: "{app}\{#MyAppExeDName}";  ValueType: string;  ValueName: "installpath"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: {cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}; Flags: nowait postinstall skipifsilent
