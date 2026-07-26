# Copy presets out of the User Library into racks/ for diffing.
#
# The spike loop is: save in Live, copy here, diff. This removes the
# copy step's friction and its typos.
#
#   .\scripts\grab.ps1 s5_a s5_b        # by name, from the default folder
#   .\scripts\grab.ps1 -Latest 2        # the 2 most recently saved presets
#   .\scripts\grab.ps1 s9_drum -Kind Instrument
#
# Presets keep their names: s5_a.adg lands as racks/s5_a.adg.

[CmdletBinding()]
param(
    # Position=0 matters: without it PowerShell binds the first positional
    # argument to -Latest and fails to cast "s5_len_a" to int.
    [Parameter(Position = 0, ValueFromRemainingArguments)]
    [string[]]$Names,

    # How many recently modified presets to take instead of naming them.
    [int]$Latest = 0,

    # Which preset folder. Audio Effect Rack is the default because most
    # spikes use one.
    [ValidateSet('AudioEffect', 'Instrument', 'DrumRack', 'MidiEffect')]
    [string]$Kind = 'AudioEffect'
)

$ErrorActionPreference = 'Stop'

# Live 12.4.3 on this machine. If Live's User Library moves, change this.
$UserLibrary = 'C:\Music\AlienMindLibrary\Ableton Library\User Library'

$folders = @{
    AudioEffect = 'Presets\Audio Effects\Audio Effect Rack'
    Instrument  = 'Presets\Instruments\Instrument Rack'
    DrumRack    = 'Presets\Instruments\Drum Rack'
    MidiEffect  = 'Presets\MIDI Effects\MIDI Effect Rack'
}

$src = Join-Path $UserLibrary $folders[$Kind]
$dest = Join-Path $PSScriptRoot '..\racks' | Resolve-Path

if (-not (Test-Path $src)) {
    throw "Preset folder not found: $src"
}

if ($Latest -gt 0) {
    $files = Get-ChildItem (Join-Path $src '*.adg') |
             Sort-Object LastWriteTime -Descending |
             Select-Object -First $Latest
} elseif ($Names) {
    $files = foreach ($n in $Names) {
        $p = Join-Path $src "$($n -replace '\.adg$','').adg"
        if (-not (Test-Path $p)) { throw "Not found: $p" }
        Get-Item $p
    }
} else {
    throw 'Give preset names, or -Latest N.'
}

foreach ($f in $files) {
    $target = Join-Path $dest $f.Name
    Copy-Item $f.FullName $target -Force
    $kb = [math]::Round($f.Length / 1KB)
    Write-Host ("  {0,-24} {1,6} KB   {2}" -f $f.Name, $kb, $f.LastWriteTime.ToString('HH:mm:ss'))
}

Write-Host ""
Write-Host "$($files.Count) file(s) -> racks\"
