; Unscreen installer — Inno Setup script.
;
; Compile (from the repository root):
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ^
;     /DMyAppVersion=0.4.3 /DMyAppExeName=unscreen.exe /DBundleDir=build\bundle ^
;     packaging\windows\installer.iss
;
; The installer distinguishes four flows based on what it finds in the
; registry before anything is copied:
;   * install    - no previous Unscreen installation -> fresh install
;   * upgrade    - an older version is installed      -> silently uninstall
;                  it just before copying files (user data in %APPDATA%
;                  is untouched), then install the new version
;   * repair     - the same version is installed      -> ask, then overwrite
;   * downgrade  - a newer version is installed       -> abort with a hint
;                  to uninstall first

#define MyAppName "Unscreen"
#define MyAppId "D2E3F4A5-B6C7-48D9-A0B1-C2D3E4F5A6B7"
#ifndef MyAppPublisher
  #define MyAppPublisher "Sakth1"
#endif
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef MyAppExeName
  #define MyAppExeName "unscreen.exe"
#endif
#ifndef BundleDir
  #define BundleDir "build\bundle"
#endif
#ifndef MyAppComments
  #define MyAppComments "Cross-device app usage timeline tracker"
#endif

[Setup]
; IMPORTANT: AppId must never change, it is what lets the installer detect
; existing installations (registry key "{#MyAppId}_is1").
AppId={{D2E3F4A5-B6C7-48D9-A0B1-C2D3E4F5A6B7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppComments={#MyAppComments}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputBaseFilename={#MyAppName}-{#MyAppVersion}-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
WizardResizable=yes
SetupLogging=yes
CloseApplications=yes
RestartApplications=no
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\..\src\assets\icon_windows.ico
VersionInfoVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoDescription={#MyAppComments}
VersionInfoCompany={#MyAppPublisher}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Hides the "Dir already exists" prompt when repairing an install.
EnableDirDoesntExistWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  InstalledVersion: String;
  UpgradeUninstallCmd: String;
  AppMode: String;

const
  UninstallKeyBase = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppId}_is1';

{ Compare two dotted-decimal version strings. Returns -1/0/1. }
function CompareVersions(Version1, Version2: String): Integer;
var
  Packed1: Int64;
  Packed2: Int64;
begin
  if not StrToVersion(Version1, Packed1) then
    Packed1 := 0;
  if not StrToVersion(Version2, Packed2) then
    Packed2 := 0;
  Result := ComparePackedVersion(Packed1, Packed2);
end;

{ Read DisplayVersion/UninstallString from any registry view that has the
  uninstall key (64-bit and 32-bit, HKLM and HKCU). }
function GetInstalledInfo(out Version: String; out UninstallCmd: String): Boolean;
begin
  Result := False;
  Version := '';
  UninstallCmd := '';

  if RegKeyExists(HKLM64, UninstallKeyBase) then
  begin
    RegQueryStringValue(HKLM64, UninstallKeyBase, 'DisplayVersion', Version);
    RegQueryStringValue(HKLM64, UninstallKeyBase, 'UninstallString', UninstallCmd);
    Result := True;
  end
  else if RegKeyExists(HKLM, UninstallKeyBase) then
  begin
    RegQueryStringValue(HKLM, UninstallKeyBase, 'DisplayVersion', Version);
    RegQueryStringValue(HKLM, UninstallKeyBase, 'UninstallString', UninstallCmd);
    Result := True;
  end
  else if RegKeyExists(HKCU64, UninstallKeyBase) then
  begin
    RegQueryStringValue(HKCU64, UninstallKeyBase, 'DisplayVersion', Version);
    RegQueryStringValue(HKCU64, UninstallKeyBase, 'UninstallString', UninstallCmd);
    Result := True;
  end
  else if RegKeyExists(HKCU, UninstallKeyBase) then
  begin
    RegQueryStringValue(HKCU, UninstallKeyBase, 'DisplayVersion', Version);
    RegQueryStringValue(HKCU, UninstallKeyBase, 'UninstallString', UninstallCmd);
    Result := True;
  end;
end;

{ Decide the flow: install / upgrade / repair / abort-on-downgrade. }
function InitializeSetup(): Boolean;
var
  UninstallCmd: String;
  Compare: Integer;
begin
  Result := True;
  AppMode := 'install';
  UpgradeUninstallCmd := '';

  if GetInstalledInfo(InstalledVersion, UninstallCmd) and (InstalledVersion <> '') then
  begin
    Compare := CompareVersions(InstalledVersion, '{#MyAppVersion}');
    if Compare = 0 then
    begin
      AppMode := 'repair';
      if MsgBox(
        'Unscreen ' + InstalledVersion + ' is already installed on this computer.'#13#10#13#10 +
        'Do you want to reinstall it now?',
        mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
      end;
    end
    else if Compare < 0 then
    begin
      AppMode := 'upgrade';
      UpgradeUninstallCmd := UninstallCmd;
    end
    else
    begin
      AppMode := 'downgrade';
      MsgBox(
        'You are attempting to downgrade Unscreen from ' + InstalledVersion +
        ' to {#MyAppVersion}, which is not supported.'#13#10#13#10 +
        'Uninstall the current app to install the older version.',
        mbCriticalError, MB_OK);
      Result := False;
    end;
  end;
end;

{ Reword the welcome page so the user knows exactly what will happen. }
procedure InitializeWizard();
begin
  case AppMode of
    'upgrade':
      WizardForm.WelcomeLabel2.Caption :=
        'Unscreen ' + InstalledVersion + ' is already installed on your computer.'#13#10#13#10 +
        'This wizard will update it to {#MyAppVersion}. Your data is kept.';
    'repair':
      WizardForm.WelcomeLabel2.Caption :=
        'Unscreen {#MyAppVersion} is already installed on your computer.'#13#10#13#10 +
        'This wizard will reinstall the current version. Your data is kept.';
  else
    WizardForm.WelcomeLabel2.Caption :=
      'This will install Unscreen {#MyAppVersion} on your computer.'#13#10#13#10 +
      'It is recommended that you close all other applications before continuing.';
  end;
end;

// On upgrades, remove the previous installation right before copying files so
// stale bundle files (Flutter assets, removed DLLs) cannot linger. The
// uninstaller only removes the app directory and registry entries, so user
// data in %APPDATA%\Unscreen survives.
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if (CurStep = ssInstall) and (AppMode = 'upgrade') and (UpgradeUninstallCmd <> '') then
  begin
    Log('Removing previous installation: ' + UpgradeUninstallCmd);
    if not Exec(
      RemoveQuotes(UpgradeUninstallCmd),
      '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      MsgBox(
        'Could not remove the previous installation of Unscreen.'#13#10#13#10 +
        'Uninstall it manually, then run setup again.',
        mbCriticalError, MB_OK);
    end;
  end;
end;
