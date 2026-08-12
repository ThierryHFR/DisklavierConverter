param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python 3.11 ou plus récent est nécessaire pour construire le programme.'
}

$pythonBits = python -c "import struct; print(struct.calcsize('P') * 8)"
if ($pythonBits -eq '32') {
    $requirements = 'requirements-windows-x86.txt'
} elseif ($pythonBits -eq '64') {
    $requirements = 'requirements-windows.txt'
} else {
    throw "Architecture Python non supportée : $pythonBits bits."
}

Write-Host "Build Windows $pythonBits bits avec $requirements"
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
