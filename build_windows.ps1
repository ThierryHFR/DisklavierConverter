param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python 3.11 ou plus récent est nécessaire pour construire le programme.'
}

python -m pip install -r requirements-windows.txt
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
