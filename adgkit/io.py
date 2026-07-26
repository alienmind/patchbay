"""Read and write Ableton .adg / .adv / .als files.

All of these are gzipped XML. The only tricky part is that Live is fussy
about round-tripping, so we preserve the tree exactly and never
pretty-print on write.
"""

import gzip
from pathlib import Path
from lxml import etree


def load(path):
    """Decompress and parse. Returns an lxml ElementTree root."""
    with gzip.open(path, "rb") as f:
        data = f.read()
    return etree.fromstring(data)


def load_raw(path):
    """Decompress to raw XML bytes. Use this for diffing."""
    with gzip.open(path, "rb") as f:
        return f.read()


def save(root, path):
    """Serialise and gzip. Live rejects files with an altered declaration,
    so we force the same header Live writes."""
    body = etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=False,
        pretty_print=False,
    )
    with gzip.open(path, "wb") as f:
        f.write(body)


def unpack(src, dest=None):
    """Write the plain XML next to the source, for eyeballing in an editor."""
    src = Path(src)
    dest = Path(dest) if dest else src.with_suffix(src.suffix + ".xml")
    dest.write_bytes(load_raw(src))
    return dest


def repack(src, dest):
    """Take a hand-edited .xml back to a loadable .adg."""
    root = etree.parse(str(src)).getroot()
    save(root, dest)
    return dest
