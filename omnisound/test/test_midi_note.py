# Copyright 2019 Mark S. Weiss

from copy import deepcopy
from typing import List

import pytest

import omnisound.note.adapters.midi_note as midi_note
from omnisound.note.adapters.note import AMP_I, DUR_I, NoteValues
from omnisound.note.adapters.performance_attrs import PerformanceAttrs
from omnisound.note.containers.note_sequence import NoteSequence

MIDI_INSTRUMENT = midi_note.MidiInstrument.Accordion
STARTS: List[float] = [1.0, 0.5, 1.5]
INT_STARTS: List[int] = [1, 5, 10]
START = STARTS[0]
INT_START = INT_STARTS[0]
DURS: List[float] = [1.0, 2.0, 2.5]
DUR = DURS[0]
AMPS: List[float] = [1.0, 2.0, 3.0]
AMP = AMPS[0]
PITCHES: List[float] = [1.0, 1.5, 2.0]
PITCH = PITCHES[0]

# noinspection PyTypeChecker
ATTR_VALS_DEFAULTS_MAP = {'instrument': float(MIDI_INSTRUMENT.value),
                          'time': START,
                          'duration': DUR,
                          'velocity': AMP,
                          'pitch': PITCH}
NOTE_SEQUENCE_IDX = 0

# TODO TEST PERFORMANCE ATTRS
PERFORMANCE_ATTRS = PerformanceAttrs()
ATTR_NAME = 'test_attr'
ATTR_VAL = 100
ATTR_TYPE = int

OCTAVE = 4

NOTE_CLS_NAME = midi_note.CLASS_NAME
ATTR_NAME_IDX_MAP = midi_note.ATTR_NAME_IDX_MAP
NUM_NOTES = 2
NUM_ATTRIBUTES = len(midi_note.ATTR_NAMES)


def _note_sequence(attr_name_idx_map = None, attr_vals_defaults_map=None, num_attributes=None):
    attr_name_idx_map = attr_name_idx_map or ATTR_NAME_IDX_MAP
    attr_vals_defaults_map = attr_vals_defaults_map or ATTR_VALS_DEFAULTS_MAP
    num_attributes = num_attributes  or NUM_ATTRIBUTES
    note_sequence = NoteSequence(make_note=midi_note.make_note,
                                 num_notes=NUM_NOTES,
                                 num_attributes=num_attributes,
                                 attr_name_idx_map=attr_name_idx_map,
                                 attr_vals_defaults_map=attr_vals_defaults_map)
    return note_sequence


@pytest.fixture
def note_sequence():
    return _note_sequence()


def _note(attr_name_idx_map=None, attr_vals_defaults_map=None,
          attr_get_type_cast_map=None, num_attributes=None):
    attr_name_idx_map = attr_name_idx_map or ATTR_NAME_IDX_MAP
    attr_vals_defaults_map = attr_vals_defaults_map or ATTR_VALS_DEFAULTS_MAP
    return midi_note.make_note(
        _note_sequence(
            attr_name_idx_map=attr_name_idx_map,
            attr_vals_defaults_map=attr_vals_defaults_map,
            num_attributes=num_attributes).note_attr_vals[NOTE_SEQUENCE_IDX],
        attr_name_idx_map,
        attr_get_type_cast_map=attr_get_type_cast_map)


@pytest.fixture
def note():
    return _note()


def _setup_note_values():
    note_values = NoteValues(midi_note.ATTR_NAMES)
    # noinspection PyTypeChecker
    note_values.instrument = float(MIDI_INSTRUMENT.value)
    note_values.time = START
    note_values.duration = DUR
    note_values.velocity = AMP
    note_values.pitch = PITCH
    return note_values


# noinspection PyTypeChecker
def test_note():
    # Test adding a non-standard mapping
    attr_name_idx_map = deepcopy(ATTR_NAME_IDX_MAP)
    attr_name_idx_map['v'] = AMP_I
    attr_name_idx_map['dur'] = DUR_I
    note = _note(attr_name_idx_map=attr_name_idx_map)

    # note.instrument is returned cast to int, even though all s are stored
    # in the note.attrs as float64, because CSoundNote configures the underlying note to cast the return of getattr()
    assert note.instrument == MIDI_INSTRUMENT.value
    assert type(note.instrument) == type(MIDI_INSTRUMENT.value) == int

    assert note.time == START
    assert note.duration == DUR
    assert note.dur == DUR
    assert note.velocity == AMP
    assert note.v == AMP
    assert note.pitch == PITCH

    note.instrument += 1.0
    assert note.instrument == int(MIDI_INSTRUMENT.value) + 1
    note.time += 1.0
    assert note.time == START + 1.0
    note.duration += 1.0
    assert note.duration == DUR + 1.0
    assert note.dur == DUR + 1.0
    note.velocity += 1.0
    assert note.velocity == AMP + 1.0
    assert note.v == AMP + 1.0
    note.pitch += 1.0
    assert note.pitch == PITCH + 1.0


@pytest.mark.parametrize('pitch', PITCHES)
@pytest.mark.parametrize('amplitude', AMPS)
@pytest.mark.parametrize('duration', DURS)
@pytest.mark.parametrize('start', STARTS)
def test_midi_note_attrs(start, duration, amplitude, pitch):
    # Add multiple aliased property names for note attributes
    attr_name_idx_map = {'i': 0, 'instrument': 0,
                         't': 1, 'time': 1,
                         'd': 2, 'dur': 2, 'duration': 2,
                         'v': 3, 'velocity': 3,
                         'p': 4, 'pitch': 4}
    # Test assigning default s to each note created in the underlying NoteSequence
    # noinspection PyTypeChecker
    attr_vals_defaults_map = {
        'instrument': float(MIDI_INSTRUMENT.value),
        'time': start,
        'duration': duration,
        'velocity': amplitude,
        'pitch': pitch,
    }
    attr_get_type_cast_map = {'p': int, 'v': int}
    note = _note(attr_name_idx_map=attr_name_idx_map,
                 attr_vals_defaults_map=attr_vals_defaults_map,
                 attr_get_type_cast_map=attr_get_type_cast_map,
                 num_attributes=len(attr_vals_defaults_map))

    # noinspection PyTypeChecker
    assert note.instrument == note.i == int(MIDI_INSTRUMENT.value)
    assert type(note.instrument) == int
    assert note.time == note.t == start
    assert note.duration == note.dur == note.d == duration
    assert note.velocity == note.v == int(amplitude)
    assert note.pitch == note.p == int(pitch)


@pytest.mark.parametrize('pitch', PITCHES)
@pytest.mark.parametrize('amplitude', AMPS)
@pytest.mark.parametrize('duration', DURS)
@pytest.mark.parametrize('start', STARTS)
def test_midi_note_to_str(start, duration, amplitude, pitch):
    # Add multiple aliased property names for note attributes
    attr_name_idx_map = {'instrument': 0,
                         'time': 1,
                         'duration': 2,
                         'velocity': 3,
                         'pitch': 4}
    # Test assigning default s to each note created in the underlying NoteSequence
    # noinspection PyTypeChecker
    attr_vals_defaults_map = {
        'instrument': float(MIDI_INSTRUMENT.value),
        'time': start,
        'duration': duration,
        'velocity': amplitude,
        'pitch': pitch,
    }
    note = _note(attr_name_idx_map=attr_name_idx_map,
                 attr_vals_defaults_map=attr_vals_defaults_map,
                 num_attributes=len(attr_vals_defaults_map))

    expected_str_note = (f'instrument: {MIDI_INSTRUMENT.value} time: {start} duration: {duration} '
                         f'velocity: {int(amplitude)} pitch: {int(pitch)} channel: {midi_note.DEFAULT_CHANNEL}')
    assert expected_str_note == str(note)


@pytest.mark.parametrize('pitch', PITCHES)
@pytest.mark.parametrize('amplitude', AMPS)
@pytest.mark.parametrize('duration', DURS)
@pytest.mark.parametrize('start', STARTS)
def test_midi_note_attrs_fluent(start, duration, amplitude, pitch):
    # Add multiple aliased property names for note attributes
    attr_name_idx_map = {'i': 0, 'instrument': 0,
                         't': 1, 'time': 1,
                         'd': 2, 'dur': 2, 'duration': 2,
                         'v': 3, 'velocity': 3,
                         'p': 4, 'pitch': 4}
    # Set the note  to not equal the values passed in to the test
    # noinspection PyTypeChecker
    attr_vals_defaults_map = {
        'instrument': float(MIDI_INSTRUMENT.value + 1),
        'time': 0.0,
        'duration': 0.0,
        'velocity': 0.0,
        'pitch': 0.0,
    }
    attr_get_type_cast_map = {'p': int, 'v': int}
    # Don't pass in attr_vals_defaults_map, so not creating a Note with the s passed in to each test
    note = _note(attr_name_idx_map=attr_name_idx_map,
                 attr_vals_defaults_map=attr_vals_defaults_map,
                 attr_get_type_cast_map=attr_get_type_cast_map,
                 num_attributes=len(attr_vals_defaults_map))

    # Assert the note does not have the expected attr s
    assert note.time == note.t != start
    assert note.duration == note.dur == note.d != duration
    assert note.velocity == note.v != amplitude
    assert note.pitch == note.p != pitch
    # Then use the fluent accessors with chained syntax to assign the s passed in to this test
    note.I(MIDI_INSTRUMENT.value).T(start).D(duration).V(amplitude).P(pitch)
    # Assert the note now has the expected attr s
    assert note.time == note.t == start
    assert note.duration == note.dur == note.d == duration
    assert note.velocity == note.v == int(amplitude)
    assert note.pitch == note.p == int(pitch)


def test_midi_note_channel(note):
    assert note.channel == midi_note.DEFAULT_CHANNEL
    note.channel = midi_note.DEFAULT_CHANNEL + 1
    assert note.channel == midi_note.DEFAULT_CHANNEL + 1


def test_note_values():
    note_values = _setup_note_values()
    note = _note(attr_vals_defaults_map=note_values.as_dict())

    # noinspection PyTypeChecker
    assert note.instrument == float(MIDI_INSTRUMENT.value)
    assert note.time == START
    assert note.duration == AMP
    assert note.velocity == DUR
    assert note.pitch == PITCH


if __name__ == '__main__':
    pytest.main(['-xrf'])
