"""Locate nodes in a preset tree.

The navigation here follows ARCHITECTURE.md section 3: a rack preset is a
GroupDevicePreset with two sibling subtrees. Device holds what the rack
IS — its macros, its chain selector. BranchPresets holds what the rack
CONTAINS — its chains and their devices.

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
    """The rack's own device node — where macros and the chain selector live.

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
    The rack device's ReturnBranches element is empty in presets — see
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


def param(device, name):
    """A named parameter element on a device. None if absent.

    Absent is a real possibility rather than an error: a device loads with
    parameters missing and Live defaults them (ARCHITECTURE.md section 8).
    """
    found = device.find(name)
    if found is not None and found.find("Manual") is not None:
        return found
    return None


def params(device):
    """Every parameter element on a device, in document order."""
    return [c for c in device
            if isinstance(c.tag, str)
            and c.tag not in NON_PARAMS
            and c.find("Manual") is not None]


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
