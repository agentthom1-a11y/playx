# PlayX Privacy, safety and security notes (beta)

- Studio binds to `127.0.0.1:8765` by default. It is *not* a hosted website; the browser talks to a server on the same machine.
- Audio is processed locally, stored under `%USERPROFILE%\PlayX` on Windows (`~/PlayX` on Unix), and is **not** uploaded to the PlayX team or any third-party server.
- Inputs and exports are stored until the user manually deletes them. Disk usage can grow quickly; monitor free space. To clear your workspace, shut down PlayX and remove `%USERPROFILE%\PlayX` after backing up outputs you want.
- The optional Claude planner sends **track metadata, not audio files**, to Anthropic. It requires the user to configure credentials and is never called by Studio's default flow. API provider terms and data practices apply separately.
- We have no ad analytics, trackers, account database, email collection, or embedded telemetry in the current repository.
- Studio validates local Host/Origin headers and uses unguessable job IDs for exports. These safeguards **do not replace authentication** for a remotely hosted service. Never port-forward or host the Studio on a public server.
- Unsupported or corrupt files are rejected when the decoder cannot identify them, but input processing uses large native audio libraries; only open music you trust.
- Third-party media rights remain the user's responsibility. A legal right to listen to a track does not necessarily include rights to publish a derivative mix.
- No guarantee that generated transitions are musically accurate, click-free, compliant with broadcasting standards, or safe for live performance.

**Before broad release:** external security review, Windows code signing, dependency vulnerability policy, automatic retention/cleanup controls, software bill of materials, privacy policy/legal review, crash reporting opt-in, and support SLAs.
