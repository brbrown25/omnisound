# Copyright 2018 Mark S. Weiss

from typing import List, Tuple

import pytest

from aleatoric.csound_note import CSoundNote
from aleatoric.measure import Measure, Meter, NoteDur, Swing
from aleatoric.note_sequence import NoteSequence

INSTRUMENT = 1
START = 0.0
DUR = float(NoteDur.QUARTER.value)
AMP = 1
PITCH = 10.1
NOTE = CSoundNote(instrument=INSTRUMENT, start=START, duration=DUR, amplitude=AMP, pitch=PITCH)

ATTR_NAME = 'test_attr'
ATTR_VAL = 100
ATTR_TYPE = int

BEATS_PER_MEASURE = 4
BEAT_DUR = NoteDur.QRTR

SWING_FACTOR = 0.5


@pytest.fixture
def note_list():
    note_1 = CSoundNote.copy(NOTE)
    note_2 = CSoundNote.copy(NOTE)
    note_2.start += DUR
    note_3 = CSoundNote.copy(NOTE)
    note_3.start += (DUR * 2)
    note_4 = CSoundNote.copy(NOTE)
    note_4.start += (DUR * 3)
    return [note_1, note_2, note_3, note_4]


@pytest.fixture
def note_sequence(note_list):
    return NoteSequence(note_list)


@pytest.fixture
def meter():
    return Meter(beats_per_measure=BEATS_PER_MEASURE, beat_dur=BEAT_DUR)


@pytest.fixture
def swing():
    return Swing(swing_factor=SWING_FACTOR)


@pytest.fixture
def measure(note_list, meter, swing):
    return Measure(note_list, meter=meter, swing=swing)


def _setup_test_swing(measure, swing_direction, swing_on=True) -> Tuple[Swing, Measure]:
    measure.swing.swing_direction = swing_direction
    if swing_on:
        measure.swing.swing_on()
    else:
        measure.swing.swing_off()
    return measure.swing, measure


def _apply_swing_and_get_note_starts(measure) -> List[float]:
    measure.apply_swing()
    actual_note_starts = [note.start for note in measure.note_list]
    return actual_note_starts


def test_measure(meter, swing, measure):
    # Assert post-invariant of `Measure.__init__()`, which is that notes are sorted ascending by start
    for i in range(len(measure.note_list) - 2):
        assert measure.note_list[i].start <= measure.note_list[i + 1].start
    # Verify attribute assignments
    assert measure.beat == 0
    assert measure.next_note_start == 0.0
    assert measure.max_duration == measure.meter.beats_per_measure * measure.meter.beat_dur
    assert measure.meter == meter
    assert measure.swing == swing


def test_swing_on_off(swing, measure):
    """Integration test of behavior of Measure based on its use of Swing as a helper attribute.
       Assumes Swing is tested, and verifies that Measure behaves as expected when using Swing.
    """
    expected_swing_note_starts = [0.0, 0.375, 0.75, 1.125]
    # Does not adjust notes if swing is off
    swing.swing_off()
    swing.swing_direction = Swing.SwingDirection.Forward
    measure.swing = swing
    actual_note_starts = _apply_swing_and_get_note_starts(measure)
    assert expected_swing_note_starts != actual_note_starts
    # Does adjust notes if swing is on
    swing.swing_on()
    actual_note_starts = _apply_swing_and_get_note_starts(measure)
    assert expected_swing_note_starts == actual_note_starts


def test_beat(measure):
    """Beat management logic is in Measure class, but it relies on Meter attribute helper class for state
       of what is beats per measure for the Measure. This test tests the interactio between the classes.
    """
    assert measure.beat == 0
    measure.increment_beat()
    assert measure.beat == 1
    measure.increment_beat()
    assert measure.beat == 2
    measure.decrement_beat()
    assert measure.beat == 1
    # Test not changing on boundary values
    measure.decrement_beat()
    assert measure.beat == 0
    measure.decrement_beat()
    assert measure.beat == 0
    for i in range(measure.meter.beats_per_measure + 10):
        assert measure.beat <= measure.meter.beats_per_measure


def test_apply_phrasing(note_list, measure):
    """If there are at least 2 notes, first and last will be adjusted as though first as swing forward
       and last has swing reverse. This class tests use of Swing class by Measure class.
    """
    expected_phrasing_note_starts = [0.0, 0.375]
    measure.swing.swing_on()
    measure.apply_phrasing()
    assert measure[0].start == expected_phrasing_note_starts[0]
    assert measure[-1].start == expected_phrasing_note_starts[-1]

    # If there is only one note in the measure, phrasing is a no-op
    expected_phrasing_note_starts = [note_list[1].start]
    short_measure = Measure([note_list[1]], meter=measure.meter, swing=measure.swing)
    short_measure.apply_phrasing()
    assert short_measure[0].start == expected_phrasing_note_starts[0]


def test_add_notes_on_beat(note_list, note_sequence, meter, swing):
    # Test adding a Note and having it copied and placed at each beat position
    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)
    assert len(measure) == 0
    expected_note_start_times = [0.0, 0.25, 0.5, 0.75]
    note = note_list[0]
    measure.add_notes_on_beat(note)
    assert len(measure) == 4
    assert [note.start for note in measure] == expected_note_start_times

    # Test adding a list of notes and having each added at the beat position
    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)
    expected_note_start_times = [0.0, 0.25, 0.5, 0.75]
    measure.add_notes_on_beat(note_list)
    assert len(measure) == 4
    assert [note.start for note in measure] == expected_note_start_times

    # Test adding a NoteSequence and having each added at the beat position
    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)
    expected_note_start_times = [0.0, 0.25, 0.5, 0.75]
    measure.add_notes_on_beat(NoteSequence(note_list))
    assert len(measure) == 4
    assert [note.start for note in measure] == expected_note_start_times

    # Test that adding more notes than there are beat positions raises
    extra_note = CSoundNote.copy(note_list[0])
    note_list.append(extra_note)
    with pytest.raises(ValueError):
        measure.add_notes_on_beat(note_list)


def test_add_note_on_beat(meter, swing):
    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)

    # Each note is added on the beat without incrementing the beat, by default ...
    expected_note_start_time = 0.0
    measure.add_note_on_beat(CSoundNote.copy(NOTE))
    assert len(measure) == 1
    assert measure[0].start == expected_note_start_time

    # ... So this note starts at the same time as the last note. But this call passes a flag
    #  to override the default and increment the beat when adding this note ...
    expected_note_start_time = 0.0
    measure.add_note_on_beat(CSoundNote.copy(NOTE), increment_beat=True)
    assert len(measure) == 2
    assert measure[1].start == expected_note_start_time

    # ... so this note starts on the second beat, after the beat at which the last note was added
    expected_note_start_time = 0.25
    measure.add_note_on_beat(CSoundNote.copy(NOTE))
    assert len(measure) == 3
    assert measure[2].start == expected_note_start_time


def test_add_notes_on_start(note_list, note_sequence, meter, swing):
    # Test adding a Note and having it copied and placed at each beat position
    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)
    assert len(measure) == 0

    # Test adding a list of notes and having each added at the beat position
    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)
    expected_note_start_times = [0.0, 0.25, 0.5, 0.75]
    measure.add_notes_on_start(note_list)
    assert len(measure) == 4
    assert [note.start for note in measure] == expected_note_start_times

    # Test adding a NoteSequence and having each added at the beat position
    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)
    expected_note_start_times = [0.0, 0.25, 0.5, 0.75]
    measure.add_notes_on_start(NoteSequence(note_list))
    assert len(measure) == 4
    assert [note.start for note in measure] == expected_note_start_times

    # Test that adding notes past measure.max_duration raises
    note = CSoundNote.copy(NOTE)
    note.dur = measure.max_duration + 1
    note_list = [note]
    with pytest.raises(ValueError):
        measure.add_notes_on_start(note_list)


def test_add_note_on_start(meter, swing):
    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)

    # Each note is added at measure.start, without incrementing the start, by default ...
    expected_note_start_time = 0.0
    measure.add_note_on_start(CSoundNote.copy(NOTE))
    assert len(measure) == 1
    assert measure[0].start == expected_note_start_time

    # ... So this note starts at the same time as the last note. But this call passes a flag
    #  to override the default and increment the start when adding this note ...
    expected_note_start_time = 0.0
    measure.add_note_on_start(CSoundNote.copy(NOTE), increment_start=True)
    assert len(measure) == 2
    assert measure[1].start == expected_note_start_time

    # ... so this note starts on the second beat, after the beat at which the last note was added
    expected_note_start_time = 0.25
    measure.add_note_on_start(CSoundNote.copy(NOTE))
    assert len(measure) == 3
    assert measure[2].start == expected_note_start_time

    # Test case of adding a note that would have a start + dur that would be > measure.max_duration raises
    note = CSoundNote.copy(NOTE)
    note.dur = measure.max_duration + 1
    with pytest.raises(ValueError):
        measure.add_note_on_start(note)


def test_note_sequence_insert_remove(meter, swing):
    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)

    # Insert a single note at the front of the list
    start = 0.1
    note = CSoundNote.copy(NOTE)
    note.start = start
    measure.insert(0, note)
    note_front = measure[0]
    assert note_front.start == start

    # Insert a list of 2 notes at the front of the list
    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)
    note_1 = CSoundNote.copy(NOTE)
    note_2 = CSoundNote.copy(NOTE)
    start_1 = 0.1
    note_1.start = start_1
    start_2 = 0.2
    note_2.start = start_2
    note_list = [note_1, note_2]
    measure.insert(0, note_list)
    assert measure[0].start == start_1
    assert measure[1].start == start_2

    # Insert a NoteSequence of 2 notes at the front of the list
    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)
    note_1 = CSoundNote.copy(NOTE)
    note_2 = CSoundNote.copy(NOTE)
    start_1 = 0.1
    note_1.start = start_1
    start_2 = 0.2
    note_2.start = start_2
    note_list = [note_1, note_2]
    measure.insert(0, NoteSequence(note_list))
    assert measure[0].start == start_1
    assert measure[1].start == start_2

    # After removing a note, the new front note is the one added second to most recently
    expected_start = measure[1].start
    note_to_remove = measure[0]
    measure.remove(note_to_remove)
    assert len(measure) == 1
    assert measure[0].start == pytest.approx(expected_start)

    # Remove notes added as NoteSequence and List[Note]
    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)
    note_1 = CSoundNote.copy(NOTE)
    note_2 = CSoundNote.copy(NOTE)
    note_list = [note_1, note_2]
    measure.insert(0, note_list)
    assert len(measure) == 2
    measure.remove(note_list)
    assert len(measure) == 0

    empty_note_list = []
    measure = Measure(empty_note_list, meter=meter, swing=swing)
    note_1 = CSoundNote.copy(NOTE)
    note_2 = CSoundNote.copy(NOTE)
    note_list = [note_1, note_2]
    measure.insert(0, NoteSequence(note_list))
    assert len(measure) == 2
    measure.remove(NoteSequence(note_list))
    assert len(measure) == 0


def test_set_get_instrument(measure):
    assert measure.instrument == [1, 1, 1, 1]
    assert measure.i == [1, 1, 1, 1]
    measure.instrument = 2
    assert measure.instrument == [2, 2, 2, 2]
    assert measure.i == [2, 2, 2, 2]
    measure.i = 3
    assert measure.instrument == [3, 3, 3, 3]
    assert measure.i == [3, 3, 3, 3]


def test_set_get_start(measure):
    assert measure.start == [0.0, 0.25, 0.5, 0.75]
    assert measure.s == [0.0, 0.25, 0.5, 0.75]
    measure.start = 1.0
    assert measure.start == [1.0, 1.0, 1.0, 1.0]
    assert measure.s == [1.0, 1.0, 1.0, 1.0]
    measure.s = 2.0
    assert measure.start == [2.0, 2.0, 2.0, 2.0]
    assert measure.s == [2.0, 2.0, 2.0, 2.0]


def test_set_get_dur(measure):
    assert measure.dur == [0.25, 0.25, 0.25, 0.25]
    assert measure.d == [0.25, 0.25, 0.25, 0.25]
    measure.dur = 1.0
    assert measure.dur == [1.0, 1.0, 1.0, 1.0]
    assert measure.d == [1.0, 1.0, 1.0, 1.0]
    measure.d = 2.0
    assert measure.dur == [2.0, 2.0, 2.0, 2.0]
    assert measure.d == [2.0, 2.0, 2.0, 2.0]


def test_set_get_amp(measure):
    assert measure.amp == [1, 1, 1, 1]
    assert measure.a == [1, 1, 1, 1]
    measure.amp = 2
    assert measure.amp == [2, 2, 2, 2]
    assert measure.a == [2, 2, 2, 2]
    measure.a = 3
    assert measure.amp == [3, 3, 3, 3]
    assert measure.a == [3, 3, 3, 3]


def test_set_get_pitch(measure):
    assert measure.pitch == [10.1, 10.1, 10.1, 10.1]
    assert measure.p == [10.1, 10.1, 10.1, 10.1]
    measure.pitch = 10.08
    assert measure.pitch == [10.08, 10.08, 10.08, 10.08]
    assert measure.p == [10.08, 10.08, 10.08, 10.08]
    measure.p = 10.09
    assert measure.pitch == [10.09, 10.09, 10.09, 10.09]
    assert measure.p == [10.09, 10.09, 10.09, 10.09]


def test_setattr(measure):
    expected_amp = 100
    expected_dur = NoteDur.EIGHTH.value

    for note in measure:
        assert note.amp != expected_amp
    for note in measure:
        assert note.dur != expected_dur

    measure.set_notes_attr('amp', expected_amp)
    measure.set_notes_attr('dur', expected_dur)
    for note in measure:
        assert note.amp == expected_amp
    for note in measure:
        assert note.dur == expected_dur


def test_transpose(measure):
    expected_pitch = 10.02
    measure.transpose(interval=1)
    for note in measure:
        assert note.pitch == expected_pitch


if __name__ == '__main__':
    pytest.main(['-xrf'])
