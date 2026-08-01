"""A vocabulary of real device nodes, harvested from real files.

KICKOFF.md's donor pattern: do not generate device XML from nothing, copy
it from a rack Live actually saved. This module is the index over those
donors.

It exists because a device's true parameter names are not guessable.
Saturator's Drive knob is `PreDrive`, its Output is `PostDrive`. Operator
carries 217 parameters at paths like `Operator.0/Envelope/DecayTime`.
Any binding written from imagination is wrong; a binding written against
this index is checkable.

S12 showed devices load with parameters missing, so a donor is not needed
for a file to load - it is needed for the device to arrive *configured*,
and for us to know what it can be asked to do.
"""

import copy
from pathlib import Path

from . import find, io

# Container and wrapper nodes that carry LomId but are not instruments or
# effects in the sense we mean here.
NOT_A_DEVICE = {
    "AudioBranchMixerDevice",
    "AudioEffectGroupDevice", "InstrumentGroupDevice",
    "DrumGroupDevice", "MidiEffectGroupDevice",
}


def _max_device_name(el):
    """The AMXD name of a Max device, or its XML tag if not found."""
    tag = el.tag
    if tag not in ("MxDeviceMidiEffect", "MxDeviceAudioEffect"):
        return tag
    ref = el.find(".//MxPatchRef/FileRef/RelativePath")
    if ref is not None and ref.get("Value"):
        return ref.get("Value").split("/")[-1].replace(".amxd", "")
    ref = el.find(".//MxPatchRef/FileRef/Path")
    if ref is not None and ref.get("Value"):
        return ref.get("Value").split("/")[-1].replace(".amxd", "")
    return tag


class Device:
    """One harvested device node, plus what it can be asked to do."""

    def __init__(self, tag, element, source, named=False, params=None,
                 tier=0):
        self.tag = tag
        self._element = element
        self.source = source
        #: True when the file is named after the device, which breaks ties.
        self.named = named
        #: Which harvest path this came from. Breaks a TIE on parameter
        #: count, ahead of the named-file rule. See Library.from_paths.
        self.tier = tier
        # Harvest has already walked this subtree to count parameters, and
        # walking Operator's 217 again per access is what made a DR1 build
        # spend 27 seconds in all_params. The element is never mutated in
        # place - `instance` deepcopies - so the map cannot go stale.
        self._params = params

    @property
    def params(self):
        """{path: element} for every parameter, at any depth."""
        if self._params is None:
            self._params = find.all_params(self._element)
        return self._params

    def search(self, *words):
        """Parameter paths containing all these words. Case insensitive."""
        return find.search_params(self._element, *words)

    def range_of(self, path):
        from . import params as P
        p = find.param(self._element, path)
        return None if p is None else P.range_of(p)

    def instance(self):
        """A fresh copy, safe to insert into a tree."""
        return copy.deepcopy(self._element)

    def __repr__(self):
        return f"<Device {self.tag} {len(self.params)} params from {self.source}>"


#: One Library per root, built on first ask. See Library.default.
_DEFAULTS: dict = {}


def _forget():
    """Drop the memoised default libraries. For a test that adds a donor."""
    _DEFAULTS.clear()


class Library:
    """Devices indexed by tag, harvested from a set of files.

    When the same device appears in several files, the copy with the most
    parameters wins - a fuller donor is a better donor.
    """

    def __init__(self):
        self._devices = {}

    @classmethod
    def from_paths(cls, *paths):
        """Harvest each path, an EARLIER path breaking a tie against a later.

        A fuller copy still wins on parameter count, which is how a 12.4.3
        spike file replaced an older `MidiScale` donor that lacked
        `InternalScale`. What the tier settles is the TIE, and a tie is the
        common case: a probe cut from a donor has exactly the donor's
        parameters. Decided by filename order instead, `racks/q17_a.adg`
        redonated Operator with glide on and its filter at 30 Hz to every
        rack in the build, because `q` sorts before the `s1_source.adg` that
        had been winning.
        """
        lib = cls()
        for tier, p in enumerate(reversed(paths)):
            lib.harvest_all(p, tier=tier)
        return lib

    @classmethod
    def default(cls, root=None):
        """Harvest donors/ and racks/, in that order of preference.

        donors/ is the curated asset; racks/ is spike evidence that happens
        to contain usable devices, which is why it comes second.

        Memoised per root. Every rack build asks for this, so a DR1 build
        asked 87 times and re-read 7,511 gzip files to get the same 56
        devices back. Add a donor while a process is running and it is not
        seen; `_forget` drops the cache for a test that needs to.
        """
        root = Path(root or Path(__file__).resolve().parent.parent).resolve()
        cached = _DEFAULTS.get(root)
        if cached is None:
            cached = _DEFAULTS[root] = cls.from_paths(root / "donors",
                                                      root / "racks")
        return cached

    def harvest_all(self, path, tier=0):
        """Index one file, or every Ableton file in one directory.

        `.als` too, not only `.adg`. Harvesting never looks at preset
        structure - it takes any element carrying a LomId and two or more
        parameters - so a Live Set donates its devices exactly as a rack
        does, and one Set is worth dozens of hand-saved racks.
        """
        p = Path(path)
        if not p.is_dir():
            return self.harvest(p, tier=tier)
        for ext in ("*.adg", "*.adv", "*.als"):
            for f in sorted(p.glob(ext)):
                self.harvest(f, tier=tier)
        return self

    def harvest(self, path, tier=0):
        """Index every device node in one file.

        A fuller copy wins, and a TIE goes to the file named after the
        device. That second rule is load bearing. A one-change probe is the
        same device with the same parameter count as the donor it was cut
        from, so it ties every time, and without the rule the winner is
        decided by filename order - which is case-insensitive on Windows and
        case-sensitive elsewhere, so the same repo builds different racks on
        different machines.
        """
        try:
            root = io.load(path)
        except Exception:
            return self
        for el in root.iter():
            if not isinstance(el.tag, str) or el.tag in NOT_A_DEVICE:
                continue
            if el.find("LomId") is None:
                continue
            found = find.all_params(el)
            n = len(found)
            if n < 2:
                continue
            tag = _max_device_name(el)
            named = Path(path).stem == tag
            best = self._devices.get(tag)
            if best is None or ((n, tier, named)
                                > (len(best.params), best.tier, best.named)):
                self._devices[tag] = Device(tag, el, Path(path).name,
                                               named=named, params=found,
                                               tier=tier)
        return self

    def __contains__(self, tag):
        return tag in self._devices

    def __iter__(self):
        return iter(sorted(self._devices))

    def __len__(self):
        return len(self._devices)

    def get(self, tag):
        """The indexed device, or None."""
        return self._devices.get(tag)

    def device(self, tag):
        """The indexed device. Raises with the available list if unknown."""
        d = self._devices.get(tag)
        if d is None:
            raise KeyError(
                f"no donor for {tag!r}. Available: {', '.join(self)}.\n"
                f"Save a rack containing one into donors/ and re-harvest.")
        return d

    def instance(self, tag):
        """A fresh copy of a device node, ready to insert."""
        return self.device(tag).instance()

    def report(self):
        print(f"{len(self._devices)} device(s) indexed\n")
        for tag in self:
            d = self._devices[tag]
            print(f"  {tag:26} {len(d.params):4} params   from {d.source}")
        return self._devices
