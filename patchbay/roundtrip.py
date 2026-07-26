"""S1: prove load -> save with zero changes is lossless.

Byte identity is the strong result and is what we want, but Live's own
serialiser may differ from lxml's in ways that do not matter (attribute
order, self-closing tags, trailing newline). So report both: byte
identity, and structural identity over every fact flatten() can see.

Structural identity with byte difference is a pass with a caveat. Only
dragging the output into Live settles it, which is why this prints the
output path and tells you to do exactly that.
"""

from pathlib import Path

from . import io
from .diff import flatten, compare


def check(src, dest=None):
    src = Path(src)
    dest = Path(dest) if dest else src.with_name(src.stem + ".roundtrip" + src.suffix)

    io.save(io.load(src), dest)

    src_xml, dest_xml = io.load_raw(src), io.load_raw(dest)
    byte_same = src_xml == dest_xml

    # show_all: a round trip must not change one byte of meaning, not even
    # the per-save churn Live itself regenerates
    changed, only_a, only_b = compare(src, dest, show_all=True)
    struct_same = not (changed or only_a or only_b)

    print(f"src   {src}  ({len(src_xml)} bytes xml)")
    print(f"out   {dest}  ({len(dest_xml)} bytes xml)")
    print(f"facts {len(flatten(io.load(src)))}")
    print()
    print(f"byte identical:       {'YES' if byte_same else 'no'}")
    print(f"structurally identical: {'YES' if struct_same else 'NO'}")

    if not struct_same:
        print()
        print("S1 FAILS. Round trip is lossy. Do not build on this.")
        if changed:
            print(f"  changed {len(changed)}: {sorted(changed)[:5]}")
        if only_a:
            print(f"  lost {len(only_a)}: {sorted(only_a)[:5]}")
        if only_b:
            print(f"  invented {len(only_b)}: {sorted(only_b)[:5]}")
        return False

    if not byte_same:
        print()
        print("Structure survived but bytes differ (serialiser cosmetics).")
    print()
    print(f"NOW DRAG {dest} INTO LIVE. S1 is not passed until it opens.")
    return True
