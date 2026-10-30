#ifndef GameVersion
  #define GameVersion "2.0.3"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\LeadTheTarget"
#endif
#ifndef ReleaseDir
  #define ReleaseDir "..\release"
#endif

[Setup]
AppId={{645A7AB7-137A-49A6-BEAD-733E1F3D2019}
AppName=Lead the Target
AppVersion={#GameVersion}
AppPublisher=Lead the Target contributors
AppPublisherURL=https://github.com/Leaferd6712/Lead-the-Target
AppSupportURL=https://github.com/Leaferd6712/Lead-the-Target/issues
DefaultDirName={localappdata}\Programs\LeadTheTarget
DefaultGroupName=Lead the Target
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
UninstallDisplayIcon={app}\LeadTheTarget.exe
OutputDir={#ReleaseDir}
OutputBaseFilename=LeadTheTarget-v{#GameVersion}-windows-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=no
CloseApplications=yes
SetupIconFile=..\assets\app.ico
LicenseFile=..\LICENSE

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Lead the Target"; Filename: "{app}\LeadTheTarget.exe"
Name: "{group}\Uninstall Lead the Target"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Lead the Target"; Filename: "{app}\LeadTheTarget.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LeadTheTarget.exe"; Description: "Launch Lead the Target"; Flags: nowait postinstall skipifsilent
