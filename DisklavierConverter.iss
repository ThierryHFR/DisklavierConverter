[Setup]
AppName=Disklavier Converter
AppVersion=1.0.0
DefaultDirName={autopf}\Disklavier Converter
DefaultGroupName=Disklavier Converter
OutputBaseFilename=DisklavierConverterSetup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\DisklavierConverter.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Disklavier Converter"; Filename: "{app}\DisklavierConverter.exe"
