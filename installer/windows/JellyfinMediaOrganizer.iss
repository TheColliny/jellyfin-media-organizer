#define MyAppName "Jellyfin Media Organizer"
; CI (and BUILD_WINDOWS_INSTALLER.bat) may supply the version through JMO_VERSION so the
; installer filename always matches the release tag. Fall back to the hardcoded value.
#define MyAppVersion GetEnv("JMO_VERSION")
#if MyAppVersion == ""
  #define MyAppVersion "0.4.0"
#endif
#define MyAppExeName "JellyfinMediaOrganizer.exe"
#define MyMonitorExeName "JellyfinMediaMonitor.exe"
#define MyAppId "{{A97C0A50-45EA-4396-923C-00405DBED1D0}"

#define ProjectRoot GetEnv("JMO_PROJECT_ROOT")
#if ProjectRoot == ""
  #define ProjectRoot AddBackslash(SourcePath) + "..\.."
#endif
#define ProjectRootSlash AddBackslash(ProjectRoot)
#define AppBuildDir ProjectRootSlash + "dist\JellyfinMediaOrganizer"
#define MonitorBuildDir ProjectRootSlash + "dist\JellyfinMediaMonitor"
#define AppIconFile ProjectRootSlash + "jellyfin_organizer\assets\JellyfinMediaOrganizer.ico"
#define ReleaseDir ProjectRootSlash + "release"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=TheColliny
AppPublisherURL=https://github.com/TheColliny/jellyfin-media-organizer
AppSupportURL=https://github.com/TheColliny/jellyfin-media-organizer/issues
AppUpdatesURL=https://github.com/TheColliny/jellyfin-media-organizer/releases
DefaultDirName={autopf}\Jellyfin Media Organizer
DefaultGroupName=Jellyfin Media Organizer
DisableProgramGroupPage=yes
DisableDirPage=auto
UsePreviousAppDir=yes
UsePreviousTasks=yes
PrivilegesRequired=admin
SourceDir={#ProjectRoot}
OutputDir={#ReleaseDir}
OutputBaseFilename=JellyfinMediaOrganizer-Setup-{#MyAppVersion}
SetupIconFile={#AppIconFile}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#MyAppVersion}.0
VersionInfoDescription={#MyAppName} Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[InstallDelete]
; Clean old PyInstaller runtime folders during an in-place upgrade so stale DLLs/modules do not linger.
; User settings are stored outside Program Files and are not touched here.
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\monitor"

[Files]
Source: "{#AppBuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MonitorBuildDir}\*"; DestDir: "{app}\monitor"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Jellyfin Media Organizer"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"; AppUserModelID: "JellyfinMediaOrganizer.Desktop"
Name: "{autodesktop}\Jellyfin Media Organizer"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"; AppUserModelID: "JellyfinMediaOrganizer.Desktop"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Jellyfin Media Organizer"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/IM {#MyMonitorExeName} /F"; Flags: runhidden skipifdoesntexist; RunOnceId: "StopJellyfinMediaMonitor"

[Registry]
; If the user enabled monitor-at-login, remove that per-user startup value during uninstall.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "JellyfinMediaOrganizerMonitor"; Flags: uninsdeletevalue dontcreatekey

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  { Stop the lightweight monitor before an in-place upgrade so its EXE can be replaced. }
  Exec(ExpandConstant('{sys}\taskkill.exe'),
       '/IM {#MyMonitorExeName} /F',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;
