# Mixxx experimental MIDI integration

1. Install Mixxx 2.4+ and loopMIDI (Windows).
2. Create a virtual MIDI port called **PlayX**.
3. Copy `mixxx/PlayX.midi.xml` into the Mixxx user controller mappings directory (find your actual user data directory in Mixxx documentation).
4. Enable the PlayX MIDI port in Mixxx Preferences → Controllers, selecting **PlayX Virtual MIDI**.
5. Load two tracks manually, beatmatch them and start both decks; assign both to the crossfader.
6. Run `playx mixxx-ports` then `playx mixxx-transition --port "PlayX" --seconds 8`.

The bridge sends MIDI CC16 to move the crossfader. It does **not** load tracks, beatmatch, detect Mixxx's beat clock, or synchronize against live playback. It is experimental, not unattended live-performance software. Offline rendering works independently of Mixxx.

The architecture references DJ_SERENA's slow planner / deterministic executor pattern. No upstream code is bundled.
