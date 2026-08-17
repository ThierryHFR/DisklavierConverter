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

PyInstaller must be run on the target operating system and architecture: Windows builds on Windows,
macOS builds on macOS, and Linux builds on Linux.

The GitHub Actions workflow builds both Windows x64 and Windows x86 versions.
The x86 build uses 32-bit Python 3.11 and a compatible NumPy version. To create
the x86 version locally, install 32-bit Python 3.11 and run the same
`build_windows.ps1` command; the script selects the correct dependencies
automatically.

GitHub Actions also publishes a distributable package for every matrix target:
the Windows targets receive an Inno Setup installer, Linux receives a `.tar.gz`
archive, and macOS receives a `.zip` archive containing the application.

The graphical interface is available in French, English, Spanish, Italian and
German. It detects the operating system language automatically; the language
can also be changed from the selector in the application.

Inno Setup 6 is needed only on the machine that builds the installer; it is not
needed by people who install the program.

## Usage

The graphical application lets you select one or more Yamaha Disklavier WAV
files and an output directory. By default, MIDI files are written to
`Music/DisklaviertoMidi` in the user's home directory. Each output file keeps
the input filename and uses the `.mid` extension.

The **Advanced options** section exposes the same decoder options as the
command-line converter:

| GUI field | Command-line option | Default |
| --- | --- | --- |
| Templates file | `--templates` | The bundled `yamaha_templates.bin` |
| Sample offset | `--offset` | `1400` |
| Time offset (seconds) | `--time-offset` | `-1.177` |
| Keep Yamaha setup messages | `--keep-setup` | Disabled |

Leaving the templates field empty uses the bundled template. The offset fields
must contain a valid integer and number respectively.

Use **Detect automatically** before converting a new WAV. The detector finds
the 14-sample phase alignment and sets the time offset so the first musical
group starts at zero. An absolute time offset copied from a reference MIDI
cannot be recovered from the WAV alone.

The command-line converter remains available for scripted use:

```text
.\dist\DisklavierConverter.exe entree.wav -o sortie.mid
```

The program reads the right WAV channel, where Yamaha normally stores Analog-MIDI data.
Run the program with `-h` to see the advanced options.

The complete command-line syntax is:

```text
disklavier_converter.py WAV [-o OUTPUT] [-t TEMPLATES]
                            [--offset OFFSET]
                            [--time-offset TIME_OFFSET]
                            [--keep-setup]
```

The decoder compensates for the Yamaha transport preamble and removes its
setup messages by default. Use `--keep-setup` when those `program_change` and
`pitchwheel` messages must be preserved:

```bash
python3 disklavier_converter.py entree.wav -o sortie.mid --keep-setup
```

The decoder also retains message positions inside each Yamaha burst and
resolves omitted idle `F` nibbles using the surrounding note-off events.

## Yamaha templates

`yamaha_templates.bin` is the demodulator's calibration data. It contains 16 reference waveforms, each made of 2,240 signed 16-bit PCM samples, representing the phase states of the Yamaha control carrier.

The converter compares short blocks from the WAV right channel with these reference waveforms to recover the transmitted phase symbols and reconstruct MIDI events. The file is about 70 KB and contains no music or MIDI data.

The included template was calibrated for the Yamaha ENSPIRE/Disklavier signal path used during development. Other models, encoders, or processing chains may require a different template.

## License

This project is distributed under the GNU General Public License v3 or later. See [LICENSE](LICENSE).

Test WAV/MIDI files and GDB captures are not included in this repository because they are large and may contain copyrighted musical material.
