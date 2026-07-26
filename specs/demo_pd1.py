from pathlib import Path

"""A proof that the DSL can express a real rack.

Two engines, the same grammar, different synthesis. Macro 2 moves cutoff
on both — which is the sound family constraint, expressed structurally
rather than enforced by convention.
"""

from adgkit.dsl import Grammar, Rack, RackKind

PUSH = Grammar("Engine", "Cutoff", "Resonance", "Decay",
               "Drive", "Movement", "Space", "Character")


def build(out: str = "build/demo_pd1.adg") -> "Path":
    rack = Rack("PD1 demo", PUSH, kind=RackKind.INSTRUMENT)

    with rack.engine("FM", "Operator") as e:
        e.bind(cutoff=("Filter/Frequency", 200, 8000),
               resonance="Filter/Resonance",
               decay="Filter/Envelope/DecayTime")

    with rack.engine("Sample", "OriginalSimpler") as e:
        e.bind(cutoff=("Filter/Slot/Value/SimplerFilter/Freq", 200, 8000),
               resonance="Filter/Slot/Value/SimplerFilter/Res",
               decay="Filter/Slot/Value/SimplerFilter/Envelope/DecayTime")

    return rack.save(out)


if __name__ == "__main__":
    print("wrote", build())
