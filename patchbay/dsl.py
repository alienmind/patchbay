"""A declarative way to say what a rack is.

The design follows one line of PATCHBAYGROUND.md: "This consistency is the
actual product, more than any individual rack." The macro grammar is
identical across every instrument rack, so the thing worth expressing is
not "build a rack" but "bind this engine's parameters to the standard
grammar".

    PUSH = Grammar("Engine", "Cutoff", "Resonance", "Decay",
                   "Drive", "Movement", "Space", "Character")

    rack = Rack("PD1", PUSH, kind=RackKind.INSTRUMENT)

    with rack.engine("FM", "Operator") as e:
        e.bind(cutoff=("Filter/Frequency", 200, 8000),
               decay="Filter/Envelope/DecayTime")

    with rack.engine("Sample", "OriginalSimpler") as e:
        e.bind(cutoff=("Filter/Slot/Value/SimplerFilter/Freq", 200, 8000),
               decay="Filter/Slot/Value/SimplerFilter/Envelope/DecayTime")

    rack.variations(Variation("dark", cutoff=30, decay=110))

    rack.save("build/PD1.adg")

Three things fall out of that shape rather than being programmed:

  The sound family constraint. Every engine binds its own parameters to
  the same grammar slots, so one macro moves the same musical idea through
  every synthesis method. Variation index N means the same thing across
  engines because the grammar is what they share.

  Engine select. Macro 1 drives the chain selector and zones are
  distributed evenly across 0..127, so that knob sweeps engines.

  Variations. A variation is a vector over grammar slots, in macro space,
  so it renders through every engine without being written per engine.
  A sound is a variation, not a chain - which is what makes ~692 of them
  tractable.

What this is not: a general graph DSL. It expresses the racks in
PATCHBAYGROUND.md and stops there.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator, Mapping, Sequence, Union

from lxml import etree

from . import clone, find, io, params, variations
from .library import Library

MACRO_MAX: int = 127
MAX_MACROS: int = 16

#: A binding target: a parameter path, optionally with the range the macro
#: should drive it across.
Binding = Union[str, tuple[str, float, float]]

Element = etree._Element


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


class Grammar:
    """An ordered list of macro slots, shared by every rack that uses it.

    Slot 1 is macro 1. Lookup is case insensitive, so `cutoff` finds the
    slot declared as "Cutoff".
    """

    __slots__ = ("slots", "_index")

    def __init__(self, *slots: str) -> None:
        if len(slots) > MAX_MACROS:
            raise ValueError(f"a rack has {MAX_MACROS} macros; got {len(slots)} slots")
        if len(slots) != len({s.lower() for s in slots}):
            raise ValueError("grammar slot names must be unique")
        self.slots: tuple[str, ...] = tuple(slots)
        self._index: dict[str, int] = {s.lower(): i + 1 for i, s in enumerate(slots)}

    def macro_of(self, slot: str) -> int:
        """Which macro number serves this slot. 1-based, as in Live's UI."""
        n = self._index.get(slot.lower())
        if n is None:
            raise KeyError(
                f"{slot!r} is not in this grammar. Slots: {', '.join(self.slots)}")
        return n

    def __contains__(self, slot: object) -> bool:
        return isinstance(slot, str) and slot.lower() in self._index

    def __len__(self) -> int:
        return len(self.slots)

    def __iter__(self) -> Iterator[str]:
        return iter(self.slots)

    def __repr__(self) -> str:
        return f"<Grammar {len(self.slots)} slots: {', '.join(self.slots)}>"


@dataclass(slots=True)
class BoundParam:
    """One grammar slot bound to one parameter, optionally range-scoped."""

    slot: str
    path: str
    lo: float | None = None
    hi: float | None = None

    @property
    def has_range(self) -> bool:
        return self.lo is not None and self.hi is not None


class Variation:
    """One sound, as a position for each grammar slot it cares about.

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
class Engine:
    """One chain, and the bindings from its parameters to grammar slots."""

    rack: "Rack"
    name: str
    device_tag: str
    bindings: dict[str, BoundParam] = field(default_factory=dict)

    def bind(self, **slots: Binding) -> "Engine":
        """Bind grammar slots to this device's parameters.

        Each value is a parameter path, or a (path, lo, hi) tuple to also
        narrow the range the macro drives it across. Live 12.4.3 has no UI
        for that range, so it is only reachable this way.
        """
        for slot, spec in slots.items():
            self.rack.grammar.macro_of(slot)  # fail early on a typo
            if isinstance(spec, str):
                self.bindings[slot] = BoundParam(slot, spec)
            else:
                path, lo, hi = spec
                self.bindings[slot] = BoundParam(slot, path, float(lo), float(hi))
        return self

    def __enter__(self) -> "Engine":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


class Rack:
    """A rack described by its engines and their grammar bindings."""

    def __init__(
        self,
        name: str,
        grammar: Grammar,
        kind: RackKind = RackKind.INSTRUMENT,
        library: Library | None = None,
        skeleton: Path | str | None = None,
    ) -> None:
        self.name = name
        self.grammar = grammar
        self.kind = kind
        self.library: Library = library or Library.default()
        self.engines: list[Engine] = []
        self.variation_set: list[Variation] = []
        self._skeleton = Path(skeleton) if skeleton else None
        self._branch_template: Element | None = None

    def engine(self, name: str, device_tag: str) -> Engine:
        """Add an engine. One engine is one chain."""
        if device_tag not in self.library:
            raise KeyError(
                f"no donor for {device_tag!r}. Available: "
                f"{', '.join(self.library)}. Save a rack containing one "
                f"into donors/ and re-harvest.")
        e = Engine(self, name, device_tag)
        self.engines.append(e)
        return e

    # --- variations -------------------------------------------------------

    def variations(self, *added: Variation) -> "Rack":
        """Add variations. Slots are checked against the grammar at once.

        Whether the slot is actually *driven* by anything is checked at
        build time, when the bindings are known.
        """
        for v in added:
            if not isinstance(v, Variation):
                raise TypeError(f"expected a Variation, got {type(v).__name__}")
            for slot in v.values:
                self.grammar.macro_of(slot)      # fail early on a typo
            self.variation_set.append(v)
        return self

    def driven_slots(self) -> set[str]:
        """Grammar slots something in this rack actually answers to.

        A variation may only name these. Live accepts a participation flag
        on an unmapped macro and then does nothing with it on recall, so the
        entry reads as live and is not (SPIKES.md Q5). Silence is the worse
        failure, so this refuses.
        """
        out = {b.slot.lower() for e in self.engines for b in e.bindings.values()}
        if "engine" in self.grammar:
            out.add("engine")
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
        branches = self._make_chains(preset)
        self._distribute_zones(branches)
        self._map_engine_selector(rack_dev)

        for engine, branch in zip(self.engines, branches):
            self._apply_bindings(engine, branch)

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

        self._strip_inherited_mappings(preset)

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
        """The TOP-LEVEL GroupDevicePreset, if it matches this rack kind.

        Top level only, deliberately. A rack nested inside another rack's
        chain cannot be lifted out and used as a standalone preset: Live
        refuses to even accept the drop. Cause unknown, recorded as an open
        question in doc/SPIKES.md.

        Silently falling back to a nested rack is how this produced files
        that looked fine, passed every check, and could not be loaded.
        """
        for gdp in root:
            if isinstance(gdp.tag, str) and gdp.tag == "GroupDevicePreset":
                dev = find.rack_device(gdp)
                if dev is not None and dev.tag == self.kind.value and find.branches(gdp):
                    return gdp
        return None

    def _find_skeleton(self) -> Path:
        root = Path(__file__).resolve().parent.parent
        named = root / "donors" / f"skeleton_{self.kind.name.lower()}.adg"
        if named.exists():
            return named

        checked: list[str] = []
        for folder in ("donors", "racks"):
            for candidate in sorted((root / folder).glob("*.adg")):
                checked.append(candidate.name)
                try:
                    if self._preset_of_kind(io.load(candidate)) is not None:
                        return candidate
                except Exception:
                    continue

        raise FileNotFoundError(
            f"no top-level {self.kind.value} to use as a skeleton.\n"
            f"Save an empty rack of that kind from Live to "
            f"donors/skeleton_{self.kind.name.lower()}.adg.\n"
            f"Checked {len(checked)} file(s). Racks nested inside another "
            f"rack are not usable as skeletons: Live rejects the result.")

    def _name_macros(self, rack_dev: Element) -> None:
        """Write the grammar's slot names onto the macros."""
        for i, slot in enumerate(self.grammar):
            el = rack_dev.find(f"MacroDisplayNames.{i}")
            if el is not None:
                el.set("Value", slot)
        vis = rack_dev.find("NumVisibleMacroControls")
        if vis is not None:
            # All 16 slots always exist; this only sets how many show.
            vis.set("Value", "16" if len(self.grammar) > 8 else "8")

    def _make_chains(self, preset: Element) -> list[Element]:
        assert self._branch_template is not None
        container = preset.find("BranchPresets")
        made: list[Element] = []

        for i, engine in enumerate(self.engines):
            branch = copy.deepcopy(self._branch_template)
            branch.set("Id", str(i))

            name = branch.find("Name")
            if name is not None:
                name.set("Value", engine.name)

            devices = branch.find("DevicePresets")
            wrapper = self._device_wrapper()
            for child in list(devices):
                devices.remove(child)

            holder = wrapper.find("Device")
            for child in list(holder):
                holder.remove(child)
            holder.append(self.library.instance(engine.device_tag))
            wrapper.set("Id", "0")
            devices.append(wrapper)

            container.append(branch)
            made.append(branch)
        return made

    def _device_wrapper(self) -> Element:
        """An empty AbletonDevicePreset, modelled on the skeleton's."""
        assert self._branch_template is not None
        presets = self._branch_template.find("DevicePresets")
        for child in presets:
            if child.tag == "AbletonDevicePreset":
                return copy.deepcopy(child)
        raise ValueError("skeleton chain has no AbletonDevicePreset to model on")

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
        """
        n = len(branches)
        for i, branch in enumerate(branches):
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
        """Macro 1 drives the chain selector, if the grammar declares it."""
        if "engine" not in self.grammar:
            return
        selector = find.chain_selector(rack_dev)
        if selector is not None:
            params.map_to_macro(selector, self.grammar.macro_of("engine"))

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
                (v.name, {self.grammar.macro_of(s): p for s, p in v.values.items()}))
        variations.write(rack_dev, snapshots)

    def _apply_bindings(self, engine: Engine, branch: Element) -> None:
        devices = find.devices(branch)
        if not devices:
            raise ValueError(f"{engine.name}: chain has no device")
        device = devices[0]

        for bound in engine.bindings.values():
            param = find.param(device, bound.path)
            if param is None:
                leaf = bound.path.rsplit("/", 1)[-1]
                near = find.search_params(device, leaf[:5])
                hint = f" Did you mean one of {near[:4]}?" if near else ""
                raise KeyError(
                    f"{engine.name}: {engine.device_tag} has no parameter "
                    f"{bound.path!r}.{hint}")
            params.map_to_macro(param, self.grammar.macro_of(bound.slot))
            if bound.has_range:
                assert bound.lo is not None and bound.hi is not None
                params.set_range(param, bound.lo, bound.hi)

    def __repr__(self) -> str:
        return f"<Rack {self.name!r} {self.kind.name} {len(self.engines)} engines>"
