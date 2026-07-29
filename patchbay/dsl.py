"""A declarative way to say what a rack is.

The design follows one line of PATCHBAYGROUND.md: "This consistency is the
actual product, more than any individual rack." The macro layout is
identical across every instrument rack, so the thing worth expressing is
not "build a rack" but "bind this engine's parameters to the standard
layout".

    PUSH = Layout(Slot("Engine", selects=True), Slot("Cutoff"),
                  Slot("Decay"))

    FM = (Engine("Operator")
          .drives(PUSH.cutoff, "Filter/Frequency", over=Range(200, 8000, "Hz"))
          .drives(PUSH.decay, "Filter/Envelope/DecayTime"))

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

  Engine select. Macro 1 drives the chain selector and zones are
  distributed evenly across 0..127, so that knob sweeps engines.

  Variations. A variation is a vector over layout slots, in macro space,
  so it renders through every engine without being written per engine.
  A sound is a variation, not a chain - which is what makes ~692 of them
  tractable.

What this is not: a general graph DSL. It expresses the racks in
PATCHBAYGROUND.md and stops there.

Two surfaces live here during T9. `Slot`, `Range`, `Layout`, `Engine` and
`Rack` are the one above. `LegacyLayout`, `LegacyEngine`, `LegacyNest` and
`LegacyRack` are the previous one, still exported and still what
`examples/patchbayground.py` and `extract.py` are written against; T9d
deletes them. The new types hold the declaration and realise it through
the legacy ones, which is why the output cannot move: `tests/golden.txt`
gates both.
"""

from __future__ import annotations

import copy
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

#: A binding target: a parameter path, optionally with the range the macro
#: should drive it across.
Binding = Union[str, tuple[str, float, float]]

Element = etree._Element


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


class RackKind(str, Enum):
    """Which kind of rack to build.

    This matters more than it looks: an instrument cannot live in an audio
    effect chain, and Live will not load a preset that tries. The kind
    selects both the rack device tag and the branch tag.
    """

    INSTRUMENT = "InstrumentGroupDevice"
    AUDIO_EFFECT = "AudioEffectGroupDevice"
    DRUM = "DrumGroupDevice"

    @property
    def branch_tag(self) -> str:
        return {
            RackKind.INSTRUMENT: "InstrumentBranchPreset",
            RackKind.AUDIO_EFFECT: "AudioEffectBranchPreset",
            RackKind.DRUM: "DrumBranchPreset",
        }[self]


class LegacyLayout:
    """An ordered list of macro slots, shared by every rack that uses it.

    Slot 1 is macro 1. Lookup is case insensitive, so `cutoff` finds the
    slot declared as "Cutoff".

    A slot name is two things that look like one: the KEY a rack binds
    against, and the WORD shown on the hardware. `labels` separates them,
    so the key stays stable while the display says what this rack's knob
    actually does.
    """

    __slots__ = ("slots", "selector", "start", "labels", "_index")

    def __init__(self, *slots: str, selector: str | None = "engine",
                 start: Mapping[str, float] | None = None,
                 labels: Mapping[str, str] | None = None) -> None:
        if len(slots) > MAX_MACROS:
            raise ValueError(f"a rack has {MAX_MACROS} macros; got {len(slots)} slots")
        if len(slots) != len({s.lower() for s in slots}):
            raise ValueError("layout slot names must be unique")
        self.slots: tuple[str, ...] = tuple(slots)
        self._index: dict[str, int] = {s.lower(): i + 1 for i, s in enumerate(slots)}
        # Where each knob sits on a fresh drop. A macro Live has never been
        # told about reads 0, and 0 through a binding is the BOTTOM of the
        # parameter's range: silent volume, shut filter, instant release. So
        # a rack that binds a slot and does not place it loads mute. The
        # position belongs to the layout rather than the rack, for the same
        # reason the slot names do: one knob means one thing everywhere.
        self.start: dict[str, float] = {}
        for slot, pos in (start or {}).items():
            if slot.lower() not in self._index:
                raise KeyError(
                    f"start position for {slot!r}, which is not a slot here. "
                    f"Slots: {', '.join(self.slots)}")
            self.start[slot.lower()] = _macro_pos(slot, pos)
        self.labels: dict[str, str] = {}
        for slot, text in (labels or {}).items():
            if slot.lower() not in self._index:
                raise KeyError(
                    f"label for {slot!r}, which is not a slot here. "
                    f"Slots: {', '.join(self.slots)}")
            self.labels[slot.lower()] = text
        # Which slot drives the chain selector. Named rather than fixed at
        # slot 1, because a drum rack's macro 1 is not a selector. A layout
        # that declares no such slot passes selector=None and gets no
        # selector mapping at all.
        if selector is not None and selector.lower() not in self._index:
            selector = None
        self.selector: str | None = selector

    def macro_of(self, slot: str) -> int:
        """Which macro number serves this slot. 1-based, as in Live's UI."""
        n = self._index.get(slot.lower())
        if n is None:
            raise KeyError(
                f"{slot!r} is not in this layout. Slots: {', '.join(self.slots)}")
        return n

    def __contains__(self, slot: object) -> bool:
        return isinstance(slot, str) and slot.lower() in self._index

    def __len__(self) -> int:
        return len(self.slots)

    def __iter__(self) -> Iterator[str]:
        return iter(self.slots)

    def __repr__(self) -> str:
        return f"<LegacyLayout {len(self.slots)} slots: {', '.join(self.slots)}>"


@dataclass(slots=True)
class BoundParam:
    """One layout slot bound to one parameter, optionally range-scoped."""

    slot: str
    path: str
    lo: float | None = None
    hi: float | None = None

    @property
    def has_range(self) -> bool:
        return self.lo is not None and self.hi is not None


class Variation:
    """One sound, as a position for each layout slot it cares about.

    Values are macro positions, 0..127, because that is the only scale a
    variation has (ARCHITECTURE.md section 11). A slot left out is left
    unset, so recalling this variation does not move that knob.

        Variation("dark plucks", cutoff=40, decay=15, resonance=90)

    The sound family constraint falls out of this rather than being
    enforced: the vector is written in slot terms, every engine binds the
    same slots to its own parameters, and Live applies each engine's own
    range at recall. So variation N is the same musical idea whichever
    engine is selected, and index alignment across engines is structural.
    """

    __slots__ = ("name", "values")

    def __init__(self, name: str, **slots: float) -> None:
        self.name = name
        self.values: dict[str, float] = {k: float(v) for k, v in slots.items()}

    def __repr__(self) -> str:
        shown = ", ".join(f"{k}={v:g}" for k, v in self.values.items())
        return f"<Variation {self.name!r} {shown}>"


@dataclass(slots=True)
class LegacyEngine:
    """One chain, and the bindings from its parameters to layout slots."""

    rack: "LegacyRack"
    name: str
    device_tag: str
    #: Slot -> the parameters it drives. A list because one macro driving
    #: several parameters is normal, not exotic: Meld is two synthesis
    #: engines behind one device and binding only the A side filters half
    #: the sound, which is audible and passes every structural check.
    bindings: dict[str, list[BoundParam]] = field(default_factory=dict)
    #: A drum pad's MIDI note. None on an ordinary chain. See LegacyRack.pad.
    note: int | None = None
    #: Sample file this chain's device plays. None leaves the donor's own.
    sample_path: Path | None = None
    #: Explicit chain-select bounds, or None to take an even share. See zone.
    zone_bounds: tuple[int, int] | None = None

    def bind(self, **slots: Binding | list[Binding]) -> "LegacyEngine":
        """Bind layout slots to this device's parameters.

        Each value is a parameter path, or a (path, lo, hi) tuple to also
        narrow the range the macro drives it across. Live 12.4.3 has no UI
        for that range, so it is only reachable this way.

        A list of either drives several parameters from the one macro:

            e.bind(filter=[("MeldVoice_EngineA_Filter_Frequency", *CUTOFF),
                           ("MeldVoice_EngineB_Filter_Frequency", *CUTOFF)])

        Binding the same slot twice REPLACES rather than accumulates, so a
        repeated `bind` call is an edit and not a silent second mapping.
        """
        for slot, spec in slots.items():
            self.rack.layout.macro_of(slot)  # fail early on a typo
            specs = spec if isinstance(spec, list) else [spec]
            self.bindings[slot] = [self._bound(slot, s) for s in specs]
        return self

    def _bound(self, slot: str, spec: Binding) -> BoundParam:
        if isinstance(spec, str):
            return BoundParam(slot, spec)
        path, lo, hi = spec
        return BoundParam(slot, path, float(lo), float(hi))

    def zone(self, lo: int, hi: int) -> "LegacyEngine":
        """Where on the 0..127 selector this chain answers.

        The default is an even share of the scale among the chains that are
        not pads, which is what a generated rack wants. This is for the rack
        that was not generated: a hand built one whose chains overlap, or
        divide unevenly, or leave a dead band.

        Declaring it on ONE chain switches the whole rack to explicit, so a
        half declared rack cannot mix a stated bound with a share computed
        from a different chain count. Bounds only, crossfades collapsed onto
        them - ARCHITECTURE.md section 7.
        """
        lo, hi = int(lo), int(hi)
        if not 0 <= lo <= hi <= MACRO_MAX:
            raise ValueError(
                f"{self.name}: zone {lo}..{hi} is not within 0..{MACRO_MAX} "
                f"with Min <= Max. Live's invariant is "
                f"Min <= XfMin <= XfMax <= Max (Q7).")
        self.zone_bounds = (lo, hi)
        return self

    def sample(self, path: Path | str) -> "LegacyEngine":
        """Point this chain's device at a sample file.

        Refuses a path that does not exist. Live would load the rack and
        show the sample offline, which is a rack that passes every check
        here and is silently broken, so this fails at declaration instead.
        """
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(
                f"{self.name}: no sample at {p}. A missing sample loads as "
                f"an offline rack rather than an error, so it is refused here.")
        self.sample_path = p
        return self

    def __enter__(self) -> "LegacyEngine":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


@dataclass(slots=True)
class LegacyNest:
    """One chain holding another rack, and the macro-to-macro bindings.

    Nesting is how DR1 is shaped: a drum pad whose chain is an instrument
    rack, whose chain is another instrument rack. Three levels, observed in
    racks/s1_source.adg.

    A macro-to-macro mapping is not a special case. The inner rack's
    MacroControls.N is an ordinary parameter node and takes a KeyMidi like
    any other, with Channel 16 at every depth (ARCHITECTURE.md section 5).
    So the bindings here are outer slot -> inner slot, and the default is
    identity across the shared layout, which is the whole point of one
    layout.
    """

    rack: "LegacyRack"
    name: str
    inner: "LegacyRack"
    bindings: dict[str, str] = field(default_factory=dict)
    #: A drum pad's MIDI note. None on an ordinary chain. See LegacyRack.pad.
    note: int | None = None
    #: Explicit chain-select bounds, or None to take an even share.
    zone_bounds: tuple[int, int] | None = None

    def zone(self, lo: int, hi: int) -> "LegacyNest":
        """Where on the 0..127 selector this chain answers. See LegacyEngine.zone."""
        LegacyEngine.zone(self, lo, hi)
        return self

    def bind(self, **slots: str) -> "LegacyNest":
        """Bind outer layout slots to inner ones. `cutoff="cutoff"`.

        Calling this at all replaces the identity default, so a partial
        binding means only what is named is driven.
        """
        for outer, inner in slots.items():
            self.rack.layout.macro_of(outer)     # fail early on a typo
            self.inner.layout.macro_of(inner)
            self.bindings[outer] = inner
        return self

    def resolved(self) -> dict[str, str]:
        """The bindings to write, defaulting to identity on shared slots."""
        if self.bindings:
            return dict(self.bindings)
        driven = self.inner.driven_slots()
        return {s: s for s in self.rack.layout if s.lower() in driven
                and s in self.inner.layout}

    def __enter__(self) -> "LegacyNest":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


LegacyChain = Union[LegacyEngine, LegacyNest]


class LegacyRack:
    """A rack described by its engines and their layout bindings."""

    def __init__(
        self,
        name: str,
        layout: LegacyLayout,
        kind: RackKind = RackKind.INSTRUMENT,
        library: Library | None = None,
        skeleton: Path | str | None = None,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        self.name = name
        self.layout = layout
        self.kind = kind
        self.library: Library = library or Library.default()
        self.engines: list[LegacyChain] = []
        self.variation_set: list[Variation] = []
        self.starts: dict[str, float] = dict(layout.start)
        self.display: dict[str, str] = dict(layout.labels)
        for slot, text in (labels or {}).items():
            layout.macro_of(slot)               # fail early on a typo
            self.display[slot.lower()] = text
        self._skeleton = Path(skeleton) if skeleton else None
        self._branch_template: Element | None = None
        self._wrapper_template: Element | None = None

    def engine(self, name: str, device_tag: str) -> LegacyEngine:
        """Add an engine. One engine is one chain."""
        if device_tag not in self.library:
            raise KeyError(
                f"no donor for {device_tag!r}. Available: "
                f"{', '.join(self.library)}. Save a rack containing one "
                f"into donors/ and re-harvest.")
        e = LegacyEngine(self, name, device_tag)
        self.engines.append(e)
        return e

    def nest(self, name: str, inner: "LegacyRack") -> LegacyNest:
        """Add a chain holding another rack. One nested rack is one chain.

        An instrument cannot live in an audio effect chain, and Live will
        not load a preset that tries, so the pairing is refused here rather
        than discovered on a drop.
        """
        if inner is self:
            raise ValueError(f"rack {self.name!r} cannot nest itself")
        if self.kind is RackKind.AUDIO_EFFECT and inner.kind is not RackKind.AUDIO_EFFECT:
            raise ValueError(
                f"{inner.kind.name.lower()} rack {inner.name!r} cannot go in an "
                f"audio effect chain; Live refuses the preset")
        n = LegacyNest(self, name, inner)
        self.engines.append(n)
        return n

    def pad(self, name: str, note: int, device: str | None = None,
            rack: "LegacyRack | None" = None) -> LegacyChain:
        """Add a drum pad: one chain, triggered by a MIDI note.

        A pad is a chain like any other, with one thing swapped. An
        ordinary chain is selected by a zone on the rack's chain selector;
        a pad is selected by `ReceivingNote`, and Live leaves its zone at
        0/0/0/0. So pads are exempt from zone distribution and nothing else
        changes.

        Holds either a device or a whole rack, which is how DR1 reaches
        three levels:

            kit.pad("KICK", 36, rack=pad_rack("KICK"))
            kit.pad("RIM", 37, device="OriginalSimpler")
        """
        if self.kind is not RackKind.DRUM:
            raise ValueError(
                f"pads belong to a drum rack; {self.name!r} is "
                f"{self.kind.name.lower()}. Use engine() or nest().")
        if not 0 <= note <= 127:
            raise ValueError(f"{name}: MIDI note must be 0..127, got {note}")
        if (device is None) == (rack is None):
            raise ValueError(f"{name}: pass exactly one of device= or rack=")

        taken = {c.note: c.name for c in self.engines if c.note is not None}
        if note in taken:
            raise ValueError(
                f"{name}: note {note} already triggers pad {taken[note]!r}. "
                f"Two pads on one note fire together.")

        chain = self.nest(name, rack) if rack is not None else self.engine(name, device)
        chain.note = note
        return chain

    def label(self, **slots: str) -> "LegacyRack":
        """Rename this rack's knobs on the display. The slot keys do not move.

        The keyword form of the `labels=` argument, for a rack built up in
        steps rather than declared in one call.
        """
        for slot, text in slots.items():
            self.layout.macro_of(slot)          # fail early on a typo
            self.display[slot.lower()] = text
        return self

    def start(self, **slots: float) -> "LegacyRack":
        """Move this rack's knobs off the layout's opening position.

        The layout sets where a slot opens; this is for the rack that
        needs a different one, and it overrides slot by slot rather than
        replacing the set.
        """
        for slot, pos in slots.items():
            self.layout.macro_of(slot)          # fail early on a typo
            self.starts[slot.lower()] = _macro_pos(slot, pos)
        return self

    # --- variations -------------------------------------------------------

    def variations(self, *added: Variation) -> "LegacyRack":
        """Add variations. Slots are checked against the layout at once.

        Whether the slot is actually *driven* by anything is checked at
        build time, when the bindings are known.
        """
        for v in added:
            if not isinstance(v, Variation):
                raise TypeError(f"expected a Variation, got {type(v).__name__}")
            for slot in v.values:
                self.layout.macro_of(slot)      # fail early on a typo
            self.variation_set.append(v)
        return self

    def driven_slots(self) -> set[str]:
        """Layout slots something in this rack actually answers to.

        A variation may only name these. Live accepts a participation flag
        on an unmapped macro and then does nothing with it on recall, so the
        entry reads as live and is not (SPIKES.md Q5). Silence is the worse
        failure, so this refuses.
        """
        out: set[str] = set()
        for chain in self.engines:
            if isinstance(chain, LegacyNest):
                out |= {s.lower() for s in chain.resolved()}
            else:
                out |= {slot.lower() for slot, bound in chain.bindings.items()
                        if bound}
        if self.layout.selector is not None:
            out.add(self.layout.selector.lower())
        return out

    def engine_macro(self, engine: str | int) -> float:
        """The macro position that selects an engine, at its zone's centre.

        Zones are distributed evenly by `_distribute_zones`, so this is
        derived from the same arithmetic rather than restated. Use it to
        make an engine choice part of a variation.
        """
        n = len(self.engines)
        if not n:
            raise ValueError(f"rack {self.name!r} has no engines")
        if isinstance(engine, int):
            i = engine
        else:
            names = [e.name for e in self.engines]
            if engine not in names:
                raise KeyError(f"{engine!r} is not an engine here: {names}")
            i = names.index(engine)
        lo, hi = self._zone_bounds(i, n)
        return (lo + hi) / 2

    # --- realisation ------------------------------------------------------

    def build(self) -> Element:
        """Realise the description as an lxml tree."""
        if not self.engines:
            raise ValueError(f"rack {self.name!r} has no engines")

        root = self._load_skeleton()
        preset = find.preset(root)
        rack_dev = find.rack_device(preset)
        if rack_dev is None:
            raise ValueError("skeleton has no rack device")

        self._name_macros(rack_dev)
        self._write_starts(rack_dev)
        branches = self._make_chains(preset)
        self._distribute_zones(branches)
        self._map_engine_selector(rack_dev)

        for chain, branch in zip(self.engines, branches):
            if isinstance(chain, LegacyNest):
                self._apply_nest(chain, branch)
            else:
                self._apply_bindings(chain, branch)

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
        """
        src = self._skeleton or self._find_skeleton()
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
                self._branch_template = copy.deepcopy(child)
            container.remove(child)
        if self._branch_template is None:
            raise ValueError(f"{src} skeleton has no chains to model on")
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
                    return candidate
                if fallback is None:
                    fallback = candidate
        if fallback is not None:
            return fallback

        raise FileNotFoundError(
            f"no {self.kind.value} to use as a skeleton.\n"
            f"Save an empty rack of that kind from Live to "
            f"donors/skeleton_{self.kind.name.lower()}.adg.\n"
            f"Checked {len(checked)} file(s).")

    def _name_macros(self, rack_dev: Element) -> None:
        """Write what each knob is CALLED, which is not what it is keyed by.

        The layout's slot name is the default and a label overrides it.
        Position is the contract; the word is local. A kick reading
        "Drive & Snap" where a hat reads "Drive" is the same slot, the same
        chaining and the same muscle memory, and it is the only way a slot
        that drives a pair can say so on the hardware.
        """
        for i, slot in enumerate(self.layout):
            el = rack_dev.find(f"MacroDisplayNames.{i}")
            if el is not None:
                el.set("Value", self.display.get(slot.lower(), slot))
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
        for slot, pos in self.starts.items():
            if slot not in driven:
                continue
            macro = find.macro(rack_dev, self.layout.macro_of(slot))
            if macro is not None:
                params.set_value(macro, pos)

    def _make_chains(self, preset: Element) -> list[Element]:
        assert self._branch_template is not None
        container = preset.find("BranchPresets")
        made: list[Element] = []

        for i, chain in enumerate(self.engines):
            branch = copy.deepcopy(self._branch_template)
            branch.set("Id", str(i))

            name = branch.find("Name")
            if name is not None:
                name.set("Value", chain.name)

            devices = branch.find("DevicePresets")
            for child in list(devices):
                devices.remove(child)

            if isinstance(chain, LegacyNest):
                devices.append(self._nested_preset(chain))
            else:
                wrapper = self._device_wrapper()
                holder = wrapper.find("Device")
                for child in list(holder):
                    holder.remove(child)
                holder.append(self.library.instance(chain.device_tag))
                wrapper.set("Id", "0")
                devices.append(wrapper)

            if chain.note is not None:
                clone.set_receiving_note(branch, chain.note)

            container.append(branch)
            made.append(branch)
        return made

    def _nested_preset(self, nest: LegacyNest) -> Element:
        """The inner rack's GroupDevicePreset, ready to sit in a chain.

        A nested preset carries an Id and a top-level one does not - the
        one difference between the two positions, and the reason lifting a
        nested rack out used to produce a file Live refused as a drop. See
        THE_BASEMENT.md.
        """
        preset = find.preset(nest.inner.build())
        parent = preset.getparent()
        if parent is not None:
            parent.remove(preset)
        preset.set("Id", "0")
        return preset

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

    def _distribute_zones(self, branches: Sequence[Element]) -> None:
        """Spread chain-select zones evenly across 0..127, without overlap.

        Bounds, not start plus length, with fades collapsed onto them - see
        ARCHITECTURE.md section 7.

        Pads are skipped. A pad is selected by its note, and Live leaves
        every pad's zone at 0/0/0/0 - slicing the selector across them
        would express a choice a drum rack does not make.

        Any engine carrying explicit bounds turns the whole rack explicit;
        see LegacyEngine.zone.
        """
        pairs = [(b, self.engines[i]) for i, b in enumerate(branches)
                 if self.engines[i].note is None]
        explicit = any(e.zone_bounds is not None for _, e in pairs)
        n = len(pairs)
        for i, (branch, engine) in enumerate(pairs):
            if explicit:
                if engine.zone_bounds is None:
                    raise ValueError(
                        f"{self.name}: chain {engine.name!r} has no zone while "
                        f"another chain declares one. Mixing a stated bound "
                        f"with an even share computed from a different chain "
                        f"count produces overlaps nobody wrote. Give every "
                        f"chain a zone, or none.")
                lo, hi = engine.zone_bounds
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

        Which slot that is comes from the layout, not from a fixed name.
        Hardcoding one meant renaming the slot silently produced a rack that
        loaded and whose first macro moved nothing.
        """
        if self.layout.selector is None:
            return
        selector = find.chain_selector(rack_dev)
        if selector is not None:
            params.map_to_macro(selector, self.layout.macro_of(self.layout.selector))

    def _write_variations(self, rack_dev: Element) -> None:
        """Realise the variation set in macro space.

        A skeleton carries whatever variations the rack it came from had, so
        this replaces rather than appends. An empty set still clears them:
        inheriting a donor's variations would be silent nonsense.
        """
        driven = self.driven_slots()
        snapshots = []
        for v in self.variation_set:
            stray = sorted(s for s in v.values if s.lower() not in driven)
            if stray:
                raise ValueError(
                    f"variation {v.name!r} sets {', '.join(stray)}, which no "
                    f"engine binds. Live would load that and move nothing on "
                    f"recall. Driven slots here: "
                    f"{', '.join(sorted(driven)) or 'none'}. Either bind it on "
                    f"an engine or drop it from the variation.")
            snapshots.append(
                (v.name, {self.layout.macro_of(s): p for s, p in v.values.items()}))
        variations.write(rack_dev, snapshots)

    def _apply_nest(self, nest: LegacyNest, branch: Element) -> None:
        """Map this rack's macros onto the nested rack's macros.

        Nothing here knows how deep it is: a KeyMidi on the inner rack's
        MacroControls.N carries Channel 16 whatever the depth, and the
        owning rack is resolved by containment. So the mapping written at
        depth 3 is the same mapping written at depth 1.
        """
        inner_preset = next((d for d in find.devices(branch)
                             if d.tag == "GroupDevicePreset"), None)
        if inner_preset is None:
            raise ValueError(f"{nest.name}: chain holds no nested rack")
        inner_dev = find.rack_device(inner_preset)
        if inner_dev is None:
            raise ValueError(f"{nest.name}: nested rack has no rack device")

        for outer, inner in nest.resolved().items():
            target = find.macro(inner_dev, nest.inner.layout.macro_of(inner))
            if target is None:
                raise ValueError(
                    f"{nest.name}: nested rack has no macro for slot {inner!r}")
            params.map_to_macro(target, self.layout.macro_of(outer))

    def _apply_bindings(self, engine: LegacyEngine, branch: Element) -> None:
        devices = find.devices(branch)
        if not devices:
            raise ValueError(f"{engine.name}: chain has no device")
        device = devices[0]

        for bound in [b for group in engine.bindings.values() for b in group]:
            param = find.param(device, bound.path)
            if param is None:
                leaf = bound.path.rsplit("/", 1)[-1]
                near = find.search_params(device, leaf[:5])
                hint = f" Did you mean one of {near[:4]}?" if near else ""
                raise KeyError(
                    f"{engine.name}: {engine.device_tag} has no parameter "
                    f"{bound.path!r}.{hint}")
            params.map_to_macro(param, self.layout.macro_of(bound.slot))
            if bound.has_range:
                assert bound.lo is not None and bound.hi is not None
                params.set_range(param, bound.lo, bound.hi)

        if engine.sample_path is not None:
            n = samples.retarget(device, engine.sample_path)
            if not n:
                raise ValueError(
                    f"{engine.name}: {engine.device_tag} has no SampleRef to "
                    f"retarget. The donor for this device carries no sample, "
                    f"so there is nothing for sample() to point at.")

    def __repr__(self) -> str:
        return f"<LegacyRack {self.name!r} {self.kind.name} {len(self.engines)} engines>"


# --- the T9 surface -------------------------------------------------------
#
# Everything below is the syntax `doc/DSL.md` argues for: a slot carries its
# own start, label and selector flag, an engine profile is a value with
# `drives` and `offers`, `bind` splits into one verb per relation, and a
# range states its unit. The types hold the declaration and hand it to the
# legacy classes above to realise, so the XML written is the same XML, which
# is what `tests/golden.txt` asserts. T9d folds the realisation in here and
# deletes the legacy half.


def _key(display: str) -> str:
    """The Python name for a slot displayed as `display`.

    "Send A" -> send_a. Live's macro name is free text; a Python identifier
    is not, and the two are allowed to differ.
    """
    k = re.sub(r"[^0-9a-zA-Z]+", "_", display).strip("_").lower()
    if not k or k[0].isdigit():
        k = f"slot_{k}"
    return k


@dataclass(frozen=True, slots=True)
class Range:
    """A range a macro drives a parameter across, in the parameter's units.

    `unit` is documentation. Nothing reads it, because nothing can: the
    format records none, and the same slot is in Hz on one engine and dB on
    the next. It is here so the constant says which it is, which is the
    fact Q14 cost a rack to find.
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

    Everything about a slot in one place, so it is named once. The legacy
    surface spreads the same facts across `selector=`, `start={}` and
    `labels={}`, each keyed by the slot name written again as a string.
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

    def to(self, inner: "Slot") -> "SlotPair":
        """This outer slot drives a differently named inner one."""
        return SlotPair(self, inner)

    def __repr__(self) -> str:
        return f"<{self.display} m{self.number}>"


@dataclass(frozen=True, slots=True)
class SlotPair:
    outer: Slot
    inner: Slot


class Layout:
    """An ordered list of slots, and the namespace that names them.

    `PATCHBAYGROUND.filter` is the slot itself, not the string "Filter", so
    a typo raises here rather than at the binding that uses it. `Send A`
    answers to `send_a`: the word on the hardware and the Python name are
    already two things, and this finishes the split.
    """

    def __init__(self, *slots: Slot | str) -> None:
        placed = []
        for i, s in enumerate(slots):
            s = Slot(s) if isinstance(s, str) else s
            placed.append(replace(s, number=i + 1))
        self.slots: tuple[Slot, ...] = tuple(placed)

        self._by_key: dict[str, Slot] = {}
        for s in self.slots:
            if s.key in self._by_key:
                raise ValueError(
                    f"slots {self._by_key[s.key].display!r} and {s.display!r} "
                    f"both mean {s.key!r} in Python; rename one")
            self._by_key[s.key] = s

        selecting = [s for s in self.slots if s.selects]
        if len(selecting) > 1:
            raise ValueError(
                f"{', '.join(s.display for s in selecting)} all claim the "
                f"chain selector; a rack has one")
        self.selector: Slot | None = selecting[0] if selecting else None

        self._legacy = LegacyLayout(
            *[s.display for s in self.slots],
            selector=self.selector.display if self.selector else None,
            start={s.display: s.start for s in self.slots if s.start is not None},
            labels={s.display: s.label for s in self.slots if s.label is not None},
        )

    def __getattr__(self, name: str) -> Slot:
        try:
            return self.__dict__["_by_key"][name]
        except KeyError:
            raise AttributeError(
                f"{name!r} is not a slot here. Slots: "
                f"{', '.join(s.key for s in self.slots)}") from None

    def __getitem__(self, name: str) -> Slot:
        return getattr(self, _key(name))

    def __iter__(self) -> Iterator[Slot]:
        return iter(self.slots)

    def __len__(self) -> int:
        return len(self.slots)

    def __repr__(self) -> str:
        return (f"<Layout {len(self.slots)} slots: "
                f"{', '.join(s.display for s in self.slots)}>")

    def deriving(self, selects: Slot | None = None,
                 relabel: Mapping[Slot, str] | None = None) -> "Layout":
        """The same slots in the same order, with the selector or a label moved.

        PAD is PATCHBAYGROUND with the selector on Sound instead of
        Instrument. Written out by hand that is the slot list splatted and
        every dict copied, and a start silently dropped is not visible: it
        happened while testing something else and produced a rack that
        loads silent.
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
        values: dict[str, float] = {}
        for slot, pos in (_at or {}).items():
            values[self[slot.display].display] = float(pos)
        for key, pos in by_key.items():
            values[getattr(self, key).display] = float(pos)
        return Variation(name, **values)


@dataclass(frozen=True, slots=True)
class Drive:
    """One slot driving one device parameter, over an optional range."""

    slot: Slot | None
    path: str
    over: Range | None = None


class Engine:
    """How one device answers to a layout. A value, reusable across racks.

    This is the thing the project is about and the legacy surface had no
    value for: `examples/patchbayground.py` expresses it as five functions
    that take a rack, mutate it and return it. Every builder call here
    returns a NEW Engine, so a profile can be extended without disturbing a
    rack that already holds it.
    """

    __slots__ = ("device", "_drives", "_offers", "_sample", "_zone")

    def __init__(self, device: str, _drives=(), _offers=None,
                 _sample=None, _zone=None) -> None:
        self.device = device
        self._drives: tuple[Drive, ...] = tuple(_drives)
        self._offers: dict[str, tuple[Drive, ...]] = dict(_offers or {})
        self._sample: Path | None = _sample
        self._zone: tuple[int, int] | None = _zone

    def _copy(self, **kw) -> "Engine":
        base = dict(_drives=self._drives, _offers=self._offers,
                    _sample=self._sample, _zone=self._zone)
        base.update(kw)
        return Engine(self.device, **base)

    def drives(self, slot: Slot, *paths: str,
               over: Range | None = None) -> "Engine":
        """This slot drives these parameters, over this range.

        Several paths in one call is the Meld case: two synthesis engines
        behind one device, every A path with a B twin, one knob.

        Repeating the call ACCUMULATES, where a second legacy `bind` of the
        same slot replaced it. A per-slot fluent call reads as a second
        mapping, so the reading and the behaviour agree instead of a
        docstring having to say which one won.
        """
        added = tuple(Drive(slot, p, over) for p in paths)
        return self._copy(_drives=self._drives + added)

    def offers(self, role: str, *paths: str,
               over: Range | None = None) -> "Engine":
        """What this engine can serve when a rack asks for `role`.

        A rack spends its wildcard slot on one role and asks the whole
        family for it. An engine that does not offer it leaves the slot
        empty rather than substituting something else.
        """
        offers = dict(self._offers)
        offers[role] = tuple(Drive(None, p, over) for p in paths)
        return self._copy(_offers=offers)

    def sample(self, path: Path | str) -> "Engine":
        """Point this chain's device at a sample file. See LegacyEngine.sample."""
        return self._copy(_sample=Path(path))

    def zone(self, lo: int, hi: int) -> "Engine":
        """Where on the 0..127 selector this chain answers. See LegacyEngine.zone."""
        return self._copy(_zone=(int(lo), int(hi)))

    def _for(self, role: str | None, wildcard: Slot | None) -> tuple[Drive, ...]:
        """Every drive this engine writes in a rack that asked for `role`."""
        out = self._drives
        if role and wildcard is not None and role in self._offers:
            out = out + tuple(replace(d, slot=wildcard) for d in self._offers[role])
        return out

    def __repr__(self) -> str:
        return f"<Engine {self.device} {len(self._drives)} drives>"


class Nested:
    """A rack sitting in a chain, and which outer slots reach into it."""

    __slots__ = ("rack", "items", "_zone")

    def __init__(self, rack: "Rack", items=(), zone=None) -> None:
        self.rack = rack
        self.items = tuple(items)
        self._zone = zone

    def zone(self, lo: int, hi: int) -> "Nested":
        """Where on the 0..127 selector this chain answers. See LegacyEngine.zone."""
        return Nested(self.rack, self.items, (int(lo), int(hi)))


Content = Union[Engine, "Rack", Nested]


@dataclass(frozen=True, slots=True)
class _Chain:
    name: str
    content: Content
    note: int | None = None


class Rack:
    """A rack, assembled by chaining. Each call returns a new Rack.

    A profile or a sub-rack can therefore sit in two racks without one
    build reaching the other.
    """

    __slots__ = ("name", "layout", "kind", "_chains", "_variations",
                 "_labels", "_starts", "_role", "_wildcard", "_library")

    def __init__(self, name, layout, kind, chains=(), variations=(),
                 labels=None, starts=None, role=None, wildcard=None,
                 library=None):
        self.name = name
        self.layout = layout
        self.kind = kind
        self._chains: tuple[_Chain, ...] = tuple(chains)
        self._variations: tuple[Variation, ...] = tuple(variations)
        self._labels: dict[str, str] = dict(labels or {})
        self._starts: dict[str, float] = dict(starts or {})
        self._role: str | None = role
        self._wildcard: Slot | None = wildcard
        self._library: Library | None = library

    @classmethod
    def instrument(cls, name: str, layout: Layout,
                   library: Library | None = None) -> "Rack":
        return cls(name, layout, RackKind.INSTRUMENT, library=library)

    @classmethod
    def audio_effect(cls, name: str, layout: Layout,
                     library: Library | None = None) -> "Rack":
        return cls(name, layout, RackKind.AUDIO_EFFECT, library=library)

    @classmethod
    def drum(cls, name: str, layout: Layout,
             library: Library | None = None) -> "Rack":
        return cls(name, layout, RackKind.DRUM, library=library)

    def _with(self, **kw) -> "Rack":
        base = dict(name=self.name, layout=self.layout, kind=self.kind,
                    chains=self._chains, variations=self._variations,
                    labels=self._labels, starts=self._starts, role=self._role,
                    wildcard=self._wildcard, library=self._library)
        base.update(kw)
        return Rack(**base)

    # --- assembly ---------------------------------------------------------

    def chain(self, name: str, content: Content) -> "Rack":
        """Add a chain. Its content is an engine profile or another rack.

        One verb per relation: nesting cannot be misread as parameter
        binding, and this takes either because the outer rack does not care
        which it got.
        """
        return self._with(chains=self._chains + (_Chain(name, content),))

    def pad(self, name: str, note: int, content: Content) -> "Rack":
        """Add a drum pad: a chain selected by a MIDI note, not a zone."""
        return self._with(chains=self._chains + (_Chain(name, content, note),))

    def spends(self, slot: Slot, role: str, label: str | None = None) -> "Rack":
        """Spend the wildcard slot on one role, for every chain at once.

        The role is a rack decision and every engine answers it or does
        not, so it is stated here rather than repeated per chain. The knob
        takes the role's name unless a label says otherwise.
        """
        return self._with(role=role, wildcard=slot,
                          labels={**self._labels,
                                  slot.display: label or role.title()})

    def label(self, slot: Slot, text: str) -> "Rack":
        """Rename one knob on the display. The slot itself does not move."""
        return self._with(labels={**self._labels, slot.display: text})

    def start(self, slot: Slot, pos: float) -> "Rack":
        """Move one knob off the layout's opening position, for this rack."""
        return self._with(starts={**self._starts, slot.display: float(pos)})

    def variations(self, *added: Variation) -> "Rack":
        return self._with(variations=self._variations + added)

    def chaining(self, *items: Union[Slot, SlotPair]) -> Nested:
        """Use this rack as a chain, driven by these outer slots.

        A bare Slot chains to the inner slot of the same name. `Slot.to`
        names an inner slot that differs. No items at all keeps the
        identity default across every slot the inner rack drives.
        """
        return Nested(self, items)

    # --- realisation ------------------------------------------------------

    @property
    def engines(self) -> tuple[_Chain, ...]:
        """The chains declared so far, under the name `compile.report` reads."""
        return self._chains

    def _realise(self) -> LegacyRack:
        """This declaration as a LegacyRack, which owns the XML.

        T9d moves that machinery here. Until it does, the two surfaces
        write the same bytes by construction rather than by agreement, and
        `tests/golden.txt` is what says so.
        """
        rack = LegacyRack(self.name, self.layout._legacy, kind=self.kind,
                          library=self._library, labels=self._labels)
        rack.start(**self._starts)

        for ch in self._chains:
            content = ch.content
            if isinstance(content, Rack):
                content = Nested(content, ())

            if isinstance(content, Nested):
                inner = content.rack._realise()
                node = (rack.pad(ch.name, ch.note, rack=inner)
                        if ch.note is not None else rack.nest(ch.name, inner))
                pairs = {}
                for item in content.items:
                    if isinstance(item, SlotPair):
                        pairs[item.outer.display] = item.inner.display
                    else:
                        pairs[item.display] = item.display
                if pairs:
                    node.bind(**pairs)
                if content._zone:
                    node.zone(*content._zone)
            else:
                node = (rack.pad(ch.name, ch.note, device=content.device)
                        if ch.note is not None
                        else rack.engine(ch.name, content.device))
                grouped: dict[str, list[Binding]] = {}
                for d in content._for(self._role, self._wildcard):
                    assert d.slot is not None
                    spec: Binding = (d.path if d.over is None
                                     else (d.path, d.over.lo, d.over.hi))
                    grouped.setdefault(d.slot.display, []).append(spec)
                if grouped:
                    node.bind(**grouped)
                if content._sample is not None:
                    node.sample(content._sample)
                if content._zone:
                    node.zone(*content._zone)

        rack.variations(*self._variations)
        return rack

    def engine_macro(self, chain: str | int) -> float:
        """The macro position that selects a chain, at its zone's centre.

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
        lo, hi = LegacyRack._zone_bounds(i, len(names))
        return (lo + hi) / 2

    def driven_slots(self) -> set[str]:
        return self._realise().driven_slots()

    def build(self) -> Element:
        return self._realise().build()

    def save(self, path: Path | str) -> Path:
        return self._realise().save(path)

    def __repr__(self) -> str:
        return f"<Rack {self.name!r} {self.kind.name} {len(self._chains)} chains>"
