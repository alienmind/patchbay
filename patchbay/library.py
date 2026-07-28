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


class Device:
    """One harvested device node, plus what it can be asked to do."""

    def __init__(self, tag, element, source, named=False):
        self.tag = tag
        self._element = element
        self.source = source
        #: True when the file is named after the device, which breaks ties.
        self.named = named

    @property
    def params(self):
        """{path: element} for every parameter, at any depth."""
        return find.all_params(self._element)

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


class Library:
    """Devices indexed by tag, harvested from a set of files.

    When the same device appears in several files, the copy with the most
    parameters wins - a fuller donor is a better donor.
    """

    def __init__(self):
        self._devices = {}

    @classmethod
    def from_paths(cls, *paths):
        lib = cls()
        for p in paths:
            lib.harvest_all(p)
        return lib

    @classmethod
    def default(cls, root=None):
        """Harvest donors/ and racks/, in that order of preference.

        donors/ is the curated asset; racks/ is spike evidence that happens
        to contain usable devices, which is why it comes second.
        """
        root = Path(root or Path(__file__).resolve().parent.parent)
        return cls.from_paths(root / "donors", root / "racks")

    def harvest_all(self, path):
        """Index one file, or every Ableton file in one directory.

        `.als` too, not only `.adg`. Harvesting never looks at preset
        structure - it takes any element carrying a LomId and two or more
        parameters - so a Live Set donates its devices exactly as a rack
        does, and one Set is worth dozens of hand-saved racks.
        """
        p = Path(path)
        if not p.is_dir():
            return self.harvest(p)
        for ext in ("*.adg", "*.adv", "*.als"):
            for f in sorted(p.glob(ext)):
                self.harvest(f)
        return self

    def harvest(self, path):
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
            n = len(find.all_params(el))
            if n < 2:
                continue
            named = Path(path).stem == el.tag
            best = self._devices.get(el.tag)
            if best is None or (n, named) > (len(best.params), best.named):
                self._devices[el.tag] = Device(el.tag, el, Path(path).name,
                                               named=named)
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
