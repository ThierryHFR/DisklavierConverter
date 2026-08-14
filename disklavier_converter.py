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
        lengths = (full, full - 1, full - 2) if s[0] in '89' else (full, full - 1)
        cuts = [i for i in lengths if i < len(s) and s[i] in STATUS]
        cut = cuts[0] if cuts else full
        out.append(s[:cut]); s = s[cut:]
    return out

def split_burst_spans(s):
    """Split a burst while retaining each message's non-idle start index."""
    out = []
    base = 0
    while s:
        if s.startswith('c400000'):
            out.append((s[:7], base)); s = s[7:]; base += 7; continue
        full = 4 if s[0] in 'cd' else 6
        if len(s) <= full:
            out.append((s, base)); break
        lengths = (full, full - 1, full - 2) if s[0] in '89' else (full, full - 1)
        cuts = [i for i in lengths if i < len(s) and s[i] in STATUS]
        cut = cuts[0] if cuts else full
        out.append((s[:cut], base)); s = s[cut:]; base += cut
    return out

def restore(s):
    if s == 'c400000': return 'c40000'
    full = 4 if s[0] in 'cd' else 6
    if len(s) == full: return s
    if s[0] in '89' and len(s) == 4: return s[:3] + 'f' + s[3:] + 'f'
    if len(s) == full - 1:
        return s[:3] + 'f' + s[3:] if s[0] in '89' else s + 'f'
    return None

def restore_candidates(s):
    if len(s) == 5 and s[0] in '89':
        return [s[:3] + 'f' + s[3:], s + 'f']
    q = restore(s)
    return [q] if q is not None else []

def midi_candidates(qs):
    out = []
    for q in qs:
        try:
            if q == 'c40000':
                out.append(mido.Message('program_change', channel=0, program=0)); continue
            data = [int(q[i:i+2], 16) for i in range(0, len(q), 2)]
            typ = data[0] >> 4
            if typ not in (8, 9, 11, 12, 14): continue
            if typ in (8, 9, 11, 14) and len(data) != 3: continue
            if typ == 12 and len(data) != 2: continue
            if any(v > 127 for v in data[1:]): continue
            # This sampler stores note-on velocity 31 units below the MIDI
            # value used by its reference Standard MIDI file.
            if typ == 9 and data[2]: data[2] = min(127, data[2] + 31)
            out.append(mido.Message.from_bytes(data))
        except (ValueError, IndexError):
            continue
    return out

def choose_candidate(events, index, options):
    if len(options) <= 1: return options[0] if options else None
    scores = []
    for msg in options:
        score = 0
        if msg.type == 'note_on' and msg.velocity:
            for future in events[index + 1:index + 21]:
                for candidate in future[1]:
                    if candidate.type == 'note_off' and candidate.note == msg.note:
                        score = 3; break
                    if (candidate.type == 'note_on' and candidate.velocity and
                            candidate.note == msg.note):
                        break
                if score: break
        scores.append(score)
    return options[scores.index(max(scores))]

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
    return nib, [(pos[a:e], ''.join(format(int(v), 'x') for v in nib[pos[a:e]]))
                 for a, e in zip(cuts[:-1], cuts[1:])]

def main():
    ap = argparse.ArgumentParser(description='Convert Yamaha Disklavier WAV to MIDI')
    ap.add_argument('wav', type=Path)
    ap.add_argument('-o', '--output', type=Path)
    ap.add_argument('-t', '--templates', type=Path, default=None)
    ap.add_argument('--offset', type=int, default=1400)
    ap.add_argument('--time-offset', type=float, default=-1.177)
    ap.add_argument('--keep-setup', action='store_true',
                    help='conserver les messages Yamaha program/pitch de préambule')
    a = ap.parse_args()
    base = Path(__file__).resolve().parent
    templates = a.templates or base / 'yamaha_templates.bin'
    out = a.output or a.wav.with_name(a.wav.stem + '_recovered.mid')
    _, bursts = decode(a.wav, templates, a.offset, 14 / 44100)
    mid = mido.MidiFile(type=0, ticks_per_beat=480); tr = mido.MidiTrack(); mid.tracks.append(tr)
    tr.append(mido.MetaMessage('set_tempo', tempo=500000, time=0)); previous = None; count = 0
    events = []
    for positions, burst in bursts:
        for piece, start in split_burst_spans(burst):
            options = midi_candidates(restore_candidates(piece))
            if options: events.append((int(positions[start]), options))
    for index, (state, options) in enumerate(events):
            msg = choose_candidate(events, index, options)
            if msg is None: continue
            if not a.keep_setup and msg.type in ('program_change', 'pitchwheel'):
                continue
            msg = normalize_message(msg)
            if msg.channel != 9: msg.channel = 0
            now = max(0.0, a.time_offset + state * (14 / 44100))
            msg.time = int(round(mido.second2tick(max(0, now - (previous or 0)), 480, 500000)))
            tr.append(msg); previous = now; count += 1
    tr.append(mido.MetaMessage('end_of_track', time=0)); mid.save(out)
    print(f'{count} événements écrits dans {out}')

if __name__ == '__main__': main()
