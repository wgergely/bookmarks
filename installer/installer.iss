#define MyAppName "Bookmarks"
#define MyAppVersion "0.7.2"
#define MyAppPublisher "Gergely Wootsch"
#define MyAppURL "http:\\github.com\wgergely\bookmarks"
#define MyAppExeName "Bookmarks.exe"
#define MyAppExeDName "Bookmarks_d.exe"

[Setup]
AppId={{C6A64D39-06F7-4229-92B1-5AFEADF201CB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}

LicenseFile={#SourcePath}..\LICENCE

ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
DisableDirPage=false
DisableProgramGroupPage=false
UsedUserAreasWarning=no
PrivilegesRequired=lowest
OutputDir={#SourcePath}packages

ChangesEnvironment=yes
ChangesAssociations=yes

OutputBaseFilename={#MyAppName}_{#MyAppVersion}
SetupIconFile={#SourcePath}..\bookmarks\rsc\icon.ico

Compression=lzma2/ultra64
SolidCompression=no
LZMAUseSeparateProcess=yes
LZMADictionarySize=65536
LZMANumFastBytes=64

VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoCopyright={#MyAppPublisher}
AppCopyright={#MyAppPublisher}

UsePreviousGroup=false
UninstallDisplayIcon={#SourcePath}..\bookmarks\rsc\icon.ico
UninstallDisplayName={#MyAppName}

DisableWelcomePage=no
ShowLanguageDialog=no

WizardStyle=modern
WizardImageFile={#SourcePath}WIZMODERNIMAGE.BMP
WizardSmallImageFile={#SourcePath}WIZMODERNSMALLIMAGE.BMP
BackColor=clBlack
BackColor2=clBlack
BackSolid=false
WizardImageBackColor=clBlack
BackColorDirection=toptobottom

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
; Pre-built binaries
Source: "{#SourcePath}dist\*"; DestDir: "{app}"; Components: standalone; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
; Bookmarks python module
Source:  "{#SourcePath}..\bookmarks\*"; DestDir: "{app}\shared\bookmarks"; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify

; Maya plugin
Source:  "{#SourcePath}..\bookmarks\maya\plugin.py"; DestName: "Bookmarks.py"; DestDir: {userdocs}\maya\plug-ins; Components: maya; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
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
