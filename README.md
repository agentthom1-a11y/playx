# PlayX — agentic DJ laboratory

**PlayX** is an open-source, local-first DJ mixing agent for Windows, macOS, and Linux. It analyzes two local audio files, chooses an explainable phrase-aware transition, renders an editable WAV mix, and includes an experimental MIDI bridge for the [Mixxx](https://mixxx.org) desktop application.

> **Status:** MVP. Offline rendering is operational after installation; real-time Mixxx control requires manual MIDI setup and preloaded decks. This is not a full Rekordbox replacement.

## Quick start

Requires Python 3.11+ and a supported audio decoder. WAV/FLAC are the safest inputs; MP3 support depends on your local libsndfile/FFmpeg environment.

```powershell
git clone https://github.com/agentthom1-a11y/playx.git
cd playx
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
playx studio
```

Open **http://127.0.0.1:8765** and enter two absolute audio paths and the output WAV path.

### Command line

```powershell
playx analyze "C:\Music\track_a.wav"
playx plan "C:\Music\track_a.wav" "C:\Music\track_b.wav" --style auto --energy 0.8 --out plan.json
playx render "C:\Music\track_a.wav" "C:\Music\track_b.wav" --plan plan.json --out mix.wav
playx mix "C:\Music\track_a.wav" "C:\Music\track_b.wav" --out mix.wav
playx mixxx-ports
playx mixxx-transition --port "PlayX" --seconds 8
```

To enable optional LLM-assisted **planning** (audio stays local; track metadata is sent to the API):

```powershell
$env:ANTHROPIC_API_KEY="YOUR_KEY"
$env:ANTHROPIC_MODEL="YOUR_AVAILABLE_MODEL"
playx plan "C:\Music\track_a.wav" "C:\Music\track_b.wav" --ai --out plan.json
```

LLM output is constrained to validated style and bar choices. It never controls the audio rendering thread.

## Features

- BPM, approximate musical key, beat/energy timeline extraction using librosa.
- Five creative transition envelopes: smooth, bass swap, filter sweep, echo out, drop swap.
- Deterministic render with beat-aligned cue choices, peak safety normalization, metadata/plan JSON.
- FastAPI local studio with responsive dark UI.
- Mixxx controller mapping and loopMIDI bridge for a live crossfade between **manually preloaded** decks.
- Pytest coverage and GitHub Actions CI.

## Design & limitations

1. **Analyze** tracks; BPM and key are estimates and must be checked by ear.
2. **Plan** chooses transition bars/style using musical intent and feasibility.
3. **Render** aligns starts on detected beats and crossfades; advanced DJ edit functions, stems and true real-time beat locking are not present.
4. **Mixxx** mode is a separate live MIDI transport; only loaded decks are controlled. Wall-clock fades are not beat-clock-locked.

Reference projects: [Mixxx](https://github.com/mixxxdj/mixxx) (GPL-2.0-or-later) and [DJ_SERENA](https://github.com/serenakeyitan/DJ_SERENA) (MIT). PlayX is an independently written implementation; neither project is bundled. Do not place copyrighted audio in this repository, and only render music you have rights to use.

See [docs/MIXXX.md](docs/MIXXX.md) for setup and caveats.

## License

MIT — see [LICENSE](LICENSE).
