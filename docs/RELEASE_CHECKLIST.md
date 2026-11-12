# Release gates — PlayX

## What is implemented in this repository

- [x] Local two-track studio with upload, waveform summaries, progress, export, and quality JSON.
- [x] 2–6 track experimental setmix CLI and heuristic setlist CLI.
- [x] Host/Origin protections, local-only server, user-scoped workspace, randomized export IDs.
- [x] Audio file size and 12-minute duration caps; no remote upload or cloud account.
- [x] Continuous tests across Linux and Windows (GitHub workflow configured; verify green runs before release).
- [x] Experimental unsigned Windows portable package workflow (verify its artifacts before release).

## Closed beta (must pass before selling paid plans)

- [ ] Verify Windows 10 and 11 installations on real machines, including low-memory 4 GB, 8 GB, and 16 GB devices.
- [ ] Validate WAV/FLAC/MP3 decoding, mono/stereo, 44.1/48 kHz, clipping, short/long/silent tracks, corrupted files, Unicode paths.
- [ ] Listen to at least 100 stylistically varied transitions, blind-rate perceived musical quality and compare against baseline crossfades.
- [ ] Measure runtime, RAM peaks, disk space, thermal load, and CPU on real machines with 3–10 minute tracks.
- [ ] Verify Mixxx controller mapping against stable Mixxx 2.5+ on Windows and two-way loopMIDI; don't advertise it as unattended until proven.
- [ ] Confirm GitHub Actions test matrix, wheel builds, security audit outcomes, and portable executable artifact.
- [ ] Resolve copyright/licensing and third-party notice review; do not distribute Mixxx in any proprietary bundle without legal review.
- [ ] Build a portable package that reliably launches without Python; code-sign installers and provide reproducible SHA-256 hashes.
- [ ] Implement disk quota/retention cleanup and better error recovery for interrupted exports.
- [ ] Fix output QA: ITU-R BS.1770/LUFS, true peak, limiter, sample rate conversion, quality control by listening.
- [ ] Implement cancellation/resume for long-running jobs and CPU/resource limit settings.
- [ ] Test secure local service against malicious uploads, supply chain vulnerabilities and localhost cross-site attacks.
- [ ] Publish human-readable privacy, terms, contact, refund policy (if paid), and a support channel.
- [ ] Beta-test with 20+ real users, track activation, successful exports and crash-free sessions with opt-in metrics.

## Public beta success criteria (proposed, not proven)

- 95%+ of supported files successfully imported.
- 95%+ of jobs with valid inputs finish without crashing.
- User rates at least 75% of generated transitions usable with minor or no adjustment.
- No known critical security issues and no unauthorized transmission of audio.
- Audio quality and runtime benchmarks published for representative Windows specs.

**No declaration of "market ready" until the above gates are independently verified.**
