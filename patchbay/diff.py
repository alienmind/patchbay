"""Structural diff between two .adg files.

This is the discovery engine. You do not reverse engineer Ableton's schema
by reading it, you do it by changing exactly one thing in Live, saving a
second copy, and diffing. Everything else in this project depends on
knowing which XML node corresponds to which knob.

Three kinds of fact matter, so flatten() emits all three:

  path            the node exists (catches structural adds/removes)
  path@Attr       an attribute, any attribute, not only Value
  path$text       element text

Ids live in attributes (Id="3") as often as in Value elements
(<PointeeId Value="3"/>), so a flattener that only reads Value cannot
answer S6.
"""

# Fields that genuinely churn on every save, established by S2: save the
# same rack twice unchanged and see what moves. These are hidden by
# default because they bury real findings.
SAVE_NOISE = ("RoundRobinRandomSeed",)

# A preset records its own file identity in PresetRef and LastPresetRef.
# Saving the same rack under two names changes these, which is unavoidable
# when producing a spike pair. Hidden by default for the same reason.
# NOT the same thing as a sample FileRef, which S7 cares about.
PRESET_REF_MARKERS = ("/PresetRef/", "/LastPresetRef/")

# Id-bearing fields. S2 showed these do NOT churn across saves: Live
# preserves them, so they are signal, not noise, and are shown by default.
# --hide-ids exists for the case where a structural change renumbers
# enough of them to drown a diff.
ID_FIELDS = ("Id", "PointeeId", "LomId", "LomIdView")

NOISE = ID_FIELDS  # backwards compatible alias

from lxml import etree
from .io import load


def _is_list_container(parent):
    """True if parent is a plural container holding one repeated child tag.

    Ableton names these consistently: MacroSnapshots holds MacroSnapshot,
    BranchPresets holds <X>BranchPreset, SampleParts holds MultiSamplePart.
    Children of these are always indexed, even when there is only one.

    Without that, appending a second item renames the first from
    MacroSnapshot to MacroSnapshot[0] and the diff reports the entire list
    as removed and re-added - 210 facts of noise for one added variation.

    Requiring a single repeated tag keeps heterogeneous nodes that merely
    end in 's', like ViewSettings, out of it.
    """
    if not isinstance(parent.tag, str) or not parent.tag.endswith("s"):
        return False
    tags = {c.tag for c in parent if isinstance(c.tag, str)}
    return len(tags) == 1


def path_of(el):
    """Build a readable path like Chain[2]/DeviceChain/Devices/Simpler[0]."""
    parts = []
    while el is not None and el.getparent() is not None:
        parent = el.getparent()
        siblings = [c for c in parent if c.tag == el.tag]
        if len(siblings) > 1 or _is_list_container(parent):
            parts.append(f"{el.tag}[{siblings.index(el)}]")
        else:
            parts.append(el.tag)
        el = parent
    return "/".join(reversed(parts))


def flatten(root):
    """Map every element to presence, attribute and text facts.

    Keys are unique per fact, so set arithmetic in compare() gives
    added/removed/changed without further bookkeeping.
    """
    out = {}
    for el in root.iter():
        if not isinstance(el.tag, str):  # comments, PIs
            continue
        key = path_of(el)
        out[key] = "<present>"
        for name, val in el.attrib.items():
            out[f"{key}@{name}"] = val
        text = (el.text or "").strip()
        if text:
            out[f"{key}$text"] = text
    return out


def _field_of(key):
    """The field name a fact belongs to, for attribute, text and presence keys."""
    if "@" in key:
        return key.rsplit("@", 1)[1]
    return key.split("$")[0].split("/")[-1].split("[")[0]


def _in_fields(key, fields):
    """True if the fact is that field, or hangs off a node of that name."""
    if _field_of(key) in fields:
        return True
    node = key.rsplit("@", 1)[0].split("$")[0]
    return any(seg.split("[")[0] in fields for seg in node.split("/"))


def _is_save_noise(key):
    """True if Live regenerates this on every save regardless of edits."""
    if _in_fields(key, SAVE_NOISE):
        return True
    return any(m in f"/{key}/" for m in PRESET_REF_MARKERS)


def compare(path_a, path_b, hide_ids=False, show_all=False, grep=None):
    """Return (changed, only_in_a, only_in_b).

    By default hides only what S2 proved churns per save. Ids are shown,
    because S2 showed Live preserves them and they are usually the finding.

    hide_ids  also drop Id/PointeeId/LomId/LomIdView
    show_all  drop nothing, including per-save churn
    grep      keep only facts whose key contains that substring
    """
    a, b = flatten(load(path_a)), flatten(load(path_b))

    if not show_all:
        a = {k: v for k, v in a.items() if not _is_save_noise(k)}
        b = {k: v for k, v in b.items() if not _is_save_noise(k)}

    if hide_ids:
        a = {k: v for k, v in a.items() if not _in_fields(k, ID_FIELDS)}
        b = {k: v for k, v in b.items() if not _in_fields(k, ID_FIELDS)}

    if grep:
        a = {k: v for k, v in a.items() if grep in k}
        b = {k: v for k, v in b.items() if grep in k}

    changed = {k: (a[k], b[k]) for k in a.keys() & b.keys() if a[k] != b[k]}
    only_a = {k: a[k] for k in a.keys() - b.keys()}
    only_b = {k: b[k] for k in b.keys() - a.keys()}
    return changed, only_a, only_b


def report(path_a, path_b, hide_ids=False, show_all=False, grep=None, limit=None):
    """limit caps the lines printed per section.

    Adding one device drags its whole parameter blob in - a Reverb is some
    800 facts - which buries whatever you were looking for. Section counts
    are always printed in full, so nothing is hidden silently.
    """
    changed, only_a, only_b = compare(path_a, path_b, hide_ids, show_all, grep)

    def trunc(keys):
        keys = sorted(keys)
        if limit and len(keys) > limit:
            return keys[:limit], len(keys) - limit
        return keys, 0

    print(f"--- {path_a}\n+++ {path_b}\n")
    if changed:
        print(f"CHANGED ({len(changed)})")
        keys, more = trunc(changed)
        for k in keys:
            av, bv = changed[k]
            print(f"  {k}\n      {av}  ->  {bv}")
        if more:
            print(f"  ... {more} more")
    if only_a:
        print(f"\nREMOVED ({len(only_a)})")
        keys, more = trunc(only_a)
        for k in keys:
            print(f"  {k} = {only_a[k]}")
        if more:
            print(f"  ... {more} more")
    if only_b:
        print(f"\nADDED ({len(only_b)})")
        keys, more = trunc(only_b)
        for k in keys:
            print(f"  {k} = {only_b[k]}")
        if more:
            print(f"  ... {more} more")
    if not (changed or only_a or only_b):
        print("identical")
    return changed, only_a, only_b
