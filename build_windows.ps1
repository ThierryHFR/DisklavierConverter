param(
    [switch]$SkipInstaller,
    [switch]$Windows7X86
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python 3.11 ou plus récent est nécessaire pour construire le programme.'
}

$pythonBits = python -c "import struct; print(struct.calcsize('P') * 8)"
if ($Windows7X86) {
    if ($pythonBits -ne '32') { throw 'Le profil Windows 7 nécessite Python 3.8 32 bits.' }
    $pythonVersion = python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
    if ($pythonVersion -ne '3.8') { throw "Le profil Windows 7 nécessite Python 3.8.x, trouvé : $pythonVersion." }
    $requirements = 'requirements-windows-7-x86.txt'
} elseif ($pythonBits -eq '32') {
    $requirements = 'requirements-windows-x86.txt'
} elseif ($pythonBits -eq '64') {
    $requirements = 'requirements-windows.txt'
} else {
    throw "Architecture Python non supportée : $pythonBits bits."
}

if ($Windows7X86) {
    Write-Host 'Build Windows 7 x86 avec Python 3.8 et PyInstaller 5.13.2'
} else {
    Write-Host "Build Windows $pythonBits bits avec $requirements"
}
python -m pip install -r $requirements
python -m PyInstaller --clean --noconfirm --onefile `
    --name DisklavierConverter `
    --add-data 'yamaha_templates.bin;.' `
    disklavier_converter.py

Write-Host 'Exécutable produit : dist\DisklavierConverter.exe'

if ($SkipInstaller) {
    Write-Host 'Création de l''installateur ignorée (-SkipInstaller).'
    exit 0
}

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
    $isccCandidates = @(
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    )
    $isccPath = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
} else {
    $isccPath = $iscc.Source
}

if (-not $isccPath) {
    Write-Warning 'Inno Setup est introuvable : seul dist\DisklavierConverter.exe a été créé.'
    Write-Host 'Installez Inno Setup puis relancez le script, ou utilisez -SkipInstaller.'
    exit 0
}

& $isccPath (Join-Path $PSScriptRoot 'DisklavierConverter.iss')
Write-Host 'Installateur produit : installer\DisklavierConverterSetup.exe'
