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

from . import clone, find, io

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
        # A rack's RETURN chain is `<ReturnBranch>` in Set form, not
        # `AudioEffectBranch`. Live refuses the wrong one outright:
        # "Illegal class of list member (AudioEffectBranch)". Preset form
        # calls it `AudioEffectBranchPreset` whatever the parent rack is
        # (S9), so this is a second tag that differs between the forms.
        ret_template = _template(BRANCH_SOURCE, "ReturnBranch")
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
    #
    # **The template decides which of these Set form has.** Q35: a tag the
    # template lacks is a tag Set form does not carry, and appending it
    # anyway is how three of them got in. `DocumentColorIndex` is preset
    # form's name for what a Set calls `Color` and belongs on no branch;
    # `ZoneSettings` belongs on a MIDI effect and an instrument branch and
    # NOT on a drum branch, whose note is in `BranchInfo`. Live did not
    # refuse either, it crashed.
    for tag in ("IsSoloed", "BranchSelectorRange", "ZoneSettings",
                "SessionViewBranchWidth", "BranchInfo",
                "AutoColored", "AutoColorScheme"):
        theirs = branch_preset.find(tag)
        mine = made.find(tag)
        if theirs is None or mine is None:
            continue
        made.replace(mine, copy.deepcopy(theirs))

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
    """One track: a name, a kind, and the racks that sit on it in order.

    `out` names another track to feed instead of the main output, and
    `sidechain` names the track that feeds every sidechain-capable device on
    this one. Both are track NAMES here and track IDS in the file, so both
    are resolved in `build` once every track has an id.
    """

    __slots__ = ("name", "kind", "presets", "color", "out", "sidechain")

    def __init__(self, name: str, kind: str = "midi",
                 presets: list[Element] | None = None,
                 color: int | None = None, out: str | None = None,
                 sidechain: str | None = None) -> None:
        if kind not in ("midi", "audio"):
            raise ValueError(f"a track is midi or audio, not {kind!r}")
        self.name = name
        self.kind = kind
        self.presets = list(presets or [])
        self.color = color
        self.out = out
        self.sidechain = sidechain


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


def _route(node: Element, target: str, upper: str, lower: str) -> None:
    """Point one `Routable`-shaped node somewhere. Three fields, no more.

    A routing node is `Target` plus the two strings Live shows in the two
    halves of the chooser. `MpeSettings` and `MpePitchBendUsesTuning` sit
    alongside them and are the same whatever the target is, so a template
    node is edited in place rather than rebuilt.
    """
    for tag, value in (("Target", target), ("UpperDisplayString", upper),
                       ("LowerDisplayString", lower)):
        el = node.find(tag)
        if el is None:
            raise ValueError(f"<{node.tag}> is not a routing node: no {tag}")
        el.set("Value", value)


def _route_output(track: Element, target_id: int, target_name: str) -> None:
    """Send this track's audio into another TRACK rather than the main out.

    Q33. Live writes `AudioOut/Track.<id>/TrackIn`, where the id is the
    target track's `Id` attribute, not its position among the tracks. No
    factory Set carries one, so the shape is from `racks/q32_set.als`, a
    Set saved by Live with T1 routed into PM1.
    """
    node = track.find("DeviceChain/AudioOutputRouting")
    if node is None:
        raise ValueError(f"<{track.tag}> has no DeviceChain/AudioOutputRouting")
    _route(node, f"AudioOut/Track.{target_id}/TrackIn", target_name, "Track In")


def _route_sidechains(track: Element, source_id: int,
                      source_name: str) -> int:
    """Feed every sidechain on this track from another track's output.

    Q33, the same file. The source is `AudioIn/Track.<id>/PostFxOut`, which
    is what the chooser calls Post FX, and it goes in the `Routable` a
    device preset already carries pointing at `AudioIn/None` (Q18): the
    node ships in the preset, only the target is unsayable there.

    Turning the sidechain ON is a separate field and is left alone. A
    device that is not listening does not start listening because a source
    was named.
    """
    made = 0
    for chain in track.iter("SideChain"):
        node = chain.find("RoutedInput/Routable")
        if node is None:
            continue
        _route(node, f"AudioIn/Track.{source_id}/PostFxOut", source_name,
               "Post FX")
        made += 1
    return made


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

    **A send on a RETURN track is `EnabledByUser="false"`.** Q37. Every send
    on both returns of the reference Set carries it, in both directions, so
    the rule is the track kind and not the index. Writing `true` there is a
    return feeding a return feeding a return, and Live takes an access
    violation rather than refusing it. Six returns crashed; one did not.
    """
    sends = track.find("DeviceChain/Mixer/Sends")
    if sends is None:
        raise ValueError(f"<{track.tag}> template has no Mixer/Sends")
    for child in list(sends):
        sends.remove(child)
    enabled = "false" if track.tag == "ReturnTrack" else "true"
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
        flag = holder.find("EnabledByUser")
        if flag is None:
            raise ValueError("the send template carries no EnabledByUser")
        flag.set("Value", enabled)
        sends.append(holder)


def _fit_sends_pre(live_set: Element, count: int) -> None:
    """One `SendPreBool` per RETURN, on the Set itself.

    Q38. Pre/post is a property of the send SLOT, so the flags live once at
    Set level rather than per track, and the list is indexed by return.
    The skeleton has two returns and two flags; six returns over a
    two-element list is a read past the end, which is a crash and not a
    refusal.

    The skeleton's own ids are 0 and 2, so they are unique among siblings
    and nothing more (rule 2). These are written 0 upward.
    """
    holder = live_set.find("SendsPre")
    if holder is None or not len(holder):
        raise ValueError(f"{SET_SKELETON} carries no SendsPre to model on")
    template = copy.deepcopy(holder[0])
    for child in list(holder):
        holder.remove(child)
    for i in range(count):
        flag = copy.deepcopy(template)
        flag.set("Id", str(i))
        holder.append(flag)


def _fit_clip_slots(track: Element, scenes: int) -> None:
    """One clip slot per SCENE, on every clip-slot list this track has.

    Q36, and the reason four attempts crashed rather than being refused.
    The Set skeleton is the 8-Track Template, which has 8 scenes. The track
    templates are `Default MIDI Track.als` and `Default Audio Track.als`,
    which have 1 apiece. Mixing the two gives 8 scenes over tracks holding
    one slot each, and Live reads slot i of every track without checking.

    A return track has an empty `FreezeSequencer` list and no
    `MainSequencer` one, which is what Live writes, so a list that starts
    empty is left empty.
    """
    for holder in track.iter("ClipSlotList"):
        if not len(holder):
            continue
        template = copy.deepcopy(holder[0])
        for child in list(holder):
            holder.remove(child)
        for i in range(scenes):
            slot = copy.deepcopy(template)
            slot.set("Id", str(i))
            holder.append(slot)


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

    # Every track needs a clip slot per scene, and the skeleton decides how
    # many there are. Q36.
    scene_holder = live_set.find("Scenes")
    scenes = 0 if scene_holder is None else len(scene_holder)

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
    built: dict[str, Element] = {}
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
        _fit_clip_slots(track, scenes)
        container.append(track)
        if spec.name in built:
            raise ValueError(
                f"two tracks are called {spec.name!r}, so a routing target "
                f"naming it is ambiguous")
        built[spec.name] = track
        made += 1

    # Routing is resolved once every track has an id, because a track may
    # feed one declared after it.
    for spec in tracks:
        for named, apply in ((spec.out, _route_output),
                             (spec.sidechain, _route_sidechains)):
            if named is None:
                continue
            other = built.get(named)
            if other is None:
                raise ValueError(
                    f"track {spec.name!r} routes to {named!r}, which is not "
                    f"a track in this Set")
            apply(built[spec.name], int(other.get("Id")), named)

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
        _fit_clip_slots(track, scenes)
        container.append(track)
        made += 1

    _fit_sends_pre(live_set, count)
    _renumber_pointees(root)

    if tempo is not None:
        for el in live_set.iter("Tempo"):
            manual = el.find("Manual")
            if manual is not None:
                manual.set("Value", str(float(tempo)))
            break
    return root


#: The id space Live calls POINTEES: anything a clip envelope or a
#: modulation source can point at. One numbering, and
#: `LiveSet/NextPointeeId` is the next free number.
def _is_pointee(el: Element) -> bool:
    """A pointee by SHAPE, not by a list of tags.

    Naming the families was wrong and Q34 is what it cost: a track carries
    131 `ControllerTargets.N`, an indexed plural whose name says nothing,
    and Live refused the Set with `PointeeId 341 is used 8 times`, once per
    track. `racks/q9_b.als` could not have caught it - it has none.

    The shape is exact in the reference Set: an `Id` plus a lone
    `LockEnvelope` child covers 14,447 nodes, `Pointee` adds 190 more with
    no child at all, and the union of 14,637 has no duplicate, no zero, and
    a maximum one below `NextPointeeId`.
    """
    if el.get("Id") is None:
        return False
    if el.tag in ("Pointee", "AutomationTarget"):
        return True
    kids = [k.tag for k in el if isinstance(k.tag, str)]
    return kids == ["LockEnvelope"]


def _renumber_pointees(root: Element) -> int:
    """Give every pointee a unique non-zero id. Returns the next free one.

    A PRESET writes `Id="0"` on all of them - 28,214 of them in
    PATCHBAYGROUND - and a SET refuses that outright:

        The document "..." is corrupt and cannot be loaded.
        (Invalid Pointee Id.)

    Verified against `racks/q9_b.als`, a Set Live saved: 267 pointees, no
    duplicates, none zero, and `NextPointeeId` one above the highest. So
    zero is not "unassigned" here, it is invalid, and the number has to be
    handed out at write time.

    References are rewritten with the nodes: a `*PointeeId` naming an id
    that was unique before renumbering follows it to the new one.
    """
    nodes = [el for el in root.iter()
             if isinstance(el.tag, str) and _is_pointee(el)]

    seen: dict[str, int] = {}
    for el in nodes:
        got = el.get("Id")
        if got not in (None, "0"):
            seen[got] = seen.get(got, 0) + 1
    unique_before = {k for k, n in seen.items() if n == 1}

    remap: dict[str, str] = {}
    next_id = 1
    for el in nodes:
        old = el.get("Id")
        el.set("Id", str(next_id))
        if old in unique_before:
            remap[old] = str(next_id)
        next_id += 1

    for el in root.iter():
        if isinstance(el.tag, str) and el.tag.endswith("PointeeId"):
            moved = remap.get(el.get("Value"))
            if moved is not None:
                el.set("Value", moved)

    live_set = root.find("LiveSet")
    if live_set is not None:
        holder = live_set.find("NextPointeeId")
        if holder is not None:
            holder.set("Value", str(next_id))
    return next_id


def save(root: Element, path: Path | str) -> Path:
    """Write the Set, refusing one Live would reject.

    Same gate as a rack: a missing device Id or a path written in two
    formats makes Live refuse the whole document, and both are things a
    donor drags in. Fail loudly rather than write it.
    """
    clone.assert_loadable(root)
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
