# Disklavier Converter

Converts Yamaha Disklavier / ENSPIRE WAV files containing an Analog-MIDI control stream into standard MIDI files.

## Building

Install Python 3.11 or newer, then run the script for your operating system from this directory.

Windows:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

The executable is created at `dist\DisklavierConverter.exe`.

Linux:

```bash
chmod +x build_linux.sh
./build_linux.sh
```

macOS:

```bash
chmod +x build_macos.sh
./build_macos.sh
```

The Linux/macOS executable is created at `dist/DisklavierConverter`.

PyInstaller must be run on the target operating system: Windows builds on Windows,
macOS builds on macOS, and Linux builds on Linux.

To create a Windows installer, open `DisklavierConverter.iss` with Inno Setup after building.

## Usage

```text
.\dist\DisklavierConverter.exe entree.wav -o sortie.mid
```

The program reads the right WAV channel, where Yamaha normally stores Analog-MIDI data.
Run the program with `-h` to see the advanced options.

## Yamaha templates

`yamaha_templates.bin` is the demodulator's calibration data. It contains 16 reference waveforms, each made of 2,240 signed 16-bit PCM samples, representing the phase states of the Yamaha control carrier.

The converter compares short blocks from the WAV right channel with these reference waveforms to recover the transmitted phase symbols and reconstruct MIDI events. The file is about 70 KB and contains no music or MIDI data.

The included template was calibrated for the Yamaha ENSPIRE/Disklavier signal path used during development. Other models, encoders, or processing chains may require a different template.

## License

This project is distributed under the GNU General Public License v3 or later. See [LICENSE](LICENSE).

Test WAV/MIDI files and GDB captures are not included in this repository because they are large and may contain copyrighted musical material.
