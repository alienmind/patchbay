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

import copy
from pathlib import Path

from lxml import etree

from . import find, io, mappings, params as P, samples, variations
from .harvest import INSTALLED_CONTENT
from .library import Library

#: Live's silent floor for a send, as the file spells it. A send left here
#: carries no information a rebuild does not already write.
FLOOR = "0.0003162277571"

#: Rack device tag -> the `Rack` constructor that builds one.
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
        # Live's own installed content is part of the DEVICE, not a sample
        # anybody chose: Hybrid Reverb's impulse response is one, and its
        # absolute path is the macOS one Ableton ships in every copy of the
        # preset. Emitting `.sample()` for it produces source that refuses
        # to build on the machine that extracted it.
        kind = live.find("RelativePathType")
        if kind is not None and kind.get("Value") == INSTALLED_CONTENT:
            continue
        el = live.find("Path")
        if el is not None and el.get("Value"):
            out.append(el.get("Value"))
    return out


def _branch_name(branch, fallback: str) -> str:
    el = branch.find("Name")
    got = el.get("Value") if el is not None else ""
    return got or fallback


def _sends_of(branch, names) -> dict[str, str]:
    """This chain's send levels, by return name.

    `Index` is positional (S9), so the names come from the return list and
    the level is read back as the string the file holds - a send is linear
    amplitude and a re-rounded one is a diff to explain every time.

    A send at the silent floor with no macro on it says nothing a rebuild
    does not already write, so it is left out.
    """
    levels: dict[str, str] = {}
    for info in branch.iter("AudioBranchSendInfo"):
        idx = info.find("Index")
        send = info.find("Send")
        if idx is None or send is None:
            continue
        try:
            name = names[int(idx.get("Value"))]
        except (ValueError, IndexError):
            continue
        manual = send.find("Manual")
        if manual is not None and manual.get("Value") != FLOOR:
            levels[name] = manual.get("Value")
    return levels


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


def _send_slots(branches, names) -> dict[str, int]:
    """Return name -> the macro that sweeps every chain's send to it.

    `Rack.sending` writes one mapping per chain, so a rack-level call is
    read back from the chains. A return name is emitted once, on the macro
    the first mapped chain names; a file where two chains disagree is not
    something this DSL can write and the first wins rather than inventing a
    per-chain verb that does not exist.
    """
    out: dict[str, int] = {}
    for branch in branches:
        for info in branch.iter("AudioBranchSendInfo"):
            idx, send = info.find("Index"), info.find("Send")
            if idx is None or send is None or send.find("KeyMidi") is None:
                continue
            cc = send.find("KeyMidi/NoteOrController")
            try:
                name = names[int(idx.get("Value"))]
                macro = int(cc.get("Value")) + 1
            except (AttributeError, ValueError, IndexError):
                continue
            out.setdefault(name, macro)
    return out


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


def slot_hints(spec_path) -> dict[str, str]:
    """Parameter path -> the slot name a known spec gives it.

    Extraction names slots positionally because guessing a name from a
    parameter path invents intent. A spec the caller NAMES is not a guess:
    it is a second file saying that whatever drives
    `Filter/Slot/Value/SimplerFilter/Freq` is called Filter. Where the
    extracted rack agrees, the name comes across; where it does not, the
    slot stays `Macro N`.

    Built from every rack in the spec, so a path two racks disagree about
    is dropped rather than resolved by order.
    """
    from . import compile as compile_spec

    hints: dict[str, set[str]] = {}
    for rack in compile_spec.racks_in(compile_spec.load_spec(spec_path)):
        for path, display in _spec_bindings(rack).items():
            hints.setdefault(path, set()).add(display)
    return {p: next(iter(d)) for p, d in hints.items() if len(d) == 1}


def _spec_bindings(rack) -> dict[str, str]:
    """Parameter path -> slot display, read off a built rack rather than
    off the DSL objects, so one reader serves every shape the DSL can make.
    """
    out: dict[str, str] = {}
    root = rack.build()
    for preset in root.iter("GroupDevicePreset"):
        rack_dev = find.rack_device(preset)
        if rack_dev is None:
            continue
        for branch in find.branches(preset) + find.return_branches(preset):
            for device in find.devices(branch):
                for macro, specs in _bindings_for(branch, device,
                                                  rack_dev).items():
                    el = rack_dev.find(f"MacroDisplayNames.{macro - 1}")
                    display = None if el is None else el.get("Value")
                    if not display or display == f"Macro {macro}":
                        continue
                    for spec in specs:
                        path = spec[0] if isinstance(spec, tuple) else spec
                        out[path] = display
    return out


def _slot_ref(named: dict[int, str], macro: int) -> str:
    """How the emitted source addresses one slot of its own layout.

    `dsl._key` and not a local rule: the emitted module has to import, so
    the reference must be the identifier `Layout` will actually build.
    """
    from .dsl import _key

    return _key(named.get(macro, f"Macro {macro}"))


def _named_slots(preset_el, rack_dev, n: int,
                 hints: dict[str, str]) -> dict[int, str]:
    """Macro number -> the name a named spec gives it, where it agrees.

    A macro is named only when every parameter it drives that the spec knows
    about answers to the SAME slot. One disagreement and the slot stays
    positional, because half a name is worse than none.
    """
    if not hints:
        return {}
    seen: dict[int, set[str]] = {}
    branches = find.branches(preset_el) + find.return_branches(preset_el)
    for branch in branches:
        for device in find.devices(branch):
            for macro, specs in _bindings_for(branch, device,
                                              rack_dev).items():
                for spec in specs:
                    path = spec[0] if isinstance(spec, tuple) else spec
                    if path in hints:
                        seen.setdefault(macro, set()).add(hints[path])
    out = {m: next(iter(d)) for m, d in seen.items()
           if len(d) == 1 and m <= n}
    # Two macros cannot share a name: the Layout refuses it, and the emitted
    # module would not import.
    taken: dict[str, int] = {}
    for macro in sorted(out):
        display = out[macro]
        if display in taken:
            del out[macro]
        else:
            taken[display] = macro
    return out


def _emit_rack(preset_el, name_hint: str, used: set[str], lines: list[str],
               depth: int = 0, hints: dict[str, str] | None = None
               ) -> tuple[str, str]:
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
    returns = find.return_branches(preset_el)
    return_names = [_branch_name(b, f"{name}_return{i}")
                    for i, b in enumerate(returns)]
    for i, branch in enumerate(branches + returns):
        nested = [d for d in branch.iter("GroupDevicePreset")]
        if nested:
            child_name = branch.find("Name")
            hint = (child_name.get("Value") if child_name is not None
                    else f"{name}_{i}")
            hint = hint if hint != "" else f"{name}_{i}"
            children[i] = _emit_rack(nested[0], hint, used, lines, depth + 1,
                                     hints)

    # The slot list. A slot carries its own position, opening value, label
    # and selector flag, so the layout is the whole of what this rack's
    # macros are and there is nothing left to state per rack.
    #
    # Slot names are positional, `Macro 1`, and answer to `macro_1` in
    # Python. Guessing a name from a parameter path would be inventing
    # intent, which CLAUDE.md rule 1 forbids for exactly the reason that
    # makes it tempting: the guess is usually right, and silently wrong the
    # rest of the time.
    named = _named_slots(preset_el, rack_dev, n, hints or {})

    lines.append(f"{layout_var} = Layout(")
    for i in range(n):
        display = named.get(i + 1, f"Macro {i + 1}")
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

    for i, branch in enumerate(branches + returns):
        # The stored name, empty string included. Live leaves a chain
        # unnamed and inventing "chain0" for it is a change to the rack.
        bname_el = branch.find("Name")
        bname = bname_el.get("Value") if bname_el is not None else f"chain{i}"
        note = _receiving_note(branch)
        is_return = i >= len(branches)
        if is_return:
            verb = f".ret({bname!r},"
        else:
            verb = (f".pad({bname!r}, {note}," if note is not None
                    else f".chain({bname!r},")
        zone = _zone_of(branch)
        levels = _sends_of(branch, return_names)
        # A return sends to nothing, so only a chain carries one.
        tail = "" if is_return or not levels else ", sends={%s}" % ", ".join(
            f"{k!r}: {v}" for k, v in sorted(levels.items()))

        if i in children:
            child_var, child_layout = children[i]
            # WHICH slots chain must be emitted, never left to the default.
            # `chaining()` with no arguments chains every slot the inner rack
            # drives, which is one mapping more than the original wherever
            # the author deliberately left a slot out. VA1 does exactly that
            # with its selector, and a bare chaining silently puts it back.
            # `chaining()` with no arguments is the IDENTITY default, which
            # is one mapping per driven slot and not the same thing as a
            # rack driven by nothing. A return is the second case, and so is
            # any chain whose author left every slot out.
            pairs = ", ".join(
                f"{layout_var}.{_slot_ref(named, o)}"
                f".to({child_layout}.macro_{inner})"
                for o, inner in sorted(_chained_slots(branch).items()))
            content = (f"{child_var}.chaining({pairs})" if pairs
                       else f"{child_var}.unchained()")
            if zone and note is None and not is_return:
                content += f".zone({zone[0]}, {zone[1]})"
            call.append(f"        {verb} {content}{tail})")
            continue

        devices = find.devices(branch)
        if not devices:
            call.append(f"        # {bname!r}: chain has no device, skipped")
            continue

        # One chain may hold several devices in series - the whole shape of
        # a channel strip - and each carries its own bindings. `then` puts
        # the next one after this one; the zone belongs to the chain and is
        # emitted once, at the end.
        content: list[str] = []
        for pos, device in enumerate(devices):
            if pos:
                content.append(f".then(Engine({device.tag!r})")
            else:
                content.append(f"Engine({device.tag!r})")

            # Only the first target: a device with several samples is a
            # multi-sampled instrument, which `sample()` cannot express and
            # Q3 gates. Emitting one of them silently would be a lie about
            # what rebuilt.
            got_samples = _sample_targets(device)
            if got_samples:
                content.append(f".sample({got_samples[0]!r})")
                if len(got_samples) > 1:
                    content.append(f"  # {len(got_samples) - 1} further "
                                   f"sample(s) not emitted: multi-sampling "
                                   f"is Q3")

            for tag, val in sorted(_settings_for(device).items()):
                content.append(f".sets({tag!r}, {_fmt_setting(val)})")

            binds = _bindings_for(branch, device, rack_dev)
            for macro, specs in sorted(binds.items()):
                for spec in specs:
                    content.append(
                        f".drives({layout_var}.{_slot_ref(named, macro)}, "
                        f"{_fmt_binding(spec)})")
            if pos:
                content[-1] += ")"
        if zone and note is None and not is_return:
            content.append(f".zone({zone[0]}, {zone[1]})")

        joined = ("\n" + " " * 12).join(content)
        call.append(f"        {verb}\n            {joined})")

    for name, macro in sorted(_send_slots(branches, return_names).items()):
        call.append(f"        .sending({layout_var}."
                    f"{_slot_ref(named, macro)}, {name!r})")

    got = variations.read(rack_dev)
    if got:
        # One call, not one per variation: `variations()` appends, so
        # splitting it would still work and reads as though order were
        # negotiable. It is not, a variation is recalled by index.
        made = []
        for v in got:
            args = ", ".join(f"{_slot_ref(named, m)}={P.fmt(p)}"
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


def source(path: Path | str, layout: Path | str | None = None) -> str:
    """The DSL source for a saved rack, as a string.

    Takes a `.adg`, which holds one rack in preset form, or a `.als`, which
    holds as many racks as its tracks carry in Set form. Q9 is the mapping
    between the two, and `preset_from_set` applies it, so everything after
    that point is one emitter.
    """
    root = io.load(path)
    presets = []
    if root.find("LiveSet") is not None or root.tag == "LiveSet":
        presets = racks_in_set(root)
        if not presets:
            raise ValueError(f"{path}: no racks on any track")
    else:
        preset_el = find.preset(root)
        if preset_el is None:
            raise ValueError(f"{path}: no GroupDevicePreset; not a rack preset")
        presets = [(Path(path).stem, preset_el)]

    hints = slot_hints(layout) if layout else {}
    note = (f"Slot names come from {Path(layout).name} where the bindings"
            if layout else "Slot names are positional")
    lines = [
        f'"""Extracted by `patchbay extract`. {note}',
        ("agree, and are positional where they do not." if layout else
         "A decompiler recovers structure, not intent. Rename the Macro N"),
        ("A decompiler recovers structure, not intent." if layout else
         "slots to whatever this rack means, and the bindings follow."),
        '"""',
        "",
        "from patchbay.dsl import Engine, Layout, Rack, Range, Slot",
        "",
    ]
    used: set[str] = set()
    made = [_emit_rack(preset, hint, used, lines, hints=hints)[0]
            for hint, preset in presets]
    lines.append(f"RACKS = [{', '.join(made)}]")
    return "\n".join(lines) + "\n"


def write_modules(path: Path | str, out: Path | str,
                  layout: Path | str | None = None) -> list[Path]:
    """One module per rack in `path`, plus an index that imports them all.

    For a Set with a strip on every track, printing one long module is the
    wrong shape: each rack wants its own file to edit and rebuild. The index
    exists so `patchbay build` takes the directory as one spec.
    """
    root = io.load(path)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    if root.find("LiveSet") is not None or root.tag == "LiveSet":
        found = racks_in_set(root)
        if not found:
            raise ValueError(f"{path}: no racks on any track")
    else:
        preset_el = find.preset(root)
        if preset_el is None:
            raise ValueError(f"{path}: no GroupDevicePreset; not a rack preset")
        found = [(Path(path).stem, preset_el)]

    hints = slot_hints(layout) if layout else {}
    made, names = [], []
    for hint, preset in found:
        used: set[str] = set()
        lines = [
            '"""Extracted by `patchbay extract`. Slot names are positional."""',
            "",
            "from patchbay.dsl import Engine, Layout, Rack, Range, Slot",
            "",
        ]
        var, _ = _emit_rack(preset, hint, used, lines, hints=hints)
        lines.append(f"RACKS = [{var}]")
        name = _ident(hint, set())
        dest = out / f"{name}.py"
        dest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        made.append(dest)
        names.append(name)

    index = out / "__init__.py"
    body = ['"""Every rack extracted from one file, as one spec."""', ""]
    body += [f"from .{n} import RACKS as {n}_racks" for n in names]
    body += ["", "RACKS = " + " + ".join(f"{n}_racks" for n in names), ""]
    index.write_text("\n".join(body), encoding="utf-8", newline="\n")
    made.append(index)
    return made


def report(path: Path | str, layout: Path | str | None = None) -> None:
    print(source(path, layout), end="")


# --- reading racks out of a Set -------------------------------------------

#: Set form to preset form, per Q9. The rack device tag is the same in both;
#: everything around it is renamed and re-nested.
BRANCH_OF = {
    "AudioEffectGroupDevice": ("AudioEffectBranch", "AudioEffectBranchPreset"),
    "InstrumentGroupDevice": ("InstrumentBranch", "InstrumentBranchPreset"),
    "MidiEffectGroupDevice": ("MidiEffectBranch", "MidiEffectBranchPreset"),
    "DrumGroupDevice": ("DrumBranch", "DrumBranchPreset"),
}

#: Ids that are live-session bookkeeping. Every preset Live saved here has
#: them at 0; a Set has them pointing into the running LOM.
SESSION_IDS = ("AutomationTarget", "ModulationTarget", "Pointee")


def _templates_for(kind_tag):
    """A branch preset and a device wrapper, from a rack of this kind.

    Donor-based like the rest: rather than synthesising `AbletonDevicePreset`
    from nothing, take one out of a file Live wrote.
    """
    branch_tag = BRANCH_OF[kind_tag][1]
    root_dir = Path(__file__).resolve().parent.parent
    for folder in ("donors", "racks"):
        for candidate in sorted((root_dir / folder).glob("*.adg")):
            try:
                tree = io.load(candidate)
            except Exception:
                continue
            branch = next(tree.iter(branch_tag), None)
            wrapper = next(tree.iter("AbletonDevicePreset"), None)
            if branch is not None and wrapper is not None:
                return copy.deepcopy(branch), copy.deepcopy(wrapper)
    raise FileNotFoundError(
        f"no {branch_tag} to model on. A rack of that kind has to exist in "
        f"donors/ or racks/ before one can be lifted out of a Set.")


def _zero_session_ids(el):
    """Point every live-session id back at nothing, as a preset does."""
    for node in el.iter():
        if isinstance(node.tag, str) and node.tag in SESSION_IDS:
            node.set("Id", "0")


def _wrap_device(device, wrapper_template, position):
    """One Set-form device in the `AbletonDevicePreset` a preset expects."""
    wrapper = copy.deepcopy(wrapper_template)
    holder = wrapper.find("Device")
    for child in list(holder):
        holder.remove(child)
    placed = copy.deepcopy(device)
    placed.set("Id", "0")
    holder.append(placed)
    wrapper.set("Id", str(position))
    return wrapper


def _set_devices(branch):
    """The devices in a Set-form branch, in order.

    A branch's chain is `DeviceChain/<X>ToXDeviceChain/Devices`, and the
    middle tag varies with the signal type, so it is found rather than
    named.
    """
    chain = branch.find("DeviceChain")
    if chain is None:
        return []
    for kid in chain:
        devices = kid.find("Devices") if isinstance(kid.tag, str) else None
        if devices is not None:
            return [d for d in devices if isinstance(d.tag, str)]
    return []


def preset_from_set(rack_dev, at_top=True):
    """Lift a rack out of a Set into the preset form a `.adg` holds.

    Q9's mapping, and every part of it was read off `racks/q9_a.adg` beside
    `racks/q9_b.als` rather than assumed:

        Device/<X>GroupDevice          same node, Branches emptied
        Branches/<X>Branch             -> BranchPresets/<X>BranchPreset
        .../DeviceChain/.../Devices/D  -> DevicePresets/AbletonDevicePreset/Device/D
        .../MixerDevice                -> MixerPreset/AbletonDevicePreset/Device/...

    A nested rack recurses, because a rack inside a Set-form chain is
    another `<X>GroupDevice` in that chain's `Devices`.
    """
    kind = rack_dev.tag
    if kind not in BRANCH_OF:
        raise ValueError(f"{kind} is not a rack device")
    branch_template, wrapper_template = _templates_for(kind)

    preset = etree.Element("GroupDevicePreset")
    # A top-level GroupDevicePreset carries NO attributes and a nested one
    # carries an Id. The caller places the Id; here the only rule is that
    # the top level has none.
    device_holder = etree.SubElement(preset, "Device")

    lifted = copy.deepcopy(rack_dev)
    lifted.set("Id", "0")
    for container in ("Branches", "ReturnBranches"):
        got = lifted.find(container)
        if got is not None:
            for child in list(got):
                got.remove(child)
    device_holder.append(lifted)

    branches = etree.SubElement(preset, "BranchPresets")
    source = rack_dev.find("Branches")
    for i, branch in enumerate(source if source is not None else []):
        branches.append(_lift_branch(branch, i, branch_template,
                                     wrapper_template))

    _zero_session_ids(preset)
    if not at_top:
        preset.set("Id", "0")
    return preset


def _lift_branch(branch, position, branch_template, wrapper_template):
    """One Set-form branch as a branch preset."""
    made = copy.deepcopy(branch_template)
    made.set("Id", str(position))

    # A chain's name is one node in a preset and four in a Set: preset form
    # holds `<Name Value="erode" />`, Set form holds EffectiveName, UserName,
    # Annotation and MemorizedFirstClipName. Take the effective one.
    mine = made.find("Name")
    theirs = branch.find("Name")
    if mine is not None and theirs is not None:
        effective = theirs.find("EffectiveName")
        if effective is None:
            effective = theirs.find("UserName")
        mine.set("Value", "" if effective is None else effective.get("Value"))
    elif mine is not None and theirs is None:
        mine.set("Value", "")

    # Carry across what both forms have and the preset side needs.
    for tag in ("IsSoloed", "BranchSelectorRange", "ZoneSettings",
                "SessionViewBranchWidth"):
        theirs = branch.find(tag)
        if theirs is None:
            continue
        mine = made.find(tag)
        if mine is not None:
            made.replace(mine, copy.deepcopy(theirs))

    devices = made.find("DevicePresets")
    for child in list(devices):
        devices.remove(child)
    for j, device in enumerate(_set_devices(branch)):
        if device.tag in BRANCH_OF:
            nested = preset_from_set(device, at_top=False)
            nested.set("Id", str(j))
            devices.append(nested)
        else:
            devices.append(_wrap_device(device, wrapper_template, j))

    mixer = branch.find("MixerDevice")
    holder = made.find("MixerPreset")
    if mixer is not None and holder is not None:
        for child in list(holder):
            holder.remove(child)
        holder.append(_wrap_device(mixer, wrapper_template, 0))
    return made


def racks_in_set(root):
    """Every top-level rack in a Set, as (track name, preset form).

    Top-level only: a rack nested inside another comes back inside its
    parent, and lifting it twice would emit it twice.
    """
    out = []
    for track in root.iter():
        if not isinstance(track.tag, str) or not track.tag.endswith("Track"):
            continue
        name_el = track.find("Name/EffectiveName")
        name = name_el.get("Value") if name_el is not None else track.tag
        chain = track.find("DeviceChain/DeviceChain/Devices")
        if chain is None:
            continue
        for device in chain:
            if isinstance(device.tag, str) and device.tag in BRANCH_OF:
                out.append((name, preset_from_set(device)))
    return out
