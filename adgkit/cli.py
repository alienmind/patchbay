import argparse
from . import io, diff, ids, mappings, roundtrip
from .diff import ID_FIELDS


def main():
    p = argparse.ArgumentParser(prog="adgkit")
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

    t = sub.add_parser("roundtrip", help="S1: load and save unchanged, prove lossless")
    t.add_argument("src")
    t.add_argument("-o", "--out")

    m = sub.add_parser("mappings", help="list macro mappings (S3)")
    m.add_argument("src")

    i = sub.add_parser("ids", help="S6: census of id fields and their scope")
    i.add_argument("src")
    i.add_argument("--fields", help=f"comma separated, default {','.join(ID_FIELDS)}")

    args = p.parse_args()

    if args.cmd == "unpack":
        print(io.unpack(args.src, args.out))
    elif args.cmd == "repack":
        print(io.repack(args.src, args.dest))
    elif args.cmd == "diff":
        diff.report(args.a, args.b, hide_ids=args.hide_ids,
                    show_all=args.show_all, grep=args.grep)
    elif args.cmd == "roundtrip":
        ok = roundtrip.check(args.src, args.out)
        raise SystemExit(0 if ok else 1)
    elif args.cmd == "mappings":
        mappings.report(args.src)
    elif args.cmd == "ids":
        fields = tuple(args.fields.split(",")) if args.fields else ID_FIELDS
        ids.report(args.src, fields)


if __name__ == "__main__":
    main()
