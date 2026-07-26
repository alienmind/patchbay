"""S6: id census.

Cloning is only viable if we know which fields carry ids, what their
uniqueness scope is, and which references point at which definitions.
This does not answer that on its own; it gives you the raw census to
read alongside a diff of "added one device".

Reports, per id-bearing field name:
  how many occurrences, the value range, and any duplicated values
  together with the paths that share them.

Duplicates are the interesting part. A field that is globally unique
across a whole file is a file-scoped id and cloning must reallocate it.
A field that repeats identically in every chain is chain-scoped and
must NOT be reallocated, or mappings break.
"""

from collections import defaultdict

from .io import load
from .diff import flatten, ID_FIELDS


def census(path, fields=ID_FIELDS):
    facts = flatten(load(path))

    buckets = defaultdict(lambda: defaultdict(list))  # field -> value -> paths
    for key, val in facts.items():
        if "@" in key:
            node, attr = key.rsplit("@", 1)
            field, where = attr, node
        else:
            leaf = key.split("$")[0].split("/")[-1].split("[")[0]
            field, where = leaf, key
        if field in fields:
            buckets[field][val].append(where)
    return buckets


def report(path, fields=ID_FIELDS):
    buckets = census(path, fields)
    print(f"id census: {path}\n")

    if not buckets:
        print(f"no fields matching {fields} found. Widen --fields.")
        return buckets

    for field in sorted(buckets):
        values = buckets[field]
        total = sum(len(v) for v in values.values())
        numeric = [int(v) for v in values if v.lstrip("-").isdigit()]
        rng = f"{min(numeric)}..{max(numeric)}" if numeric else "non-numeric"
        dupes = {v: p for v, p in values.items() if len(p) > 1}

        print(f"{field}: {total} occurrences, {len(values)} distinct, range {rng}")
        if not dupes:
            print("  unique across file -> file-scoped, clone must reallocate")
        else:
            print(f"  {len(dupes)} duplicated values -> scope is NOT the file")
            for val, paths in sorted(dupes.items())[:3]:
                print(f"    {field}={val} at {len(paths)}x, e.g.")
                for p in paths[:3]:
                    print(f"      {p}")
        print()
    return buckets
