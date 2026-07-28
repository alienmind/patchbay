"""Read a saved rack back out as DSL source. `patchbay build` in reverse.

The point is to turn racks built by hand in Live into declarations, so a
library of real racks becomes input rather than something to retype.

What this recovers is STRUCTURE: chains, device types, which parameter each
macro drives, chain zones, nesting, variations. What it cannot recover is
INTENT. It can see that macro 3 drives `Filter/Frequency` on every chain;
it cannot know that the author calls slot 3 `Filter`. So the emitted
layout is positional by default, `Layout("Macro 1", ...)`, which is
honest and compiles. Renaming is a human edit.

Guessing a slot name from a parameter path would be inventing intent, which
CLAUDE.md rule 1 forbids for exactly the reason that makes it tempting: the
guess is usually right, and silently wrong the rest of the time.
"""

from __future__ import annotations

from pathlib import Path

from . import find, io, mappings, params as P, samples, variations

KIND_OF = {
    "InstrumentGroupDevice": "RackKind.INSTRUMENT",
    "AudioEffectGroupDevice": "RackKind.AUDIO_EFFECT",
    "MidiEffectGroupDevice": "RackKind.MIDI_EFFECT",
    "DrumGroupDevice": "RackKind.DRUM",
}


def _ident(name: str, used: set[str]) -> str:
    """A python identifier for a rack name, unique within one emission."""
    out = "".join(c if c.isalnum() else "_" for c in name).strip("_").lower()
    out = out or "rack"
    if out[0].isdigit():
        out = "r" + out
    base, n = out, 2
    while out in used:
        out, n = f"{base}{n}", n + 1
    used.add(out)
    return out


def _own_mappings(preset_el, rack_dev):
    """Mappings belonging to THIS rack, not to a rack nested inside it.

    Scope matters twice here. A rack's `Device` and its `BranchPresets` are
    SIBLINGS, so searching `rack_dev` alone finds only the chain selector
    and misses every binding on every chain. Searching the whole preset
    finds too much, because a nested rack's mappings live in there too. So
    search the preset and keep what this rack owns.
    """
    for m in mappings.find(preset_el):
        if not m["macro"]:
            continue
        if mappings._owning_rack(m["element"].getparent()) is rack_dev:
            yield m


def _macro_count(preset_el, rack_dev) -> int:
    """How many macros this rack uses, from its highest owned mapping."""
    highest = max((m["macro"] for m in _own_mappings(preset_el, rack_dev)),
                  default=0)
    return max(highest, 1)


def _range_literal(param_el) -> tuple[str, str] | None:
    """The mapping range, as the strings the file holds.

    Strings rather than floats: `0.24043628000069334` survives a round trip
    through `float` only by luck of repr, and a range that shifts in the
    last digit is a diff that has to be explained every time.
    """
    r = param_el.find("MidiControllerRange")
    if r is None:
        return None
    lo, hi = r.find("Min"), r.find("Max")
    if lo is None or hi is None:
        return None
    return (lo.get("Value"), hi.get("Value"))


def _bindings_for(branch, device, rack_dev) -> dict[int, list[str | tuple]]:
    """Macro number -> what it drives, on one chain's device.

    A list, because one macro driving several parameters is ordinary: Meld
    binds each slot to both its A and B engines. Keeping only the last would
    emit a rack that filters half the sound.

    The range is emitted ALWAYS, never only where it looks non-default.
    Nothing in the file distinguishes a range the author set from one the
    donor came with, and the rebuild takes its unranged values from whatever
    donor is indexed that day. Writing it out is what makes the emitted
    source say the same thing as the rack, independently of donors.
    """
    out: dict[int, list[str | tuple]] = {}
    for m in mappings.find(device):
        if not m["macro"]:
            continue
        param = m["element"].getparent()
        path = find.param_path(param, device)
        if not path:
            continue
        rng = _range_literal(param)
        out.setdefault(m["macro"], []).append(
            path if rng is None else (path, rng[0], rng[1]))
    return out


def _fmt_binding(spec) -> str:
    """A binding as source. Range numbers go in bare, not as strings."""
    if isinstance(spec, tuple):
        return f"({spec[0]!r}, {spec[1]}, {spec[2]})"
    return repr(spec)


def _sample_targets(device) -> list[str]:
    """One path per sample: the LIVE FileRef, not the provenance one.

    `samples.file_refs` yields both, and the two disagree by design - the
    OriginalFileRef records where the audio came from before it was moved
    into the Library. Emitting that one produces source that points at a
    file the rack does not use.
    """
    out = []
    for sample_ref in device.iter("SampleRef"):
        live = sample_ref.find("FileRef")
        if live is None:
            continue
        el = live.find("Path")
        if el is not None and el.get("Value"):
            out.append(el.get("Value"))
    return out


def _zone_of(branch) -> tuple[str, str] | None:
    """This chain's selector bounds, emitted whether or not they look default.

    Not suppressed when they cover the whole scale. `Engine.zone` is all or
    nothing per rack, so a chain left out because its bounds looked ordinary
    would take an even share instead and land somewhere else.
    """
    z = find.zone(branch)
    if z is None:
        return None
    lo, hi = z.find("Min"), z.find("Max")
    if lo is None or hi is None:
        return None
    return (lo.get("Value"), hi.get("Value"))


def _receiving_note(branch) -> str | None:
    """A pad's own note. DIRECT child only.

    `.//ZoneSettings` matches the first in document order, which inside a
    nested rack is one of the SUB-chain's, not this pad's. Same shape of
    mistake as walking up to the nearest rack device instead of the nearest
    BranchPresets: the tree offers a plausible wrong answer at every depth.
    """
    zs = branch.find("ZoneSettings")
    if zs is None:
        return None
    rn = zs.find("ReceivingNote")
    return None if rn is None else rn.get("Value")


def _chained_slots(branch) -> dict[int, int]:
    """Outer macro -> inner macro, for a chain holding a nested rack.

    A macro-to-macro mapping is a `KeyMidi` on the inner rack's
    `MacroControls.N`, so the outer macro is the CC and the inner slot is
    N + 1. Reading these back is what makes nesting recoverable instead of
    reconstructed from a default.
    """
    out: dict[int, int] = {}
    for m in mappings.find(branch):
        target = m["target"]
        if not m["macro"] or not target.startswith("MacroControls."):
            continue
        try:
            inner = int(target.split(".", 1)[1]) + 1
        except ValueError:
            continue
        out[m["macro"]] = inner
    return out


def _starts(rack_dev, n: int) -> dict[int, str]:
    """Macro number -> its resting position, for the ones not at 0.

    Recoverable where a slot name is not, because this is a value rather
    than a meaning. Worth recovering: a rack whose Volume macro rebuilt at 0
    loads silent, so dropping these turns a working rack into a mute one.
    """
    out: dict[int, str] = {}
    for i in range(n):
        el = find.macro(rack_dev, i + 1)
        manual = None if el is None else el.find("Manual")
        val = None if manual is None else manual.get("Value")
        if val not in (None, "", "0"):
            out[i + 1] = val
    return out


def _selector_slot(rack_dev) -> int | None:
    """Which macro drives this rack's chain selector, if any."""
    sel = find.chain_selector(rack_dev)
    if sel is None:
        return None
    for m in mappings.find(sel):
        if m["macro"]:
            return m["macro"]
    return None


def _emit_rack(preset_el, name_hint: str, used: set[str], lines: list[str],
               depth: int = 0) -> str:
    """Emit one rack and everything under it. Returns its variable name."""
    rack_dev = find.rack_device(preset_el)
    tag = rack_dev.tag
    kind = KIND_OF.get(tag, "RackKind.INSTRUMENT")

    user = rack_dev.find("UserName")
    name = (user.get("Value") if user is not None else "") or name_hint
    var = _ident(name, used)

    n = _macro_count(preset_el, rack_dev)
    # Underscore, not a space: the emitted `e.bind(macro_1=...)` has to be a
    # keyword argument, and Layout lookup is case insensitive on the exact
    # string. "Macro 1" would emit code that cannot address its own layout.
    slots = ", ".join(f'"Macro_{i + 1}"' for i in range(n))
    sel = _selector_slot(rack_dev)
    sel_arg = f', selector="Macro_{sel}"' if sel else ", selector=None"

    # Children first, so a nested rack exists as a variable before its
    # parent references it.
    children: dict[int, str] = {}
    branches = find.branches(preset_el)
    for i, branch in enumerate(branches):
        nested = [d for d in branch.iter("GroupDevicePreset")]
        if nested:
            child_name = branch.find("Name")
            hint = (child_name.get("Value") if child_name is not None
                    else f"{name}_{i}")
            hint = hint if hint != "" else f"{name}_{i}"
            children[i] = _emit_rack(nested[0], hint, used, lines, depth + 1)

    lines.append(f'{var} = Rack({name!r}, Layout({slots}{sel_arg}), kind={kind})')

    # The emitted layout is positional, so a label that matches its own
    # slot name carries nothing. One that does not is the only record of
    # what this rack called the knob.
    shown = {}
    for i in range(n):
        el = rack_dev.find(f"MacroDisplayNames.{i}")
        text = None if el is None else el.get("Value")
        # Live's own default, "Macro 1", is emitted too. It differs from the
        # positional slot name "Macro_1" by the underscore the slot needs to
        # be a keyword argument, and dropping it renames every knob on a
        # rack that was never labelled.
        if text:
            shown[f"Macro_{i + 1}"] = text
    if shown:
        lines.append(f'{var}.label(**{shown!r})')

    starts = _starts(rack_dev, n)
    if starts:
        args = ", ".join(f"macro_{k}={v}" for k, v in sorted(starts.items()))
        lines.append(f'{var}.start({args})')

    for i, branch in enumerate(branches):
        # The stored name, empty string included. Live leaves a chain
        # unnamed and inventing "chain0" for it is a change to the rack.
        bname_el = branch.find("Name")
        bname = bname_el.get("Value") if bname_el is not None else f"chain{i}"
        note = _receiving_note(branch)

        if i in children:
            call = (f'{var}.pad({bname!r}, {note}, rack={children[i]})'
                    if note is not None else
                    f'{var}.nest({bname!r}, {children[i]})')
            # WHICH slots chain must be emitted, never left to the default.
            # `nest()` with no arguments chains every slot the inner rack
            # drives, which is one mapping more than the original wherever
            # the author deliberately left a slot out. VA1 does exactly that
            # with its selector, and a bare nest silently puts it back.
            chain = _chained_slots(branch)
            if chain:
                args = ", ".join(f'macro_{o}="macro_{i2}"'
                                 for o, i2 in sorted(chain.items()))
                call += f'.bind({args})'
            zone = _zone_of(branch)
            if zone and note is None:
                call += f'.zone({zone[0]}, {zone[1]})'
            lines.append(call)
            continue

        devices = find.devices(branch)
        if not devices:
            lines.append(f'# {bname!r}: chain has no device, skipped')
            continue
        device = devices[0]

        if note is not None:
            lines.append(
                f'with {var}.pad({bname!r}, {note}, '
                f'device={device.tag!r}) as e:')
        else:
            lines.append(f'with {var}.engine({bname!r}, {device.tag!r}) as e:')

        # Before the bindings, because `sample()` replaces the whole
        # MultiSampleMap on some devices and a binding written first would
        # be emitted against a map that is about to go.
        #
        # Only the first target: a device with several samples is a
        # multi-sampled instrument, which `sample()` cannot express and Q3
        # gates. Emitting one of them silently would be a lie about what
        # rebuilt.
        got_samples = _sample_targets(device)
        if got_samples:
            lines.append(f'    e.sample({got_samples[0]!r})')
            if len(got_samples) > 1:
                lines.append(f'    # {len(got_samples) - 1} further sample(s) '
                             f'not emitted: multi-sampling is Q3')

        binds = _bindings_for(branch, device, rack_dev)
        if binds:
            args = ", ".join(
                f"macro_{k}=" + (_fmt_binding(v[0]) if len(v) == 1
                                 else "[" + ", ".join(map(_fmt_binding, v)) + "]")
                for k, v in sorted(binds.items()))
            lines.append(f'    e.bind({args})')
        else:
            lines.append('    pass  # no macro drives this chain')

        zone = _zone_of(branch)
        if zone and note is None:
            lines.append(f'    e.zone({zone[0]}, {zone[1]})')

    got = variations.read(rack_dev)
    if got:
        # One call, not one per variation: `variations()` appends, so
        # splitting it would still work and reads as though order were
        # negotiable. It is not - a variation is recalled by index.
        made = []
        for v in got:
            args = ", ".join(f"macro_{m}={P.fmt(p)}"
                             for m, p in sorted(v["values"].items()))
            made.append(f'Variation({(v["name"] or "")!r}{", " + args if args else ""})')
        lines.append(f"{var}.variations(")
        for m in made:
            lines.append(f"    {m},")
        lines.append(")")

    lines.append("")
    return var


def source(path: Path | str) -> str:
    """The DSL source for a `.adg`, as a string."""
    root = io.load(path)
    preset_el = find.preset(root)
    if preset_el is None:
        raise ValueError(f"{path}: no GroupDevicePreset; not a rack preset")

    lines = [
        '"""Extracted by `patchbay extract`. Slot names are positional.',
        "",
        "A decompiler recovers structure, not intent. Rename the Macro N",
        "slots to whatever this rack means, and the bindings follow.",
        '"""',
        "",
        "from patchbay.dsl import Layout, Rack, RackKind, Variation",
        "",
    ]
    used: set[str] = set()
    var = _emit_rack(preset_el, Path(path).stem, used, lines)
    lines.append(f"RACKS = [{var}]")
    return "\n".join(lines) + "\n"


def report(path: Path | str) -> None:
    print(source(path), end="")
