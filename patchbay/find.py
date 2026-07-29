"""Locate nodes in a preset tree.

The navigation here follows ARCHITECTURE.md section 3: a rack preset is a
GroupDevicePreset with two sibling subtrees. Device holds what the rack
IS - its macros, its chain selector. BranchPresets holds what the rack
CONTAINS - its chains and their devices.

Getting that backwards is the single easiest mistake to make in this
format, so every helper here is explicit about which side it walks.
"""

RACK_TAGS = ("AudioEffectGroupDevice", "InstrumentGroupDevice",
             "DrumGroupDevice", "MidiEffectGroupDevice")

# Nodes that wrap a real device inside a chain.
DEVICE_WRAPPERS = ("AbletonDevicePreset", "GroupDevicePreset")

# Children of a device node that are bookkeeping rather than parameters.
NON_PARAMS = {
    "LomId", "LomIdView", "IsExpanded", "BreakoutIsExpanded",
    "ModulationSourceCount", "ParametersListWrapper", "Pointee",
    "LastSelectedTimeableIndex", "LastSelectedClipEnvelopeIndex",
    "LastPresetRef", "LockedScripts", "IsFolded", "ShouldShowPresetName",
    "UserName", "Annotation", "SourceContext", "MpePitchBendUsesTuning",
    "ViewData", "OverwriteProtectionNumber",
}


def preset(root):
    """The outermost GroupDevicePreset, i.e. the rack this file describes."""
    if root.tag == "GroupDevicePreset":
        return root
    found = root.find("GroupDevicePreset")
    if found is None:
        found = next(root.iter("GroupDevicePreset"), None)
    return found


def rack_device(preset_el):
    """The rack's own device node - where macros and the chain selector live.

    This is Device/<X>GroupDevice, NOT anything under BranchPresets.
    """
    dev = preset_el.find("Device")
    if dev is None:
        return None
    for child in dev:
        if isinstance(child.tag, str) and child.tag in RACK_TAGS:
            return child
    return None


def branches(preset_el):
    """The rack's chains, in order."""
    container = preset_el.find("BranchPresets")
    return [] if container is None else [c for c in container
                                         if isinstance(c.tag, str)]


def return_branches(preset_el):
    """The rack's return chains, in order.

    Note the container is ReturnBranchPresets, a sibling of BranchPresets.
    The rack device's ReturnBranches element is empty in presets - see
    ARCHITECTURE.md section 12.
    """
    container = preset_el.find("ReturnBranchPresets")
    return [] if container is None else [c for c in container
                                         if isinstance(c.tag, str)]


def devices(branch):
    """Device nodes in a chain, in order.

    Returns the actual device elements (Saturator, OriginalSimpler, ...),
    unwrapping the AbletonDevicePreset that holds each one. A nested rack
    appears as its GroupDevicePreset, since that is the thing you would
    want to recurse into.
    """
    container = branch.find("DevicePresets")
    if container is None:
        return []
    out = []
    for wrapper in container:
        if not isinstance(wrapper.tag, str):
            continue
        if wrapper.tag == "GroupDevicePreset":
            out.append(wrapper)
            continue
        dev = wrapper.find("Device")
        if dev is not None:
            out.extend(c for c in dev if isinstance(c.tag, str))
    return out


def nested_racks(preset_el):
    """Immediate child racks, one per chain that contains one."""
    out = []
    for branch in branches(preset_el):
        for d in devices(branch):
            if d.tag == "GroupDevicePreset":
                out.append(d)
    return out


def walk_racks(preset_el):
    """This rack and every rack nested beneath it, depth first."""
    yield preset_el
    for child in nested_racks(preset_el):
        yield from walk_racks(child)


def param(device, path):
    """A parameter on a device, by name or by slash-separated path.

    Simple devices keep parameters as direct children - Saturator's Drive
    is `PreDrive`. Larger ones nest them: Simpler has 109 parameters and
    Operator 217, at paths like `Operator.0/Envelope/DecayTime`. Both
    address the same way here.

    Returns None when absent, which is a real state rather than an error:
    a device loads with parameters missing and Live defaults them
    (ARCHITECTURE.md section 8).
    """
    found = device.find(path)
    if found is not None and found.find("Manual") is not None:
        return found
    return None


def params(device):
    """Direct parameter children only, in document order."""
    return [c for c in device
            if isinstance(c.tag, str)
            and c.tag not in NON_PARAMS
            and c.find("Manual") is not None]


#: Subtrees a setting never comes from. A sample's path is a plain `Value`
#: like any other and `sample()` already owns it, so scanning it would have
#: two mechanisms writing one fact.
NOT_SETTINGS = {"SampleRef", "FileRef", "SourceContext", "MultiSampleMap"}


def settings(device):
    """A device's plain settings: {path: element}, at any depth.

    A SETTING is a childless element carrying its value on itself,
    `<ModulationMatrix_Target1 Value="6" />`. It is not a parameter: no
    `Manual`, no `MidiControllerRange`, so nothing can drive it and it can
    only be set. Drift keeps its modulation routing this way (Q16), which
    is why a macro bound to `Lfo_Amount` resolved and reached nothing.
    """
    out = {}
    for el in device.iter():
        if el is device or not isinstance(el.tag, str):
            continue
        if el.tag in NON_PARAMS or len(el) or el.get("Value") is None:
            continue
        path = param_path(el, device)
        if set(path.split("/")) & NOT_SETTINGS:
            continue
        out[path] = el
    return out


def setting(device, path):
    """One plain setting by path. None when absent, as `param` is."""
    return settings(device).get(path)


def param_path(el, device):
    """The slash path from a device down to one of its parameters."""
    parts = []
    while el is not None and el is not device:
        parts.append(el.tag)
        el = el.getparent()
    return "/".join(reversed(parts))


def all_params(device):
    """Every parameter at any depth, as {path: element}.

    This is what makes a device's real vocabulary visible. Use it to build
    a binding rather than guessing element names - Saturator's Drive knob
    is `PreDrive` and its Output is `PostDrive`, and no amount of reasoning
    gets you there.
    """
    out = {}
    for el in device.iter():
        if el is device or not isinstance(el.tag, str):
            continue
        if el.find("Manual") is not None:
            out[param_path(el, device)] = el
    return out


def search_params(device, *words):
    """Parameter paths containing all the given words, case insensitive.

    For finding what a device actually calls the thing you mean.
    """
    words = [w.lower() for w in words]
    return sorted(p for p in all_params(device)
                  if all(w in p.lower() for w in words))


def macro(rack_dev, n):
    """Macro n as a parameter element. n is 1-based, matching Live's UI."""
    return rack_dev.find(f"MacroControls.{n - 1}")


def macro_name(rack_dev, n):
    el = rack_dev.find(f"MacroDisplayNames.{n - 1}")
    return None if el is None else el.get("Value")


def chain_selector(rack_dev):
    """The rack's chain selector, itself an ordinary mappable parameter."""
    return rack_dev.find("ChainSelector")


def mixer(branch):
    """A chain's AudioBranchMixerDevice, holding volume, pan and sends."""
    mp = branch.find("MixerPreset")
    return None if mp is None else next(mp.iter("AudioBranchMixerDevice"), None)


def zone(branch):
    """A chain's BranchSelectorRange: Min, Max, CrossfadeMin, CrossfadeMax."""
    return branch.find("BranchSelectorRange")
