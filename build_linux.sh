#!/usr/bin/env bash
set -eu
python3 -m pip install -r requirements.txt
pyinstaller --clean --noconfirm --onefile \
  --name DisklavierConverter \
  --add-data 'yamaha_templates.bin:.' \
  disklavier_converter.py
echo 'Fichier produit : dist/DisklavierConverter'
