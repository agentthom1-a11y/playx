# PLAYX — agentic DJ lab

**v0.2 (experimental)** · [Mixxx](https://mixxx.org/) + Python + optional Claude orchestration.

Local-first DJ mixing software that analyzes two local tracks, chooses a transition, beat-aligns it approximately, optionally synchronizes the incoming song's tempo without changing its pitch, and renders a 24-bit WAV with an automated technical quality report. There is a separate **experimental** Mixxx controller mapping for beat-feedback-driven transitions and highlighted-track loading.

> PlayX is a prototype, not a Rekordbox replacement or an unattended live-DJ system. Beat grids, downbeats, musical key, and subjective mix quality still require human review.

## Run PlayX on Windows

Requires Python 3.11+, libsndfile-supported WAV/FLAC (MP3 availability depends on system audio decoders).

```powershell
git clone https://github.com/agentthom1-a11y/playx.git
cd playx
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\playx.exe studio
```

Browse to <http://127.0.0.1:8765>. Audio paths must refer to local files accessible to the Python process; no remote music upload is required.

## CLI workflows

```powershell
playx analyze "C:\Music\a.wav"
playx plan "C:\Music\a.wav" "C:\Music\b.wav" --style auto --bars 8 --out plan.json
playx render "C:\Music\a.wav" "C:\Music\b.wav" --plan plan.json --out mix.wav
playx mix "C:\Music\a.wav" "C:\Music\b.wav" --style bass_swap --out mix.wav
playx quality mix.wav --out report.json
```

A render also writes `mix.wav.quality.json`. For faster rendering without time stretching, use `--no-tempo-sync` on `mix` or `plan`. Tempo matching uses librosa and can take substantial processing time on full-length recordings; it is not a high-quality commercial-grade mastering engine. Half/double-time BPM relationships are recognized, but not guaranteed correct for all genres.

Optionally set `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` and run `playx plan ... --ai`. Only track metadata, not audio files or local file paths, is supplied to the LLM. It picks a validated style and rationale; sound rendering remains deterministic.

## Live Mixxx bridge

See **[Mixxx setup](docs/MIXXX.md)** for Windows loopMIDI setup, selected-track loading, status feedback and beat-linked crossfades.

```powershell
playx mixxx-ports
playx mixxx-status --port "PlayX"
playx mixxx-load-selected --port "PlayX" --deck 2
playx mixxx-beatmix --port "PlayX" --bars 8 --style smooth
```

**Limitations:** Mixxx MIDI cannot load arbitrary file paths; its library MoveDown command depends on foreground keyboard focus. The beat feedback is per beat, not a downbeat/phrase classifier. Crossfade recipes in live mode control crossfader only (not EQ/effects). A style named `echo_out` in live mode is **not** a real echo processor. Offline `echo_out` is a simple delay-based effect. No streaming audio, stems, hot-cue automation, or true-peak limiting. This project is not production-hardened; verify it using synthetic or authorized music and monitor playback manually.

## Development

```powershell
py -m pytest -q
```

GitHub Actions runs the unit/integration-lite tests on pushes. Tests do not connect to a physical Mixxx installation, sound card or virtual MIDI driver. See [Mixxx MIDI scripting](https://github.com/mixxxdj/mixxx/wiki/midi-scripting) and [DJ_SERENA](https://github.com/serenakeyitan/DJ_SERENA) for architecture references; their source is not bundled. MIT license. Only mix recordings you are licensed or authorized to use.
