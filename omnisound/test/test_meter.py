# Copyright 2018 Mark S. Weiss

import pytest

from omnisound.note.containers.measure import Meter, NoteDur
from omnisound.note.containers.note_sequence import NoteSequence
import omnisound.note.adapters.csound_note as csound_note

INSTRUMENT = 1
START = 0.0
DUR = float(NoteDur.QUARTER.value)
AMP = 100.0
PITCH = 9.01

BEATS_PER_MEASURE = 4
BEAT_NOTE_DUR = NoteDur.QRTR
TEMPO_QPM = 240
# 4 beats per measure, quarter note is one beat, 240 QPM, so each quarter_note is 1/4 second, measure is 1 sec
MEASURE_DUR = 1
DEFAULT_IS_QUANTIZING = True

ATTR_VALS_DEFAULTS_MAP = {'instrument': float(INSTRUMENT),
                          'start': START,
                          'duration': DUR,
                          'amplitude': AMP,
                          'pitch': PITCH}
NOTE_SEQUENCE_IDX = 0
ATTR_NAME_IDX_MAP = csound_note.ATTR_NAME_IDX_MAP
NUM_NOTES = 4
NUM_ATTRIBUTES = len(csound_note.ATTR_NAMES)


def _note_sequence(attr_name_idx_map=None, attr_vals_defaults_map=None, num_attributes=None):
    attr_name_idx_map = attr_name_idx_map or ATTR_NAME_IDX_MAP
    attr_vals_defaults_map = attr_vals_defaults_map or ATTR_VALS_DEFAULTS_MAP
    num_attributes = num_attributes or NUM_ATTRIBUTES
    note_sequence = NoteSequence(make_note=csound_note.make_note,
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
    return csound_note.make_note(
            _note_sequence(
                    attr_name_idx_map=attr_name_idx_map,
                    attr_vals_defaults_map=attr_vals_defaults_map,
                    num_attributes=num_attributes).note_attr_vals[NOTE_SEQUENCE_IDX],
            attr_name_idx_map,
            attr_get_type_cast_map=attr_get_type_cast_map)


@pytest.fixture
def note():
    return _note()


@pytest.fixture
def meter():
    return Meter(beat_note_dur=BEAT_NOTE_DUR, beats_per_measure=BEATS_PER_MEASURE, tempo=TEMPO_QPM,
                 quantizing=DEFAULT_IS_QUANTIZING)


def test_meter():
    meter = Meter(beat_note_dur=BEAT_NOTE_DUR, beats_per_measure=BEATS_PER_MEASURE, tempo=TEMPO_QPM,
                  quantizing=DEFAULT_IS_QUANTIZING)

    assert meter.beats_per_measure == BEATS_PER_MEASURE
    assert meter.beat_note_dur == BEAT_NOTE_DUR
    beat_note_dur: float = BEAT_NOTE_DUR.value
    assert meter.meter_notation == (BEATS_PER_MEASURE, int(1 / beat_note_dur))
    assert meter.tempo_qpm == TEMPO_QPM
    assert meter.quarter_note_dur_secs == pytest.approx(Meter.SECS_PER_MINUTE / TEMPO_QPM)
    assert meter.quarter_notes_per_beat_note == pytest.approx(beat_note_dur / Meter.QUARTER_NOTE_DUR)
    assert meter.note_dur_secs == pytest.approx(meter.quarter_notes_per_beat_note * meter.quarter_note_dur_secs)
    assert meter.measure_dur_secs == pytest.approx(MEASURE_DUR)
    # 4/4
    # 4 quarter note beats per measure
    # 1 whole note beat per measure
    expected_beat_start_times_secs = [0.0, 0.25, 0.5, 0.75]
    for i, start in enumerate(meter.beat_start_times_secs):
        assert start == pytest.approx(expected_beat_start_times_secs[i])


def test_quantizing_on_off(meter):
    # Default is quantizing on
    assert meter.is_quantizing()
    # Can override default
    meter_2 = Meter(beat_note_dur=BEAT_NOTE_DUR, beats_per_measure=BEATS_PER_MEASURE, quantizing=False)
    assert not meter_2.is_quantizing()
    # Can toggle with methods
    meter_2.quantizing_on()
    assert meter_2.is_quantizing()
    meter_2.quantizing_off()
    assert not meter_2.is_quantizing()


def _setup_test_quantize(meter, quantize_on=True):
    sequence_before_quantize = _note_sequence()
    for note in sequence_before_quantize:
        note.dur *= 2
    sequence_before_quantize[1].start += DUR
    sequence_before_quantize[2].start += (DUR * 2)
    sequence_before_quantize[3].start += (DUR * 3)

    sequence_after_quantize = _note_sequence()
    for note in sequence_after_quantize:
        note.dur *= 2
    sequence_after_quantize[1].start += DUR
    sequence_after_quantize[2].start += (DUR * 2)
    sequence_after_quantize[3].start += (DUR * 3)

    if quantize_on:
        meter.quantizing_on()
    else:
        meter.quantizing_off()

    meter.quantize(sequence_after_quantize)

    return sequence_before_quantize, sequence_after_quantize


def test_quantize_on_off(note_sequence, meter):
    # BEFORE
    # measure ------------------------*
    # 0    0.25    0.50    0.75    1.00     1.25
    # n0************
    #        n1*************
    #               n2***************
    #                        n3***************

    # AFTER
    # measure ------------------------*
    # 0    0.25    0.50    0.75    1.00
    # n0*********
    #    n1*********
    #           n2**********
    #                   n3************

    # Test quantize on
    note_list_before_quantize, note_list_after_quantize = _setup_test_quantize(meter, quantize_on=True)

    # Test dur adjustments
    # Assert that after quantization the durations are adjusted
    # Expected adjustment is -0.125 because:
    # - max adjusted start + duration is 1.25
    # - measure_duration is 1.0
    # - adjustment is note_dur *= (1.0 - 1.25), so after adjustment its 0.5 + (0.5 * -0.25) == 0.375
    expected_dur_adjustment = 0.125
    for i, note in enumerate(note_list_after_quantize):
        assert note.dur == pytest.approx(note_list_before_quantize[i].dur - expected_dur_adjustment)

    # Test start adjustments
    # Expected start adjustments
    # - First note starts at 0.0, no adjustment
    # - Second note is 0.25 - (note.dur * total_adjustment) = 0.125
    # - Third note is 0.5 - (note.dur * total_adjustment) = 0.375
    # - Third note is 0.75 - (note.dur * total_adjustment) = 0.625
    expected_starts = [0.0, 0.125, 0.375, 0.625]
    for i, note in enumerate(note_list_after_quantize):
        assert note.start == pytest.approx(expected_starts[i])

    # Test quantize off
    note_list_before_quantize, note_list_after_quantize = _setup_test_quantize(meter, quantize_on=False)

    expected_dur_adjustment = 0.125
    for i, note in enumerate(note_list_after_quantize):
        assert note.dur != pytest.approx(note_list_before_quantize[i].dur - expected_dur_adjustment)

    expected_starts = [0.0, 0.125, 0.375, 0.625]
    for i, note in enumerate(note_list_after_quantize):
        assert note.start == pytest.approx(0.0) or note.start != pytest.approx(expected_starts[i])


def test_quantize_to_beat(note_sequence, meter):
    # Simplest test case: Note durations sum to measure duration and no quantizing required
    # Also note_list is already sorted by start ascending, so the order after quantization will be unchanged

    note_sequence[1].start += DUR
    note_sequence[2].start += (DUR * 2)
    note_sequence[3].start += (DUR * 3)

    note_starts_before_quantize = [note.start for note in note_sequence]
    note_durations_before_quantize = [note.dur for note in note_sequence]
    meter.quantize_to_beat(note_sequence)
    note_starts_after_quantize = [note.start for note in note_sequence]
    note_durations_after_quantize = [note.dur for note in note_sequence]
    assert note_starts_before_quantize == note_starts_after_quantize and \
        note_durations_before_quantize == note_durations_after_quantize

    # Test: Note durations not on the beat, quantization required
    note_sequence_with_offset_start_times = _note_sequence()
    note_sequence_with_offset_start_times[1].start += DUR
    note_sequence_with_offset_start_times[2].start += (DUR * 2)
    note_sequence_with_offset_start_times[3].start += (DUR * 3)
    # Modify the note start_times in the copy to be offset from the beats
    for i, note in enumerate(note_sequence_with_offset_start_times):
        note.start += 0.05
        assert note.start != note_sequence[i].start
    # Quantize and then assert the start times match the original start_times, which are on the beat
    meter.quantize_to_beat(note_sequence_with_offset_start_times)
    assert [note.start for note in note_sequence_with_offset_start_times] == \
           [note.start for note in note_sequence]


if __name__ == '__main__':
    pytest.main(['-xrf'])
