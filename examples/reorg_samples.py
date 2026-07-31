"""Sort a drop folder of samples into the per-rack tree.

    python examples/reorg_samples.py                 # say what would happen
    python examples/reorg_samples.py --apply         # do it
    python examples/reorg_samples.py --explain       # show WHY each file landed

Drop anything into `samples/all/`, in whatever shape it was packaged in,
and this puts a copy of each file where a rack will find it. Nothing is
moved or deleted: the drop folder is left exactly as it was, so a wrong
classification costs a re-run and not a file.

`samples/README.md` is the contract this writes to. It lives in `examples/`
because it is full of the words `kick` and `snare`, and CLAUDE.md rule 6
keeps those out of `patchbay/`.

## The pipeline

Classification is a list of STAGES, tried in order, first verdict wins.
Each stage answers from a different kind of evidence, and a stage that
cannot answer returns nothing rather than guessing:

    1. FolderFormStage  a folder that says LOOP, whatever the file is named
    2. NameStage        a regex over the filename
    3. FolderStage      the same regexes over the enclosing folder names

A stage records itself on the verdict, so `--explain` says which evidence
decided each file and every classification is answerable. That is the whole
reason for the structure: **the third stage is audio analysis** - transient,
pitch, length, brightness - and it needs somewhere to plug in that does not
mean rewriting the other two. `doc/TODO.md` has that design.

## Where the rules came from

Not invented. Derived from 1332 files across ten commercial packs sitting
in `samples/all/`, by token frequency and then by checking what each rule
actually caught. Two things that survey settled:

**Bare `oh` is not an open hat.** It matched exactly one file in 1332 and
that file was `..._Vocal_Oh`. An open hat is spelled with `hat` or `ohh`
in every pack here, so the abbreviation costs more than it earns.

**`tom`, `rim`, `ride`, `crash`, `sub` and `808` matched nothing at all.**
Their rules stay because the pads exist, not because this drop needed them.

## Ordering

The rules are one ordered list and the FIRST MATCH WINS, so the order is
the design. Specific before general, always:

    loop before everything a `kick_loop` is a loop, not a kick
    ohat before hat        "open_hat" contains "hat"
    clap, rim before snare a pack that ships "snare_clap" means the clap
    crash, ride before cy  the abbreviation is the fallback (all in misc)

Abbreviations are matched at word boundaries only. Bare `bd` inside
`bd_01` is a kick; inside `abdomen` it is nothing, and `\\b` is what keeps
those apart.

The dictionary began as `trackster`'s, a Circuit Tracks tool of the same
author's, which classifies for a 2-page 64-pad grid. Its merges did not
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
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from patchbay import samples                        # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
DROP = SAMPLES / "all"
MANIFEST = SAMPLES / "manifests" / "reorg_log.csv"


@dataclass(frozen=True, slots=True)
class Rule:
    """One category, where it lands, and what names mean it.

    `dest` is a path under `samples/`, which is the per-rack scheme
    `samples/README.md` documents: `<RACK>/<category>/` for a rack with
    categories, `<RACK>/` for a flat one.

    **`dest = None` means recognised and deliberately not placed.** Only
    `samples/<RACK>/` is ever read by a build, so sorting a file no rack
    can play would create a folder nothing opens. Saying so is more useful
    than either inventing a home for it or failing to classify it.
    """

    category: str
    dest: str | None
    patterns: tuple[str, ...]

    def matches(self, text: str) -> bool:
        return any(re.search(p, text, re.I) for p in self.patterns)


#: Ordered. First match wins. Counts in the comments are hits over the 1332
#: files surveyed in `samples/all/`, so a rule with 0 is carried for a pad
#: that exists rather than for evidence that arrived.
RULES: tuple[Rule, ...] = (
    # A LOOP FIRST, whatever instrument is in it. `kick_loop_120bpm` is not
    # a kick a pad can play: it is bar length and tempo locked, and a pad
    # holding one is unplayable. This is the only rule about the FORM of the
    # audio rather than its sound, which is why it outranks all of them.
    #
    # `mix` is here because `Kit 01 Full Mix 126 G#` is a bar of the whole
    # kit, and `sequence`/`sq` because a sequence is a loop by another name.
    #
    # NOT PLACED. No rack here plays a loop: a pad is a one-shot and SR1
    # walks one-shots too. Recognising them is what keeps 271 files out of
    # the pads; giving them a folder would only be a folder nothing reads.
    Rule("loop", None,
         (r"\bloop\b", r"\d{2,3}\s?bpm", r"\bbreak\b", r"\bfull.?mix\b",
          r"\bmix\b", r"\bsequence\b", r"\bsq\b")),                    # 239

    # Bare `oh` is deliberately absent: see the module docstring.
    Rule("ohat", "DR1/ohat", (r"open.?hat", r"\bohh\b", r"\boh.?hat\b")),  # 0
    Rule("hat", "DR1/hat",
         (r"closed.?hat", r"\bch\b", r"hi.?hat", r"\bhh\b", r"hat")),  # 147
    Rule("clap", "DR1/clap", (r"clap", r"\bclp\b", r"\bcp\b", r"snap")),  # 50
    Rule("rim", "DR1/rim", (r"\brim", r"\brs\b", r"side.?stick")),        # 0
    Rule("snare", "DR1/snare", (r"snare", r"\bsd\b", r"\bsnr\b")),       # 70
    Rule("kick", "DR1/kick",
         (r"kick", r"\bbd\b", r"bass.?drum", r"\b808\b", r"thump",
          r"\bbdrum")),                                                # 144
    Rule("tom", "DR1/tom", (r"\btom\b", r"\btm\b", r"conga", r"bongo")),  # 0

    # The pad is MISC, and `perc` stays in the patterns because that is the
    # word packs put in filenames. A category name and a filename token are
    # two different things and only the first is ours to choose.
    #
    # `glitch` is here rather than in fx because the pack that ships 72 of
    # them files them under Drums: they are percussive one-shots, and a pad
    # is where they are playable.
    Rule("misc", "DR1/misc",
         (r"perc", r"glitch", r"shaker", r"tamb", r"cowbell", r"clave",
          r"wood", r"block", r"click", r"\bcym", r"\bcy\b", r"\bpc\b",
          # Cymbals land here rather than in a `cymbals/` folder of their
          # own. There are eight pads and none of them is a crash, so misc
          # is the pad that plays one.
          r"crash", r"splash", r"\bride\b", r"\bbell\b")),               # 357

    # Everything with no pad: atmospheres, alarms, drones, speech, stabs.
    Rule("fx", "SR1",
         (r"\bfx\b", r"vox", r"vocal", r"voice", r"\bhit\b", r"stab",
          r"impact", r"riser", r"sweep", r"nois", r"drop", r"chord",
          r"\bsyn\b", r"\bsy\b", r"synth", r"drone", r"atmo", r"alarm",
          r"\btalk\b", r"screech", r"siren",
          # A bass one-shot has no pad, so SR1 is where it goes. Five files
          # here are `..._BASS_126_Gm_7`: they carry a tempo AND a key and
          # are probably bars rather than hits. The NAME cannot settle it
          # and LENGTH would, which is the audio stage's first job.
          r"\bbass\b")),                                               # 287
)


@dataclass(frozen=True, slots=True)
class Verdict:
    """What a file was classified as, and what decided it."""

    category: str
    dest: str | None
    stage: str
    evidence: str


#: The loop tokens that are safe to read off a FOLDER name. `bpm` and
#: `mix` are absent: `Kit 01 G# 126 BPM/` holds one-shots, so a tempo in a
#: folder name describes the kit rather than the file.
FOLDER_LOOP = Rule("loop", None, (r"\bloop", r"\bbreak\b", r"\bsequence\b"))


class FolderFormStage:
    """A folder that says LOOP, before any rule about what the sound is.

    Form outranks sound on ANY evidence, not just on the filename. A pack
    filed under `loops/kick/` and named `kick_004.wav` is a bar of kick, and
    reading the name first puts it on the kick pad where it is unplayable.
    That is not hypothetical: it is what happened when 20 such files were
    reclaimed into the drop.

    Only the unambiguous tokens, for the reason `FolderStage` gives.
    """

    name = "folder-form"

    def verdict(self, path: Path) -> Verdict | None:
        for parent in path.parents:
            if parent == DROP or DROP not in parent.parents:
                break
            if FOLDER_LOOP.matches(_normalise(parent.name)):
                return Verdict(FOLDER_LOOP.category, FOLDER_LOOP.dest,
                               self.name, parent.name)
        return None


class NameStage:
    """The filename, which is what survives a pack being copied around.

    A pack's own directory tree says what the vendor thought; the filename
    travels with the file. Separators are normalised to spaces first, so
    `TR808-Kick_01` and `TR808 kick 01` read the same and a `\\b`
    abbreviation is not defeated by a hyphen.
    """

    name = "name"

    def __init__(self, rules: tuple[Rule, ...]) -> None:
        self.rules = rules

    def verdict(self, path: Path) -> Verdict | None:
        text = _normalise(path.stem)
        for rule in self.rules:
            if rule.matches(text):
                return Verdict(rule.category, rule.dest, self.name, path.stem)
        return None


class FolderStage:
    """The enclosing folders, nearest first. A fallback, not a peer.

    Some packs number their files and put the sound in the folder:
    `EBM_SYN/EBM_1.wav`. The folder is weaker evidence, because a file in
    `Kicks/` may still be a kick LOOP, so this runs only when the name said
    nothing at all.

    **The loop rule is skipped here**, and that is not an oversight.
    `Dark Magic - Techno City/Kit 01 G# 126 BPM/` holds one-shots, and a
    tempo in a FOLDER name describes the kit rather than the file. Applied
    to folders, the `bpm` pattern would call every one of them a loop.
    """

    name = "folder"

    def __init__(self, rules: tuple[Rule, ...]) -> None:
        self.rules = tuple(r for r in rules if r.category != "loop")

    def verdict(self, path: Path) -> Verdict | None:
        for parent in path.parents:
            if parent == DROP or DROP not in parent.parents:
                break
            text = _normalise(parent.name)
            for rule in self.rules:
                if rule.matches(text):
                    return Verdict(rule.category, rule.dest, self.name,
                                   parent.name)
        return None


#: Tried in order, first verdict wins. Audio analysis becomes a third entry
#: here and nothing above it changes. `doc/TODO.md` has the design.
PIPELINE = (FolderFormStage(), NameStage(RULES), FolderStage(RULES))


def _normalise(text: str) -> str:
    return re.sub(r"[_\-.()\[\]]+", " ", text).lower()


def classify(path: Path | str) -> Verdict | None:
    """Run the pipeline over one file. None when no stage could answer."""
    path = Path(path)
    for stage in PIPELINE:
        got = stage.verdict(path)
        if got is not None:
            return got
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


@dataclass(slots=True)
class Plan:
    """What a run would do. Nothing here has touched the disk."""

    moves: list[tuple[Path, Path, Verdict]]
    duplicates: list[Path]
    unplaced: list[tuple[Path, Verdict]]
    unknown: list[Path]


def plan() -> Plan:
    """What a run would copy, skip, leave in place, and fail to classify.

    Duplicates are exact CONTENT matches against what is already in the
    destination, which is what a second copy of the same pack produces.
    Two takes that merely sound alike are not caught, and are not meant to
    be: that is a listening decision.
    """
    if not DROP.is_dir():
        return Plan([], [], [], [])

    known: dict[str, set[str]] = {}
    counters: dict[str, int] = {}
    made = Plan([], [], [], [])

    for src in samples.audio(DROP, recursive=True):
        got = classify(src)
        if got is None:
            made.unknown.append(src)
            continue
        if got.dest is None:
            made.unplaced.append((src, got))
            continue
        folder = SAMPLES / got.dest

        if got.dest not in known:
            known[got.dest] = {_digest(p) for p in samples.audio(folder)}
            counters[got.dest] = _next_index(folder, got.category)

        mine = _digest(src)
        if mine in known[got.dest]:
            made.duplicates.append(src)
            continue
        known[got.dest].add(mine)

        dst = folder / (f"{got.category}_{counters[got.dest]:03d}"
                        f"{src.suffix.lower()}")
        counters[got.dest] += 1
        made.moves.append((src, dst, got))
    return made


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true",
                    help="copy the files. Without it, nothing is written")
    ap.add_argument("--explain", action="store_true",
                    help="per file, which stage decided it and on what")
    args = ap.parse_args()

    if not DROP.is_dir():
        print(f"nothing to do: {DROP} does not exist")
        print("create it and drop samples in, in any shape.")
        return 0

    got = plan()
    if not (got.moves or got.duplicates or got.unplaced or got.unknown):
        print(f"{DROP} holds no audio")
        return 0

    per_dest: dict[str, int] = {}
    per_stage: dict[str, int] = {}
    for _, dst, why in got.moves:
        key = dst.parent.relative_to(SAMPLES).as_posix()
        per_dest[key] = per_dest.get(key, 0) + 1
        per_stage[why.stage] = per_stage.get(why.stage, 0) + 1

    print(f"{'copying' if args.apply else 'would copy'} "
          f"{len(got.moves)} file(s):")
    for dest in sorted(per_dest):
        print(f"  {dest:<16} {per_dest[dest]:>4}")
    if got.duplicates:
        print(f"  {'already there':<16} {len(got.duplicates):>4} (same content)")
    if got.unplaced:
        kinds = sorted({w.category for _, w in got.unplaced})
        print(f"  {'not placed':<16} {len(got.unplaced):>4} "
              f"({', '.join(kinds)}: no rack plays these)")
    if got.unknown:
        print(f"  {'UNCLASSIFIED':<16} {len(got.unknown):>4} "
              f"(left where they are)")
    print("decided by: " + ", ".join(f"{k} {v}" for k, v in
                                     sorted(per_stage.items())))

    if args.explain:
        for src, dst, why in got.moves:
            print(f"    {why.category:<6} {why.stage:<7} "
                  f"{why.evidence[:44]:<46} -> "
                  f"{dst.relative_to(SAMPLES).as_posix()}")
        for src, why in got.unplaced:
            print(f"    {why.category:<6} {why.stage:<7} "
                  f"{why.evidence[:44]:<46} -> not placed")
        for p in got.unknown:
            print(f"    ?      -       {p.relative_to(DROP).as_posix()[:44]}")

    if not args.apply:
        print("\nnothing written. Re-run with --apply.")
        return 0

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    with open(MANIFEST, "a", encoding="utf-8", newline="\n") as log:
        for src, dst, _ in got.moves:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            log.write(f"{src},{dst},{stamp}\n")
    print(f"\n{len(got.moves)} copied, logged to "
          f"{MANIFEST.relative_to(ROOT)}")
    print(f"{DROP.relative_to(ROOT)} is untouched. Delete it when satisfied.")
    if got.unplaced:
        print(f"{len(got.unplaced)} recognised and left alone: no rack reads "
              f"anything outside samples/<RACK>/.")
    if got.unknown:
        print(f"{len(got.unknown)} file(s) classified as nothing. Rename them "
              f"so the sound is in the name, or add a pattern to RULES.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
