#!/usr/bin/env python3
"""Windows-friendly standalone Yamaha Disklavier WAV to MIDI converter."""
import argparse
import wave
from pathlib import Path

import mido
import numpy as np

PERM = np.array([3, 4, 12, 11, 2, 5, 13, 10, 0, 7, 15, 8, 1, 6, 14, 9])
INV = np.argsort(PERM)
STATUS = set('89abcdef')
BEAM_WIDTH = 50


def normalize_message(msg):
    """Apply the MIDI conventions expected by sequencers such as Cubase."""
    if msg.type == 'program_change':
        msg = msg.copy(program=0, channel=0)
    elif msg.type == 'note_on' and msg.velocity == 0:
        msg = mido.Message('note_off', channel=msg.channel,
                           note=msg.note, velocity=64)
    return msg


def is_note_off(msg):
    """Return whether a MIDI message releases a note.

    Yamaha data may encode a release either as an explicit ``note_off`` or
    as a ``note_on`` with velocity zero.  Candidate selection happens before
    messages are normalized, so both forms must be recognized here.
    """
    return msg.type == 'note_off' or (
        msg.type == 'note_on' and msg.velocity == 0
    )


def split_burst(s):
    out = []
    while s:
        if s.startswith('c400000'):
            out.append('c400000')
            s = s[7:]
            continue
        full = 4 if s[0] in 'cd' else 6
        if len(s) <= full:
            out.append(s)
            break
        lengths = (full, full - 1, full - 2) if s[0] in '89' else (full, full - 1)
        cuts = [i for i in lengths if i < len(s) and s[i] in STATUS]
        cut = cuts[0] if cuts else full
        out.append(s[:cut])
        s = s[cut:]
    return out


def split_burst_spans(s):
    """Split a burst while retaining each message's non-idle start index."""
    out = []
    base = 0
    while s:
        if s.startswith('c400000'):
            out.append((s[:7], base))
            s = s[7:]
            base += 7
            continue
        full = 4 if s[0] in 'cd' else 6
        if len(s) <= full:
            out.append((s, base))
            break
        lengths = (full, full - 1, full - 2) if s[0] in '89' else (full, full - 1)
        cuts = [i for i in lengths if i < len(s) and s[i] in STATUS]
        cut = cuts[0] if cuts else full
        out.append((s[:cut], base))
        s = s[cut:]
        base += cut
    return out


def restore(s):
    if s == 'c400000':
        return 'c40000'
    full = 4 if s[0] in 'cd' else 6
    if len(s) == full:
        return s
    if s[0] in '89' and len(s) == 4:
        return s[:3] + 'f' + s[3:] + 'f'
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
                out.append(mido.Message('program_change', channel=0, program=0))
                continue
            data = [int(q[i:i + 2], 16) for i in range(0, len(q), 2)]
            typ = data[0] >> 4
            if typ not in (8, 9, 11, 12, 14):
                continue
            if typ in (8, 9, 11, 14) and len(data) != 3:
                continue
            if typ == 12 and len(data) != 2:
                continue
            if any(value > 127 for value in data[1:]):
                continue
            if typ == 9 and data[2]:
                data[2] = min(127, data[2] + 31)
            out.append(mido.Message.from_bytes(data))
        except (ValueError, IndexError):
            continue
    return out


def resolve_candidates(events):
    """Choose MIDI candidates while keeping note-on/off state coherent.

    Some five-nibble Yamaha messages have two valid MIDI interpretations.
    Choosing each one independently can create a spurious note-on whose
    release is then assigned to another note.  Keep a small set of the best
    active-note states and resolve the whole stream instead.
    """
    # (cost, active-note counts, selected messages)
    beam = [(0, (), ())]
    for _, options in events:
        expanded = []
        for cost, active_tuple, selected in beam:
            active = dict(active_tuple)
            for msg in options:
                next_active = active.copy()
                next_cost = cost
                if hasattr(msg, 'note'):
                    note = (msg.channel, msg.note)
                    if msg.type == 'note_on' and msg.velocity:
                        next_active[note] = next_active.get(note, 0) + 1
                    elif is_note_off(msg):
                        if next_active.get(note, 0):
                            next_active[note] -= 1
                        else:
                            next_cost += 100
                expanded.append((
                    next_cost,
                    tuple(sorted((key, value) for key, value in next_active.items()
                                 if value)),
                    selected + (msg,),
                ))

        expanded.sort(key=lambda item: item[0] + 100 * sum(
            value for _, value in item[1]
        ))
        beam = []
        seen_states = set()
        for item in expanded:
            state = item[1]
            if state in seen_states:
                continue
            seen_states.add(state)
            beam.append(item)
            if len(beam) >= BEAM_WIDTH:
                break

    return min(beam, key=lambda item: item[0] + 100 * sum(
        value for _, value in item[1]
    ))[2]


def decode(path, template_path, offset, period, progress_callback=None):
    """Decode the WAV and optionally report progress between 0.0 and 1.0."""
    report = progress_callback or (lambda _value: None)
    with wave.open(str(path), 'rb') as wav_file:
        channels = wav_file.getnchannels()
        samples = np.frombuffer(
            wav_file.readframes(wav_file.getnframes()), dtype='<i2'
        ).reshape(-1, channels)[:, 1].astype(float)
    report(0.05)
    templates_raw = np.fromfile(template_path, dtype='<i2').reshape(16, 2240).astype(float)
    indices = np.arange(14) * 160.0
    templates = np.array([
        np.interp(indices, np.arange(2240), template) for template in templates_raw
    ])
    sample_count = (len(samples) - offset) // 14
    if sample_count <= 0:
        raise ValueError('Le fichier WAV ne contient pas assez de données Yamaha.')

    states = np.empty(sample_count, dtype=np.int64)
    chunk_size = 100_000
    for start in range(0, sample_count, chunk_size):
        end = min(start + chunk_size, sample_count)
        blocks = samples[offset + start * 14:offset + end * 14].reshape(end - start, 14)
        distances = ((blocks[:, None, :] + templates[None, :, :]) ** 2).mean(2)
        states[start:end] = distances.argmin(1)
        report(0.05 + 0.65 * end / sample_count)

    nibbles = np.empty(sample_count, dtype=np.uint8)
    nibbles[0] = 255
    nibbles[1:] = [INV[(int(after) - int(before)) & 15]
                   for before, after in zip(states[:-1], states[1:])]
    positions = np.flatnonzero(nibbles[1:] != 15) + 1
    positions = positions[positions >= 1300]
    cuts = np.r_[0, np.flatnonzero(np.diff(positions) > 50) + 1, len(positions)]
    bursts = [
        (positions[start:end], ''.join(format(int(value), 'x')
                                       for value in nibbles[positions[start:end]]))
        for start, end in zip(cuts[:-1], cuts[1:])
    ]
    report(0.8)
    return nibbles, bursts


def detect_parameters(input_path, template_path=None):
    """Estimate the symbol alignment and a relative musical time origin.

    The WAV contains enough information to determine the sample alignment.
    Its absolute MIDI start time is not encoded, so the returned time offset
    places the first detected group of at least three notes at time zero.
    """
    input_path = Path(input_path)
    base = Path(__file__).resolve().parent
    templates_path = Path(template_path) if template_path else base / 'yamaha_templates.bin'
    with wave.open(str(input_path), 'rb') as wav_file:
        channels = wav_file.getnchannels()
        samples = np.frombuffer(
            wav_file.readframes(wav_file.getnframes()), dtype='<i2'
        ).reshape(-1, channels)[:, 1].astype(float)
    raw = np.fromfile(templates_path, dtype='<i2').reshape(16, 2240).astype(float)
    indices = np.arange(14) * 160.0
    templates = np.array([
        np.interp(indices, np.arange(2240), template) for template in raw
    ])

    # The carrier is continuous, so its amplitude does not reveal the start
    # of the data.  Only the phase modulo 14 samples matters; test the 14
    # possible phases around the conventional 1400-sample reference.
    candidates = range(1400, 1414)
    best = None
    for offset in candidates:
        count = min((len(samples) - offset) // 14, 30_000)
        blocks = samples[offset:offset + count * 14].reshape(count, 14)
        states = ((blocks[:, None, :] + templates[None, :, :]) ** 2).mean(2).argmin(1)
        nibbles = np.empty(count, dtype=np.uint8)
        nibbles[0] = 255
        nibbles[1:] = [INV[(int(after) - int(before)) & 15]
                       for before, after in zip(states[:-1], states[1:])]
        score = float(np.mean(nibbles[1:] == 15))
        if best is None or score > best[0]:
            best = (score, offset)
    offset = best[1]

    _, bursts = decode(input_path, templates_path, offset, 14 / 44100)
    events = []
    for positions, burst in bursts:
        for piece, start in split_burst_spans(burst):
            options = midi_candidates(restore_candidates(piece))
            if options:
                events.append((int(positions[start]), options))
    first_group = None
    for index, (state, options) in enumerate(events):
        if any(msg.type == 'note_on' and msg.velocity for msg in options):
            nearby = sum(
                any(msg.type == 'note_on' and msg.velocity and 21 <= msg.note <= 108
                    for msg in future)
                for _, future in events[index:index + 12]
            )
            if nearby >= 3 and any(
                    msg.type == 'note_on' and msg.velocity and 21 <= msg.note <= 108
                    for msg in options):
                first_group = state
                break
    time_offset = 0.0 if first_group is None else -first_group * (14 / 44100)
    return offset, time_offset


def convert_file(input_path, output_path, template_path=None, offset=1400,
                 time_offset=-1.177, keep_setup=False, progress_callback=None):
    """Convert one Yamaha WAV file and return the number of MIDI events."""
    report = progress_callback or (lambda _value: None)
    input_path = Path(input_path)
    output_path = Path(output_path)
    base = Path(__file__).resolve().parent
    templates = Path(template_path) if template_path else base / 'yamaha_templates.bin'
    _, bursts = decode(input_path, templates, offset, 14 / 44100,
                       lambda value: report(value * 0.7))

    events = []
    total_bursts = max(1, len(bursts))
    for burst_index, (positions, burst) in enumerate(bursts, 1):
        for piece, start in split_burst_spans(burst):
            options = midi_candidates(restore_candidates(piece))
            if options:
                events.append((int(positions[start]), options))
        report(0.7 + 0.1 * burst_index / total_bursts)

    mid = mido.MidiFile(type=0, ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
    selected = resolve_candidates(events)
    previous = None
    count = 0
    total_events = max(1, len(events))
    for index, ((state, _options), msg) in enumerate(zip(events, selected)):
        if msg is None:
            continue
        if not keep_setup and msg.type in ('program_change', 'pitchwheel'):
            continue
        msg = normalize_message(msg)
        if msg.channel != 9:
            msg.channel = 0
        now = max(0.0, time_offset + state * (14 / 44100))
        msg.time = int(round(mido.second2tick(
            max(0, now - (previous or 0)), 480, 500000)))
        track.append(msg)
        previous = now
        count += 1
        report(0.8 + 0.2 * (index + 1) / total_events)

    track.append(mido.MetaMessage('end_of_track', time=0))
    mid.save(output_path)
    report(1.0)
    return count


def main():
    ap = argparse.ArgumentParser(description='Convert Yamaha Disklavier WAV to MIDI')
    ap.add_argument('wav', type=Path)
    ap.add_argument('-o', '--output', type=Path)
    ap.add_argument('-t', '--templates', type=Path, default=None)
    ap.add_argument('--offset', type=int, default=1400)
    ap.add_argument('--time-offset', type=float, default=-1.177)
    ap.add_argument('--keep-setup', action='store_true',
                    help='conserver les messages Yamaha program/pitch de préambule')
    args = ap.parse_args()
    output = args.output or args.wav.with_name(args.wav.stem + '_recovered.mid')
    count = convert_file(args.wav, output, args.templates, args.offset,
                         args.time_offset, args.keep_setup)
    print(f'{count} événements écrits dans {output}')


if __name__ == '__main__':
    main()
