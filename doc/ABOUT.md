---
title: "PatchBay"
---

# PatchBay

Build Ableton Live racks and Sets from code.

## Why this project?

Live already exposes a programming interface. The Live Object Model drives a session that is **open
and running**: create a track, name it, set its routing, fire a clip, move a parameter. Anything you
can script against a live Set, script through the LOM.

The LOM stops short in two ways. Parts of it are undocumented, and parts of what the Set contains
simply has no API at all. Grouping devices into a rack, creating a macro mapping, setting a chain
zone: none of these are in the Object Model.

PatchBay covers the other half by writing the **files**. An `.adg` is a gzipped XML document, so is
an `.als`, so is an `.adv`. What the API will not build, the file format will, and patchbay writes
and reads that XML directly.

That changes what maintenance costs. A rack or a project kept current by hand is hands on work:
every mapping clicked, every variation dialled, every fix repeated in each copy that inherited it,
and all of it held together by the author's discipline. Nothing records what changed or why, and
nothing carries a correction forward.

Declared as code, a rack gets the tools ordinary software already has. It lives in version control,
it diffs, it reviews, it rebuilds. A new Live version, a renamed parameter, or a change of taste by
whoever authored the racks is an edit to a spec and one `patchbay build`, not an afternoon of
mousing. The source of truth is the spec, and the `.adg` is output.
