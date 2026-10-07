# Q7(a) screencast

The Q7(a) mark needs a **narrated, ≤8-minute, 720p MP4** of SkipQ in use,
showing one order followed across *both* personas and two rule violations
refused on screen. The [completed local MP4](screencast.mp4) is **6:26,
1280×720, 7.9 MB**, with captions and computer-generated narration. It records
automated actions in the actual running app, including both sign-ins, the
same order through collection, both expected outcomes spoken before the
violations, and the visible refusals. Review it before submission. Both repositories are now published on default `main`; anonymous repository
access and full video-download hash equality passed. Student playback review
remains pending.

## What is here

| File | Role |
|---|---|
| `screencast.mp4` | Actual live UI recording, computer-generated voice, burned-in captions; all elapsed waits and the payment failure/retry retained. |
| `screencast.srt`, `video-chapters.md` | Separate captions and chapter timestamps. |
| `video-verification.json`, `video-recording.log`, `video-timeline.json` | Exact media verification, genuine UI/cleanup log and recorded scene intervals. |
| `video-production.md` | Production method, speech disclosure, reproduction commands and access limits. |
| `video-narration.json`, `record_video.py`, `video_tools.py` | Exact generated narration and live capture/encoding sources. |
| `script.md` | The timed narration script (~7:20), with the expected outcome of each rule violation stated *before* it happens — the TMA-critical marker. |
| `demo-data.md` | The seeded accounts, stalls, menu, orders and the exact state the recording must start from (and what it restores). |
| `recording-steps.md` | The human runbook: the guarded database, both servers, two logged-in personas, recording settings, the take, and the post-take checks (≤8:00, 720p, MP4, <100 MB, link plays for a non-owner). |
| `demo_script.py` | A scripted, headless Playwright verification of the *exact* `script.md` steps: it drives both personas through the running UI, asserts every visible outcome, captures 26 per-step screenshots, and restores the seed state. |
| `demo-run-log.md` | The authentic passing run: date, machine, exact command, verbatim console output, step-by-step what was verified, and the genuine development iterations. |
| `demo-screenshots/` | The 26 authentic 1280×720 headless-Chromium captures from that run — a reference for what each moment of the recording should look like. |

## Run the verification yourself

From `backend/`, with MongoDB running, the guarded `skipq_system_test`
database seeded, the API serving that database on `127.0.0.1:5001` and the
CRA dev server on `127.0.0.1:5173`:

```bash
MONGODB_DB=skipq_system_test .venv/bin/python q7-screencast/demo_script.py
```

It prints `DEMO SCRIPT: ALL STEPS PASSED` on success, and leaves the seed
invariants intact (it deletes only its own run order and the test diner's
cart lines, and restores the two vendor-side states it changed).

## Boundaries

- Scripts, screenshots and silent footage are preparation. `screencast.mp4`
  is the newly created narrated recording; its voice is synthesized and its
  UI actions are automated, explicitly disclosed. It must not be described
  as the student's own recorded voice or manual operation.
- The first encoder attempt failed while copying protected macOS font
  metadata. `video-encoding-first-failure.log` retains the failure; the helper
  now copies font bytes only. The live application take had no capture failure,
  and the encoder retry did not change or trim its footage.
- The demo script is evidence that the scripted narration matches the
  running app — not the assessed application's own test suites.
- All of this runs against the guarded `skipq_system_test` database; it
  never touches the development database or its data.
