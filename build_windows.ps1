$ErrorActionPreference = 'Stop'
python -m pip install -r requirements.txt
pyinstaller --clean --noconfirm --onefile `
  --name DisklavierConverter `
  --add-data "yamaha_templates.bin;." `
  disklavier_converter.py
Write-Host 'Fichier produit : dist\DisklavierConverter.exe'
