# Copyright 2018 Mark S. Weiss

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Dict, List, Union

from numpy import float64, ndarray, resize, zeros

from omnisound.note.adapters.performance_attrs import PerformanceAttrs
from omnisound.note.generators.scale_globals import MajorKey, MinorKey
from omnisound.utils.utils import validate_type, validate_type_choice, validate_types


class NoteConfig(object):
    def __init__(self, fields):
        self.__dict__['_attr_name_idx_map'] = fields
        for field in fields:
            setattr(self, field, None)

    def as_dict(self) -> Dict:
        return {field: getattr(self, field) for field in self.__dict__['_attr_name_idx_map']}

    def as_list(self) -> List:
        return [getattr(self, field) for field in self.__dict__['_attr_name_idx_map']]

    def as_array(self) -> ndarray:
        ret = zeros(len(self.__dict__['_attr_name_idx_map']))
        for i, field in enumerate(self.__dict__['_attr_name_idx_map']):
            ret[i] = getattr(self, field)
        return ret


class Note(ABC):
    """Models the core attributes of a musical note common to multiple back ends.

       Core properties are defined here that are the property interface for Notes in derived classes, which are
       notes that define the attributes for a specific back end, e.g. `CSoundNote`, `MidiNote`, etc. The core
       properties are `instrument`, `start`, `duration`, `amplitude` and `pitch`. The interface here is abstract so
       types aren't specified, but derived classes are expected to define types and enforce them with validation in
       `__init__()` and all setters. Derived notes may also create aliased properties for these core properties that
       match the conventions of their backend, and of course they may define additional properties specific to that
       backend.

       In addition, each derived type is expected to define equality, a `copy()` constructor, and `str`. Note that
       `str` may be meaningful output, as in the case of `CSoundNote`, which produces a string that can be inserted
       into a CSound score file which CSound uses to render audio. Or it may be merely a string representation of
       the information in the note, as is the case for Midi.

       Finally, each note is responsible for being able to translate a musical key (pitch on a scale) to a valid
       pitch value for that Note's backend, in the `get_pitch_for_key()` method.

       It is is strongly preferred that all getter properties return self in derived classes
       to support fluid interfaces for defining and modifying notes most easily in the least number of lines.
    """

    DEFAULT_NAME = 'Note'

    INSTRUMENT = 0
    START = 1
    DUR = 2
    AMP = 3
    PITCH = 4
    # noinspection SpellCheckingInspection
    BASE_ATTR_NAMES = {
        'instrument': INSTRUMENT,
        'i': INSTRUMENT,
        'start': START,
        's': START,
        'dur': DUR,
        'd': DUR,
        'amp': AMP,
        'a': AMP,
        'pitch': PITCH,
        'p': PITCH,
    }
    NUM_BASE_ATTRS = len(set(BASE_ATTR_NAMES.values()))

    def __init__(self, name: str = None, attrs: ndarray = None, **kwargs):
        """
        :param name: str - optional name of the Note
        :param kwargs: any {name: value} pairs for Note attributes. These can match BASE_ATTR_NAMES, in which case
         they will set values for them. Or they can be new attr_names, in which case they will be appended to the
         attributes for the Note and the value will be set for this attribute.

         Any base attributes for which no value is provided are initialized to 0.0. All values are stored internally
         as `numpy.float64` and returned as that type. Derived types wishing to cast values can do so by wrapping
         individual attributes. An example of this is `CsoundNote.instrument`, which must be `int`.

         Storage for the Note is passed in by reference. This allows the Note to provide an OO API to get and set
         attributes just for this Note, but also to allow the Note to be a row in a matrix owner by a Generator
         or Modifier, which provides a vector-space API to manipulate all Notes (rows) in the matrix, such as
         dot product to apply a Vector (another note) to all dimensions, applying a scalar to all Notes
         in one dimension, and so on.

         NOTE: This API supports adding attributes to the Note. This must not overflow the fixed-size bounds of the
         backing ndarray, which is owned by a parent Generator or Modifier. The parent is responsible for allocating
         or reallocating the ndarray correctly.
        """
        self.__dict__['_attrs'] = attrs or zeros(Note.NUM_BASE_ATTRS)
        self.__dict__['_attrs'].fill(0)
        self.__dict__['_num_attrs'] = Note.NUM_BASE_ATTRS
        self.__dict__['name'] = name or Note.DEFAULT_NAME

        if not kwargs:
            # noinspection SpellCheckingInspection
            assert len(self.__dict__['_attrs']) >= Note.NUM_BASE_ATTRS
            self.__dict__['_attr_name_idx_map'] = deepcopy(Note.BASE_ATTR_NAMES)
        # The user provided attributes and values. For any of them that match BASE_ATTR_NAMES, simply
        # set the value for that attribute from the value provided. For any that are new attributes, append
        # those attributes to `self.__dict__['_attrs']` and `self.__dict__['_attr_name_idx_map']`
        # and set the value for that attribute.
        else:
            for attr_name, attr_val in kwargs.items():
                validate_types(('kwarg attr_name', attr_name, str), ('kwarg attr_val', attr_val, float))
            self.__dict__['_attr_name_idx_map'] = deepcopy(Note.BASE_ATTR_NAMES)
            # Find the names in kwargs but not in BASE_ATTR_NAMES
            new_attr_names = kwargs.keys() - Note.BASE_ATTR_NAMES.keys()
            assert len(self.__dict__['_attrs']) >= Note.NUM_BASE_ATTRS + len(new_attr_names)
            # Add the new names to successive indexes in attr_names
            for i, attr_name in enumerate(new_attr_names):
                attr_idx = len(Note.BASE_ATTR_NAMES) + i
                self.__dict__['_attr_name_idx_map'][attr_name] = attr_idx
            # For every attr_name, if it is in kwargs then assign attrs to the value passed in in kwargs
            for attr_name in self.__dict__['_attr_name_idx_map']:
                if attr_name in kwargs:
                    self.__dict__['_attrs'][self.__dict__['_attr_name_idx_map'][attr_name]] = kwargs[attr_name]

        print('IN INIT')
        print(self.__dict__['_attr_name_idx_map'])

    def num_attrs(self) -> int:
        return self.__dict__['_num_attrs']

    def add_attr_name(self, attr_name: str, attr_idx: int):
        """Let's the user create more than one attribute that maps to the same attr index. So, for example,
           it supports aliasing multiple attribute names to one index. This should be called before assigning
           attributes with __setattr__() in derived class __init__() calls. This way the attributes are already
           in the attr_name_idx_map and get their value assigned correctly."""
        self.__dict__['_attr_name_idx_map'][attr_name] = attr_idx

    # def add_note_attr(self, attr_name: str, attr_val: float):
    #     validate_types(('attr_name', attr_name, str), ('attr_val', attr_val, float))
    #     # It's a new attribute name, so map the name to the next index in the numpy array, i.e. append it
    #     # and also add the attribute key to the object's `__dict__` so `note.attr` calls are valid. These will be
    #     # intercepted by `__getattr__` for gets, so we don't need to actually set a value for the key in
    #     # `self.__dict__`, but we need the key present for the get call to succeed.
    #     self.__dict__[attr_name] = None
    #     attr_idx = self.__dict__['_num_attrs']
    #     self.__dict__['_attr_name_idx_map'][attr_name] = attr_idx
    #     self.__dict__['_attrs'][attr_idx] = attr_val
    #     self.__dict__['_num_attrs'] += 1

    def __getattr__(self, attr_name: str) -> float64:
        """Handle returning note_attr from _attrs ndarray or any other attr a derived Note class might define"""
        validate_type('attr_name', attr_name, str)

        print(self.__dict__)
        print(dir(self))
        print(type(self))
        print('_attr_name_idx_map' in dir(self))

        if attr_name in self.__dict__['_attr_name_idx_map']:
            return self.__dict__['_attrs'][self.__dict__['_attr_name_idx_map'][attr_name]]
        else:
            return self.__dict__[attr_name]

    def __setattr__(self, attr_name: str, attr_val: Any):
        """Handle setting note_attr from _attrs ndarray or any other attr a derived Note class might define"""
        validate_type('attr_name', attr_name, str)
        if attr_name in self.__dict__['_attr_name_idx_map']:
            self.__dict__['_attrs'][self.__dict__['_attr_name_idx_map'][attr_name]] = attr_val
        else:
            self.__dict__[attr_name] = attr_val

    @abstractmethod
    def transpose(self, interval: int):
        raise NotImplemented('Derived type must implement Note.transpose -> Note')

    @property
    @abstractmethod
    def performance_attrs(self) -> PerformanceAttrs:
        raise NotImplemented('Derived type must implement Note.performance_attrs -> PerformanceAttrs')

    @performance_attrs.setter
    @abstractmethod
    def performance_attrs(self, performance_attrs: PerformanceAttrs):
        raise NotImplemented('Derived type must implement Note.performance_attrs')

    @property
    @abstractmethod
    def pa(self) -> PerformanceAttrs:
        """Alias to something shorter for client code convenience."""
        raise NotImplemented('Derived type must implement Note.pa -> PerformanceAttrs')

    @pa.setter
    @abstractmethod
    def pa(self, performance_attrs: PerformanceAttrs):
        """Alias to something shorter for client code convenience."""
        raise NotImplemented('Derived type must implement Note.pa')

    @classmethod
    @abstractmethod
    def get_pitch_for_key(cls, key: Union[MajorKey, MinorKey], octave: int) -> Any:
        raise NotImplemented('Note subtypes must implement get_pitch() and return a valid pitch value for their type')

    @staticmethod
    @abstractmethod
    def copy(source_note: 'Note') -> 'Note':
        raise NotImplemented('Derived type must implement Note.copy() -> Note')

    @abstractmethod
    def __eq__(self, other: 'Note') -> bool:
        raise NotImplemented('Derived type must implement Note.__eq__() -> bool')

    @abstractmethod
    def __str__(self):
        raise NotImplemented('Derived type must implement Note.__str__()')
