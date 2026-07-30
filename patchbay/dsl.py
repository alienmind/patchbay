"""A declarative way to say what a rack is.

The design follows one line of PATCHBAYGROUND.md: "This consistency is the
actual product, more than any individual rack." The macro layout is
identical across every instrument rack, so the thing worth expressing is
not "build a rack" but "bind this engine's parameters to the standard
layout".

    PUSH = Layout(Slot("Engine", selects=True), Slot("Cutoff", start=127),
                  Slot("Decay"))

    FM = (Engine("Operator")
          .drives(PUSH.cutoff, "Filter/Frequency", over=Range(200, 8000, "Hz"))
          .drives(PUSH.decay, "Filter/Envelope/DecayTime")
          .offers("attack", "Operator.0/Envelope/AttackTime"))

    SAMPLE = (Engine("OriginalSimpler")
              .drives(PUSH.cutoff, "Filter/Slot/Value/SimplerFilter/Freq",
                      over=Range(200, 8000, "Hz"))
              .drives(PUSH.decay,
                      "Filter/Slot/Value/SimplerFilter/Envelope/DecayTime"))

    rack = (Rack.instrument("PD1", PUSH)
            .chain("FM", FM)
            .chain("Sample", SAMPLE)
            .variations(PUSH.variation("dark", cutoff=30, decay=110)))

    rack.save("build/PD1.adg")

Three things fall out of that shape rather than being programmed:

  The sound family constraint. Every engine binds its own parameters to
  the same layout slots, so one macro moves the same musical idea through
  every synthesis method. Variation index N means the same thing across
  engines because the layout is what they share.

  Engine select. The layout's selector slot drives the chain selector and
  zones are distributed evenly across 0..127, so that knob sweeps engines.

  Variations. A variation is a vector over layout slots, in macro space,
  so it renders through every engine without being written per engine.
  A sound is a variation, not a chain - which is what makes ~692 of them
  tractable.

One verb per relation. `drives` binds a slot to a device parameter,
`offers` says what an engine could serve, `spends` picks which of those a
rack wants, `chain` and `pad` add chains, `chaining` puts a rack inside
one. Nesting cannot be misread as parameter binding, because they are not
the same call.

Values, not mutation. Every builder returns a new object, so a layout, an
engine profile or a sub-rack can sit in two racks without one build
reaching the other.

What this is not: a general graph DSL. It expresses the racks in
PATCHBAYGROUND.md and stops there.
"""

from __future__ import annotations

import copy
import difflib
import re
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Iterator, Mapping, Sequence, Union

from lxml import etree

from . import clone, find, io, params, samples, variations
from .library import Library

MACRO_MAX: int = 127
MAX_MACROS: int = 16

Element = etree._Element

#: Emptied skeleton trees by (file, rack kind), and the file each kind
#: resolves to. Both are pure functions of what is on disk, and both were
#: recomputed once per rack. See _load_skeleton.
_SKELETONS: dict = {}
_SKELETON_PATHS: dict = {}

#: A return branch and a send entry, from the first file found carrying one.
_RETURN_TEMPLATES: dict = {}

#: Live's silent floor for a send, in linear amplitude: 10^(-70/20). A send
#: nobody set reads this, which is what Live writes when a return appears.
SEND_FLOOR: float = 0.0003162277571


def _neutralised_sends(el: Element) -> Element:
    """Put every send in a lifted template back on the floor, unmapped.

    A skeleton is for SHAPE. The file it came from is spike evidence, and
    `racks/q23_a.adg` arrived carrying a send at 0.339 with a macro mapped
    to it, sorted ahead of the drum rack that had been supplying this, and
    gave all eight DR1 pads a reverb send nobody declared. The golden caught
    it. Same rule as a donor: never anybody's values, never their mappings.
    """
    for send in el.iter("Send"):
        clone.strip_macro_mappings(send)
        params.set_value(send, SEND_FLOOR)
    return el


def _macro_pos(slot: str, pos: float) -> float:
    """A macro position, checked against the only scale macros have.

    Out of range is refused rather than clamped: Live clamps silently, so a
    127 meant as a percentage would load as a rack that works and a 200
    would load as one that looks identical and is not what was written.
    """
    pos = float(pos)
    if not 0.0 <= pos <= MACRO_MAX:
        raise ValueError(
            f"{slot}: macro positions are 0..{MACRO_MAX}, got {pos:g}")
    return pos


def _key(display: str) -> str:
    """The Python name for a slot displayed as `display`.

    "Send A" -> send_a. Live's macro name is free text; a Python identifier
    is not, and the two are allowed to differ.
    """
    k = re.sub(r"[^0-9a-zA-Z]+", "_", display).strip("_").lower()
    if not k or k[0].isdigit():
        k = f"slot_{k}"
    return k


class RackKind(str, Enum):
    """Which kind of rack to build.

    This matters more than it looks: an instrument cannot live in an audio
    effect chain, and Live will not load a preset that tries. The kind
    selects both the rack device tag and the branch tag.
    """

    INSTRUMENT = "InstrumentGroupDevice"
    AUDIO_EFFECT = "AudioEffectGroupDevice"
    MIDI_EFFECT = "MidiEffectGroupDevice"
    DRUM = "DrumGroupDevice"

    @property
    def branch_tag(self) -> str:
        return {
            RackKind.INSTRUMENT: "InstrumentBranchPreset",
            RackKind.AUDIO_EFFECT: "AudioEffectBranchPreset",
            RackKind.MIDI_EFFECT: "MidiEffectBranchPreset",
            RackKind.DRUM: "DrumBranchPreset",
        }[self]


@dataclass(frozen=True, slots=True)
class Range:
    """A range a macro drives a parameter across, in the parameter's units.

    Where engines disagree about units this is the only place the agreement
    can live: PD1's Volume slot bound the right parameter on both engines
    and still silenced one and not the other, because one is amplitude and
    the other decibels. See Q14 in `SCHEMA.md`.

    `unit` is documentation. Nothing reads it, because nothing can: the
    format records none, and the same slot is in Hz on one engine and dB on
    the next. It is here so the constant says which it is.
    """

    lo: float
    hi: float
    unit: str = ""

    def scaled(self, factor: float) -> "Range":
        """The same range in units `factor` times smaller. Seconds to ms."""
        return Range(self.lo * factor, self.hi * factor, self.unit)

    def capped(self, hi: float) -> "Range":
        """The same floor, a lower ceiling."""
        return replace(self, hi=hi)

    def as_tuple(self) -> tuple[float, float]:
        return (self.lo, self.hi)


@dataclass(frozen=True, slots=True)
class Slot:
    """One macro: its position, what it is called, where it opens.

    Everything about a slot in one place, so it is named once and a typo
    raises at the layout rather than at the binding that uses it.

    `start` is where the knob sits on a fresh drop. A macro Live has never
    been told about reads 0, and 0 through a binding is the BOTTOM of the
    parameter's range: silent volume, shut filter, instant release. So a
    rack that binds a slot and does not place it loads mute. The position
    belongs to the slot rather than to the rack, for the same reason the
    name does: one knob means one thing everywhere.

    `label` is what the hardware SAYS, which is not what the slot IS. The
    position is the contract and the word is local: a kick's slot 4 reading
    "Drive + Snap" where a hat's reads "Drive" is the same slot, the same
    chaining and the same muscle memory.
    """

    display: str
    start: float | None = None
    label: str | None = None
    selects: bool = False
    #: Filled in by Layout. 1-based, as in Live's UI.
    number: int = 0

    @property
    def key(self) -> str:
        return _key(self.display)

    @property
    def name(self) -> str:
        """What this slot writes on the display: its label, or its own name."""
        return self.label if self.label is not None else self.display

    def to(self, inner: "Slot") -> "SlotPair":
        """This outer slot drives a differently named inner one."""
        return SlotPair(self, inner)

    def __repr__(self) -> str:
        return f"<{self.display} m{self.number}>"


@dataclass(frozen=True, slots=True)
class SlotPair:
    outer: Slot
    inner: Slot


@dataclass(frozen=True, slots=True)
class Variation:
    """One sound, as a position for each layout slot it cares about.

    Values are macro positions, 0..127, because that is the only scale a
    variation has (ARCHITECTURE.md section 11). A slot left out is left
    unset, so recalling this variation does not move that knob.

    The sound family constraint falls out of this rather than being
    enforced: the vector is written in slot terms, every engine binds the
    same slots to its own parameters, and Live applies each engine's own
    range at recall. So variation N is the same musical idea whichever
    engine is selected, and index alignment across engines is structural.

    Built by `Layout.variation`, which is what checks the slots belong to
    the layout the rack is using.
    """

    name: str
    values: Mapping[Slot, float]

    def __repr__(self) -> str:
        shown = ", ".join(f"{s.display}={v:g}" for s, v in self.values.items())
        return f"<Variation {self.name!r} {shown}>"


class Layout:
    """An ordered list of slots, and the namespace that names them.

    QWERTY is the analogy and it is exact. A keyboard layout is shared
    across many different physical keyboards precisely so the skill
    transfers, the position carries the meaning, and the keycap is local
    paint. That is this object, slot for slot.

    `PB.filter` is the slot itself, not the string "Filter". `Send A`
    answers to `send_a`: the word on the hardware and the Python name are
    already two things, and this finishes the split.
    """

    __slots__ = ("slots", "selector", "_by_key")

    def __init__(self, *slots: Slot | str) -> None:
        placed = []
        for i, s in enumerate(slots):
            s = Slot(s) if isinstance(s, str) else s
            if s.start is not None:
                _macro_pos(s.display, s.start)
            placed.append(replace(s, number=i + 1))
        if len(placed) > MAX_MACROS:
            raise ValueError(
                f"a rack has {MAX_MACROS} macros; got {len(placed)} slots")
        self.slots: tuple[Slot, ...] = tuple(placed)

        self._by_key: dict[str, Slot] = {}
        for s in self.slots:
            if s.key in self._by_key:
                raise ValueError(
                    f"slots {self._by_key[s.key].display!r} and {s.display!r} "
                    f"both mean {s.key!r} in Python; rename one")
            self._by_key[s.key] = s

        # Which slot drives the chain selector. Named rather than fixed at
        # slot 1, because a drum rack's macro 1 is not a selector: a pad is
        # chosen by its ReceivingNote. A layout where no slot selects gets
        # no selector mapping at all.
        selecting = [s for s in self.slots if s.selects]
        if len(selecting) > 1:
            raise ValueError(
                f"{', '.join(s.display for s in selecting)} all claim the "
                f"chain selector; a rack has one")
        self.selector: Slot | None = selecting[0] if selecting else None

    def __getattr__(self, name: str) -> Slot:
        try:
            return self._by_key[name]
        except KeyError:
            raise AttributeError(
                f"{name!r} is not a slot here. Slots: "
                f"{', '.join(s.key for s in self.slots)}") from None

    def __getitem__(self, name: str) -> Slot:
        return getattr(self, _key(name))

    def __contains__(self, slot: object) -> bool:
        if isinstance(slot, Slot):
            return slot.key in self._by_key
        return isinstance(slot, str) and _key(slot) in self._by_key

    def __iter__(self) -> Iterator[Slot]:
        return iter(self.slots)

    def __len__(self) -> int:
        return len(self.slots)

    def __repr__(self) -> str:
        return (f"<Layout {len(self.slots)} slots: "
                f"{', '.join(s.display for s in self.slots)}>")

    def deriving(self, selects: Slot | None = None,
                 relabel: Mapping[Slot, str | None] | None = None) -> "Layout":
        """The same slots in the same order, with the selector or a label moved.

        A pad layout is the instrument layout with the selector on Sound
        instead of Instrument. Written out by hand that is the slot list
        splatted and every start and label copied, and one silently dropped
        is not visible: it happened once while testing something else and
        produced a rack that loads silent.

        A relabel of None CLEARS the label, which is what moving the
        selector needs: the `>` mark belongs to whichever slot steps, so a
        layout that hands the selector to another slot takes it off the
        first.
        """
        out = []
        for s in self.slots:
            s = replace(s, selects=False, number=0)
            if selects is not None and s.key == selects.key:
                s = replace(s, selects=True)
            for slot, text in (relabel or {}).items():
                if slot.key == s.key:
                    s = replace(s, label=text)
            out.append(s)
        return Layout(*out)

    def variation(self, name: str, _at: Mapping[Slot, float] | None = None,
                  **by_key: float) -> Variation:
        """One sound, as a position per slot. Checked against THIS layout.

        `_at` takes slot objects, for values computed in a loop. The kwargs
        form takes slot keys, which is what a hand written sound uses.
        """
        values: dict[Slot, float] = {}
        for slot, pos in (_at or {}).items():
            values[self[slot.display]] = _macro_pos(slot.display, pos)
        for key, pos in by_key.items():
            slot = getattr(self, key)
            values[slot] = _macro_pos(slot.display, pos)
        return Variation(name, values)


@dataclass(frozen=True, slots=True)
class Drive:
    """One slot driving one device parameter, over an optional range."""

    slot: Slot | None
    path: str
    over: Range | None = None


class Engine:
    """How one device answers to a layout. A value, reusable across racks.

    This is the thing the project is about, so it is a thing rather than a
    function that mutates a rack: a profile can be declared once, extended,
    inspected, and used by every rack that wants that engine.
    """

    __slots__ = ("device", "_drives", "_offers", "_sample", "_zone", "_sets")

    def __init__(self, device: str, _drives=(), _offers=None,
                 _sample=None, _zone=None, _sets=()) -> None:
        self.device = device
        self._drives: tuple[Drive, ...] = tuple(_drives)
        self._offers: dict[str, tuple[Drive, ...]] = dict(_offers or {})
        self._sample: Path | None = _sample
        self._zone: tuple[int, int] | None = _zone
        self._sets: tuple[tuple[str, object], ...] = tuple(_sets)

    def _copy(self, **kw) -> "Engine":
        base = dict(_drives=self._drives, _offers=self._offers,
                    _sample=self._sample, _zone=self._zone, _sets=self._sets)
        base.update(kw)
        return Engine(self.device, **base)

    def drives(self, slot: Slot, *paths: str,
               over: Range | None = None) -> "Engine":
        """This slot drives these parameters, over this range.

        Several paths in one call is the Meld case: two synthesis engines
        behind one device, every A path with a B twin, one knob. Binding
        only the A side produced a rack in which macro 3 filtered half the
        sound and left the other half wide open, which passes every
        structural check there is.

        Repeating the call ACCUMULATES. A per-slot call reads as a second
        mapping, which is what that case wants.

        What this is not is a second axis. Both Meld engines move together
        because the layout has one Filter knob; an A knob and a B knob would
        be two slots out of eight, and a Push page has no room for that.
        """
        return self._copy(_drives=self._drives
                          + tuple(Drive(slot, p, over) for p in paths))

    def offers(self, role: str, *paths: str,
               over: Range | None = None) -> "Engine":
        """What this engine can serve when a rack asks for `role`.

        A rack spends its wildcard slot on one role and asks the whole
        family for it. An engine that does not offer it leaves the slot
        EMPTY rather than substituting something else, which is what makes
        the wildcard a decision instead of a leftover.
        """
        offers = dict(self._offers)
        offers[role] = tuple(Drive(None, p, over) for p in paths)
        return self._copy(_offers=offers)

    def sets(self, path: str, value) -> "Engine":
        """Give one of this device's controls a fixed value.

        The third verb, and the one `drives` cannot cover. Drift keeps its
        modulation ROUTING in elements with no `Manual`:
        `<ModulationMatrix_Target1 Value="6" />` says the first row lands on
        LP Frequency. Nothing can drive that, because there is nothing for a
        `KeyMidi` to sit in, so a rack states it (Q16 in `SCHEMA.md`).

        Also takes an ordinary parameter, for the value a rack wants that
        the donor does not happen to carry. A donor is for the parameter
        list and its native ranges, not for anybody's settings, and a value
        inherited by accident is still a value nobody wrote: every Drift
        built here carried the donor's own modulation row until this
        existed.

        Setting the same path twice replaces, unlike `drives`. Two values
        for one control is an edit, not a second one.
        """
        kept = tuple((k, v) for k, v in self._sets if k != path)
        return self._copy(_sets=kept + ((path, value),))

    def sample(self, path: Path | str) -> "Engine":
        """Point this chain's device at a sample file.

        Refuses a path that is not a file. Live loads a missing sample as an
        offline rack, which passes every check this tooling has and makes no
        sound, so it fails at declaration instead.

        Path only. S7 established that Live re-reads the file on load and
        recomputes duration, sample end and the loop ends, so the rest is
        its own bookkeeping and nothing computes a CRC.
        """
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(
                f"{self.device}: no sample at {p}. A missing sample loads as "
                f"an offline rack rather than an error, so it is refused here.")
        return self._copy(_sample=p)

    def zone(self, lo: int, hi: int) -> "Engine":
        """Where on the 0..127 selector this chain answers.

        The default is an even share of the scale among the chains that are
        not pads, which is what a generated rack wants. This is for the rack
        that was not generated: a hand built one whose chains overlap,
        divide unevenly, or leave a dead band.

        Declaring it on ONE chain switches the whole rack to explicit, so a
        half declared rack cannot mix a stated bound with a share computed
        from a different chain count. Bounds only, crossfades collapsed onto
        them - ARCHITECTURE.md section 7.
        """
        return self._copy(_zone=_zone_bounds_checked(self.device, lo, hi))

    def then(self, other: "Engine") -> "Series":
        """Put another device after this one, in the same chain.

        A chain is a signal path, not a slot. The instrument racks never
        needed this because one chain was one synth, but the channel strip
        is the other shape entirely: EQC is an EQ into a compressor into a
        gain, all in series, all reached by one set of macros.
        """
        return Series((self, other))

    def _for(self, role: str | None, wildcard: Slot | None) -> tuple[Drive, ...]:
        """Every drive this engine writes in a rack that asked for `role`."""
        out = self._drives
        if role and wildcard is not None and role in self._offers:
            out = out + tuple(replace(d, slot=wildcard) for d in self._offers[role])
        return out

    def __repr__(self) -> str:
        return f"<Engine {self.device} {len(self._drives)} drives>"


class Series:
    """Several devices in ONE chain, in signal order.

    Built with `Engine.then`, never directly. The zone belongs to the chain
    rather than to any device in it, so it is declared here and an engine
    that already carries one is refused: a chain has one position on the
    selector however many devices sit in it.
    """

    __slots__ = ("engines", "_zone")

    def __init__(self, engines, zone=None) -> None:
        self.engines: tuple[Engine, ...] = tuple(engines)
        placed = [e.device for e in self.engines if e._zone is not None]
        if placed:
            raise ValueError(
                f"zone declared on {', '.join(placed)} inside a series. A "
                f"chain has one zone however many devices it holds; declare "
                f"it on the series.")
        self._zone: tuple[int, int] | None = zone

    def then(self, other: Engine) -> "Series":
        return Series(self.engines + (other,), self._zone)

    def zone(self, lo: int, hi: int) -> "Series":
        """Where on the 0..127 selector this chain answers. See Engine.zone."""
        who = " then ".join(e.device for e in self.engines)
        return Series(self.engines, _zone_bounds_checked(who, lo, hi))

    def __iter__(self) -> Iterator[Engine]:
        return iter(self.engines)

    def __len__(self) -> int:
        return len(self.engines)

    def __repr__(self) -> str:
        return f"<Series {' then '.join(e.device for e in self.engines)}>"


def _zone_bounds_checked(who: str, lo: int, hi: int) -> tuple[int, int]:
    lo, hi = int(lo), int(hi)
    if not 0 <= lo <= hi <= MACRO_MAX:
        raise ValueError(
            f"{who}: zone {lo}..{hi} is not within 0..{MACRO_MAX} with "
            f"Min <= Max. Live's invariant is "
            f"Min <= XfMin <= XfMax <= Max (Q7).")
    return (lo, hi)


class Nested:
    """A rack sitting in a chain, and which outer slots reach into it.

    Nesting is how DR1 is shaped: a drum pad whose chain is an instrument
    rack, whose chain is another instrument rack. Three levels, observed in
    racks/s1_source.adg.

    A macro-to-macro mapping is not a special case. The inner rack's
    `MacroControls.N` is an ordinary parameter node and takes a KeyMidi like
    any other, with Channel 16 at every depth (ARCHITECTURE.md section 5).
    """

    __slots__ = ("rack", "items", "_zone", "chained")

    def __init__(self, rack: "Rack", items=(), zone=None, chained=True) -> None:
        self.rack = rack
        self.items = tuple(items)
        self._zone = zone
        #: False means drive NOTHING, which is not what no items means.
        self.chained = chained

    def zone(self, lo: int, hi: int) -> "Nested":
        """Where on the 0..127 selector this chain answers. See Engine.zone."""
        return Nested(self.rack, self.items,
                      _zone_bounds_checked(self.rack.name, lo, hi),
                      self.chained)


Content = Union[Engine, "Series", "Rack", Nested]


@dataclass(frozen=True, slots=True)
class _Chain:
    """One declared chain, before anything is resolved against a device."""

    name: str
    content: Content
    note: int | None = None
    #: Return name -> send level, linear amplitude. Resolved to positions at
    #: build, because `Index` on a send is positional (S9).
    sends: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _Bound:
    """One mapping to write: which macro, which parameter, over what."""

    macro: int
    path: str
    over: Range | None


@dataclass(frozen=True, slots=True)
class _Placed:
    """One device in a chain, with everything that is written into it."""

    device: str
    bindings: tuple[_Bound, ...]
    settings: tuple[tuple[str, object], ...]
    sample: Path | None


@dataclass(frozen=True, slots=True)
class _Resolved:
    """One chain with the rack's decisions folded in, ready to become XML.

    `devices` is in signal order and holds one entry per device, so a chain
    carrying a single engine is the one-element case rather than a shape of
    its own.
    """

    name: str
    note: int | None
    devices: tuple[_Placed, ...]
    inner: "Rack | None"
    chained: Mapping[int, int]
    zone: tuple[int, int] | None
    sends: Mapping[str, float] = field(default_factory=dict)


class Rack:
    """A rack described by its chains and their layout bindings.

    Assembled by chaining, and every call returns a new Rack, so a sub-rack
    can sit in two racks without one build reaching the other.
    """

    __slots__ = ("name", "layout", "kind", "_chains", "_returns",
                 "_variations", "_labels", "_starts", "_role", "_wildcard",
                 "_library", "_skeleton", "_branch_template",
                 "_wrapper_template", "_return_template", "_send_template",
                 "_send_slots")

    def __init__(self, name: str, layout: Layout, kind: RackKind, chains=(),
                 variations=(), labels=None, starts=None, role=None,
                 wildcard=None, library=None, skeleton=None, returns=(),
                 send_slots=None):
        self.name = name
        self.layout = layout
        self.kind = kind
        self._chains: tuple[_Chain, ...] = tuple(chains)
        self._returns: tuple[_Chain, ...] = tuple(returns)
        #: Return name -> the slot whose macro drives every chain's send.
        self._send_slots: dict[str, Slot] = dict(send_slots or {})
        self._variations: tuple[Variation, ...] = tuple(variations)
        self._labels: dict[str, str] = dict(labels or {})
        self._starts: dict[str, float] = dict(starts or {})
        self._role: str | None = role
        self._wildcard: Slot | None = wildcard
        self._library: Library | None = library
        self._skeleton: Path | None = Path(skeleton) if skeleton else None
        self._branch_template: Element | None = None
        self._wrapper_template: Element | None = None
        self._return_template: Element | None = None
        self._send_template: Element | None = None

    @classmethod
    def instrument(cls, name: str, layout: Layout, **kw) -> "Rack":
        return cls(name, layout, RackKind.INSTRUMENT, **kw)

    @classmethod
    def audio_effect(cls, name: str, layout: Layout, **kw) -> "Rack":
        return cls(name, layout, RackKind.AUDIO_EFFECT, **kw)

    @classmethod
    def midi_effect(cls, name: str, layout: Layout, **kw) -> "Rack":
        return cls(name, layout, RackKind.MIDI_EFFECT, **kw)

    @classmethod
    def drum(cls, name: str, layout: Layout, **kw) -> "Rack":
        return cls(name, layout, RackKind.DRUM, **kw)

    def _with(self, **kw) -> "Rack":
        base = dict(name=self.name, layout=self.layout, kind=self.kind,
                    chains=self._chains, returns=self._returns,
                    send_slots=self._send_slots, variations=self._variations,
                    labels=self._labels, starts=self._starts, role=self._role,
                    wildcard=self._wildcard, library=self._library,
                    skeleton=self._skeleton)
        base.update(kw)
        return Rack(**base)

    # --- assembly ---------------------------------------------------------

    def chain(self, name: str, content: Content,
              sends: Mapping[str, float] | None = None) -> "Rack":
        """Add a chain. Its content is an engine profile or another rack.

        One chain is one engine, or one nested rack. The outer rack does not
        care which, which is why this is one verb.

        `sends` is return name to level, in linear amplitude - a third scale,
        not macros and not zones (S9). A return this rack does not have
        raises at build.
        """
        return self._with(chains=self._chains + (
            _Chain(name, self._checked(content), None, dict(sends or {})),))

    def ret(self, name: str, content: Content) -> "Rack":
        """Add a RETURN chain: an effect every pad can send to.

        A return branch is an `AudioEffectBranchPreset` whatever the parent
        rack is, and it lives in `ReturnBranchPresets`, a sibling of
        `BranchPresets` (S9). Its content is an effect, or a whole rack when
        the return is a selector across several of them.

        Adding one seeds a send on EVERY chain at the silent floor, which is
        what Live does, so a pad that names no level still has the entry.
        """
        return self._with(returns=self._returns + (
            _Chain(name, self._checked_return(content)),))

    def sending(self, slot: Slot, ret: str) -> "Rack":
        """This slot drives EVERY chain's send to that return.

        One knob for how much of the whole kit goes to the reverb, which is
        what a send slot means at kit level. It is one mapping per chain,
        written into each chain's own `SendInfos` entry, because a send
        belongs to a chain and not to the rack.

        Buried once and dug back up. The first check said the knob moved
        nothing, and Q23 concluded a send only takes a value. Live then
        wrote the same mapping by hand - `racks/q23_a.adg` against
        `racks/q23_b.adg`, reproduced here byte for byte - and the knob
        sweeps the send. See `THE_BASEMENT.md` for what the wrong conclusion
        cost.
        """
        return self._with(send_slots={**self._send_slots, ret: slot})

    def _checked_return(self, content: Content) -> Content:
        inner = content.rack if isinstance(content, Nested) else content
        if isinstance(inner, Rack) and inner.kind is not RackKind.AUDIO_EFFECT:
            raise ValueError(
                f"return chain {inner.name!r} is a "
                f"{inner.kind.name.lower()} rack; a return branch is an "
                f"AudioEffectBranchPreset whatever the parent rack is")
        return content

    def pad(self, name: str, note: int, content: Content,
            sends: Mapping[str, float] | None = None) -> "Rack":
        """Add a drum pad: a chain selected by a MIDI note, not a zone.

        A pad is a chain like any other, with one thing swapped. An ordinary
        chain is selected by a zone on the rack's chain selector; a pad is
        selected by `ReceivingNote`, and Live leaves its zone at 0/0/0/0. So
        pads are exempt from zone distribution and nothing else changes.
        """
        if self.kind is not RackKind.DRUM:
            raise ValueError(
                f"pads belong to a drum rack; {self.name!r} is "
                f"{self.kind.name.lower()}. Use chain().")
        if not 0 <= note <= 127:
            raise ValueError(f"{name}: MIDI note must be 0..127, got {note}")
        taken = {c.note: c.name for c in self._chains if c.note is not None}
        if note in taken:
            raise ValueError(
                f"{name}: note {note} already triggers pad {taken[note]!r}. "
                f"Two pads on one note fire together.")
        return self._with(chains=self._chains + (
            _Chain(name, self._checked(content), note, dict(sends or {})),))

    def _checked(self, content: Content) -> Content:
        """Refuse a pairing Live would refuse, here rather than on the drop."""
        inner = content.rack if isinstance(content, Nested) else content
        if isinstance(inner, Rack):
            if inner is self:
                raise ValueError(f"rack {self.name!r} cannot nest itself")
            # An effect rack's chain carries effects of its own kind and
            # nothing else. An instrument rack's chain is the permissive one:
            # it takes an instrument, and effects after it.
            strict = (RackKind.AUDIO_EFFECT, RackKind.MIDI_EFFECT)
            if self.kind in strict and inner.kind is not self.kind:
                what = self.kind.name.lower().replace("_", " ")
                raise ValueError(
                    f"{inner.kind.name.lower()} rack {inner.name!r} cannot go "
                    f"in an {what} chain; Live refuses the preset")
        return content

    def named(self, name: str) -> "Rack":
        """The same rack under another name. Nothing else moves.

        A strip is dropped once per track and the file has to say which
        track it is on, so one declaration becomes eight instances by name
        alone.
        """
        return self._with(name=name)

    def spends(self, slot: Slot, role: str, label: str | None = None) -> "Rack":
        """Spend the wildcard slot on one role, for every chain at once.

        The role is a rack decision and every engine answers it or does not,
        so it is stated here rather than repeated per chain. The knob takes
        the role's name unless a label says otherwise.
        """
        return self._with(role=role, wildcard=slot,
                          labels={**self._labels,
                                  slot.display: label or role.title()})

    def label(self, slot: Slot, text: str) -> "Rack":
        """Rename one knob on the display. The slot itself does not move.

        Position is the contract, the word is local. It is also the only way
        a slot that drives a PAIR can say so on the hardware, and nothing in
        the format marks a selector as stepping rather than sweeping.
        """
        return self._with(labels={**self._labels, slot.display: text})

    def start(self, slot: Slot, pos: float) -> "Rack":
        """Move one knob off the layout's opening position, for this rack."""
        return self._with(starts={**self._starts,
                                  slot.display: _macro_pos(slot.display, pos)})

    def variations(self, *added: Variation) -> "Rack":
        """Add variations. Whether a slot is DRIVEN is checked at build."""
        for v in added:
            if not isinstance(v, Variation):
                raise TypeError(f"expected a Variation, got {type(v).__name__}")
        return self._with(variations=self._variations + added)

    def chaining(self, *items: Union[Slot, SlotPair]) -> Nested:
        """Use this rack as a chain, driven by these outer slots.

        A bare Slot chains to the inner slot of the same name, `Slot.to`
        names an inner slot that differs, and no items at all keeps the
        identity default across every slot the inner rack drives.
        """
        return Nested(self, items)

    def unchained(self) -> Nested:
        """Use this rack as a chain, driven by NOTHING.

        `chaining()` with no arguments means the identity default, every
        slot the inner rack drives from the matching outer knob. That is the
        right default for a sub-rack and the wrong one for a return, whose
        effects answer their own macros and no outer knob at all. The two
        cases are one call apart and read differently on purpose.
        """
        return Nested(self, (), chained=False)

    def using(self, skeleton: Path | str) -> "Rack":
        """Model this rack on a particular file rather than a found donor."""
        return self._with(skeleton=Path(skeleton))

    # --- what this rack answers to ----------------------------------------

    @property
    def engines(self) -> tuple[_Chain, ...]:
        """The chains declared so far. One chain is one engine or one rack."""
        return self._chains

    @property
    def variation_set(self) -> tuple[Variation, ...]:
        """The variations declared so far. A sound is a variation, not a chain."""
        return self._variations

    @property
    def library(self) -> Library:
        return self._library or Library.default()

    def driven_slots(self) -> set[str]:
        """Layout slot keys something in this rack actually answers to.

        A variation may only name these. Live accepts a participation flag
        on an unmapped macro and then does nothing with it on recall, so the
        entry reads as live and is not (SPIKES.md Q5). Silence is the worse
        failure, so this refuses.
        """
        out: set[str] = set()
        for ch in self._chains:
            content = ch.content
            if isinstance(content, Rack):
                content = Nested(content, ())
            if isinstance(content, Nested):
                out |= {s.key for s, _ in self._pairs(content)}
            else:
                engines = (content,) if isinstance(content, Engine) else content
                for engine in engines:
                    out |= {d.slot.key
                            for d in engine._for(self._role, self._wildcard)
                            if d.slot is not None}
        out |= {s.key for s in self._send_slots.values()}
        if self.layout.selector is not None:
            out.add(self.layout.selector.key)
        return out

    def _pairs(self, nested: Nested) -> list[tuple[Slot, Slot]]:
        """Outer slot, inner slot, defaulting to identity on shared slots."""
        if not nested.chained:
            return []
        if nested.items:
            out = []
            for item in nested.items:
                pair = item if isinstance(item, SlotPair) else SlotPair(item, item)
                out.append((self.layout[pair.outer.display],
                            nested.rack.layout[pair.inner.display]))
            return out
        driven = nested.rack.driven_slots()
        return [(s, nested.rack.layout[s.display]) for s in self.layout
                if s.key in driven and s in nested.rack.layout]

    def engine_macro(self, chain: str | int) -> float:
        """The macro position that selects a chain, at its zone's centre.

        Zones are distributed evenly by `_distribute_zones`, so this is
        derived from the same arithmetic rather than restated. Use it to
        make an engine choice part of a variation.

        Pads are excluded: a pad answers to its note, and the selector is
        shared out among the chains that are not pads.
        """
        names = [c.name for c in self._chains if c.note is None]
        if not names:
            raise ValueError(f"rack {self.name!r} has no chains on the selector")
        if isinstance(chain, int):
            i = chain
        else:
            if chain not in names:
                raise KeyError(f"{chain!r} is not a chain here: {names}")
            i = names.index(chain)
        lo, hi = self._zone_bounds(i, len(names))
        return (lo + hi) / 2

    # --- realisation ------------------------------------------------------

    def _resolve(self, which=None) -> list[_Resolved]:
        """Every chain with the rack's role, labels and defaults folded in."""
        out: list[_Resolved] = []
        for ch in (self._chains if which is None else which):
            content = ch.content
            if isinstance(content, Rack):
                content = Nested(content, ())

            if isinstance(content, Nested):
                out.append(_Resolved(
                    name=ch.name, note=ch.note, devices=(),
                    inner=content.rack,
                    chained={o.number: i.number for o, i in self._pairs(content)},
                    zone=content._zone, sends=ch.sends))
            else:
                engines = (content,) if isinstance(content, Engine) else tuple(content)
                zone = content._zone
                out.append(_Resolved(
                    name=ch.name, note=ch.note,
                    devices=tuple(self._place(e) for e in engines),
                    inner=None, chained={}, zone=zone, sends=ch.sends))
        return out

    def _place(self, engine: Engine) -> _Placed:
        """One engine's bindings resolved against this rack's layout."""
        bound = []
        for d in engine._for(self._role, self._wildcard):
            if d.slot is None:
                continue
            bound.append(_Bound(self.layout[d.slot.display].number,
                                d.path, d.over))
        return _Placed(device=engine.device, bindings=tuple(bound),
                       settings=engine._sets, sample=engine._sample)

    def build(self) -> Element:
        """Realise the description as an lxml tree."""
        if not self._chains:
            raise ValueError(f"rack {self.name!r} has no chains")

        chains = self._resolve()
        returns = self._resolve(self._returns)
        root = self._load_skeleton()
        preset = find.preset(root)
        rack_dev = find.rack_device(preset)
        if rack_dev is None:
            raise ValueError("skeleton has no rack device")

        self._name_macros(rack_dev)
        self._write_starts(rack_dev)
        branches = self._make_chains(preset, chains)
        self._distribute_zones(branches, chains)
        self._map_engine_selector(rack_dev)

        made = list(zip(chains, branches))
        if returns:
            made += list(zip(returns, self._make_returns(preset, returns)))
        for chain, branch in made:
            if chain.inner is not None:
                self._apply_nest(chain, branch)
            else:
                self._apply_bindings(chain, branch)

        self._write_sends(branches + self._return_branches(preset),
                          chains + returns, [r.name for r in returns])
        if returns:
            # Live ships this false, which hides the send column in the
            # chain list. A rack that writes sends and does not show them
            # looks like a rack whose sends did not write (S9).
            visible = rack_dev.find("AreSendsVisible")
            if visible is not None:
                visible.set("Value", "true")
        self._write_variations(rack_dev)

        user_name = rack_dev.find("UserName")
        if user_name is not None:
            user_name.set("Value", self.name)

        clone.assert_loadable(root)
        return root

    def save(self, path: Path | str) -> Path:
        root = self.build()
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        io.save(root, out)
        return out

    # --- internals --------------------------------------------------------

    def _load_skeleton(self) -> Element:
        """A real rack of the right kind, with its chains removed.

        Donor-based like everything else: rather than synthesising a
        GroupDevicePreset, take one Live wrote and empty it.

        Emptying it is deterministic per (file, kind), so the result is
        memoised and copied out. DR1 is 87 racks and was re-reading and
        re-emptying the same two files 87 times.
        """
        src = self._skeleton or self._find_skeleton()
        key = (Path(src).resolve(), self.kind.value)
        cached = _SKELETONS.get(key)
        if cached is not None:
            root, wrapper, branch = cached
            self._wrapper_template = (None if wrapper is None
                                      else copy.deepcopy(wrapper))
            self._branch_template = copy.deepcopy(branch)
            return copy.deepcopy(root)

        root = io.load(src)
        preset = self._preset_of_kind(root)
        if preset is None:
            raise ValueError(f"{src} contains no {self.kind.value} to model on")

        # Detach it from any parent, so a nested rack works as a skeleton.
        parent = preset.getparent()
        if parent is not None:
            parent.remove(preset)
            wrapper = etree.Element("Ableton")
            for key, val in root.attrib.items():
                wrapper.set(key, val)
            wrapper.append(preset)
            root = wrapper

        # A nested preset carries the Id it held among its DevicePresets
        # siblings. A top-level one carries no attributes at all, in all 26
        # racks Live saved here, and a stray Id is what makes Live refuse
        # the drop. See THE_BASEMENT.md.
        preset.attrib.pop("Id", None)

        self._strip_inherited_mappings(preset)

        self._wrapper_template = next(
            (copy.deepcopy(w) for w in preset.iter("AbletonDevicePreset")), None)

        container = preset.find("BranchPresets")
        self._branch_template = None
        for child in list(container):
            if self._branch_template is None:
                self._branch_template = _neutralised_sends(copy.deepcopy(child))
            container.remove(child)
        if self._branch_template is None:
            raise ValueError(f"{src} skeleton has no chains to model on")

        _SKELETONS[key] = (copy.deepcopy(root),
                           None if self._wrapper_template is None
                           else copy.deepcopy(self._wrapper_template),
                           copy.deepcopy(self._branch_template))
        return root

    @staticmethod
    def _strip_inherited_mappings(preset: Element) -> int:
        """Drop mappings on the skeleton rack's own macros.

        A skeleton harvested from a nested rack carries KeyMidi blocks on
        its MacroControls and ChainSelector - but those describe how its
        *parent* drove it, and this rack has no parent. Left in place they
        are mappings to a macro that does not exist.

        Only the rack device's own controls are touched. Mappings inside
        chains belong to the chains and are removed with them.
        """
        device = preset.find("Device")
        if device is None:
            return 0
        removed = 0
        for el in device.iter():
            km = el.find("KeyMidi") if isinstance(el.tag, str) else None
            if km is not None:
                el.remove(km)
                removed += 1
        return removed

    def _preset_of_kind(self, root: Element) -> Element | None:
        """A GroupDevicePreset of this rack's kind, top level for preference.

        A rack nested in another rack's chain is usable as a skeleton, but
        only once its Id is dropped - see _load_skeleton. Top level is still
        preferred, because a nested rack also carries its parent's mappings
        on its own macros and those have to be stripped.
        """
        top = find.preset(root)
        candidates = list(find.walk_racks(top)) if top is not None else []
        for gdp in candidates:
            dev = find.rack_device(gdp)
            if dev is not None and dev.tag == self.kind.value and find.branches(gdp):
                return gdp
        return None

    def _find_skeleton(self) -> Path:
        root = Path(__file__).resolve().parent.parent
        named = root / "donors" / f"skeleton_{self.kind.name.lower()}.adg"
        if named.exists():
            return named

        # The search reads every .adg in donors/ and racks/ to find one rack
        # of this kind, and the answer depends only on the kind. Memoised for
        # the same reason the library is: DR1 ran it 9 times for 15 seconds.
        hit = _SKELETON_PATHS.get(self.kind.value)
        if hit is not None:
            return hit

        # A plain donor first, meaning a file named after the single device
        # it carries. Without that preference the skeleton is whichever rack
        # of the right kind sorts first, so adding a file with an unrelated
        # name silently rebuilds every rack - a one-change probe cut from a
        # donor sorts next to it and did exactly that.
        checked: list[str] = []
        fallback: Path | None = None
        for folder in ("donors", "racks"):
            for candidate in sorted((root / folder).glob("*.adg")):
                checked.append(candidate.name)
                try:
                    if self._preset_of_kind(io.load(candidate)) is None:
                        continue
                except Exception:
                    continue
                if candidate.stem in self.library:
                    _SKELETON_PATHS[self.kind.value] = candidate
                    return candidate
                if fallback is None:
                    fallback = candidate
        if fallback is not None:
            _SKELETON_PATHS[self.kind.value] = fallback
            return fallback

        raise FileNotFoundError(
            f"no {self.kind.value} to use as a skeleton.\n"
            f"Save an empty rack of that kind from Live to "
            f"donors/skeleton_{self.kind.name.lower()}.adg.\n"
            f"Checked {len(checked)} file(s).")

    def _name_macros(self, rack_dev: Element) -> None:
        """Write what each knob is CALLED, which is not what it is keyed by."""
        for i, slot in enumerate(self.layout):
            el = rack_dev.find(f"MacroDisplayNames.{i}")
            if el is not None:
                el.set("Value", self._labels.get(slot.display, slot.name))
        vis = rack_dev.find("NumVisibleMacroControls")
        if vis is not None:
            # All 16 slots always exist; this only sets how many show.
            vis.set("Value", "16" if len(self.layout) > 8 else "8")

    def _write_starts(self, rack_dev: Element) -> None:
        """Place the knobs, for the slots this rack actually drives.

        Only driven slots. A start written on a slot no engine binds shows a
        knob parked somewhere meaningful and moving nothing, which reads as
        a mapping that broke. A layout declares starts for all its slots
        because it does not know which rack binds what.
        """
        driven = self.driven_slots()
        for slot in self.layout:
            pos = self._starts.get(slot.display, slot.start)
            if pos is None or slot.key not in driven:
                continue
            macro = find.macro(rack_dev, slot.number)
            if macro is not None:
                params.set_value(macro, pos)

    def _make_chains(self, preset: Element,
                     chains: Sequence[_Resolved]) -> list[Element]:
        assert self._branch_template is not None
        container = preset.find("BranchPresets")
        made: list[Element] = []

        for i, chain in enumerate(chains):
            branch = copy.deepcopy(self._branch_template)
            branch.set("Id", str(i))

            name = branch.find("Name")
            if name is not None:
                name.set("Value", chain.name)

            devices = branch.find("DevicePresets")
            for child in list(devices):
                devices.remove(child)

            if chain.inner is not None:
                devices.append(self._nested_preset(chain.inner))
            else:
                # Two Ids, one rule a level apart: the device is the only
                # member of its holder and the holder is a member of
                # DevicePresets, numbering with the signal chain. A donor
                # also arrives carrying the mappings and the blank int64
                # fields of wherever it was cut from. All of it is in
                # `_device_holder`. See Q9.
                for slot, placed in enumerate(chain.devices):
                    devices.append(self._device_holder(placed, slot))

            if chain.note is not None:
                clone.set_receiving_note(branch, chain.note)

            container.append(branch)
            made.append(branch)
        return made

    def _return_branches(self, preset: Element) -> list[Element]:
        container = preset.find("ReturnBranchPresets")
        return [] if container is None else [
            c for c in container if isinstance(c.tag, str)]

    def _make_returns(self, preset: Element,
                      returns: Sequence[_Resolved]) -> list[Element]:
        """Build the rack's return chains into `ReturnBranchPresets`.

        A return branch is an `AudioEffectBranchPreset` whatever the parent
        rack is, so the template comes from a file that HAS one rather than
        from this rack's own branch template, which is the wrong tag with
        the wrong children (S9).
        """
        container = preset.find("ReturnBranchPresets")
        if container is None:
            container = etree.SubElement(preset, "ReturnBranchPresets")
        for child in list(container):
            container.remove(child)

        made: list[Element] = []
        for i, chain in enumerate(returns):
            branch = copy.deepcopy(self._return_skeleton())
            branch.set("Id", str(i))
            name = branch.find("Name")
            if name is not None:
                name.set("Value", chain.name)

            devices = branch.find("DevicePresets")
            for child in list(devices):
                devices.remove(child)
            if chain.inner is not None:
                devices.append(self._nested_preset(chain.inner))
            else:
                for slot, placed in enumerate(chain.devices):
                    devices.append(self._device_holder(placed, slot))

            container.append(branch)
            made.append(branch)
        return made

    def _write_sends(self, branches: Sequence[Element],
                     chains: Sequence[_Resolved], names: Sequence[str]) -> None:
        """One `AudioBranchSendInfo` per return, on every chain and return.

        Live seeds a send on every existing chain the moment a return is
        added, all at the silent floor, so a chain that names no level still
        carries the entry (S9). `Index` is POSITIONAL, which is why a spec
        names the return and this resolves it here.
        """
        if not names:
            return
        order = {name: i for i, name in enumerate(names)}
        for chain, branch in zip(chains, branches):
            stray = set(chain.sends) - set(order)
            if stray:
                raise ValueError(
                    f"{chain.name}: sends to {sorted(stray)}, which is not a "
                    f"return of {self.name!r}. Returns: {list(names)}")
            infos = next(branch.iter("SendInfos"), None)
            if infos is None:
                raise ValueError(
                    f"{chain.name}: chain mixer has no SendInfos to write to")
            for child in list(infos):
                infos.remove(child)
            for name, index in order.items():
                info = copy.deepcopy(self._send_skeleton())
                info.set("Id", str(index))
                info.find("Index").set("Value", str(index))
                level = chain.sends.get(name, SEND_FLOOR)
                send = info.find("Send")
                params.set_value(send, level)
                slot = self._send_slots.get(name)
                if slot is not None:
                    params.map_to_macro(send, self.layout[slot.display].number)
                infos.append(info)

    def _nested_preset(self, inner: "Rack") -> Element:
        """The inner rack's GroupDevicePreset, ready to sit in a chain.

        A nested preset carries an Id and a top-level one does not - the one
        difference between the two positions, and the reason lifting a
        nested rack out used to produce a file Live refused as a drop. See
        THE_BASEMENT.md.
        """
        preset = find.preset(inner.build())
        parent = preset.getparent()
        if parent is not None:
            parent.remove(preset)
        preset.set("Id", "0")
        return preset

    def _device_holder(self, placed: _Placed, slot: int) -> Element:
        """One device in its `AbletonDevicePreset`, ready to sit in a chain."""
        wrapper = self._device_wrapper()
        holder = wrapper.find("Device")
        for child in list(holder):
            holder.remove(child)
        device = self.library.instance(placed.device)
        device.set("Id", "0")
        clone.strip_macro_mappings(device)
        clone.fill_empty_int64_fields(device)
        # The third thing a donor drags in: a path written in two formats at
        # once, which Live refuses outright. See Q22.
        clone.strip_legacy_path_elements(device)
        # And the fourth: a donor harvested from a `.als` carries the ids the
        # running Set was using for automation. A preset carries zeros.
        clone.zero_session_ids(device)
        # And the fifth: a sample part with no path. A donor names no file,
        # and Live reads the leftover part as a MISSING sample rather than
        # as an empty sampler. A chain that declares one never gets here
        # with a blank path.
        if placed.sample is None:
            clone.strip_unsourced_samples(device)
        holder.append(device)
        wrapper.set("Id", str(slot))
        return wrapper

    def _return_skeleton(self) -> Element:
        """An emptied return branch, from a file that has one.

        `racks/s9_b.adg` is where S9 established the shape, and any rack
        carrying a return serves. Searched rather than named, so a hand
        saved rack in `donors/` takes over the moment one exists.
        """
        if self._return_template is None:
            self._load_return_templates()
        return self._return_template

    def _send_skeleton(self) -> Element:
        if self._send_template is None:
            self._load_return_templates()
        return self._send_template

    def _load_return_templates(self) -> None:
        cached = _RETURN_TEMPLATES.get("branch")
        if cached is None:
            branch, send = self._find_return_templates()
            _RETURN_TEMPLATES["branch"] = branch
            _RETURN_TEMPLATES["send"] = send
        self._return_template = copy.deepcopy(_RETURN_TEMPLATES["branch"])
        self._send_template = copy.deepcopy(_RETURN_TEMPLATES["send"])

    def _find_return_templates(self) -> tuple[Element, Element]:
        root = Path(__file__).resolve().parent.parent
        checked = 0
        for folder in ("donors", "racks"):
            for candidate in sorted((root / folder).glob("*.adg")):
                checked += 1
                try:
                    tree = io.load(candidate)
                except Exception:
                    continue
                branch = next((b for c in tree.iter("ReturnBranchPresets")
                               for b in c if isinstance(b.tag, str)), None)
                send = next(tree.iter("AudioBranchSendInfo"), None)
                if branch is None or send is None:
                    continue
                branch, send = copy.deepcopy(branch), copy.deepcopy(send)
                # A template is for SHAPE. The file it came from is spike
                # evidence, so its send carries whatever that session left -
                # `racks/q23_a.adg` arrived with one at 0.339 and its twin
                # with a macro mapped to it, and both sorted ahead of the
                # file that had been supplying this. Same rule as a donor.
                clone.strip_macro_mappings(branch)
                clone.strip_macro_mappings(send)
                params.set_value(send.find("Send"), SEND_FLOOR)
                return branch, send
        raise FileNotFoundError(
            f"no return chain to model on. Save a rack with one return "
            f"chain into donors/ and re-harvest. Checked {checked} file(s).")

    def _device_wrapper(self) -> Element:
        """An empty AbletonDevicePreset, modelled on the skeleton's.

        Searched across the whole skeleton rather than its first chain,
        because a chain may hold a nested rack instead of a device and then
        has no wrapper to copy - which is exactly the case in the only drum
        rack available as a skeleton.
        """
        if self._wrapper_template is None:
            raise ValueError(
                "skeleton has no AbletonDevicePreset anywhere to model a "
                "device wrapper on")
        return copy.deepcopy(self._wrapper_template)

    @staticmethod
    def _zone_bounds(i: int, n: int) -> tuple[int, int]:
        """Chain i of n, as absolute bounds on the 0..127 selector scale."""
        width = (MACRO_MAX + 1) / n
        lo = round(i * width)
        hi = MACRO_MAX if i == n - 1 else round((i + 1) * width) - 1
        return lo, hi

    def _distribute_zones(self, branches: Sequence[Element],
                          chains: Sequence[_Resolved]) -> None:
        """Spread chain-select zones evenly across 0..127, without overlap.

        Bounds, not start plus length, with fades collapsed onto them - see
        ARCHITECTURE.md section 7.

        Pads are skipped. A pad is selected by its note, and Live leaves
        every pad's zone at 0/0/0/0 - slicing the selector across them would
        express a choice a drum rack does not make.

        Any chain carrying explicit bounds turns the whole rack explicit;
        see Engine.zone.
        """
        pairs = [(b, chains[i]) for i, b in enumerate(branches)
                 if chains[i].note is None]
        explicit = any(c.zone is not None for _, c in pairs)
        n = len(pairs)
        for i, (branch, chain) in enumerate(pairs):
            if explicit:
                if chain.zone is None:
                    raise ValueError(
                        f"{self.name}: chain {chain.name!r} has no zone while "
                        f"another chain declares one. Mixing a stated bound "
                        f"with an even share computed from a different chain "
                        f"count produces overlaps nobody wrote. Give every "
                        f"chain a zone, or none.")
                lo, hi = chain.zone
            else:
                lo, hi = self._zone_bounds(i, n)
            zone = find.zone(branch)
            if zone is None:
                continue
            for tag, val in (("Min", lo), ("CrossfadeMin", lo),
                             ("CrossfadeMax", hi), ("Max", hi)):
                el = zone.find(tag)
                if el is not None:
                    el.set("Value", str(val))

    def _map_engine_selector(self, rack_dev: Element) -> None:
        """The layout's selector slot drives the chain selector.

        Which slot that is comes from the layout, not from a fixed position.
        Hardcoding one meant renaming the slot silently produced a rack that
        loaded and whose first macro moved nothing.
        """
        if self.layout.selector is None:
            return
        selector = find.chain_selector(rack_dev)
        if selector is not None:
            params.map_to_macro(selector, self.layout.selector.number)

    def _write_variations(self, rack_dev: Element) -> None:
        """Realise the variation set in macro space.

        A skeleton carries whatever variations the rack it came from had, so
        this replaces rather than appends. An empty set still clears them:
        inheriting a donor's variations would be silent nonsense.
        """
        driven = self.driven_slots()
        snapshots = []
        for v in self._variations:
            stray = sorted(s.display for s in v.values if s.key not in driven)
            if stray:
                raise ValueError(
                    f"variation {v.name!r} sets {', '.join(stray)}, which no "
                    f"chain drives. Live would load that and move nothing on "
                    f"recall. Driven slots here: "
                    f"{', '.join(sorted(driven)) or 'none'}. Either bind it on "
                    f"an engine or drop it from the variation.")
            snapshots.append(
                (v.name, {s.number: p for s, p in v.values.items()}))
        variations.write(rack_dev, snapshots)

    def _apply_nest(self, chain: _Resolved, branch: Element) -> None:
        """Map this rack's macros onto the nested rack's macros.

        Nothing here knows how deep it is: a KeyMidi on the inner rack's
        MacroControls.N carries Channel 16 whatever the depth, and the
        owning rack is resolved by containment. So the mapping written at
        depth 3 is the same mapping written at depth 1.
        """
        inner_preset = next((d for d in find.devices(branch)
                             if d.tag == "GroupDevicePreset"), None)
        if inner_preset is None:
            raise ValueError(f"{chain.name}: chain holds no nested rack")
        inner_dev = find.rack_device(inner_preset)
        if inner_dev is None:
            raise ValueError(f"{chain.name}: nested rack has no rack device")

        for outer, inner in chain.chained.items():
            target = find.macro(inner_dev, inner)
            if target is None:
                raise ValueError(
                    f"{chain.name}: nested rack has no macro {inner}")
            params.map_to_macro(target, outer)

    def _apply_bindings(self, chain: _Resolved, branch: Element) -> None:
        devices = find.devices(branch)
        if len(devices) != len(chain.devices):
            raise ValueError(
                f"{chain.name}: {len(chain.devices)} device(s) declared, "
                f"{len(devices)} in the branch")
        for placed, device in zip(chain.devices, devices):
            self._apply_to_device(chain, placed, device)

    def _apply_to_device(self, chain: _Resolved, placed: _Placed,
                         device: Element) -> None:
        for path, value in placed.settings:
            target = find.param(device, path)
            if target is not None:
                params.set_value(target, value)
                continue
            target = find.setting(device, path)
            if target is None:
                # Ranked by similarity, not by prefix. These names share
                # long prefixes by design, `ModulationMatrix_Target1` next
                # to `_Source1` and `_Target2`, so a prefix match offers
                # four siblings of the one you meant and not the one itself.
                near = difflib.get_close_matches(
                    path, list(find.settings(device)) + list(find.all_params(device)),
                    n=4, cutoff=0.6)
                hint = f" Did you mean one of {near}?" if near else ""
                raise KeyError(
                    f"{chain.name}: {placed.device} has no parameter or "
                    f"setting {path!r}.{hint}")
            params.set_raw(target, value)

        for bound in placed.bindings:
            param = find.param(device, bound.path)
            if param is None:
                leaf = bound.path.rsplit("/", 1)[-1]
                near = find.search_params(device, leaf[:5])
                hint = f" Did you mean one of {near[:4]}?" if near else ""
                raise KeyError(
                    f"{chain.name}: {placed.device} has no parameter "
                    f"{bound.path!r}.{hint}")
            params.map_to_macro(param, bound.macro)
            if bound.over is not None:
                params.set_range(param, bound.over.lo, bound.over.hi)

        if placed.sample is not None:
            n = samples.retarget(device, placed.sample)
            if not n:
                raise ValueError(
                    f"{chain.name}: {placed.device} has no SampleRef to "
                    f"retarget. The donor for this device carries no sample, "
                    f"so there is nothing for sample() to point at.")

    def __repr__(self) -> str:
        return f"<Rack {self.name!r} {self.kind.name} {len(self._chains)} chains>"
