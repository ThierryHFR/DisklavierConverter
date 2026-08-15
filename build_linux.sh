#!/usr/bin/env bash
set -eu
python3 -m pip install -r requirements.txt
pyinstaller --clean --noconfirm --onefile \
  --windowed \
  --name DisklavierConverter \
  --add-data 'yamaha_templates.bin:.' \
  disklavier_gui.py
echo 'Fichier produit : dist/DisklavierConverter'
