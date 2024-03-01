#define MyAppName "${APP_NAME}"
#define MyAppVersion "${MAJOR_VERSION}.${MINOR_VERSION}.${PATCH_VERSION}"
#define MyAppPublisher "Gergely Wootsch"
#define MyAppURL "${APP_URL}"
#define MyAppExeName "${APP_EXE_NAME}"

[Setup]
AppId={{C6A64D39-06F7-4229-92B1-5AFEADF201CB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}/{#MyAppName}

LicenseFile=${LICENSE_FILE}

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
SetupIconFile=${APP_ICON_FILE}

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
UninstallDisplayIcon=${APP_ICON_FILE}
UninstallDisplayName={#MyAppName}

DisableWelcomePage=no
ShowLanguageDialog=no

WizardStyle=modern
WizardImageFile=${WIZARD_IMAGE}
WizardSmallImageFile=${WIZARD_SMALL_IMAGE}
BackColor=clBlack
BackColor2=clBlack
BackSolid=false
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
Name: templates; Description: {#MyAppName} folder templates; Types: full compact custom; Flags: fixed;
Name: maya; Description: {#MyAppName}: Maya Plugin; Types: full; Check: DirExists(ExpandConstant('{userdocs}/maya'))

[Files]
; Pre-built binaries
Source: "${PACKAGE_DIR}/*"; DestDir: "{app}"; Components: standalone; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
; Bookmarks python module
Source: "${SOURCE_DIR}/*"; DestDir: "{app}/shared/bookmarks"; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
; Templates
Source: "${SOURCE_DIR}/rsc/templates/*.zip"; DestDir: "{localappdata}/{#MyAppName}/asset_templates"; Components: standalone; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
; Icon
Source: "${APP_ICON_FILE}"; DestName: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
; Maya plugin
Source: "${SOURCE_DIR}/maya/plugin.py"; DestName: "Bookmarks.py"; DestDir: {userdocs}/maya/plug-ins; Components: maya; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify

[Registry]
; Used by the DCC plugins and the standalone executable to locate the install dir
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Bookmarks_ROOT"; ValueData: "{app}";

; Install path
Root: HKCU; Subkey: "Software/{#MyAppName}/{#MyAppName}";  ValueData: "{app}/{#MyAppExeName}";  ValueType: string;  ValueName: "installpath"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; IconIndex: 0
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\icon.ico"; IconIndex: 0
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon; IconFilename: "{app}\icon.ico"; IconIndex: 0

[Run]
Filename: "{app}/{#MyAppExeName}"; Description: {cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}; Flags: nowait postinstall skipifsilent
