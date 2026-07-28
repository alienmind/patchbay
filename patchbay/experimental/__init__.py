"""Prototypes that are not the library yet.

Nothing here is imported by `patchbay/`. A module lands here when it has
been proved against the shipping code and is waiting on a decision in
`doc/TODO.md`, and it leaves in one of two directions: into `patchbay/`
when the decision is yes, or deleted with a note in `THE_BASEMENT.md` when
it is no.

`dsl2` is T9's prototype. It is a front end over `patchbay.dsl` and writes
no XML of its own, which is what makes "the output does not move" provable
rather than asserted.
"""
