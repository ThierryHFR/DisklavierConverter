# Disklavier Converter

Convertit un WAV Yamaha Disklavier / ENSPIRE contenant un flux Analog-MIDI en fichier MIDI.

## Compilation

Installer Python 3.11+ puis exécuter le script correspondant dans ce dossier.

Windows :

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

Le résultat est `dist\DisklavierConverter.exe`.

Linux :

```bash
chmod +x build_linux.sh
./build_linux.sh
```

macOS :

```bash
chmod +x build_macos.sh
./build_macos.sh
```

Le résultat Linux/macOS est `dist/DisklavierConverter`.

PyInstaller doit être lancé sur le système cible : Windows sous Windows,
macOS sous macOS et Linux sous Linux.

Pour créer un installateur, ouvrir `DisklavierConverter.iss` avec Inno Setup après la compilation.

## Utilisation

```text
.\dist\DisklavierConverter.exe entree.wav -o sortie.mid
```

Le programme utilise le canal droit du WAV, où Yamaha place généralement les données Analog-MIDI.
Les paramètres avancés sont disponibles avec `-h`.

## Licence

Ce projet est distribué sous licence GNU GPL v3 ou ultérieure. Voir [LICENSE](LICENSE).

Les fichiers WAV/MIDI de test et les captures GDB ne sont pas inclus dans ce dépôt ; ils sont trop volumineux et peuvent contenir des données musicales protégées.
