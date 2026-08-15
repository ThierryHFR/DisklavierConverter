#!/usr/bin/env python3
"""Windows-friendly standalone Yamaha Disklavier WAV to MIDI converter."""
import argparse
import wave
from pathlib import Path
import numpy as np
import mido

PERM = np.array([3,4,12,11,2,5,13,10,0,7,15,8,1,6,14,9])
INV = np.argsort(PERM)
STATUS = set('89abcdef')


def normalize_message(msg):
    """Apply the MIDI conventions expected by sequencers such as Cubase."""
    if msg.type == 'program_change':
        # Recovered files are intended for piano playback, not the source
        # instrument selected in the captured stream.
        msg = msg.copy(program=0, channel=0)
    elif msg.type == 'note_on' and msg.velocity == 0:
        # Treat the MIDI shorthand for note-off explicitly for older sequencers.
        msg = mido.Message('note_off', channel=msg.channel,
                           note=msg.note, velocity=64)
    return msg

def split_burst(s):
    out = []
    while s:
        if s.startswith('c400000'):
            out.append('c400000'); s = s[7:]; continue
        full = 4 if s[0] in 'cd' else 6
        if len(s) <= full:
            out.append(s); break
        cuts = [i for i in (full, full - 1) if i < len(s) and s[i] in STATUS]
        cut = cuts[0] if cuts else full
        out.append(s[:cut]); s = s[cut:]
    return out

def restore(s):
    if s == 'c400000': return 'c40000'
    full = 4 if s[0] in 'cd' else 6
    if len(s) == full: return s
    if s[0] in '89' and len(s) == 4: return s[:3] + 'f' + s[3:] + 'f'
    if len(s) == full - 1:
        return s[:3] + 'f' + s[3:] if s[0] in '89' else s + 'f'
    return None

def decode(path, template_path, offset, period):
    with wave.open(str(path), 'rb') as w:
        fs, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').reshape(-1, ch)[:, 1].astype(float)
    t0 = np.fromfile(template_path, dtype='<i2').reshape(16, 2240).astype(float)
    idx = np.arange(14) * 160.0
    templates = np.array([np.interp(idx, np.arange(2240), q) for q in t0])
    n = (len(x) - offset) // 14
    blocks = x[offset:offset + n * 14].reshape(n, 14)
    d = ((blocks[:, None, :] + templates[None, :, :]) ** 2).mean(2)
    states = d.argmin(1)
    nib = np.empty(n, dtype=np.uint8); nib[0] = 255
    nib[1:] = [INV[(int(b) - int(a)) & 15] for a, b in zip(states[:-1], states[1:])]
    pos = np.flatnonzero(nib[1:] != 15) + 1
    pos = pos[pos >= 1300]
    cuts = np.r_[0, np.flatnonzero(np.diff(pos) > 50) + 1, len(pos)]
    return nib, [(int(pos[a]), ''.join(format(int(v), 'x') for v in nib[pos[a:e]]))
                 for a, e in zip(cuts[:-1], cuts[1:])]

def convert_file(input_path, output_path, template_path=None, offset=1400,
                 time_offset=0.819):
    """Convert one Yamaha WAV file and return the number of MIDI events."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    base = Path(__file__).resolve().parent
    templates = Path(template_path) if template_path else base / 'yamaha_templates.bin'
    _, bursts = decode(input_path, templates, offset, 14 / 44100)
    mid = mido.MidiFile(type=0, ticks_per_beat=480); tr = mido.MidiTrack(); mid.tracks.append(tr)
    tr.append(mido.MetaMessage('set_tempo', tempo=500000, time=0)); previous = None; count = 0
    for state, burst in bursts:
        for piece in split_burst(burst):
            q = restore(piece)
            if q is None: continue
            if q == 'c40000':
                msg = mido.Message('program_change', channel=0, program=0)
            else:
                data = [int(q[i:i+2], 16) for i in range(0, len(q), 2)]
                typ = data[0] >> 4
                if typ not in (8, 9, 11, 12, 14): continue
                if typ in (8, 9, 11, 14) and len(data) != 3: continue
                if typ == 12 and len(data) != 2: continue
                if typ == 9 and data[2]: data[2] = min(127, data[2] + 15)
                try: msg = mido.Message.from_bytes(data)
                except ValueError: continue
            msg = normalize_message(msg)
            if msg.channel != 9: msg.channel = 0
            now = time_offset + state * (14 / 44100)
            msg.time = int(round(mido.second2tick(max(0, now - (previous or 0)), 480, 500000)))
            tr.append(msg); previous = now; count += 1
    tr.append(mido.MetaMessage('end_of_track', time=0)); mid.save(out)
    return count


def main():
    ap = argparse.ArgumentParser(description='Convert Yamaha Disklavier WAV to MIDI')
    ap.add_argument('wav', type=Path)
    ap.add_argument('-o', '--output', type=Path)
    ap.add_argument('-t', '--templates', type=Path, default=None)
    ap.add_argument('--offset', type=int, default=1400)
    ap.add_argument('--time-offset', type=float, default=0.819)
    a = ap.parse_args()
    out = a.output or a.wav.with_name(a.wav.stem + '_recovered.mid')
    count = convert_file(a.wav, out, a.templates, a.offset, a.time_offset)
    print(f'{count} événements écrits dans {out}')

if __name__ == '__main__': main()
