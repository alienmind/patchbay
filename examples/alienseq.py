"""Generates the giant SEQ rack for AlienMindLiveSet."""

import copy
from pathlib import Path
from patchbay import io, find
from patchbay.dsl import Layout, Rack, Slot
from patchbay.library import Library
from alienseqs import RACKS as ALIEN_SEQS

def get_seq_rack():
    layout = Layout(Slot("Sequence", selects=True))
    rack = Rack.instrument("SEQ1", layout)
    
    # We have exactly 44 sequence racks. We map them evenly across 0-127
    total_seqs = len(ALIEN_SEQS)
    step = 128 / total_seqs
    
    for i, inner_rack in enumerate(ALIEN_SEQS):
        start = int(i * step)
        end = int((i + 1) * step) - 1
        if i == total_seqs - 1:
            end = 127
            
        # The inner racks were extracted as unchained. We chain them here.
        rack = rack.chain(inner_rack.name, inner_rack.unchained().zone(start, end))
        
    return rack

def get_seq_xml():
    """Returns the GroupDevicePreset XML tree for the SEQ rack, with SQ Sequencer injected."""
    rack = get_seq_rack()
    root = rack.build()
    preset = root.find(".//GroupDevicePreset")
    
    # Now we need to inject the SQ Sequencer into each branch of the preset.
    source = Path('donors/AlienSequencerRacks')
    adgs = [adg for adg in source.rglob('*.adg') if 'AlienMind Sequencer Rack' not in adg.name]
    
    # Map by name
    adg_by_name = {adg.stem.lower(): adg for adg in adgs}
    
    branches = find.branches(preset)
    for i, inner_rack in enumerate(ALIEN_SEQS):
        branch = branches[i]
        
        adg_path = adg_by_name.get(inner_rack.name.lower())
        if not adg_path:
            for adg in adgs:
                if adg.stem.lower() in inner_rack.name.lower():
                    adg_path = adg
                    break
        
        if adg_path:
            original = io.load(adg_path)
            # In the original ADG, SQ Sequencer is at the top level chain
            sq = original.find('.//MxDeviceMidiEffect').getparent().getparent()
            if sq is not None:
                sq = copy.deepcopy(sq)
                sq.set('Id', '0')
                
                devices = branch.find('DevicePresets')
                for child in devices:
                    old_id = int(child.get('Id', '0'))
                    child.set('Id', str(old_id + 1))
                    
                devices.insert(0, sq)
                
    return preset
RACKS = []
