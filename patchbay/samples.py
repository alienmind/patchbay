"""Retarget a device's sample to a different file on disk.

S7 is the whole basis for this module being small. Live RE-READS the
sample file on load and recomputes `DefaultDuration`, `SampleEnd` and the
loop ends from what it finds. `OriginalFileSize` and `OriginalCrc` are not
validated. So the 18 other facts a real swap moves in Live are Live
keeping its own bookkeeping tidy, not requirements, and a path-only
rewrite retargets a sample.

That is also why nothing here computes a CRC. See S7 for the brute force
search that failed to identify the algorithm, and for why it stopped
mattering.

There are TWO FileRefs per sample and both must move together:

    SampleRef/FileRef                                   the live reference
    SampleRef/SourceContext/SourceContext/
              OriginalFileRef/FileRef                   provenance

Leaving the second pointing at the old file is the kind of inconsistency
that loads today and confuses a later reader, so both are written.
"""

from __future__ import annotations

from pathlib import Path

# RelativePathType values seen in real files (S7):
#   6  relative to the User Library
#   1  relative, permitted to escape upward with ".."
#   0  no relative path; resolve by the absolute Path alone
ABSOLUTE = 0

PATH_FIELDS = ("Path", "RelativePath", "RelativePathType")


def _set(ref, tag: str, value: str) -> bool:
    el = ref.find(tag)
    if el is None:
        return False
    el.set("Value", value)
    return True


def file_refs(device):
    """Both FileRefs of every sample in this device, in document order."""
    for sample_ref in device.iter("SampleRef"):
        live = sample_ref.find("FileRef")
        if live is not None:
            yield live
        for original in sample_ref.iter("OriginalFileRef"):
            ref = original.find("FileRef")
            if ref is not None:
                yield ref


def retarget(device, path: Path | str) -> int:
    """Point every sample in `device` at `path`. Returns refs rewritten.

    The absolute path is authoritative and the relative one is cleared,
    rather than left pointing at the previous file where it would be a
    stale second opinion about which sample this is.

    Forward slashes even on Windows: that is how Live writes them, in
    every FileRef in every file examined.

    Retargeting to where the device ALREADY points writes nothing. A donor
    arrives carrying its own sample, with a User Library relative path and a
    provenance ref naming where the audio came from before it was imported.
    Rewriting that pair to say the same thing in our own flattened form
    destroys the provenance and changes the file for no gain, which is what
    `patchbay extract` then has to explain as a difference.
    """
    p = Path(path).resolve()
    absolute = p.as_posix()

    live = [r.find("Path") for sr in device.iter("SampleRef")
            for r in [sr.find("FileRef")] if r is not None]
    if live and all(el is not None and el.get("Value") == absolute
                    for el in live):
        # The count, not 0: the caller reads 0 as "this device has no
        # sample to point at" and raises on it.
        return len(list(file_refs(device)))

    n = 0
    for ref in file_refs(device):
        if _set(ref, "Path", absolute):
            _set(ref, "RelativePath", "")
            _set(ref, "RelativePathType", str(ABSOLUTE))
            n += 1
    return n


def targets(device) -> list[str]:
    """Every sample path this device currently refers to. For tests."""
    out = []
    for ref in file_refs(device):
        el = ref.find("Path")
        if el is not None:
            out.append(el.get("Value"))
    return out
