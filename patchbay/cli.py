import argparse
import sys
from . import compile as compile_spec
from . import io, diff, clone, find, ids, mappings, roundtrip, variations
from .diff import ID_FIELDS


def main():
    try:
        _main()
    except (BrokenPipeError, OSError) as e:
        # Piping to head closes stdout early. On Windows that surfaces as
        # OSError EINVAL rather than BrokenPipeError, and without this the
        # tool dies with a traceback on a completely normal `| head`.
        if isinstance(e, OSError) and not isinstance(e, BrokenPipeError):
            if e.errno not in (22, 32):
                raise
        try:
            sys.stdout.close()
        except Exception:
            pass
        raise SystemExit(0)


def _main():
    p = argparse.ArgumentParser(prog="patchbay")
    sub = p.add_subparsers(dest="cmd", required=True)

    u = sub.add_parser("unpack", help="gunzip an .adg to readable .xml")
    u.add_argument("src")
    u.add_argument("-o", "--out")

    r = sub.add_parser("repack", help="gzip an .xml back to .adg")
    r.add_argument("src")
    r.add_argument("dest")

    d = sub.add_parser("diff", help="structural diff between two .adg files")
    d.add_argument("a")
    d.add_argument("b")
    d.add_argument("--hide-ids", action="store_true",
                   help="drop Id/PointeeId/LomId/LomIdView (shown by default)")
    d.add_argument("--all", action="store_true", dest="show_all",
                   help="hide nothing, including per-save churn")
    d.add_argument("--grep", help="only facts whose path contains this")
    d.add_argument("-n", "--limit", type=int,
                   help="cap lines shown per section; counts stay exact")

    t = sub.add_parser("roundtrip", help="S1: load and save unchanged, prove lossless")
    t.add_argument("src")
    t.add_argument("-o", "--out")

    m = sub.add_parser("mappings", help="list macro mappings (S3)")
    m.add_argument("src")

    v = sub.add_parser("variations",
                       help="list macro variations (S8; the XML calls them "
                            "snapshots)")
    v.add_argument("src")

    cl = sub.add_parser("clone", help="duplicate a chain N times (Phase 2)")
    cl.add_argument("src")
    cl.add_argument("dest")
    cl.add_argument("-c", "--chain", type=int, default=0,
                    help="index of the chain to duplicate (default 0)")
    cl.add_argument("-n", "--count", type=int, default=1,
                    help="how many copies (default 1)")
    cl.add_argument("--pad", action="store_true",
                    help="drum pad: give each copy the next free ReceivingNote")
    cl.add_argument("--stride", type=int,
                    help="give each copy its own block of STRIDE macros "
                         "instead of ganging every copy to the same ones")

    b = sub.add_parser("build", help="compile a spec into rack presets")
    b.add_argument("spec", help="a Python file declaring racks")
    b.add_argument("-o", "--out", default="build", help="output directory")
    b.add_argument("--only", nargs="+", help="build only these racks, by name")

    ck = sub.add_parser("check", help="would Live accept this file?")
    ck.add_argument("src")

    ex = sub.add_parser("extract", help="emit DSL source for a saved rack")
    ex.add_argument("src")

    i = sub.add_parser("ids", help="S6: census of id fields and their scope")
    i.add_argument("src")
    i.add_argument("--fields", help=f"comma separated, default {','.join(ID_FIELDS)}")

    args = p.parse_args()

    if args.cmd == "extract":
        from . import extract
        extract.report(args.src)
    elif args.cmd == "unpack":
        print(io.unpack(args.src, args.out))
    elif args.cmd == "repack":
        print(io.repack(args.src, args.dest))
    elif args.cmd == "diff":
        diff.report(args.a, args.b, hide_ids=args.hide_ids,
                    show_all=args.show_all, grep=args.grep, limit=args.limit)
    elif args.cmd == "roundtrip":
        ok = roundtrip.check(args.src, args.out)
        raise SystemExit(0 if ok else 1)
    elif args.cmd == "mappings":
        mappings.report(args.src)
    elif args.cmd == "variations":
        variations.report(args.src)
    elif args.cmd == "clone":
        root = io.load(args.src)
        preset = find.preset(root)
        chains = find.branches(preset)
        if not 0 <= args.chain < len(chains):
            raise SystemExit(
                f"chain {args.chain} out of range; file has {len(chains)}")
        target = chains[args.chain]
        report = None
        if args.stride:
            made, report = clone.clone_branch_per_macro(
                target, args.count, args.stride)
            if args.pad:
                notes = clone.free_receiving_notes(preset, len(made))
                for dup, n in zip(made, notes):
                    clone.set_receiving_note(dup, n)
        else:
            made = (clone.clone_pad(preset, target, args.count) if args.pad
                    else clone.clone_branch(target, args.count))
        clone.assert_loadable(root)
        io.save(root, args.dest)
        print(f"cloned <{target.tag}> x{args.count} -> {len(chains) + len(made)} chains")
        for m in made:
            zs = m.find("ZoneSettings")
            note = zs.find("ReceivingNote").get("Value") if zs is not None else None
            print(f"  new Id={m.get('Id')}" + (f"  ReceivingNote={note}" if note else ""))
        if report:
            for dup, moved, skipped in report:
                for tag, was, now in moved:
                    print(f"    Id={dup.get('Id')} {tag}: macro {was} -> {now}")
                for tag, was, now in skipped:
                    print(f"    Id={dup.get('Id')} {tag}: macro {was} -> {now} "
                          f"OUT OF RANGE, left on {was}")
        print(f"wrote {args.dest}")
    elif args.cmd == "build":
        try:
            compile_spec.report(args.spec, args.out, args.only)
        except compile_spec.SpecError as e:
            raise SystemExit(f"spec error: {e}")
    elif args.cmd == "check":
        bad = ids.report(args.src)
        raise SystemExit(1 if bad else 0)
    elif args.cmd == "ids":
        fields = tuple(args.fields.split(",")) if args.fields else ID_FIELDS
        ids.report(args.src, fields)


if __name__ == "__main__":
    main()
