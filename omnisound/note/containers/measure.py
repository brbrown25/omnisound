# Copyright 2018 Mark S. Weiss

# TODO FEATURE augment, diminish, to_major and to_minor
#  See implementation in mingus https://bspaans.github.io/python-mingus/doc/wiki/tutorialBarModule.html
# TODO FEATURE ChordSequence, i.e. Progressions

from copy import copy
from typing import Any, Dict, Union

import pytest

from omnisound.note.adapters.note import Note, START_I
from omnisound.note.adapters.performance_attrs import PerformanceAttrs
from omnisound.note.containers.note_sequence import NoteSequence
from omnisound.note.modifiers.meter import Meter, NoteDur
from omnisound.note.modifiers.swing import Swing
from omnisound.utils.utils import (validate_optional_types,
                                   validate_types)


class MeasureSwingNotEnabledException(Exception):
    pass


class MeasureBeatInvalidPositionException(Exception):
    pass


class Measure(NoteSequence):
    """Represents a musical measure in a musical Score. As such it includes a NoteSequence
       and attributes that affect the performance of all Notes in that NoteSequence.
       Additional attributes are Meter, BPM, Scale and Key.

       Also manages musical notions of time. So maintains a Meter and knows how long a beat is,
       current beat position, and can add notes on beat or at a specified time. Also manages the
       notes in the underlying note_sequence in order sorted by start_time.
    """

    DEFAULT_METER = Meter(beats_per_measure=4, beat_note_dur=NoteDur.QUARTER, quantizing=True)

    # Measure does not take `child_sequences` arg because musical measures do not meaningfully have "child measures"
    def __init__(self, note_cls: Any = None,
                 num_notes: int = None,
                 num_attributes: int = None,
                 attr_name_idx_map: Dict[str, int] = None,
                 attr_vals_defaults_map: Dict[str, float] = None,
                 meter: Meter = None,
                 swing: Swing = None,
                 performance_attrs: PerformanceAttrs = None):
        validate_optional_types(('meter', meter, Meter), ('swing', swing, Swing),
                                ('performance_attrs', performance_attrs, PerformanceAttrs))
        super(Measure, self).__init__(note_cls=note_cls,
                                      num_notes=num_notes,
                                      num_attributes=num_attributes,
                                      attr_name_idx_map=attr_name_idx_map,
                                      attr_vals_defaults_map=attr_vals_defaults_map)

        self._sort_notes_by_start_time()

        self.meter = meter or copy(Measure.DEFAULT_METER)
        self.swing = swing
        self.measure_performance_attrs = performance_attrs
        # Support adding notes based on Meter
        self.beat = 0
        # Support adding notes offset from end of previous note
        self.next_note_start = 0.0
        self.max_duration = self.meter.beats_per_measure * self.meter.beat_note_dur.value

    def _sort_notes_by_start_time(self):
        # Sort notes by start time to manage adding on beat
        # The underlying NoteSequence stores the notes in a numpy array, which is a fixed-order data structure.
        # So we compute an ordered array mapping note start times to their index in the underlying array, then
        #  swap the values into the right indexes so the Notes in the underlying array are in sorted order
        sorted_notes = [note.as_list() for note in self]
        sorted_notes.sort(key=lambda x: x[START_I])
        # Now walk the dict of copied attributes, and write them back into the underlying notes at each index
        for i, sorted_note in enumerate(sorted_notes):
            for j, attr_name in enumerate(self.attr_name_idx_map.keys()):
                self[i].__setattr__(attr_name, sorted_note[j])

    # Beat state management
    def reset_current_beat(self):
        self.beat = 0

    def increment_beat(self):
        self.beat = min(self.beat + 1, self.meter.beats_per_measure)

    def decrement_beat(self):
        self.beat = max(0, self.beat - 1)
    # /Beat state management

    # Adding notes in sequence on the beat
    def add_note_on_beat(self, note: Note, increment_beat=False) -> 'Measure':
        """Modifies the note_sequence in place by setting its start_time to the value of measure.beat.
        If increment_beat == True the measure_beat is also incremented, after the insertion. So this method
        is a convenience method for inserting multiple notes in sequence on the beat.
        """
        validate_types(('note', note, Note), ('increment_beat', increment_beat, bool))

        note.start = self.meter.beat_start_times_secs[self.beat]
        self.append(note)
        # Maintain the invariant that notes are sorted ascending by start
        self._sort_notes_by_start_time()

        # Increment beat position if flag set and beat is not on last beat of the measure already
        if increment_beat:
            self.increment_beat()

        return self

    def add_notes_on_beat(self, to_add: NoteSequence) -> 'Measure':
        """Uses note as a template and makes copies of it to fill the measure. Each new note's start time is set
           to that beat start time.

           NOTE: This *replaces* all notes in the Measure with this sequence of notes on the beat
        """
        # Otherwise the note_list is the NoteSequence or List[Note] passed in. Retrieve it and validate
        # that it doesn't have more notes than there are beats per measure.
        if len(to_add) > self.meter.beats_per_measure:
            raise ValueError(f'Sequence `to_add` must have a number of notes <= to the number of beats per measure')

        # Now iterate the beats per measure and assign each note in note_list to the next start time on the beat
        for i, beat_start_time in enumerate(self.meter.beat_start_times_secs):
            # There might be fewer notes than beats per measure, because `to_add` is a sequence
            if i == len(self):
                break
            self[i].start = beat_start_time

        # Maintain the invariant that notes are sorted ascending by start
        self._sort_notes_by_start_time()
        return self
    # /Adding notes in sequence on the beat

    # Adding notes in sequence from the current start time, one note immediately after another
    def add_note_on_start(self, note: Note, increment_start=False) -> 'Measure':
        """Modifies the note_sequence in place by setting its start_time to the value of measure.start.
           If increment_start == True then measure.start is also incremented, after the insertion. So this method
           is a convenience method for inserting multiple notes in sequence.
           Validates that all the durations fit in the total duration of the measure.
        """
        validate_types(('note', note, Note), ('increment_start', increment_start, bool))
        if self.next_note_start + note.dur > self.max_duration:
            raise ValueError((f'measure.next_note_start {self.next_note_start} + note.duration {note.dur} > '
                              f'measure.max_duration {self.max_duration}'))
        note.start = self.next_note_start
        self.append(note)
        # Maintain the invariant that notes are sorted ascending by start
        self._sort_notes_by_start_time()

        if increment_start:
            self.next_note_start += note.dur

        return self

    def add_notes_on_start(self, to_add: NoteSequence) -> 'Measure':
        """Uses note as a template and makes copies of it to fill the measure. Each new note's start time is set
           to that of the previous notes start + duration.
           Validates that all the durations fit in the total duration of the measure.

           NOTE: This *replaces* all notes in the Measure with this sequence of notes on the beat
        """
        sum_of_durations = sum([note.dur for note in to_add])
        if self.next_note_start + sum_of_durations > self.max_duration:
            raise ValueError((f'measure.next_note_start {self.next_note_start} + '
                              f'sum of note.durations {sum_of_durations} > '
                              f'measure.max_duration {self.max_duration}'))

        for note in to_add:
            note.start = self.next_note_start
            self.append(note)
            self.next_note_start += note.dur

        # Maintain the invariant that notes are sorted ascending by start
        self._sort_notes_by_start_time()
        return self
    # Adding notes in sequence from the current start time, one note immediately after another

    # Quantize notes
    def quantizing_on(self):
        self.meter.quantizing_on()

    def quantizing_off(self):
        self.meter.quantizing_off()

    def is_quantizing(self):
        return self.meter.is_quantizing()

    def quantize(self):
        self.meter.quantize(self)

    def quantize_to_beat(self):
        self.meter.quantize_to_beat(self)
    # /Quantize notes

    # Apply Swing and Phrasing to notes
    def swing_on(self):
        if self.swing:
            self.swing.swing_on()
        else:
            raise MeasureSwingNotEnabledException('Measure.swing_on() called but swing is None in Measure')

    def swing_off(self):
        if self.swing:
            self.swing.swing_off()
        else:
            raise MeasureSwingNotEnabledException('Measure.swing_off() called but swing is None in Measure')

    def is_swing_on(self):
        if self.swing:
            return self.swing.is_swing_on()
        else:
            raise MeasureSwingNotEnabledException('Measure.is_swing_on() called but swing is None in Measure')

    def apply_swing(self):
        """Moves all notes in Measure according to how self.swing is configured.
        """
        if self.swing:
            self.swing.apply_swing(self)
        else:
            raise MeasureSwingNotEnabledException('Measure.apply_swing() called but swing is None in Measure')

    def apply_phrasing(self):
        """Moves the first note in Measure forward and the last back by self.swing.swing.swing_factor.
           The idea is to slightly accentuate the metric phrasing of each measure. Handles boundary condition
           of having 0 or 1 notes. If there is only 1 note no adjustment is made.
        """
        if self.swing:
            if len(self) > 1:
                self[0].start += \
                    self.swing.calculate_swing_adj(self[0], Swing.SwingDirection.Forward)
                self[-1].start += \
                    self.swing.calculate_swing_adj(self[-1], Swing.SwingDirection.Reverse)
        else:
            raise MeasureSwingNotEnabledException('Measure.apply_phrasing() called but swing is None in Measure')
    # /Apply Swing and Phrasing to notes

    # Getters and setters for all core note properties, get from all notes, apply to all notes
    # Getters retrieve the value for a note property from each note and return a list of values
    # Setters apply a value for a note property to each note in the note_list
    # Getters and setters for all core note properties, get from all notes, apply to all notes
    @property
    def pa(self):
        return self.measure_performance_attrs

    @pa.setter
    def pa(self, performance_attrs: PerformanceAttrs):
        self.measure_performance_attrs = performance_attrs
        for note in self:
            note.performance_attrs = performance_attrs

    @property
    def performance_attrs(self):
        return self.measure_performance_attrs

    @performance_attrs.setter
    def performance_attrs(self, performance_attrs: PerformanceAttrs):
        self.measure_performance_attrs = performance_attrs
        for note in self:
            note.performance_attrs = performance_attrs

    # NoteSequence note_list management
    # Wrap all parent methods to maintain invariant that note_list is sorted by note.start_time ascending
    def append(self, note: Note) -> 'Measure':
        super(Measure, self).append(note)
        self._sort_notes_by_start_time()
        return self

    def extend(self, to_add: NoteSequence) -> 'Measure':
        super(Measure, self).extend(to_add)
        self._sort_notes_by_start_time()
        return self

    def __add__(self, to_add: Union[Note, NoteSequence]) -> 'Measure':
        super(Measure, self).__add__(to_add)
        self._sort_notes_by_start_time()
        return self

    def __lshift__(self, to_add: Union[Note, NoteSequence]) -> 'Measure':
        return self.__add__(to_add)

    def insert(self, index: int, to_add: Union[Note, NoteSequence]) -> 'Measure':
        super(Measure, self).insert(index, to_add)
        self._sort_notes_by_start_time()
        return self

    def remove(self, to_remove: Union[Note, NoteSequence]) -> 'Measure':
        super(Measure, self).remove(to_remove)
        self._sort_notes_by_start_time()
        return self
    # /NoteSequence note_list management

    # Iterator support
    def __eq__(self, other: 'Measure') -> bool:
        if not super(Measure, self).__eq__(other):
            return False
        return self.meter == other.meter and \
            self.swing == other.swing and \
            self.beat == other.beat and \
            self.next_note_start == pytest.approx(other.next_note_start) and \
            self.max_duration == pytest.approx(other.max_duration)
    # /Iterator support

    @staticmethod
    def copy(source: 'Measure') -> 'Measure':
        # Call the dup() for the subclass of this note type
        new_measure = Measure(note_cls=source.note_cls,
                              num_notes=source.num_notes,
                              num_attributes=source._num_attributes,
                              attr_name_idx_map=source.attr_name_idx_map,
                              attr_vals_defaults_map=source.attr_vals_defaults_map,
                              meter=source.meter,
                              swing=source.swing,
                              performance_attrs=source.performance_attrs)
        new_measure.beat = source.beat
        return new_measure
