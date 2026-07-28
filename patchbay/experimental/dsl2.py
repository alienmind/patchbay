"""T9's proposed DSL surface, as a front end over `patchbay.dsl`.

The shape and the argument for it are the last section of `doc/DSL.md`;
the migration is T9 in `doc/TODO.md`. This module is what makes that
proposal a finding rather than a sketch: it declares the same racks through
the proposed syntax and they come out identical, so the migration is known
to be a surface change before anyone starts it.

Every class here is a thin front end and nothing new is written to XML.
That is deliberate and is the whole method. When T9a writes these types
for real inside `patchbay/dsl.py`, this module is deleted rather than
promoted.

Proved against `examples/experimental/patchbayground2.py`: PD1, PD1W, BS1,
LD1 and VA1, plus a drum rack holding a nested pad, every one diffing
identical against what the current syntax builds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Union

from patchbay import dsl as legacy


def _key(display: str) -> str:
    """The Python name for a slot displayed as `display`.

    "Send A" -> send_a. Live's macro name is free text; a Python
    identifier is not, and the two are allowed to differ.
    """
    k = re.sub(r"[^0-9a-zA-Z]+", "_", display).strip("_").lower()
    if not k or k[0].isdigit():
        k = f"slot_{k}"
    return k


@dataclass(frozen=True, slots=True)
class Range:
    """A range a macro drives a parameter across, in the parameter's units.

    `unit` is documentation. Nothing reads it, because nothing can: the
    format does not record one, and the same slot is in Hz on one engine
    and dB on the next. It is here so the constant says which it is.
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

    Everything about a slot in one place. The current DSL spreads the same
    facts across `selector=`, `start={}` and `labels={}`, each keyed by the
    slot name written again as a string.
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
    """An ordered list of slots, and the namespace that names them."""

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

        self._legacy = legacy.Layout(
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

    def __iter__(self):
        return iter(self.slots)

    def __len__(self) -> int:
        return len(self.slots)

    def deriving(self, selects: Slot | None = None,
                 relabel: Mapping[Slot, str] | None = None) -> "Layout":
        """The same slots in the same order, with the selector or a label moved.

        PAD is PATCHBAYGROUND with the selector on Sound instead of
        Instrument. Written out, that is the slot list splatted and every
        dict copied by hand, and a start silently dropped is not visible.
        """
        by_key = {s.key: s for s in self.slots}
        out = []
        for s in self.slots:
            s = replace(s, selects=False, number=0)
            if selects is not None and s.key == selects.key:
                s = replace(s, selects=True)
            for slot, text in (relabel or {}).items():
                if slot.key == s.key:
                    s = replace(s, label=text)
            out.append(s)
        del by_key
        return Layout(*out)

    def variation(self, name: str, _at: Mapping[Slot, float] | None = None,
                  **by_key: float) -> "Variation":
        """One sound, as a position per slot. Checked against THIS layout.

        `_at` takes slot objects, for values computed in a loop. The kwargs
        form takes slot keys, which is what a hand written sound uses.
        """
        values: dict[Slot, float] = {}
        for slot, pos in (_at or {}).items():
            values[self[slot.display]] = float(pos)
        for key, pos in by_key.items():
            values[getattr(self, key)] = float(pos)
        return Variation(name, values)


@dataclass(frozen=True, slots=True)
class Variation:
    name: str
    values: dict[Slot, float]


@dataclass(frozen=True, slots=True)
class Drive:
    """One slot driving one device parameter, over an optional range."""

    slot: Slot
    path: str
    over: Range | None = None


class Engine:
    """How one device answers to a layout. A value, reusable across racks.

    Every builder call returns a NEW Engine, so a profile can be extended
    without disturbing a rack that already holds it.
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
        behind one device, every A path with a B twin, one knob. Repeating
        the call ACCUMULATES, so a slot reaches whatever it was told to.
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
        return self._copy(_sample=Path(path))

    def zone(self, lo: int, hi: int) -> "Engine":
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
        return Nested(self.rack, self.items, (int(lo), int(hi)))


Content = Union[Engine, "Rack", Nested]


@dataclass(frozen=True, slots=True)
class _Chain:
    name: str
    content: Content
    note: int | None = None


class Rack:
    """A rack, assembled by chaining. Each call returns a new Rack."""

    __slots__ = ("name", "layout", "kind", "_chains", "_variations",
                 "_labels", "_starts", "_role", "_wildcard", "_skeleton")

    def __init__(self, name, layout, kind, chains=(), variations=(),
                 labels=None, starts=None, role=None, wildcard=None,
                 skeleton=None):
        self.name = name
        self.layout = layout
        self.kind = kind
        self._chains = tuple(chains)
        self._variations = tuple(variations)
        self._labels: dict[str, str] = dict(labels or {})
        self._starts: dict[str, float] = dict(starts or {})
        self._role: str | None = role
        self._wildcard: Slot | None = wildcard
        self._skeleton = skeleton

    @classmethod
    def instrument(cls, name: str, layout: Layout) -> "Rack":
        return cls(name, layout, legacy.RackKind.INSTRUMENT)

    @classmethod
    def audio_effect(cls, name: str, layout: Layout) -> "Rack":
        return cls(name, layout, legacy.RackKind.AUDIO_EFFECT)

    @classmethod
    def drum(cls, name: str, layout: Layout) -> "Rack":
        return cls(name, layout, legacy.RackKind.DRUM)

    def _with(self, **kw) -> "Rack":
        base = dict(name=self.name, layout=self.layout, kind=self.kind,
                    chains=self._chains, variations=self._variations,
                    labels=self._labels, starts=self._starts, role=self._role,
                    wildcard=self._wildcard, skeleton=self._skeleton)
        base.update(kw)
        return Rack(**base)

    # --- assembly ---------------------------------------------------------

    def chain(self, name: str, content: Content) -> "Rack":
        """Add a chain. Its content is a device profile or another rack."""
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
        return self._with(labels={**self._labels, slot.display: text})

    def start(self, slot: Slot, pos: float) -> "Rack":
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

    def _legacy(self) -> legacy.Rack:
        rack = legacy.Rack(self.name, self.layout._legacy, kind=self.kind,
                           skeleton=self._skeleton, labels=self._labels)
        for slot, pos in self._starts.items():
            rack.start(**{slot: pos})

        for ch in self._chains:
            content = ch.content
            if isinstance(content, Rack):
                content = Nested(content, ())

            if isinstance(content, Nested):
                node = rack.nest(ch.name, content.rack._legacy())
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
                node = rack.engine(ch.name, content.device)
                grouped: dict[str, list] = {}
                for d in content._for(self._role, self._wildcard):
                    spec = (d.path if d.over is None
                            else (d.path, d.over.lo, d.over.hi))
                    grouped.setdefault(d.slot.display, []).append(spec)
                if grouped:
                    node.bind(**grouped)
                if content._sample is not None:
                    node.sample(content._sample)
                if content._zone:
                    node.zone(*content._zone)

            node.note = ch.note
        rack.variations(*[
            legacy.Variation(v.name, **{s.display: p for s, p in v.values.items()})
            for v in self._variations])
        return rack

    def engine_macro(self, chain: str | int) -> float:
        """The macro position that selects a chain, at its zone's centre."""
        names = [c.name for c in self._chains if c.note is None]
        i = chain if isinstance(chain, int) else names.index(chain)
        lo, hi = legacy.Rack._zone_bounds(i, len(names))
        return (lo + hi) / 2

    def build(self):
        return self._legacy().build()

    def save(self, path: Path | str) -> Path:
        return self._legacy().save(path)

    def __repr__(self) -> str:
        return f"<Rack {self.name!r} {self.kind.name} {len(self._chains)} chains>"
