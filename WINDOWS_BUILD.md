# Windows

## Pour les utilisateurs

Téléchargez `DisklavierConverterSetup.exe`, lancez-le, puis utilisez le
raccourci créé dans le menu Démarrer. Python, les bibliothèques et Inno Setup
ne sont pas nécessaires sur le PC utilisateur.

## Pour créer une version

Installez Python 3.11 ou plus récent et Inno Setup 6, puis ouvrez PowerShell
dans ce dossier :

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

Le script crée automatiquement :

```text
dist\DisklavierConverter.exe
installer\DisklavierConverterSetup.exe
```

Si Inno Setup n’est pas installé, le script crée tout de même l’exécutable.
Pour demander explicitement cette version sans installateur :

```powershell
.\build_windows.ps1 -SkipInstaller
```

Utilisation :

```powershell
.\dist\DisklavierConverter.exe Mona_Lisa.wav -o Mona_Lisa.mid
```

Le fichier `yamaha_templates.bin` est intégré dans l’exécutable. Aucun Python
ni paquet supplémentaire n’est nécessaire sur le PC qui utilise le programme.

Pour produire un exécutable Windows 32 bits, utilisez l’installateur Python
3.11 32 bits. Le script détecte automatiquement cette architecture et utilise
`requirements-windows-x86.txt` (notamment NumPy 1.24.4). Un Python 64 bits
produit l’exécutable Windows 64 bits habituel.
