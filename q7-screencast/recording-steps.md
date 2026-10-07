# Q7(a) screencast — recording steps (human-only)

The TMA requires a **narrated ≤8-minute, 720p MP4** of the application in
use. This page is the runbook: what to have running, how to record, and how
to check the finished file. The narration itself is yours to deliver
(`script.md` is the timed script; `demo-run-log.md` proves every step
behaves as scripted).

## 1. Prerequisites — the exact running state

All from `backend/` unless noted. The recording uses the **guarded
`skipq_system_test` database** so it never touches the development data.

1. MongoDB is running locally (`127.0.0.1:27017`).
2. The guarded database is seeded:
   `MONGODB_DB=skipq_system_test .venv/bin/python -m db_seed.seed`
3. The API serves *that* database on port 5001 (its own process, so it
   cannot share a MongoEngine alias with a development process):
   `MONGODB_DB=skipq_system_test .venv/bin/python -m flask --app app:create_app run --host 127.0.0.1 --port 5001`
4. The frontend dev server on port 5173 (from `frontend/`, Node 22.17.0):
   `npm start`
5. Sanity-check before recording (optional but cheap): run the demo
   script's preflight only, or just load
   `http://127.0.0.1:5173` and confirm the sign-in screen appears.

Expected visible state: diner `diner.one@skipq.test` has a seeded cart
(2× M1 + 1× M2); Charcoal Grill is open; Pineapple Tart is seeded sold
out. Details in `demo-data.md`.

## 2. Two logged-in personas

The TMA wants the **same order** followed across both roles, so you need
both at once:

- **Window/tab 1 — diner:** sign in as `diner.one@skipq.test`.
- **Window/tab 2 — vendor:** sign in as `vendor.one@skipq.test` (a second
  browser context, or an incognito window, so the two sessions cannot
  cross).

Same password for both: `SkipQDemo2026!`.

## 3. Recording settings

- **Resolution:** 1280×720 (720p). The app's UI is built for that width;
  the demo screenshots are captured at the same viewport.
- **Format:** MP4 (H.264), with your microphone for narration.
- **Length target:** start the take around the 0:00 line of `script.md`
  and aim to finish before 7:50. If you stall on a polling wait, that is
  fine — say "it polls every three seconds" and let it happen; do not
  speed-ramp or cut, unless you then **explain the cut on screen** (the
  TMA accepts cuts of pure waiting only with an on-screen explanation).
- **Size:** resolution alone does not determine file size. At approximately 1,000 kb/s video plus 96 kb/s audio, eight minutes is approximately 66 MB before container overhead. Check the actual file size when you finish. If it exceeds 100 MB,
  host it on an accessible service instead and link that — but verify the
  link plays from an account **without** owner privileges before relying
  on it.

macOS options: QuickTime Player's screen recording (Cmd-Shift-5 → record
selected portion, tick "microphone"), or OBS. Either is fine; the
requirement is the content, not the tool. QuickTime typically creates MOV, so export/transcode to H.264 MP4; renaming the extension does not convert the file.

## 4. The take (follow `script.md`)

One continuous take following the timed script:

1. Intro on the sign-in screen (0:00).
2. Diner: sign in, open Cart and remove all seeded lines, return to stalls, menu, add M1, cart, checkout, pay (0:20–1:30).
3. Diner: tracking, Pending (1:30).
4. Vendor: sign in in the second context; the queue shows the diner's
   exact queue number; Accept → Preparing; cut to the diner's own
   Preparing (1:45–2:30).
5. Vendor: Mark ready → the diner's Ready banner; Mark collected →
   terminal on both screens; diner's Order List Past filter (2:30–3:30).
6. **Violation 1** — say the expected outcome first (the "Before I pay"
   marker), add M2 and open checkout while available, then vendor marks it sold out. On the existing checkout screen the diner's Pay $2.50 is
   refused naming M2, cart retained, no order stored (3:30–5:20).
7. **Violation 2** — say the expected outcome first, remove the sold-out M2, add M1 (cart $6.50) and open checkout. Then
   vendor closes the stall; on the existing checkout screen the diner's Pay $6.50 is refused naming the
   closed stall (5:20–7:00).
8. Close (7:00–7:20).

If a take is interrupted, check the current cart, order, item availability and trading state before proceeding. Phase boundaries are not automatically idempotent. For a complete reset, use the guarded drop-and-reseed procedure in `demo-data.md`; reseeding alone does not remove a previously created demo order.

## 5. After the take

- Trim accidental dead time at the very start/end only; keep every
  genuine error, retry and polling wait you actually performed.
- Confirm: ≤8:00 long, 720p, MP4, <100 MB, both personas' screens shown,
  the same queue number visible on both sides, both refusals preceded by
  the stated expectation.
- Place the file at `backend/q7-screencast/` (e.g.
  `q7-screencast/screencast.mp4`) — it is the Q7(a) artifact the report
  links from `docs/report/report.md` (Q7(a) section) and both READMEs.
- Verify the link plays from a non-owner account before submission.

## 6. What is *not* in this folder

- This folder deliberately contains the **scripted, un-narrated
  verification** (`demo_script.py` + `demo-run-log.md` + screenshots),
  not the submission MP4. A script or silent video does not satisfy Q7(a);
  the narrated recording is the human step.
- The demo script's screenshots (`demo-screenshots/`) are 1280×720
  headless-Chromium captures of the exact scripted steps; they are
  evidence that the script's expectations match the running app, and they
  double as a reference for what each moment of the recording should look
  like.

Known sold-out/removed cart lines are visibly blocked before payment. For the prescribed sold-out API refusal, keep checkout open from before the vendor changes availability; this demonstrates a genuine stale screen. Reopening or refreshing checkout after the change correctly disables Pay.
