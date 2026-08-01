"""EXAMPLE_ALIENSET - an example Set combining multiple techniques

Designed for techno but also for other electronic music genres. Uses the consistent PB layout for 
instruments from playgrnd, but relies on a CPU-efficient ALIEN_FX series rack 
for effects instead of a heavy channel strip. Returns are self-contained inside the Drum Rack.

    patchbay build examples/alienset.py -o build/alienset/
    patchbay session examples/alienset.py -o build/alienset.als
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

from patchbay import clone, live_set, samples
from patchbay.dsl import Engine, Layout, Rack, Range, Slot
from patchbay.library import Library
from patchbay.live_set import Session, Track
from alienmindsequencer import get_seq_xml

# ===========================================================================
# The layout and ranges
# ===========================================================================

PB = Layout(
    Slot("Instrument", selects=True),
    Slot("Sound"),
    Slot("Filter", start=127),
    Slot("Drive"),
    Slot("Movement"),
    Slot("Character"),
    Slot("Release", start=30),
    Slot("Volume", start=127),
)

PAIRED = "Filter + Res"

CUTOFF = Range(30.0, 18500.0, "Hz")
RELEASE = Range(0.01, 20.0, "s")
RESONANCE = Range(0.0, 1.0, "")
VOLUME = Range(0.0, 1.0, "amplitude")
RELEASE_MS = RELEASE.scaled(1000.0)
GLIDE = Range(0.01, 2.0, "s")
GLIDE_MS = GLIDE.scaled(1000.0)

# ===========================================================================
# The Engines
# ===========================================================================

FM = (Engine("Operator")
      .sets("Lfo/LfoOn", True)
      .sets("Filter/LfoOn", True)
      .drives(PB.filter, "Filter/Frequency", over=CUTOFF)
      .drives(PB.filter, "Filter/Resonance", over=RESONANCE)
      .drives(PB.drive, "Filter/Drive")
      .drives(PB.movement, "Lfo/LfoAmount")
      .drives(PB.release, "Operator.0/Envelope/ReleaseTime", over=RELEASE_MS)
      .drives(PB.volume, "Globals/Volume", over=Range(0.0003162277571, 1.0, "amplitude"))
      .offers("attack", "Operator.0/Envelope/AttackTime")
      .offers("glide", "Globals/PortamentoTime", over=GLIDE_MS)
      .offers("saturation", "Shaper/Drive"))

SAMPLER = (Engine("OriginalSimpler")
           .drives(PB.filter, "Filter/Slot/Value/SimplerFilter/Freq", over=CUTOFF)
           .drives(PB.filter, "Filter/Slot/Value/SimplerFilter/Res", over=RESONANCE)
           .drives(PB.drive, "Filter/Slot/Value/SimplerFilter/Drive")
           .drives(PB.movement, "Pitch/PitchLfoAmount")
           .drives(PB.release, "VolumeAndPan/Envelope/ReleaseTime", over=RELEASE_MS)
           .drives(PB.volume, "VolumeAndPan/Volume", over=Range(-36.0, 0.0, "dB"))
           .offers("attack", "VolumeAndPan/Envelope/AttackTime")
           .offers("glide", "Globals/PortamentoTime", over=GLIDE_MS))

WAVE = (Engine("InstrumentVector")
        .drives(PB.filter, "Voice_Filter1_Frequency", over=CUTOFF)
        .drives(PB.filter, "Voice_Filter1_Resonance", over=RESONANCE)
        .drives(PB.drive, "Voice_Filter1_Drive")
        .drives(PB.release, "Voice_Modulators_AmpEnvelope_Times_Release", over=RELEASE)
        .drives(PB.volume, "Volume", over=VOLUME)
        .offers("attack", "Voice_Modulators_AmpEnvelope_Times_Attack")
        .offers("glide", "Voice_Global_Glide", over=GLIDE))

DRIFT = (Engine("Drift")
         .sets("ModulationMatrix_Source1", 2)
         .sets("ModulationMatrix_Target1", 6)
         .sets("ModulationMatrix_Amount1", 1.0)
         .drives(PB.filter, "Filter_Frequency", over=CUTOFF)
         .drives(PB.filter, "Filter_Resonance", over=RESONANCE)
         .drives(PB.movement, "Lfo_Amount")
         .drives(PB.release, "Envelope1_Release", over=RELEASE)
         .drives(PB.volume, "Global_Volume", over=VOLUME)
         .offers("attack", "Envelope1_Attack")
         .offers("glide", "Global_Glide", over=GLIDE))

MELD = (Engine("InstrumentMeld")
        .drives(PB.filter, "MeldVoice_EngineA_Filter_Frequency",
                "MeldVoice_EngineB_Filter_Frequency", over=CUTOFF)
        .drives(PB.filter, "MeldVoice_EngineA_Filter_Macro1",
                "MeldVoice_EngineB_Filter_Macro1", over=RESONANCE)
        .drives(PB.drive, "MeldVoice_Drive")
        .drives(PB.release, "MeldVoice_EngineA_AmpEnvelope_Times_Release",
                "MeldVoice_EngineB_AmpEnvelope_Times_Release", over=RELEASE)
        .drives(PB.volume, "Volume", over=VOLUME)
        .offers("attack", "MeldVoice_EngineA_AmpEnvelope_Times_Attack",
                "MeldVoice_EngineB_AmpEnvelope_Times_Attack")
        .offers("glide", "MeldVoice_EngineA_GlideTime",
                "MeldVoice_EngineB_GlideTime", over=GLIDE)
        .offers("morph", "MeldVoice_EngineA_Filter_Macro2",
                "MeldVoice_EngineB_Filter_Macro2"))


# ===========================================================================
# The instrument racks
# ===========================================================================

def sound_family(rack: Rack) -> list:
    out = []
    for i, (eng, cut, rel, chr_) in enumerate(product(
            ("FM", "Sample"),
            (20, 55, 90, 120),
            (10, 45, 80, 115),
            (0, 64, 127))):
        out.append(PB.variation(
            f"{i:03d} {eng[0]} f{cut} r{rel} c{chr_}",
            instrument=rack.engine_macro(eng),
            filter=cut, release=rel, character=chr_))
    return out

# Pad: lush wavetable + drift
PD1 = (Rack.instrument("PD1", PB)
        .spends(PB.character, "attack")
        .label(PB.filter, PAIRED)
        .chain("Wave", WAVE)
        .chain("Drift", DRIFT))

# Bass: FM + Wavetable + Meld (morph)
BS1 = (Rack.instrument("BS1", PB)
       .spends(PB.character, "morph")
       .label(PB.filter, PAIRED)
       .chain("Wave", WAVE)
       .chain("Drift", DRIFT)
       .chain("Meld", MELD))

# Lead: FM + Meld
LD1 = (Rack.instrument("LD1", PB)
       .spends(PB.character, "glide")
       .label(PB.filter, PAIRED)
       .chain("FM", FM.sets("Globals/PortamentoOn", True))
       .chain("Meld", MELD))

# ARP: Same engines as LD1, but dedicated track for arps
ARP1 = (Rack.instrument("ARP1", PB)
        .spends(PB.character, "glide")
        .label(PB.filter, PAIRED)
        .chain("FM", FM.sets("Globals/PortamentoOn", True))
        .chain("Meld", MELD))

# Sampler track (Multisampler focus)
SR1 = (Rack.instrument("SR1", PB)
       .spends(PB.character, "attack")
       .label(PB.filter, PAIRED)
       .chain("Sample", SAMPLER))




# ===========================================================================
# FX RACKS (from BerlinTechno)
# ===========================================================================

ALIEN_FX_LAYOUT = Layout(
    Slot("EROSION"),
    Slot("GLITCH"),
    Slot("ROAR"),
    Slot("ECHO"),
    Slot("EQ LO", start=64),
    Slot("EQ MID", start=64),
    Slot("EQ HI", start=64),
    Slot("DRIVE"),
)

# ALIEN_FX is a CPU-efficient series rack mapping 'On' switch to the same macro as 'Amount'
ALIEN_FX = Rack.audio_effect("ALIEN_FX", ALIEN_FX_LAYOUT).chain(
    "Series FX",
    Engine("Erosion")
    .drives(ALIEN_FX_LAYOUT.erosion, "On")
    .drives(ALIEN_FX_LAYOUT.erosion, "Amplitude", over=Range(0.0, 200.0))
    .then(Engine("BeatRepeat")
          .drives(ALIEN_FX_LAYOUT.glitch, "On")
          .drives(ALIEN_FX_LAYOUT.glitch, "Chance", over=Range(0.0, 100.0)))
    .then(Engine("Roar")
          .drives(ALIEN_FX_LAYOUT.roar, "On")
          .drives(ALIEN_FX_LAYOUT.roar, "Output_DryWet", over=Range(0.0, 100.0)))
    .then(Engine("Echo")
          .drives(ALIEN_FX_LAYOUT.echo, "On")
          .drives(ALIEN_FX_LAYOUT.echo, "DryWet", over=Range(0.0, 1.0)))
    .then(Engine("ChannelEq")
          .drives(ALIEN_FX_LAYOUT.eq_lo, "LowShelfGain")
          .drives(ALIEN_FX_LAYOUT.eq_mid, "MidGain")
          .drives(ALIEN_FX_LAYOUT.eq_hi, "HighShelfGain"))
    .then(Engine("Saturator")
          .drives(ALIEN_FX_LAYOUT.drive, "On")
          .drives(ALIEN_FX_LAYOUT.drive, "DryWet", over=Range(0.0, 1.0)))
)


# ===========================================================================
# The Drum Rack (DR1)
# ===========================================================================

KIT = Layout(
    Slot("Sound"),
    Slot("Pitch"),
    Slot("Filter", start=127, label=PAIRED),
    Slot("Drive"),
    Slot("Send A"),
    Slot("Send B"),
    Slot("Send Vol"),
    Slot("Volume", start=127),
)

PAD_WITH_FX = Layout(
    Slot("Sound", selects=True),
    Slot("Pitch"),
    Slot("Filter", start=127, label=PAIRED),
    Slot("Send A"),
    Slot("Send B"),
    Slot("Character"),
    Slot("Release", start=30),
    Slot("Volume", start=127),
    # Alien FX slots
    Slot("Erosion"),
    Slot("Glitch"),
    Slot("Roar"),
    Slot("Echo"),
    Slot("Eq Lo", start=64),
    Slot("Eq Mid", start=64),
    Slot("Eq Hi", start=64),
    Slot("Fx Drive"),
)

PADS = (
    ("KICK", 36, "kick"),
    ("TOM", 37, "tom"),
    ("SNARE", 38, "snare"),
    ("HAT", 39, "hat"),
    ("RIM", 40, "rim"),
    ("MISC", 41, "misc"),
    ("CLAP", 42, "clap"),
    ("OHAT", 43, "ohat"),
)

PAD_LABELS = {
    "KICK": "Drive + Snap",
    "SNARE": "Drive + Snap",
}

PAD_VOICE = (Engine("OriginalSimpler")
             .drives(PAD_WITH_FX.filter, "Filter/Slot/Value/SimplerFilter/Freq", over=CUTOFF)
             .drives(PAD_WITH_FX.filter, "Filter/Slot/Value/SimplerFilter/Res", over=RESONANCE)
             .drives(PAD_WITH_FX.character, "Filter/Slot/Value/SimplerFilter/Drive")
             .drives(PAD_WITH_FX.release, "VolumeAndPan/Envelope/ReleaseTime", over=RELEASE_MS)
             .drives(PAD_WITH_FX.volume, "VolumeAndPan/Volume", over=Range(-36.0, 0.0, "dB"))
             .offers("attack", "VolumeAndPan/Envelope/AttackTime"))

PAD_FX = (Engine("Erosion")
             .drives(PAD_WITH_FX.erosion, "On")
             .drives(PAD_WITH_FX.erosion, "Amplitude", over=Range(0.0, 200.0))
          .then(Engine("BeatRepeat")
                .drives(PAD_WITH_FX.glitch, "On")
                .drives(PAD_WITH_FX.glitch, "Chance", over=Range(0.0, 100.0)))
          .then(Engine("Roar")
                .drives(PAD_WITH_FX.roar, "On")
                .drives(PAD_WITH_FX.roar, "Output_DryWet", over=Range(0.0, 100.0)))
          .then(Engine("Echo")
                .drives(PAD_WITH_FX.echo, "On")
                .drives(PAD_WITH_FX.echo, "DryWet", over=Range(0.0, 1.0)))
          .then(Engine("ChannelEq")
                .drives(PAD_WITH_FX.eq_lo, "LowShelfGain")
                .drives(PAD_WITH_FX.eq_mid, "MidGain")
                .drives(PAD_WITH_FX.eq_hi, "HighShelfGain"))
          .then(Engine("Saturator")
                .drives(PAD_WITH_FX.fx_drive, "On")
                .drives(PAD_WITH_FX.fx_drive, "DryWet", over=Range(0.0, 1.0))))

SAMPLE_ROOT = Path(__file__).resolve().parent.parent / "samples"
DR1_SAMPLES = SAMPLE_ROOT

def pad_samples(category: str, limit: int = 16) -> list[Path]:
    return samples.audio(DR1_SAMPLES / category)[:limit]

def pad_rack(name: str, sound: str) -> Rack | None:
    files = pad_samples(sound)
    if not files:
        return None

    rack = (Rack.instrument(name, PAD_WITH_FX)
            .spends(PB.character, "attack")
            .label(PB.filter, PAIRED))
    if name in PAD_LABELS:
        rack = rack.label(PAD_WITH_FX.character, PAD_LABELS[name])
    for i, wav in enumerate(files):
        content = PAD_VOICE.sample(wav)
        for fx in PAD_FX.engines:
            content = content.then(fx)
        rack = rack.chain(f"S{i + 1}", content)
    return rack

REVERB_RETURN = Rack.audio_effect("a Reverb", Layout()).chain(
    "Chain", Engine("Reverb").then(Engine("Eq8")).then(Engine("Saturator")).then(Engine("Compressor2"))
)

DRUMS_FX_RETURN = Rack.audio_effect("b Drums Fx 1", Layout()).chain(
    "Chain", Engine("Delay").then(Engine("Reverb"))
)

def dr1() -> Rack | None:
    kit = (Rack.drum("DR1", KIT)
           .ret("a Reverb", REVERB_RETURN.unchained())
           .ret("b Drums Fx 1", DRUMS_FX_RETURN.unchained())
           .sending(KIT.send_a, "a Reverb")
           .sending(KIT.send_b, "b Drums Fx 1"))
    chained = (KIT.sound, KIT.pitch, KIT.filter, KIT.send_a, KIT.send_b, KIT.drive.to(PAD_WITH_FX.character), KIT.volume.to(PAD_WITH_FX.release), KIT.volume)

    built = 0
    for name, note, sound in PADS:
        inner = pad_rack(name, sound)
        if inner is None:
            continue
        kit = kit.pad(name, note, inner.chaining(*chained))
        built += 1

    return kit if built else None

DR1 = dr1()

# ===========================================================================
# Set Assembly
# ===========================================================================

TRACKS = ("DR", "BS", "PD", "LD", "ARP", "SR", "SEQ", "PM")

def _preset(rack: Rack | None):
    if rack is None:
        return None
    return rack.build().find("GroupDevicePreset")

def _stock(tag: str):
    device = Library.default().instance(tag)
    device.set("Id", "0")
    clone.strip_macro_mappings(device)
    clone.fill_empty_int64_fields(device)
    clone.strip_legacy_path_elements(device)
    clone.zero_session_ids(device)
    return device

def _spread(count: int) -> list[int]:
    step = live_set.PALETTE / count
    return [int((i + 0.5) * step) for i in range(count)]

# ===========================================================================
# Master track FX
# ===========================================================================
MORE_LAYOUT = Layout(
    Slot("Erosion"),
    Slot("Glitch"),
    Slot("Roar"),
    Slot("Drive"),
)

MORE_FX = Rack.audio_effect("More", MORE_LAYOUT).chain(
    "Chain",
    Engine("Erosion")
    .drives(MORE_LAYOUT.erosion, "On")
    .drives(MORE_LAYOUT.erosion, "Amplitude", over=Range(0.0, 200.0))
    .then(Engine("BeatRepeat")
          .drives(MORE_LAYOUT.glitch, "On")
          .drives(MORE_LAYOUT.glitch, "Chance", over=Range(0.0, 100.0)))
    .then(Engine("Roar")
          .drives(MORE_LAYOUT.roar, "On")
          .drives(MORE_LAYOUT.roar, "Output_DryWet", over=Range(0.0, 100.0)))
    .then(Engine("Saturator")
          .drives(MORE_LAYOUT.drive, "On")
          .drives(MORE_LAYOUT.drive, "DryWet", over=Range(0.0, 1.0)))
)

def SESSION() -> Session:
    tracks = []
    colors = _spread(len(TRACKS))
    
    # Track 1: DR (Removed ALIEN_FX as it's now per-pad)
    tracks.append(Track("DR", "midi", [d for d in [
        _preset(DR1), _stock("ChannelEq"), _stock("Limiter")
    ] if d is not None], out="PM", sidechain=None, color=colors[0]))

    # Track 2: BS
    tracks.append(Track("BS", "midi", [d for d in [
        _preset(BS1), _stock("ChannelEq"), _stock("Compressor2"), _stock("Limiter")
    ] if d is not None], out="PM", sidechain="DR", color=colors[1]))

    # Track 3: PD
    tracks.append(Track("PD", "midi", [d for d in [
        _preset(PD1), _stock("ChannelEq"), _stock("Compressor2"), _stock("Limiter")
    ] if d is not None], out="PM", sidechain="DR", color=colors[2]))

    # Track 4: LD
    tracks.append(Track("LD", "midi", [d for d in [
        _preset(LD1), _stock("ChannelEq"), _stock("Compressor2"), _stock("Limiter")
    ] if d is not None], out="PM", sidechain="DR", color=colors[3]))

    # Track 5: ARP
    tracks.append(Track("ARP", "midi", [d for d in [
        _preset(ARP1), _stock("ChannelEq"), _stock("Compressor2"), _stock("Limiter")
    ] if d is not None], out="PM", sidechain="DR", color=colors[4]))

    # Track 6: SR
    tracks.append(Track("SR", "midi", [d for d in [
        _preset(SR1), _stock("ChannelEq"), _stock("Compressor2"), _stock("Limiter")
    ] if d is not None], out="PM", sidechain="DR", color=colors[5]))

    # Track 7: SEQ
    tracks.append(Track("SEQ", "midi", [d for d in [
        get_seq_xml(), _stock("ChannelEq"), _stock("Compressor2"), _stock("Limiter")
    ] if d is not None], out="PM", sidechain="DR", color=colors[6]))

    # Track 8: PM (Pre-Master / Master FX)
    tracks.append(Track("PM", "audio", [d for d in [
        _stock("AutoFilter"), _stock("Echo"), _stock("Eq8"), _preset(MORE_FX), _stock("Limiter")
    ] if d is not None], out=None, sidechain=None, color=colors[7]))

    return Session(tracks, returns=[], tempo=130.0)
