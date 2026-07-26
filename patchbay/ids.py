"""S6: id census and collision check.

Established by deliberate-failure test (see SCHEMA.md S6):

  An Id must be unique among its SIBLINGS. Nothing else about it matters.

Not file-wide unique - Id="0" occurs 548 times in one real rack that Live
opens happily. Not contiguous, and not equal to the element's index: a
rack with AbletonDevicePreset Id="2" sitting at index 1 loads fine, and so
does one where every device id is forced to 7.

But give two sibling DrumBranchPreset elements the same Id and Live
refuses the whole preset with "the preset cannot be loaded".

So the rule for clone.py is narrow and cheap: when duplicating a branch,
assign it an Id unused by its siblings. Nothing references these values,
so any free number will do.
"""

from collections import defaultdict

from .io import load
from .diff import ID_FIELDS, path_of


def collisions(root):
    """Find containers holding two children with the same tag and Id.

    This is the condition Live rejects. Returns a list of
    (container_path, tag, id_value, count).
    """
    out = []
    for parent in root.iter():
        if not isinstance(parent.tag, str):
            continue
        seen = defaultdict(list)
        for child in parent:
            if not isinstance(child.tag, str):
                continue
            idv = child.get("Id")
            if idv is not None:
                seen[(child.tag, idv)].append(child)
        for (tag, idv), els in seen.items():
            if len(els) > 1:
                out.append((path_of(parent), tag, idv, len(els)))
    return out


def next_free_id(parent, tag):
    """Lowest Id not already used by parent's children of this tag."""
    used = {c.get("Id") for c in parent if c.tag == tag and c.get("Id") is not None}
    n = 0
    while str(n) in used:
        n += 1
    return str(n)


def census(path, fields=ID_FIELDS):
    facts = {}
    root = load(path)
    buckets = defaultdict(lambda: defaultdict(list))
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        for name, val in el.attrib.items():
            if name in fields:
                buckets[name][val].append(path_of(el))
        if el.tag in fields:
            v = el.get("Value")
            if v is not None:
                buckets[el.tag][v].append(path_of(el))
    return buckets


def report(path, fields=ID_FIELDS):
    root = load(path)
    buckets = census(path, fields)

    print(f"id census: {path}\n")
    for field in sorted(buckets):
        values = buckets[field]
        total = sum(len(v) for v in values.values())
        numeric = [int(v) for v in values if v.lstrip("-").isdigit()]
        rng = f"{min(numeric)}..{max(numeric)}" if numeric else "non-numeric"
        print(f"  {field}: {total} occurrences, {len(values)} distinct, range {rng}")
    print()

    bad = collisions(root)
    if not bad:
        print("no sibling id collisions - Live will accept this file")
        return bad

    print(f"SIBLING ID COLLISIONS ({len(bad)}) - Live will REFUSE to load this")
    for container, tag, idv, count in bad:
        print(f"  {count}x <{tag} Id=\"{idv}\"> under {container}")
    return bad
