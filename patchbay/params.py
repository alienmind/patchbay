"""Read and write parameter values, ranges and macro mappings.

Three scales coexist in this format and mixing them up is the likeliest
source of silently wrong output (ARCHITECTURE.md section 12):

  device parameters   native units, per-parameter range
  macros, variations  0..127 continuous
  sends               linear amplitude, 0.000316..1

A send has a fourth: where its SLIDER sits, which is not its stored value.
`send_amplitude` converts, and Q8 measured the curve.

Everything here is explicit about which one it is dealing with.
"""

import math

MACRO_MAX = 127.0

# A macro mapping is a KeyMidi element inside the target parameter,
# encoding a virtual MIDI CC. Channel 16 is the macro bus; the CC number
# is the zero-based macro index. See ARCHITECTURE.md section 5.
MACRO_CHANNEL = "16"


def _num(text, default=None):
    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def value(param_el):
    """The parameter's value in its own units. None if not numeric."""
    manual = param_el.find("Manual")
    return None if manual is None else _num(manual.get("Value"))


def raw_value(param_el):
    """The parameter's value as written, so booleans and enums survive."""
    manual = param_el.find("Manual")
    return None if manual is None else manual.get("Value")


def set_value(param_el, v):
    """Set the parameter's value, in its own units."""
    manual = param_el.find("Manual")
    if manual is None:
        raise ValueError(f"<{param_el.tag}> has no Manual child")
    manual.set("Value", _fmt(v))
    return param_el


def set_raw(el, v):
    """Set a plain setting's value, which lives on the element itself.

    The counterpart to `set_value`, for an element with no `Manual` to put
    it in. See `find.settings`.
    """
    el.set("Value", _fmt(v))
    return el


def fmt(v):
    """Format a value the way Live writes it: no trailing .0, bools as words."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


_fmt = fmt


def range_of(param_el):
    """(min, max) - the range a macro drives this parameter across.

    This is MidiControllerRange, confirmed by S10 to be the *mapping*
    range: narrowing it narrows what the macro reaches.
    """
    r = param_el.find("MidiControllerRange")
    if r is None:
        return None
    return (_num(r.find("Min").get("Value")), _num(r.find("Max").get("Value")))


def set_range(param_el, lo, hi):
    """Set the range a macro drives this parameter across.

    Live 12.4.3 offers no way to do this through its UI - not on the
    macro, the target, or in Map mode - so this is a capability the file
    format has and the GUI does not.
    """
    r = param_el.find("MidiControllerRange")
    if r is None:
        raise ValueError(f"<{param_el.tag}> has no MidiControllerRange")
    r.find("Min").set("Value", _fmt(lo))
    r.find("Max").set("Value", _fmt(hi))
    return param_el


def macro_to_value(macro_pos, lo, hi):
    """Where a macro position lands, given the target's range.

    Linear across the range, verified on two parameters with different
    ranges. See ARCHITECTURE.md section 5.
    """
    return lo + (macro_pos / MACRO_MAX) * (hi - lo)


def value_to_macro(v, lo, hi):
    """The macro position that puts a parameter at v. Inverse of the above."""
    if hi == lo:
        return 0.0
    return (v - lo) / (hi - lo) * MACRO_MAX


def macro_position_for(param_el, v):
    """The macro position that puts this parameter at value v."""
    r = range_of(param_el)
    if r is None:
        raise ValueError(f"<{param_el.tag}> has no range")
    return value_to_macro(v, *r)


# --- macro mappings -------------------------------------------------------

def is_mapped(param_el):
    """A KeyMidi child means mapped. It is written lazily, only on mapping."""
    return param_el.find("KeyMidi") is not None


def mapped_macro(param_el):
    """Which macro drives this parameter, 1-based. None if unmapped."""
    km = param_el.find("KeyMidi")
    if km is None:
        return None
    cc = km.find("NoteOrController")
    if cc is None or not (cc.get("Value") or "").lstrip("-").isdigit():
        return None
    return int(cc.get("Value")) + 1


def map_to_macro(param_el, n):
    """Map this parameter to macro n, 1-based to match Live's UI.

    Inserts the KeyMidi block after LomId and before Manual, matching where
    Live writes it. Whether Live cares about that order is untested, so we
    match it rather than find out.

    The parameter must live in the BranchPresets subtree of the rack whose
    macro n is - there is nothing else to register, because the mapping is
    addressed by containment.
    """
    from lxml import etree

    if not 1 <= n <= 16:
        raise ValueError(f"macro must be 1..16, got {n}")

    unmap(param_el)

    km = etree.Element("KeyMidi")
    for tag, val in (("PersistentKeyString", ""),
                     ("IsNote", "false"),
                     ("Channel", MACRO_CHANNEL),
                     ("NoteOrController", str(n - 1)),
                     ("LowerRangeNote", "-1"),
                     ("UpperRangeNote", "-1"),
                     ("ControllerMapMode", "0")):
        etree.SubElement(km, tag).set("Value", val)

    lom = param_el.find("LomId")
    if lom is not None:
        lom.addnext(km)
    else:
        param_el.insert(0, km)
    return km


def unmap(param_el):
    """Remove any macro mapping. Returns True if one was there."""
    km = param_el.find("KeyMidi")
    if km is None:
        return False
    param_el.remove(km)
    return True


# --- sends ----------------------------------------------------------------

SEND_FLOOR = 0.0003162277571   # 10 ** (-70/20), Live's silent floor


def send_amount(mixer_el, index):
    """A chain's send level to return `index`, as linear amplitude."""
    infos = mixer_el.find("SendInfos")
    if infos is None:
        return None
    for info in infos:
        idx = info.find("Index")
        if idx is not None and idx.get("Value") == str(index):
            return value(info.find("Send"))
    return None


def set_send_amount(mixer_el, index, amplitude):
    """Set a chain's send level. Linear amplitude, not dB and not 0..127."""
    infos = mixer_el.find("SendInfos")
    if infos is None:
        raise ValueError("mixer has no SendInfos")
    for info in infos:
        idx = info.find("Index")
        if idx is not None and idx.get("Value") == str(index):
            return set_value(info.find("Send"), amplitude)
    raise ValueError(f"no send with Index {index}; add a return chain first")


#: A send slider loses 20 dB per HALVING of its travel: full is 0 dB, half
#: is -20 dB, a quarter is -40 dB. Measured in Live 12.4.3, Q8.
SEND_DB_PER_HALVING: float = 20.0

#: Which makes the stored amplitude the slider position raised to
#: log2(10) = 3.3219, since 10^(log2(x)) is x^log2(10).
SEND_EXPONENT: float = math.log2(10.0)

#: Live's silent floor, 10^(-70/20), reached at 8.8 percent of the travel.
#: Below that the slider reads -inf and nothing stores lower.
SEND_FLOOR: float = 0.0003162277571


def send_amplitude(knob: float) -> float:
    """The stored send value for a slider `knob` fraction of the way up.

    `knob` is 0..1, the POSITION of the slider, which is neither the stored
    amplitude nor a macro's 0..127. Three scales already, and this is the
    conversion between the first two.
    """
    if not 0.0 <= knob <= 1.0:
        raise ValueError(f"a send slider position is 0..1, got {knob:g}")
    if knob == 0.0:
        return SEND_FLOOR
    return max(knob ** SEND_EXPONENT, SEND_FLOOR)


def send_knob(amplitude: float) -> float:
    """Where the slider sits for a stored amplitude. Inverse of the above."""
    if amplitude <= SEND_FLOOR:
        return 0.0
    return amplitude ** (1.0 / SEND_EXPONENT)
