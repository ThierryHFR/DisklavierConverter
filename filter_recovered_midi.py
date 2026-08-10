#!/usr/bin/env python3
"""Conservative cleanup of MIDI reconstructed from Yamaha audio."""
import argparse
import mido

ap = argparse.ArgumentParser()
ap.add_argument('input')
ap.add_argument('-o', '--output', default='filtered.mid')
a = ap.parse_args()
src = mido.MidiFile(a.input)
out = mido.MidiFile(type=src.type, ticks_per_beat=src.ticks_per_beat)
for tr in src.tracks:
    dst = mido.MidiTrack()
    for msg in tr:
        if msg.is_meta:
            dst.append(msg.copy()); continue
        if msg.type == 'note_on' and msg.velocity == 0:
            msg = mido.Message('note_off', channel=msg.channel,
                               note=msg.note, velocity=64, time=msg.time)
        if msg.type in ('note_on', 'note_off') and not 0 <= msg.note <= 127:
            continue
        dst.append(msg)
    out.tracks.append(dst)
out.save(a.output)
print(a.output)
