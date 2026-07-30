"""PATCHBAYGROUND as a Live Set: eight tracks, six returns, every rack placed.

`doc/PATCHBAYGROUND.md` describes the Set. `patchbayground.py` declares the
racks. This is the third piece: which rack sits on which track, in what
order, and what the returns are called.

    patchbay session examples/patchbayground_set.py -o build/PATCHBAYGROUND.als

The strip is the same six racks on every track, named for the track they
sit on, which is what `STRIP_INSTANCES` in `patchbayground.py` generates.
Channel EQ stays stock, per the spec, so it is placed as a bare device
rather than wrapped in a rack.

What this file cannot state, because it is not in the format:

- **Output routing into PM1.** Live writes a routing target for a track
  feeding another track and no factory Set here has one to copy, so the
  shape is unknown and guessing it would be inventing intent. Seven
  dropdowns, once.
- **The sidechain source on each EQC.** Not in a device preset at all
  (Q18), not in the LOM, so it is manual wherever it comes from.
- **What the returns SOUND like.** Each carries a stock device at Live's
  defaults. Two reverbs and two delays of contrasting length is what the
  spec asks for, and contrasting is a decision by ear.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from patchbay import clone, io                     # noqa: E402
from patchbay.library import Library               # noqa: E402
from patchbay.live_set import Session, Track       # noqa: E402

import patchbayground as pb                        # noqa: E402

BUILD = Path(__file__).resolve().parent.parent / "build"

#: Which instrument rack each track carries. SR1 is absent from
#: `patchbayground.py` because it is blocked on samples, so its track is
#: built with the strip and no instrument: the strip is the useful half and
#: an empty track says what is missing more honestly than a stand-in.
INSTRUMENT_ON = {
    "DR1": "DR1",
    "BS1": "BS1",
    "PD1": "PD1W",
    "LD1": "LD1",
    "SR1": None,
    "VA1": "VA1",
    "VA2": "VA1",
    "PM1": None,
}

#: Named for character, not for device, per PATCHBAYGROUND.md. The first
#: four are the spread it asks for; the last two are the pair it leaves to
#: us. The device on each is stock.
RETURNS = [
    ("A-Rvb:Short", "Reverb"),
    ("B-Rvb:Long", "Hybrid"),
    ("C-Dly:Short", "Delay"),
    ("D-Dly:Long", "Echo"),
    ("E-Spc:Wide", "Chorus2"),
    ("F-Drv:Grit", "Saturator"),
]


def _preset(name: str):
    """One built rack, as the preset element a Set holds."""
    path = BUILD / f"{name}.adg"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is not built. Run `patchbay build "
            f"examples/patchbayground.py -o build/` first.")
    return io.load(path).find("GroupDevicePreset")


def _stock(tag: str):
    """A bare device at donor values, placed the way a rack places one."""
    device = Library.default().instance(tag)
    device.set("Id", "0")
    clone.strip_macro_mappings(device)
    clone.fill_empty_int64_fields(device)
    clone.strip_legacy_path_elements(device)
    clone.zero_session_ids(device)
    return device


def _strip(track: str, instrument: str | None):
    """The channel strip in spec order, with the instrument third."""
    made = []
    if track != "PM1":
        made += [_preset(f"ARP1_{track}"), _preset(f"MFX1_{track}")]
    if instrument:
        made.append(_preset(instrument))
    made += [_preset(f"EQC_{track}"), _preset(f"AFX1_{track}"),
             _preset(f"AFXS1_{track}"), _stock("ChannelEq"),
             _preset(f"VOL1_{track}")]
    return made


def session() -> Session:
    tracks = []
    for name in pb.TRACKS:
        kind = "audio" if name == "PM1" else "midi"
        tracks.append(Track(name, kind, _strip(name, INSTRUMENT_ON[name])))
    returns = [(name, _stock(tag)) for name, tag in RETURNS]
    return Session(tracks, returns, tempo=120.0)


SESSION = session()
