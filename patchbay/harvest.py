"""Lift device nodes out of saved files into one donor file per device.

Harvesting never looks at preset structure. It takes any element carrying a
`LomId` and two or more parameters, so a `.als` donates its devices exactly
as a `.adg` does, and one Live Set is worth dozens of hand-saved racks.

A donor is wanted for its parameter list and each parameter's native range,
not for anybody's settings, so what is written is scrubbed: sample paths,
device names and annotations go. A donor carrying a path also carries a
sample that will not exist on another machine, and one carrying a name
shows that name in Live instead of the device's own.
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
    "MxDeviceInstrument",
    "PluginDevice", "AuPluginDevice",
}

#: Emptied on the way out. None of it says anything about what the device
#: can do, and it travels badly: a path points at a file this machine has.
#: `BrowserContentPath` is the one that hides - it is not a FileRef, it sits
#: under SourceContext, and it spells a browser location in URL escaping.
SCRUBBED = ("Path", "RelativePath", "Name", "UserName", "Annotation",
            "MemberName", "BrowserContentPath", "SearchHint",
            "OriginalFileSize", "OriginalCrc")

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
            
            # Use max device name for Max devices
            tag = el.tag
            if tag in ("MxDeviceMidiEffect", "MxDeviceAudioEffect"):
                ref = el.find(".//MxPatchRef/FileRef/RelativePath")
                if ref is not None and ref.get("Value"):
                    tag = ref.get("Value").split("/")[-1].replace(".amxd", "")
                else:
                    ref = el.find(".//MxPatchRef/FileRef/Path")
                    if ref is not None and ref.get("Value"):
                        tag = ref.get("Value").split("/")[-1].replace(".amxd", "")

            if tag not in best or n > best[tag][0]:
                best[tag] = (n, el, f)
    return best


#: `RelativePathType` 7 is Live's own installed content, seen on every
#: `AbletonDefaultPresetRef` this repo holds. A path under it is not a file
#: this machine happens to have, it is part of the device: Hybrid Reverb's
#: impulse response is one, and scrubbing it ships a donor that loads with
#: "Media files are missing".
INSTALLED_CONTENT = "7"


def _installed(node) -> bool:
    """True for a Path or RelativePath belonging to Live's own content."""
    ref = node.getparent()
    if ref is None:
        return False
    kind = ref.find("RelativePathType")
    return kind is not None and kind.get("Value") == INSTALLED_CONTENT


def scrub(el):
    """Strip paths and names in place. See SCRUBBED."""
    for tag in SCRUBBED:
        for node in el.iter(tag):
            if not node.get("Value"):
                continue
            if tag in ("Path", "RelativePath") and _installed(node):
                continue
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
