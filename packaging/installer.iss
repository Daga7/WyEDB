; Instalador de Windows de ODS Reporter (Inno Setup 6).
;
; Con esto el programa queda INSTALADO de verdad: entrada en el menú Inicio,
; acceso directo en el escritorio y desinstalador en "Aplicaciones" de Windows,
; en lugar de un .exe suelto que se pierde al vaciar Descargas.
;
; Se instala por usuario (en %LOCALAPPDATA%\Programs), así no pide permisos
; de administrador. Mantener AppVersion sincronizada con APP_VERSION en
; shared/constants.py. Compilación (en Windows / CI):
;   ISCC.exe packaging\installer.iss

#define AppName "ODS Reporter"
#define AppVersion "3.3.1"
#define AppPublisher "S.G.I. S.A.S. Consultoría e Ingeniería"
#define AppExeName "ODS Reporter.exe"

[Setup]
; AppId identifica el programa entre versiones: NO cambiarlo nunca, o Windows
; tratará una actualización como un programa distinto.
AppId={{7C3E9B54-2D1A-4F6E-9B8C-5A0D4E7F2C61}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=ODS-Reporter-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
