"""List macro mappings in a preset.

S3 established that a mapping is a KeyMidi element on the target
parameter, with NoteOrController holding the zero-based macro index and
Channel 16 marking the virtual macro bus. There is no id and no pointer:
the target is the parameter that contains the block, and the owning rack
is the nearest enclosing rack device.

That makes mappings enumerable by walking the tree, which is the cheapest
way to verify a clone did not disturb them.
"""

MACRO_CHANNEL = "16"


def _owning_rack(el):
    """The rack device whose macro drives this parameter.

    In preset format a rack is a GroupDevicePreset with two sibling
    subtrees: Device/<X>GroupDevice holds the rack's own macros, and
    BranchPresets holds its chains. A rack's macros control parameters
    inside its BranchPresets, so the owner is found by walking up to the
    nearest BranchPresets and taking its parent's rack device.

    This is why "nearest enclosing GroupDevice" is wrong: a mapped
    parameter is never a descendant of the rack device node that owns
    the macro.
    """
    p = el.getparent()
    while p is not None:
        if p.tag == "BranchPresets":
            preset = p.getparent()
            device = preset.find("Device") if preset is not None else None
            if device is not None:
                for c in device:
                    if isinstance(c.tag, str) and c.tag.endswith("GroupDevice"):
                        return c
            return None
        p = p.getparent()
    return None


def find(root):
    """Yield one dict per macro mapping found."""
    out = []
    for km in root.iter("KeyMidi"):
        fields = {c.tag: c.get("Value") for c in km}
        target = km.getparent()
        rack = _owning_rack(target)

        cc = fields.get("NoteOrController")
        out.append({
            "target": target.tag,
            "macro": int(cc) + 1 if cc is not None and cc.isdigit() else None,
            "cc": cc,
            "channel": fields.get("Channel"),
            "is_note": fields.get("IsNote"),
            "mode": fields.get("ControllerMapMode"),
            "rack": rack.tag if rack is not None else None,
            "depth": _depth(target),
            "element": km,
        })
    return out


def _depth(el):
    """Rack nesting level of this parameter. Top level rack is 1."""
    n, p = 0, el.getparent()
    while p is not None:
        if p.tag == "BranchPresets":
            n += 1
        p = p.getparent()
    return n


def report(path):
    from .io import load
    from .diff import path_of

    found = find(load(path))
    print(f"{len(found)} macro mapping(s) in {path}\n")

    for m in sorted(found, key=lambda m: (m["depth"], m["macro"] or 0)):
        odd = []
        if m["channel"] != MACRO_CHANNEL:
            odd.append(f"channel={m['channel']} (not the macro bus)")
        if m["is_note"] != "false":
            odd.append(f"IsNote={m['is_note']}")
        if m["mode"] != "0":
            odd.append(f"mode={m['mode']} (not absolute)")

        note = "  <- " + ", ".join(odd) if odd else ""
        print(f"  Macro {m['macro']}  ->  {m['target']}"
              f"   [{m['rack']}, depth {m['depth']}]{note}")
        print(f"      {path_of(m['element'].getparent())}")
    return found
