"""Write a Live Set: tracks, returns, and racks placed on them.

`MCP.md` says a Set is the API's job and not this library's, and that was
right while the API could do it. It cannot do this one: loading a rack onto
a track means loading it BY BROWSER URI, and Live's browser index is a
snapshot taken at startup, so a rack written to the User Library five
minutes ago is not there to load. Restarting Live to pick it up defeats the
purpose of driving a running Live.

So the same trick as everywhere else here: write the file.

Set form is Q9 in `SCHEMA.md`, and `extract.preset_from_set` is this module
run backwards. What it costs is a set of TEMPLATES for the Set-form shapes,
which are taken from Live's own factory content rather than synthesised:

    Core Library/Templates/8-Track Template.als     the Set, and returns
    Core Library/Defaults/Creating Tracks/...       one MIDI, one audio track
    Core Library/Templates/Quick Start Beat.als     all four branch kinds

Nothing from those files ships in this repo. They are read from the Live
install at build time, so this module needs Live installed, which is not a
burden for something whose only output is a Live Set.

The three things the LOM cannot do at all - macro mappings, chain zones,
rack structure - are already in the `.adg` files this places, so a Set
written here arrives complete.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path

from lxml import etree

from . import find, io

Element = etree._Element

#: Where Live keeps its factory content. Overridable, because the installer
#: asks for this path and the answer is a per-machine decision.
LIVE_RESOURCES_ENV = "PATCHBAY_LIVE_RESOURCES"

#: Everything else is relative to that root.
SET_SKELETON = "Core Library/Templates/8-Track Template.als"
BRANCH_SOURCE = "Core Library/Templates/Quick Start Beat.als"
MIDI_TRACK = "Core Library/Defaults/Creating Tracks/MIDI Track/Default MIDI Track.als"
AUDIO_TRACK = "Core Library/Defaults/Creating Tracks/Audio Track/Default Audio Track.als"

#: Preset form to Set form, the other direction from `extract.BRANCH_OF`.
SET_BRANCH_OF = {
    "AudioEffectGroupDevice": ("AudioEffectBranchPreset", "AudioEffectBranch"),
    "InstrumentGroupDevice": ("InstrumentBranchPreset", "InstrumentBranch"),
    "MidiEffectGroupDevice": ("MidiEffectBranchPreset", "MidiEffectBranch"),
    "DrumGroupDevice": ("DrumBranchPreset", "DrumBranch"),
}

#: Live's silent floor for a send, the same value `dsl.SEND_FLOOR` writes
#: inside a rack. A seeded track send opens there.
SEND_FLOOR: float = 0.0003162277571

_CACHE: dict = {}


def live_resources() -> Path:
    """Live's Resources folder, from the environment or the usual places."""
    named = os.environ.get(LIVE_RESOURCES_ENV)
    if named:
        got = Path(named)
        if (got / SET_SKELETON).exists():
            return got
        raise FileNotFoundError(
            f"{LIVE_RESOURCES_ENV}={named} has no {SET_SKELETON}")
    for guess in (Path("C:/Music/Ableton/Resources"),
                  Path("C:/ProgramData/Ableton/Live 12 Suite/Resources"),
                  Path("/Applications/Ableton Live 12 Suite.app/Contents/"
                       "App-Resources")):
        if (guess / SET_SKELETON).exists():
            return guess
    raise FileNotFoundError(
        "no Live install found. Set "
        f"{LIVE_RESOURCES_ENV} to the Resources folder of your Live "
        "installation, the one holding Core Library/.")


def _factory(relative: str) -> Element:
    """One factory file, parsed once."""
    if relative not in _CACHE:
        _CACHE[relative] = io.load(live_resources() / relative)
    return _CACHE[relative]


def _template(relative: str, tag: str) -> Element:
    """A deep copy of the first `tag` in a factory file."""
    got = next(_factory(relative).iter(tag), None)
    if got is None:
        raise FileNotFoundError(f"{relative} holds no <{tag}>")
    return copy.deepcopy(got)


# --- preset form to Set form ---------------------------------------------

def _chain_container(branch: Element) -> Element:
    """A Set-form branch's `Devices`, wherever the signal type puts it.

    `MidiToAudioDeviceChain` inside an instrument branch, `AudioToAudio` in
    an effect one, `MidiToMidi` in a MIDI effect. Found rather than named,
    the same way `extract._set_devices` finds it going the other way.
    """
    chain = branch.find("DeviceChain")
    if chain is None:
        raise ValueError(f"<{branch.tag}> template has no DeviceChain")
    for kid in chain:
        devices = kid.find("Devices") if isinstance(kid.tag, str) else None
        if devices is not None:
            return devices
    raise ValueError(f"<{branch.tag}> template has no Devices")


def _device_of(preset: Element) -> Element:
    """The device inside an `AbletonDevicePreset`, or a nested rack."""
    holder = preset.find("Device")
    if holder is None:
        raise ValueError(f"<{preset.tag}> holds no Device")
    for child in holder:
        if isinstance(child.tag, str):
            return child
    raise ValueError(f"<{preset.tag}> holds an empty Device")


def _name_branch(branch: Element, text: str) -> None:
    """A chain's name is one node in a preset and four in a Set (Q9)."""
    name = branch.find("Name")
    if name is None:
        return
    for tag, value in (("EffectiveName", text), ("UserName", text),
                       ("Annotation", ""), ("MemorizedFirstClipName", "")):
        el = name.find(tag)
        if el is not None:
            el.set("Value", value)


def set_from_preset(preset: Element, position: int = 0) -> Element:
    """A `GroupDevicePreset` as the rack device a Set holds.

    The inverse of `extract.preset_from_set`, and the same mapping read the
    other way:

        Device/<X>GroupDevice          same node, Branches filled
        BranchPresets/<X>BranchPreset  -> Branches/<X>Branch
        DevicePresets/.../Device/D     -> DeviceChain/.../Devices/D
        MixerPreset/.../Device/...     -> MixerDevice
    """
    rack_dev = find.rack_device(preset)
    if rack_dev is None or rack_dev.tag not in SET_BRANCH_OF:
        raise ValueError("not a rack preset")
    preset_tag, branch_tag = SET_BRANCH_OF[rack_dev.tag]
    template = _template(BRANCH_SOURCE, branch_tag)

    made = copy.deepcopy(rack_dev)
    made.set("Id", str(position))
    branches = made.find("Branches")
    if branches is None:
        branches = etree.SubElement(made, "Branches")
    for child in list(branches):
        branches.remove(child)
    returns = made.find("ReturnBranches")
    if returns is not None:
        for child in list(returns):
            returns.remove(child)

    for i, branch_preset in enumerate(find.branches(preset)):
        branches.append(_branch_from_preset(branch_preset, i, template))

    ret_preset = preset.find("ReturnBranchPresets")
    if ret_preset is not None and len(ret_preset):
        if returns is None:
            returns = etree.SubElement(made, "ReturnBranches")
        ret_template = _template(BRANCH_SOURCE, "AudioEffectBranch")
        for i, branch_preset in enumerate(ret_preset):
            returns.append(_branch_from_preset(branch_preset, i, ret_template))
    return made


def _branch_from_preset(branch_preset: Element, position: int,
                        template: Element) -> Element:
    """One branch preset as the Set-form branch it corresponds to."""
    made = copy.deepcopy(template)
    made.set("Id", str(position))

    name = branch_preset.find("Name")
    _name_branch(made, "" if name is None else (name.get("Value") or ""))

    # What both forms carry and the Set side needs. A drum branch keeps its
    # BranchInfo, which is where the pad's note lives.
    for tag in ("IsSoloed", "BranchSelectorRange", "ZoneSettings",
                "SessionViewBranchWidth", "BranchInfo",
                "DocumentColorIndex", "AutoColored", "AutoColorScheme"):
        theirs = branch_preset.find(tag)
        if theirs is None:
            continue
        mine = made.find(tag)
        if mine is not None:
            made.replace(mine, copy.deepcopy(theirs))
        else:
            made.append(copy.deepcopy(theirs))

    devices = _chain_container(made)
    for child in list(devices):
        devices.remove(child)
    holder = branch_preset.find("DevicePresets")
    for i, device_preset in enumerate(holder if holder is not None else []):
        if device_preset.tag == "GroupDevicePreset":
            devices.append(set_from_preset(device_preset, i))
        else:
            device = copy.deepcopy(_device_of(device_preset))
            device.set("Id", str(i))
            devices.append(device)

    # The branch mixer is the one node whose TAG differs between the two
    # forms: a preset holds `MixerPreset/AbletonDevicePreset/Device/
    # AudioBranchMixerDevice`, a Set holds `MixerDevice` with the same
    # children directly under the branch. Renaming is the whole conversion.
    mixer_preset = branch_preset.find("MixerPreset")
    if mixer_preset is not None and len(mixer_preset):
        mixer = copy.deepcopy(_device_of(mixer_preset[0]))
        mixer.tag = "MixerDevice"
        mixer.attrib.pop("Id", None)
        mine = made.find("MixerDevice")
        if mine is not None:
            made.replace(mine, mixer)
        else:
            made.append(mixer)
    return made


# --- the Set itself -------------------------------------------------------

class Track:
    """One track: a name, a kind, and the racks that sit on it in order."""

    __slots__ = ("name", "kind", "presets", "color")

    def __init__(self, name: str, kind: str = "midi",
                 presets: list[Element] | None = None,
                 color: int | None = None) -> None:
        if kind not in ("midi", "audio"):
            raise ValueError(f"a track is midi or audio, not {kind!r}")
        self.name = name
        self.kind = kind
        self.presets = list(presets or [])
        self.color = color


def _name_track(track: Element, text: str) -> None:
    name = track.find("Name")
    for tag, value in (("EffectiveName", text), ("UserName", text),
                       ("Annotation", ""), ("MemorizedFirstClipName", "")):
        el = name.find(tag)
        if el is not None:
            el.set("Value", value)


def _track_devices(track: Element) -> Element:
    """A track's own `Devices`, under `DeviceChain/DeviceChain`."""
    outer = track.find("DeviceChain")
    inner = outer.find("DeviceChain")
    return inner.find("Devices")


class Session:
    """A whole Set: tracks in order, named returns, a tempo.

    A spec exports one of these as `SESSION` and `patchbay session` writes
    it, the same way a spec exports `RACKS` and `patchbay build` writes
    those.
    """

    __slots__ = ("tracks", "returns", "tempo")

    def __init__(self, tracks: list[Track], returns: list[str] | None = None,
                 tempo: float | None = None) -> None:
        self.tracks = list(tracks)
        self.returns = list(returns or [])
        self.tempo = tempo


def build_session(session: Session) -> Element:
    return build(session.tracks, session.returns, session.tempo)


def _seed_sends(track: Element, count: int, template: Element) -> None:
    """One `TrackSendHolder` per return, on this track's mixer.

    S9's rule one level up: adding a return seeds a send on every chain, and
    a Set where the counts disagree is inconsistent rather than sparse. The
    holders come from a factory template so nothing here writes a `Send`
    from nothing, and they open at the silent floor.
    """
    sends = track.find("DeviceChain/Mixer/Sends")
    if sends is None:
        raise ValueError(f"<{track.tag}> template has no Mixer/Sends")
    for child in list(sends):
        sends.remove(child)
    for i in range(count):
        holder = copy.deepcopy(template)
        holder.set("Id", str(i))
        for node in holder.iter():
            if isinstance(node.tag, str) and node.tag in ("AutomationTarget",
                                                          "ModulationTarget"):
                node.set("Id", "0")
        manual = holder.find("Send/Manual")
        if manual is not None:
            manual.set("Value", str(SEND_FLOOR))
        sends.append(holder)


def _placed(element: Element, position: int) -> Element:
    """A track device, from either a rack preset or a bare device node.

    A device that is not a rack needs no conversion at all: Q9 found the
    DEVICE node identical in both forms, and only what surrounds it is
    renamed. So a stock Channel EQ is placed as it stands.
    """
    if element.tag == "GroupDevicePreset":
        return set_from_preset(element, position)
    made = copy.deepcopy(element)
    made.set("Id", str(position))
    return made


def build(tracks: list[Track], returns: list[str] | None = None,
          tempo: float | None = None) -> Element:
    """A Live Set holding these tracks, in order, plus named returns.

    Ids are assigned by position, which is all Live asks for: unique among
    siblings (rule 2). The skeleton's own tracks are removed rather than
    reused, so nothing of Ableton's template survives except the shape.
    """
    root = copy.deepcopy(_factory(SET_SKELETON))
    live_set = root.find("LiveSet")
    container = live_set.find("Tracks")

    ret_template = None
    send_template = None
    for child in list(container):
        if child.tag == "ReturnTrack" and ret_template is None:
            ret_template = copy.deepcopy(child)
        if send_template is None:
            holder = child.find("DeviceChain/Mixer/Sends/TrackSendHolder")
            if holder is not None:
                send_template = copy.deepcopy(holder)
        container.remove(child)
    if send_template is None:
        raise ValueError(f"{SET_SKELETON} carries no TrackSendHolder")

    count = len(returns or [])
    made = 0
    for spec in tracks:
        source = MIDI_TRACK if spec.kind == "midi" else AUDIO_TRACK
        tag = "MidiTrack" if spec.kind == "midi" else "AudioTrack"
        track = _template(source, tag)
        track.set("Id", str(made))
        _name_track(track, spec.name)
        devices = _track_devices(track)
        for child in list(devices):
            devices.remove(child)
        for i, preset in enumerate(spec.presets):
            devices.append(_placed(preset, i))
        _seed_sends(track, count, send_template)
        container.append(track)
        made += 1

    for i, name in enumerate(returns or []):
        if ret_template is None:
            raise ValueError(f"{SET_SKELETON} carries no ReturnTrack to model on")
        track = copy.deepcopy(ret_template)
        track.set("Id", str(made))
        _name_track(track, name if isinstance(name, str) else name[0])
        devices = _track_devices(track)
        for child in list(devices):
            devices.remove(child)
        if not isinstance(name, str) and name[1] is not None:
            devices.append(_placed(name[1], 0))
        _seed_sends(track, count, send_template)
        container.append(track)
        made += 1

    if tempo is not None:
        for el in live_set.iter("Tempo"):
            manual = el.find("Manual")
            if manual is not None:
                manual.set("Value", str(float(tempo)))
            break
    return root


def save(root: Element, path: Path | str) -> Path:
    return io.save(root, path)


def report(spec_path, out: Path | str) -> Path:
    """Load a spec exporting SESSION and write the Set it describes."""
    from . import compile as compile_spec

    module = compile_spec.load_spec(spec_path)
    got = getattr(module, "SESSION", None)
    if got is None:
        raise compile_spec.SpecError(
            f"{Path(spec_path).name} exports no SESSION. A session spec "
            f"assigns one at module level.")
    made = save(build_session(got), out)
    print(f"{Path(spec_path).name} -> {made}")
    print(f"  {len(got.tracks)} track(s), {len(got.returns)} return(s)")
    for track in got.tracks:
        print(f"    {track.name:<6} {track.kind:<5} "
              f"{len(track.presets)} device(s)")
    for name in got.returns:
        print(f"    {name if isinstance(name, str) else name[0]}")
    return made
