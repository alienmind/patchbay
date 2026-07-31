"""Sort a drop folder of samples into the per-rack tree.

    python examples/reorg_samples.py                 # say what would happen
    python examples/reorg_samples.py --apply         # do it

Drop anything into `samples/all/`, in whatever shape it was packaged in,
and this puts a copy of each file where a rack will find it. Nothing is
moved or deleted: the drop folder is left exactly as it was, so a wrong
classification costs a re-run and not a file.

`samples/README.md` is the contract this writes to. It lives in `examples/`
because it is full of the words `kick` and `snare`, and CLAUDE.md rule 6
keeps those out of `patchbay/`.

## Classification

By FILENAME TOKEN, never by the folder a file arrived in. A pack's own
directory tree says what the vendor thought; the filename is what survives
being copied around, and sorting by it makes the result checkable against
the name rather than trusted.

The rules are an ordered list and the FIRST MATCH WINS, so the order is the
design. Specific before general, always:

    loop before everything a `kick_loop` is a loop, not a kick
    ohat before hat        "open_hat" contains "hat"
    clap, rim before snare a pack that ships "snare_clap" means the clap
    crash, ride before cy  the abbreviation is the fallback

Abbreviations are matched at word boundaries only. Bare `bd` inside
`bdrum_01` is a kick; inside `abdomen` it is nothing, and `\\b` is what
keeps those apart.

The dictionary is adapted from `trackster`, a Circuit Tracks tool of the
same author's, which classifies for a 2-page 64-pad grid. Its merges do not
transfer: it folds clap and rim into snare and both hats into one, because
that is what fits 64 pads. DR1 has eight pads and wants all four separate.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from patchbay import samples                        # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
DROP = SAMPLES / "all"
MANIFEST = SAMPLES / "manifests" / "reorg_log.csv"

#: Ordered. First match wins, so specific patterns come first. The
#: destination is a path under `samples/`, which is the per-rack scheme
#: `samples/README.md` documents: `<RACK>/<category>/` for a rack with
#: categories, `<RACK>/` for a flat one.
#:
#: `crash` and `ride` land in `cymbals/`, which no rack reads today. That is
#: deliberate: sorting them costs nothing and they are ready the day a pad
#: wants them.
RULES: list[tuple[str, str, list[str]]] = [
    # category      destination        patterns
    # A LOOP FIRST, whatever instrument is in it. `kick_loop_120bpm` is not
    # a kick a pad can play: it is bar length and tempo locked, and a pad
    # holding one is unplayable. This is the only rule about the FORM of the
    # audio rather than its sound, which is why it outranks all of them.
    ("loop",  "loops/misc",   [r"\bloop\b", r"\d{2,3}\s?bpm", r"\bbreak\b"]),
    ("ohat",  "DR1/ohat",     [r"\boh\b", r"open.?hat", r"\bohh?\b"]),
    ("hat",   "DR1/hat",      [r"closed.?hat", r"\bch\b", r"hi.?hat",
                               r"\bhh\b", r"hat"]),
    ("clap",  "DR1/clap",     [r"clap", r"\bclp\b", r"\bcp\b", r"snap"]),
    ("rim",   "DR1/rim",      [r"rim", r"\brs\b", r"side.?stick"]),
    ("snare",  "DR1/snare",   [r"snare", r"\bsd\b", r"\bsnr\b"]),
    ("kick",  "DR1/kick",     [r"kick", r"\bbd\b", r"bass.?drum", r"\b808\b",
                               r"thump", r"\bbdrum"]),
    ("tom",   "DR1/tom",      [r"\btom\b", r"\btm\b", r"conga", r"bongo"]),
    ("crash", "cymbals/crash", [r"crash", r"splash"]),
    ("ride",  "cymbals/ride", [r"\bride\b", r"\bbell\b"]),
    ("perc",  "DR1/perc",     [r"perc", r"shaker", r"tamb", r"cowbell",
                               r"clave", r"wood", r"block", r"click",
                               r"\bcym", r"\bcy\b", r"\bpc\b"]),
    ("fx",    "SR1",          [r"\bfx\b", r"vox", r"vocal", r"voice",
                               r"\bhit\b", r"stab", r"impact", r"riser",
                               r"sweep", r"noise", r"drop", r"chord",
                               r"synth"]),
]

COMPILED = [(name, dest, [re.compile(p, re.I) for p in pats])
            for name, dest, pats in RULES]


def classify(filename: str) -> tuple[str, str] | None:
    """The category and destination for one filename, or None.

    Matched against the STEM with separators normalised to spaces, so
    `TR808-Kick_01.wav` and `TR808 kick 01.wav` classify the same and a
    `\\b` abbreviation is not defeated by a hyphen.
    """
    text = re.sub(r"[_\-.()\[\]]+", " ", Path(filename).stem).lower()
    for name, dest, patterns in COMPILED:
        if any(p.search(text) for p in patterns):
            return name, dest
    return None


def _next_index(folder: Path, category: str) -> int:
    """One past the highest number already used in this folder.

    Existing files never renumber. `samples/README.md` says why: chain order
    is sort order, so renumbering moves what a knob position lands on.
    """
    highest = 0
    for p in samples.audio(folder):
        m = re.search(rf"{re.escape(category)}[_\-]?(\d+)", p.stem, re.I)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def _digest(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def plan() -> tuple[list[tuple[Path, Path]], list[Path], list[Path]]:
    """What a run would copy, skip as a duplicate, and fail to classify.

    Duplicates are exact CONTENT matches against what is already in the
    destination, which is what a second copy of the same pack produces.
    Two takes that merely sound alike are not caught, and are not meant to
    be: that is a listening decision.
    """
    if not DROP.is_dir():
        return [], [], []

    known: dict[str, set[str]] = {}
    moves: list[tuple[Path, Path]] = []
    duplicates: list[Path] = []
    unknown: list[Path] = []
    counters: dict[str, int] = {}

    for src in samples.audio(DROP, recursive=True):
        got = classify(src.name)
        if got is None:
            unknown.append(src)
            continue
        category, rel = got
        folder = SAMPLES / rel

        if rel not in known:
            known[rel] = {_digest(p) for p in samples.audio(folder)}
            counters[rel] = _next_index(folder, category)

        mine = _digest(src)
        if mine in known[rel]:
            duplicates.append(src)
            continue
        known[rel].add(mine)

        dst = folder / f"{category}_{counters[rel]:03d}{src.suffix.lower()}"
        counters[rel] += 1
        moves.append((src, dst))
    return moves, duplicates, unknown


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true",
                    help="copy the files. Without it, nothing is written")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="list every file, not just the counts")
    args = ap.parse_args()

    if not DROP.is_dir():
        print(f"nothing to do: {DROP} does not exist")
        print("create it and drop samples in, in any shape.")
        return 0

    moves, duplicates, unknown = plan()
    if not moves and not duplicates and not unknown:
        print(f"{DROP} holds no audio")
        return 0

    per_dest: dict[str, int] = {}
    for _, dst in moves:
        key = dst.parent.relative_to(SAMPLES).as_posix()
        per_dest[key] = per_dest.get(key, 0) + 1

    verb = "copying" if args.apply else "would copy"
    print(f"{verb} {len(moves)} file(s):")
    for dest in sorted(per_dest):
        print(f"  {dest:<16} {per_dest[dest]:>4}")
    if duplicates:
        print(f"  {'already there':<16} {len(duplicates):>4} (same content)")
    if unknown:
        print(f"  {'UNCLASSIFIED':<16} {len(unknown):>4} (left where they are)")

    if args.verbose:
        for src, dst in moves:
            print(f"    {src.name}  ->  "
                  f"{dst.relative_to(SAMPLES).as_posix()}")
        for p in unknown:
            print(f"    ?  {p.relative_to(DROP).as_posix()}")

    if not args.apply:
        print("\nnothing written. Re-run with --apply.")
        return 0

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    with open(MANIFEST, "a", encoding="utf-8", newline="\n") as log:
        for src, dst in moves:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            log.write(f"{src},{dst},{stamp}\n")
    print(f"\n{len(moves)} copied, logged to {MANIFEST.relative_to(ROOT)}")
    print(f"{DROP.relative_to(ROOT)} is untouched. Delete it when satisfied.")
    if unknown:
        print(f"{len(unknown)} file(s) classified as nothing. Rename them so "
              f"the sound is in the name, or add a pattern to RULES.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
