"""Duplicate chains, with the one fixup Live actually requires.

S6 settled what cloning costs. An Id must be unique among its siblings and
nothing else about it matters - not contiguity, not matching the index,
not file-wide uniqueness. Give two sibling branches the same Id and Live
rejects the entire preset with a dialog.

Everything else in a branch copies verbatim:

  Macro mappings are KeyMidi elements inside their target parameters and
  are addressed by containment, so a copied mapping refers to the copy's
  own rack automatically. There is no reference to remap.

  Chain zones, sends, device parameters and sample references are all
  plain values.

So this module is deliberately small. The landmine CLAUDE.md warned about
turned out to be a single line of work; the risk was believing otherwise
and building an id-remapping engine nothing needed.
"""

import copy

from . import find
from .ids import collisions, next_free_id


def clone_branch(branch, count=1, receiving_notes=None):
    """Duplicate a chain in place, `count` times.

    Copies are inserted directly after the original, each with an Id free
    among its siblings.

    receiving_notes: for drum rack pads, the MIDI note each copy should
    answer to. Without it every copy keeps the original's ReceivingNote and
    they all trigger together - legal, loadable, and almost never what you
    want, so passing it is strongly encouraged for DrumBranchPreset.

    Returns the list of new branch elements.
    """
    container = branch.getparent()
    if container is None:
        raise ValueError("branch has no parent; pass an element still in a tree")

    if receiving_notes is not None and len(receiving_notes) != count:
        raise ValueError(
            f"receiving_notes has {len(receiving_notes)} entries for {count} copies")

    made = []
    anchor = branch
    for i in range(count):
        dup = copy.deepcopy(branch)
        dup.set("Id", next_free_id(container, branch.tag))
        anchor.addnext(dup)
        anchor = dup

        if receiving_notes is not None:
            set_receiving_note(dup, receiving_notes[i])

        made.append(dup)
    return made


def shift_macros(branch, offset):
    """Add `offset` to every macro mapping inside this branch.

    A cloned chain keeps the original's macro indices, so all copies answer
    to the same macro and move together. That is correct for ganged
    control - the sound family constraint in PATCHBAYGROUND.md wants exactly
    it - but wrong when each chain should have its own knob.

    Shifting a copy's mappings by its position gives per-chain control:
    chain 0 on macros 1..k, chain 1 on macros k+1..2k, and so on.

    Mappings that would land outside 1..16 are left alone and reported, so
    running out of macros is visible rather than silent.
    """
    from . import params

    moved, skipped = [], []
    for el in branch.iter():
        if not isinstance(el.tag, str) or el.find("KeyMidi") is None:
            continue
        current = params.mapped_macro(el)
        if current is None:
            continue
        target = current + offset
        if 1 <= target <= 16:
            params.map_to_macro(el, target)
            moved.append((el.tag, current, target))
        else:
            skipped.append((el.tag, current, target))
    return moved, skipped


def clone_branch_per_macro(branch, count, stride):
    """Duplicate a chain, giving each copy its own block of macros.

    stride is how many macros one chain uses. With stride 2, chain 0 keeps
    macros 1-2, the first copy gets 3-4, the next 5-6.
    """
    made = clone_branch(branch, count)
    report = []
    for i, dup in enumerate(made, start=1):
        moved, skipped = shift_macros(dup, i * stride)
        report.append((dup, moved, skipped))
    return made, report


#: `ReceivingNote` counts DOWN from here, so the stored value is not the
#: MIDI note. Q42: Live's own `Acuff Kit.adg` stores 92, 91, 90 ... 77 for
#: a 16 pad kit, which is notes 36 to 51, and the 909 kit in
#: `racks/q32_set.als` stores 92 for the pad Live labels Bass Drum.
#:
#: Writing the MIDI note straight in puts C1 on note 92, off the top of the
#: grid, and the rack opens with eight named chains and an empty pad
#: layout. Live neither refuses nor warns.
NOTE_ORIGIN = 128


def encode_note(note: int) -> int:
    """MIDI note to the value `ReceivingNote` stores. Its own inverse."""
    return NOTE_ORIGIN - note


def set_receiving_note(branch, note):
    """Set which MIDI note a drum pad answers to.

    Takes the MIDI note and stores what Live stores, `128 - note` (Q42).
    SendingNote stays at 60 so the chain's instrument still plays at root
    pitch - see ARCHITECTURE.md section 12.
    """
    zs = branch.find("ZoneSettings")
    if zs is None:
        raise ValueError(f"<{branch.tag}> has no ZoneSettings; not a drum pad")
    zs.find("ReceivingNote").set("Value", str(encode_note(note)))
    return branch


def free_receiving_notes(preset_el, count, start=36):
    """`count` MIDI notes not already claimed by a pad in this rack.

    36 is C1, where Live's drum grid starts.
    """
    used = set()
    for b in find.branches(preset_el):
        zs = b.find("ZoneSettings")
        if zs is not None:
            rn = zs.find("ReceivingNote")
            if rn is not None:
                used.add(encode_note(int(rn.get("Value"))))
    out, n = [], start
    while len(out) < count and n < 128:
        if n not in used:
            out.append(n)
        n += 1
    if len(out) < count:
        raise ValueError(f"only {len(out)} free notes below 128, needed {count}")
    return out


def clone_pad(preset_el, branch, count=1):
    """Duplicate a drum pad, giving each copy the next free note."""
    return clone_branch(branch, count,
                        receiving_notes=free_receiving_notes(preset_el, count))


def check(root):
    """Sibling id collisions, the one thing Live rejects outright.

    Call before writing. Returns the collision list; empty means Live will
    accept the file, verified against its behaviour on three test files.
    """
    return collisions(root)


def missing_device_ids(root):
    """Device nodes sitting in a preset holder with no `Id` of their own.

    The second id rule, and it cost a Live check to find. A device inside
    `AbletonDevicePreset/Device` is a LIST MEMBER, and Live refuses the
    whole document if one lacks an `Id`:

        Exception: Not all list members have Ids.
        The document "..." is corrupt and cannot be loaded.

    Every rack Live has saved here writes `Id="0"` there, because the
    holder holds exactly one device. A device lifted out of a `.als` does
    not: in Set form it is a member of `Devices` and carries its position
    in the track, and losing that on the way out leaves nothing behind.
    See Q9 in `SCHEMA.md`.
    """
    out = []
    for holder in root.iter("Device"):
        for child in holder:
            if isinstance(child.tag, str) and child.get("Id") is None:
                out.append(child.tag)
    return out


def strip_macro_mappings(device):
    """Remove every KeyMidi inside a device. Returns how many were removed.

    A donor is a device cut out of a rack somebody built, and a macro
    mapping is a `KeyMidi` INSIDE its target parameter, so the donor brings
    that rack's mappings with it. `Compressor2.adg` carries five, on
    Threshold, Ratio, Gain, DryWet and On, all pointing at macro 4 of a rack
    that no longer exists. Placed unchanged, macro 4 of the new rack moves
    all five.

    Same shape as the donor's Drift modulation row: a donor is for the
    parameter list and its ranges, never for anybody's decisions.
    """
    removed = 0
    for el in device.iter():
        if not isinstance(el.tag, str):
            continue
        km = el.find("KeyMidi")
        if km is not None:
            el.remove(km)
            removed += 1
    return removed


#: Ids that point into a RUNNING session. Every preset Live saved here has
#: them at 0, and a device harvested out of a `.als` carries the numbers the
#: Set was using. See Q9.
SESSION_ID_NODES = ("AutomationTarget", "ModulationTarget", "Pointee")


def session_ids(root):
    """Live-session ids on a device, which a preset never carries."""
    return [el.tag for el in root.iter()
            if isinstance(el.tag, str) and el.tag in SESSION_ID_NODES
            and el.get("Id") not in (None, "0")]


def zero_session_ids(root):
    """Point them back at nothing. Returns how many were cleared."""
    cleared = 0
    for el in root.iter():
        if isinstance(el.tag, str) and el.tag in SESSION_ID_NODES:
            if el.get("Id") not in (None, "0"):
                el.set("Id", "0")
                cleared += 1
    return cleared


#: FileRef fields Live parses as int64. Set form leaves both blank, and
#: every `.adg` Live saved here writes "0" - 12 racks, no exception. See Q9.
INT64_FILEREF_FIELDS = ("OriginalFileSize", "OriginalCrc")


def legacy_path_elements(root):
    """`RelativePath` nodes carrying BOTH a Value and child elements.

    Two eras of the same field. Live 12.4.3 writes the path as a string on
    the node, 366 times across the racks here with no exception; older Live
    wrote it as a list of `RelativePathElement` children, one per directory.
    A donor cut from an old file arrives with both, and Live refuses the
    document outright:

        Exception: Base types can't have children
        The document "..." is corrupt and cannot be loaded.

    Six donors carry it: CrossDelay, Gate, MidiNoteLength, MidiVelocity,
    Overdrive, Redux. Nothing about the device is wrong; the path is
    written twice in two formats.
    """
    out = []
    for rp in root.iter("RelativePath"):
        if rp.get("Value") is not None and len(rp):
            out.append(rp.get("Value") or "<empty>")
    return out


def strip_legacy_path_elements(root):
    """Drop the child form, keep the Value. Returns how many were cleared."""
    cleared = 0
    for rp in root.iter("RelativePath"):
        if rp.get("Value") is not None and len(rp):
            for child in list(rp):
                rp.remove(child)
            cleared += 1
    return cleared


def empty_int64_fields(root):
    """FileRef int64 fields carrying an empty Value, as a list of paths.

    The SECOND difference between Set form and preset form, and it hides
    behind the first. A device lifted out of a `.als` brings a
    `LastPresetRef/.../FileRef` whose `OriginalFileSize` and `OriginalCrc`
    are blank, which a `.als` accepts and a `.adg` does not:

        Exception: Unexpected value for int64 node:
        The document "..." is corrupt and cannot be loaded.

    Blank is not the same as absent. Live re-reads a sample on load and
    never validates the CRC, so the VALUE means nothing; the node being
    parseable is what is required.
    """
    out = []
    for ref in root.iter("FileRef"):
        for tag in INT64_FILEREF_FIELDS:
            el = ref.find(tag)
            if el is not None and el.get("Value") == "":
                out.append(tag)
    return out


def fill_empty_int64_fields(root):
    """Write "0" where Live writes "0". Returns how many were filled."""
    filled = 0
    for ref in root.iter("FileRef"):
        for tag in INT64_FILEREF_FIELDS:
            el = ref.find(tag)
            if el is not None and el.get("Value") == "":
                el.set("Value", "0")
                filled += 1
    return filled


def assert_loadable(root):
    """Raise if the tree would be refused by Live.

    Fail loudly: a corrupt .adg that Live silently half-loads is worse
    than one it rejects, and here we can know in advance.
    """
    no_id = missing_device_ids(root)
    if no_id:
        raise ValueError(
            f"{len(no_id)} device node(s) with no Id: "
            f"{', '.join(sorted(set(no_id)))}. Live refuses the whole "
            f"document with 'Not all list members have Ids'. A donor "
            f"harvested from a .als carries no Id here; see Q9.")

    legacy = legacy_path_elements(root)
    if legacy:
        raise ValueError(
            f"{len(legacy)} RelativePath node(s) carrying both a Value and "
            f"child elements. Live refuses the whole document with 'Base "
            f"types can't have children'. A donor cut from an older Live "
            f"arrives with the path written twice; see Q22.")

    blank = empty_int64_fields(root)
    if blank:
        raise ValueError(
            f"{len(blank)} FileRef int64 field(s) left empty: "
            f"{', '.join(sorted(set(blank)))}. Live refuses the whole "
            f"document with 'Unexpected value for int64 node'. A donor "
            f"harvested from a .als arrives blank here; see Q9.")

    bad = check(root)
    if bad:
        lines = "\n".join(
            f"  {count}x <{tag} Id=\"{idv}\"> under {where}"
            for where, tag, idv, count in bad)
        raise ValueError(
            f"{len(bad)} sibling id collision(s); Live would refuse this "
            f"preset:\n{lines}")
    return root


def unsourced_samples(device):
    """Sample parts whose live FileRef names no file. Returns their names.

    A harvested donor names no file, by design: `patchbay harvest` strips
    paths so a donor carries a parameter list and not somebody's kick. What
    it leaves behind is the sample PART, an entry in `SampleParts` pointing
    at an empty path, and Live reports that as a missing sample rather than
    as an empty instrument.
    """
    out = []
    for part in device.iter("MultiSamplePart"):
        ref = part.find("SampleRef/FileRef")
        if ref is None:
            continue
        path = ref.find("Path")
        if path is not None and not (path.get("Value") or ""):
            name = part.find("Name")
            out.append((name.get("Value") if name is not None else "") or "<unnamed>")
    return out


def strip_unsourced_samples(device):
    """Drop them, leaving the container. Returns how many were removed.

    Only for a device NOTHING was declared for. A device with a sample gets
    its paths written by `samples.retarget` before this could see it, and
    `Engine.sample` refuses a path that is not a file, so a blank path here
    means no caller ever named one.
    """
    removed = 0
    for part in list(device.iter("MultiSamplePart")):
        ref = part.find("SampleRef/FileRef")
        if ref is None:
            continue
        path = ref.find("Path")
        if path is not None and not (path.get("Value") or ""):
            parent = part.getparent()
            if parent is not None:
                parent.remove(part)
                removed += 1
    return removed
