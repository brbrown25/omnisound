# Copyright 2018 Mark S. Weiss

import pytest

from aleatoric.csound_note import CSoundNote
from aleatoric.foxdot_supercollider_note import FoxDotSupercolliderNote
from aleatoric.midi_note import MidiNote
from aleatoric.scale import Scale
from aleatoric.scale_globals import MajorKey, MinorKey, ScaleCls


INSTRUMENT = 1
START = 0.0
DUR = 1.0
AMP = 100
PITCH = 9.1

KEY = MajorKey.C
OCTAVE = 4
SCALE_CLS = ScaleCls.Major
NOTE_CLS = CSoundNote


@pytest.fixture
def note():
    return CSoundNote(instrument=INSTRUMENT, start=START, duration=DUR, amplitude=AMP, pitch=PITCH)


@pytest.fixture
def scale(note):
    return Scale(key=KEY, octave=OCTAVE, scale_cls=SCALE_CLS, note_cls=NOTE_CLS, note_prototype=note)


def test_scale(note, scale):
    assert scale.key == KEY
    assert scale.octave == OCTAVE
    assert scale.note_type is NOTE_CLS
    assert scale.scale_type is SCALE_CLS
    assert scale.note_prototype == note


def test_is_major_key_is_minor_key(note, scale):
    # Default note is C Major
    assert scale.is_major_key
    assert not scale.is_minor_key

    # MinorKey case
    scale_minor = Scale(key=MinorKey.C, octave=OCTAVE, scale_cls=ScaleCls.HarmonicMinor, note_cls=NOTE_CLS,
                        note_prototype=note)
    assert not scale_minor.is_major_key
    assert scale_minor.is_minor_key


def test_get_pitch_for_key(note, scale):
    # Expect that Scale.__init__() will populate the underlying NoteSequence with the notes for the `scale_cls`
    # and `key` (type of scale and root key), starting at the value of `octave` arg passed to Scale.__init__()
    expected_pitches = (4.01, 4.03, 4.05, 4.06, 4.08, 4.10, 4.12, 5.01)
    pitches = [n.pitch for n in scale.note_list]
    for i, expected_pitch in enumerate(expected_pitches):
        assert pytest.approx(expected_pitch, pitches[i])

    # MinorKey case, HarmonicMinor class in Mingus
    scale_minor = Scale(key=MinorKey.C, octave=OCTAVE, scale_cls=ScaleCls.HarmonicMinor, note_cls=NOTE_CLS,
                        note_prototype=note)
    expected_pitches = (4.01, 4.03, 4.04, 4.06, 4.08, 4.09, 4.12, 5.01)
    pitches = [n.pitch for n in scale_minor.note_list]
    for i, expected_pitch in enumerate(expected_pitches):
        assert pytest.approx(expected_pitch, pitches[i])


if __name__ == '__main__':
    pytest.main(['-xrf'])
