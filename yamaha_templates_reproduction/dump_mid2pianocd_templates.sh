#!/usr/bin/env bash
set -eu

pid="${1:?PID Wine requis, par exemple 0x20}"
port="${2:-12345}"
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

echo "Attachement au PID Wine $pid sur le port $port..."
echo "Laisse MID2PianoCD ouvert, puis lance une conversion MIDI."
winedbg --gdb --no-start --port "$port" "$pid" >/tmp/mid2pianocd_winedbg_templates.log 2>&1 &
proxy=$!
trap 'kill "$proxy" 2>/dev/null || true' EXIT
sleep 1

# Le script GDB écrit le résultat dans ce dossier.
cd "$script_dir"
gdb -q -x dump_mid2pianocd_templates.gdb
