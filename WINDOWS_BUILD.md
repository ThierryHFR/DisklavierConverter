# Version Windows

Installer Python 3.11 ou plus récent, puis ouvrir PowerShell dans ce dossier.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

Le programme sera créé ici :

```text
dist\DisklavierConverter.exe
```

Utilisation :

```powershell
.\dist\DisklavierConverter.exe Mona_Lisa.wav -o Mona_Lisa.mid
```

Le fichier `yamaha_templates.bin` est intégré dans l’exécutable. Aucun Python
ni paquet supplémentaire n’est nécessaire sur le PC qui utilise l’exécutable.
