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
from .library import Library

#: Rack device tag -> the `Rack` constructor that builds one. A midi effect
#: rack has no constructor because `RackKind` has no member for it, and the
#: emitted `Rack.midi_effect(...)` fails loudly rather than building the
#: wrong kind of rack silently.
KIND_OF = {
    "InstrumentGroupDevice": "instrument",
    "AudioEffectGroupDevice": "audio_effect",
    "MidiEffectGroupDevice": "midi_effect",
    "DrumGroupDevice": "drum",
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
    """A binding as arguments to `drives`. Range numbers go in bare."""
    if isinstance(spec, tuple):
        return f"{spec[0]!r}, over=Range({spec[1]}, {spec[2]})"
    return repr(spec)


def _fmt_setting(text: str) -> str:
    """A setting's value as source, in the type `params.fmt` writes back.

    Numbers bare, booleans as Python, anything else quoted. The round trip
    is what this is for: `6` has to come back out as `"6"` and
    `0.8000000119` as itself, or the rebuild differs by a digit.
    """
    if text in ("true", "false"):
        return "True" if text == "true" else "False"
    try:
        return str(int(text))
    except ValueError:
        pass
    try:
        return str(float(text))
    except ValueError:
        return repr(text)


def _settings_for(device) -> dict[str, str]:
    """Values that differ from the donor this rebuilds from, at any depth.

    A rebuild fills the device from the donor, so anything equal to the
    donor is already there and emitting it would be noise. What differs is
    either something a spec SET or something Live wrote, and both have to
    be said or the rebuild is a different device.

    Both kinds, because both are reachable by `sets` and neither is
    recorded by a mapping: Drift's `ModulationMatrix_Target1` is a plain
    value, Operator's `Lfo/LfoOn` is an ordinary parameter that happens to
    be a switch, and a rack that forgets either gets a knob that moves
    nothing.
    """
    try:
        donor = Library.default().instance(device.tag)
    except Exception:                     # a device the library has never seen
        return {}

    out: dict[str, str] = {}
    now_p, was_p = find.all_params(device), find.all_params(donor)
    for path, el in now_p.items():
        before = was_p.get(path)
        if before is None:
            continue
        a = el.find("Manual").get("Value")
        b = before.find("Manual").get("Value")
        if a is not None and a != b:
            out[path] = a

    now_s, was_s = find.settings(device), find.settings(donor)
    for path, el in now_s.items():
        before = was_s.get(path)
        if before is None:
            continue
        if el.get("Value") != before.get("Value"):
            out[path] = el.get("Value")
    return out

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
               depth: int = 0) -> tuple[str, str]:
    """Emit one rack and everything under it.

    Returns its variable name and its layout's variable name. A parent needs
    both: the rack to sit in a chain, and the layout to name the inner slots
    an outer slot chains into.
    """
    rack_dev = find.rack_device(preset_el)
    kind = KIND_OF.get(rack_dev.tag, "instrument")

    user = rack_dev.find("UserName")
    name = (user.get("Value") if user is not None else "") or name_hint
    var = _ident(name, used)
    layout_var = _ident(f"{name}_layout", used)

    n = _macro_count(preset_el, rack_dev)
    sel = _selector_slot(rack_dev)
    starts = _starts(rack_dev, n)

    # Children first, so a nested rack exists as a variable before its
    # parent references it.
    children: dict[int, tuple[str, str]] = {}
    branches = find.branches(preset_el)
    for i, branch in enumerate(branches):
        nested = [d for d in branch.iter("GroupDevicePreset")]
        if nested:
            child_name = branch.find("Name")
            hint = (child_name.get("Value") if child_name is not None
                    else f"{name}_{i}")
            hint = hint if hint != "" else f"{name}_{i}"
            children[i] = _emit_rack(nested[0], hint, used, lines, depth + 1)

    # The slot list. A slot carries its own position, opening value, label
    # and selector flag, so the layout is the whole of what this rack's
    # macros are and there is nothing left to state per rack.
    #
    # Slot names are positional, `Macro 1`, and answer to `macro_1` in
    # Python. Guessing a name from a parameter path would be inventing
    # intent, which CLAUDE.md rule 1 forbids for exactly the reason that
    # makes it tempting: the guess is usually right, and silently wrong the
    # rest of the time.
    lines.append(f"{layout_var} = Layout(")
    for i in range(n):
        display = f"Macro {i + 1}"
        args = [repr(display)]
        if i + 1 in starts:
            args.append(f"start={starts[i + 1]}")
        # A label that matches the positional name carries nothing. One that
        # does not is the only record of what this rack called the knob, and
        # Live's own default happens to BE the positional name.
        el = rack_dev.find(f"MacroDisplayNames.{i}")
        text = None if el is None else el.get("Value")
        if text is not None and text != display:
            args.append(f"label={text!r}")
        if sel == i + 1:
            args.append("selects=True")
        lines.append(f"    Slot({', '.join(args)}),")
    lines.append(")")

    call = [f"{var} = (Rack.{kind}({name!r}, {layout_var})"]

    for i, branch in enumerate(branches):
        # The stored name, empty string included. Live leaves a chain
        # unnamed and inventing "chain0" for it is a change to the rack.
        bname_el = branch.find("Name")
        bname = bname_el.get("Value") if bname_el is not None else f"chain{i}"
        note = _receiving_note(branch)
        verb = f".pad({bname!r}, {note}," if note is not None else f".chain({bname!r},"
        zone = _zone_of(branch)

        if i in children:
            child_var, child_layout = children[i]
            # WHICH slots chain must be emitted, never left to the default.
            # `chaining()` with no arguments chains every slot the inner rack
            # drives, which is one mapping more than the original wherever
            # the author deliberately left a slot out. VA1 does exactly that
            # with its selector, and a bare chaining silently puts it back.
            pairs = ", ".join(
                f"{layout_var}.macro_{o}.to({child_layout}.macro_{inner})"
                for o, inner in sorted(_chained_slots(branch).items()))
            content = f"{child_var}.chaining({pairs})"
            if zone and note is None:
                content += f".zone({zone[0]}, {zone[1]})"
            call.append(f"        {verb} {content})")
            continue

        devices = find.devices(branch)
        if not devices:
            call.append(f"        # {bname!r}: chain has no device, skipped")
            continue
        device = devices[0]

        content = [f"Engine({device.tag!r})"]

        # Only the first target: a device with several samples is a
        # multi-sampled instrument, which `sample()` cannot express and Q3
        # gates. Emitting one of them silently would be a lie about what
        # rebuilt.
        got_samples = _sample_targets(device)
        if got_samples:
            content.append(f".sample({got_samples[0]!r})")
            if len(got_samples) > 1:
                content.append(f"  # {len(got_samples) - 1} further sample(s) "
                               f"not emitted: multi-sampling is Q3")

        for tag, val in sorted(_settings_for(device).items()):
            content.append(f".sets({tag!r}, {_fmt_setting(val)})")

        binds = _bindings_for(branch, device, rack_dev)
        for macro, specs in sorted(binds.items()):
            for spec in specs:
                content.append(
                    f".drives({layout_var}.macro_{macro}, {_fmt_binding(spec)})")
        if zone and note is None:
            content.append(f".zone({zone[0]}, {zone[1]})")

        joined = ("\n" + " " * 12).join(content)
        call.append(f"        {verb}\n            {joined})")

    got = variations.read(rack_dev)
    if got:
        # One call, not one per variation: `variations()` appends, so
        # splitting it would still work and reads as though order were
        # negotiable. It is not, a variation is recalled by index.
        made = []
        for v in got:
            args = ", ".join(f"macro_{m}={P.fmt(p)}"
                             for m, p in sorted(v["values"].items()))
            made.append(f'{layout_var}.variation({(v["name"] or "")!r}'
                        f'{", " + args if args else ""})')
        call.append("        .variations(")
        for m in made:
            call.append(f"            {m},")
        call.append("        )")

    lines.append("\n".join(call) + ")")
    lines.append("")
    return var, layout_var


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
        "from patchbay.dsl import Engine, Layout, Rack, Range, Slot",
        "",
    ]
    used: set[str] = set()
    var, _ = _emit_rack(preset_el, Path(path).stem, used, lines)
    lines.append(f"RACKS = [{var}]")
    return "\n".join(lines) + "\n"


def report(path: Path | str) -> None:
    print(source(path), end="")
