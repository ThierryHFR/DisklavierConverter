# Disklavier Converter

Converts Yamaha Disklavier / ENSPIRE WAV files containing an Analog-MIDI control stream into standard MIDI files.

## Building

Install Python 3.11 or newer, then run the script for your operating system from this directory.

Windows:

Install Python 3.11 or newer and Inno Setup 6. Python is required only on
the machine that builds the installer; end users do not need Python.

Open PowerShell in the project directory and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

The script installs the Python dependencies, builds the standalone executable,
and generates:

```text
installer\DisklavierConverterSetup.exe
```

This is the only file needed by Windows users. They can run it to install the
program and create the Start Menu shortcut.

The standalone executable is also created at:

```text
dist\DisklavierConverter.exe
```

To build only the standalone executable without Inno Setup:

```powershell
.\build_windows.ps1 -SkipInstaller
```

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

Inno Setup 6 is needed only on the machine that builds the installer; it is not
needed by people who install the program.

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
