"""Lift device nodes out of saved files into one donor file per device.

Harvesting never looks at preset structure. It takes any element carrying a
`LomId` and two or more parameters, so a `.als` donates its devices exactly
as a `.adg` does, and one Live Set is worth dozens of hand-saved racks.

A donor is wanted for its parameter list and each parameter's native range,
not for anybody's settings, so what is written is scrubbed: sample paths,
device names and annotations go. That matters because the file it came from
may not be ours to redistribute. Where it lands is the caller's choice and
this module does not have an opinion; the repo keeps `donors/` tracked and
`donors_local/` gitignored, and `Library.default` reads both.
"""

from __future__ import annotations

import copy
from pathlib import Path

from lxml import etree

from . import find, io
from .library import NOT_A_DEVICE

#: Tracks, chains, mixers and plugin wrappers carry a LomId and parameters
#: and are not devices anything can be asked to instantiate.
NOT_A_DONOR = NOT_A_DEVICE | {
    "LiveSet", "MidiTrack", "AudioTrack", "MainTrack", "MasterTrack",
    "ReturnTrack", "PreHearTrack", "GroupTrack", "Mixer", "MixerDevice",
    "AudioEffectBranch", "InstrumentBranch", "DrumBranch", "ReturnBranch",
    "MxDeviceAudioEffect", "MxDeviceInstrument", "MxDeviceMidiEffect",
    "PluginDevice", "AuPluginDevice",
}

#: Emptied on the way out. Paths and names are the licensed half of somebody
#: else's project and say nothing about what the device can do.
SCRUBBED = ("Path", "RelativePath", "Name", "UserName", "Annotation",
            "MemberName")

EXTENSIONS = ("*.adg", "*.adv", "*.als")


def sources(*paths) -> list[Path]:
    """Every Ableton file under these paths, files taken as given."""
    out = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for ext in EXTENSIONS:
                out += sorted(p.rglob(ext))
        else:
            out.append(p)
    return out


def scan(*paths) -> dict[str, tuple[int, object, Path]]:
    """tag -> (parameter count, element, source), keeping the fullest copy.

    A fuller donor is a better donor, which is the same rule `Library` uses
    when the same device turns up in several files.
    """
    best: dict[str, tuple[int, object, Path]] = {}
    for f in sources(*paths):
        try:
            root = io.load(f)
        except Exception:
            continue
        for el in root.iter():
            if not isinstance(el.tag, str) or el.tag in NOT_A_DONOR:
                continue
            if el.find("LomId") is None:
                continue
            n = len(find.all_params(el))
            if n < 2:
                continue
            if el.tag not in best or n > best[el.tag][0]:
                best[el.tag] = (n, el, f)
    return best


def scrub(el):
    """Strip paths and names in place. See SCRUBBED."""
    for tag in SCRUBBED:
        for node in el.iter(tag):
            if node.get("Value"):
                node.set("Value", "")
    return el


def _wrap(el):
    """One device in the smallest container `io.load` and `harvest` accept.

    Not a `GroupDevicePreset`. Nothing loads these in Live; they exist to be
    indexed, and a fake preset wrapper would invite someone to drag one in.
    """
    root = etree.Element("Ableton", MajorVersion="5",
                         MinorVersion="12.0_12203", SchemaChangeCount="3",
                         Creator="patchbay harvest", Revision="")
    etree.SubElement(root, "DonorLibrary").append(el)
    return root


def run(paths, out, known=(), prefix="h_") -> list[tuple[str, int, Path, Path]]:
    """Write one donor per device tag. Returns (tag, params, source, written).

    `known` names tags to leave alone. Displacing an indexed donor with a
    fuller copy of the same device silently rebuilds every rack that was
    gated against the old one, so the caller passes what it already has.
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    known = set(known)

    written = []
    for tag, (n, el, src) in sorted(scan(*paths).items()):
        if tag in known:
            continue
        node = scrub(copy.deepcopy(el))
        node.attrib.pop("Id", None)
        dest = out / f"{prefix}{tag}.adg"
        io.save(_wrap(node), dest)
        written.append((tag, n, src, dest))
    return written


def report(paths, out, keep_known=False) -> int:
    from .library import Library

    known = () if keep_known else set(Library.default())
    written = run(paths, out, known=known)
    for tag, n, src, dest in written:
        print(f"  {tag:26} {n:5} params  <- {src.name}")
    if known:
        print(f"\nleft alone, already indexed: {', '.join(sorted(known))}")
    print(f"\n{len(written)} donor(s) written to {out}")
    return len(written)
