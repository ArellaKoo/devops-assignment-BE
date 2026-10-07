# Automated live demonstration — production notes

The user requested: “can you do a video demo for me covering evrrythung”. This
authorizes making the local recording. Publishing and submission remain pending.

## What is recorded

`record_video.py` drives the actual running React app in two independent
Playwright Chromium contexts. Both accounts sign in through the forms. Real
requests reach the Flask API and the guarded `skipq_system_test` MongoDB database.
The recording continuously samples the selected persona's viewport at a target
eight frames per second. Encoding retains the actual elapsed frame intervals,
including polling, action waits, the deliberate simulated-payment failure and
its retry. Persona switches have chapter labels. It does not animate the old
screenshots, mock responses, inject browser tokens, or alter application time.

The original Q7 script is extended with payment retry, immutable purchase
history, vendor add/edit/remove, seeded-order cancellation/refund and an older
seeded Ready order's allowed no-show. The original newly created order is followed
through collection on both roles. Expected outcomes are spoken in separate beats
before the vendor marks the item sold out and before the vendor closes the stall.
Both resulting checkout refusals and retained carts are shown. Read-only database
counts verify that neither refusal creates a second order.

The final two evidence slides are explicitly labelled summaries of retained
7 October verification/load artifacts. These are not live test runs in the video.

## Narration and captions

The voice is **computer-generated macOS Samantha**, speaking the exact text in
`video-narration.json` at 175 words per minute. It is not a recording of the
student's voice. The opening/closing narration and a persistent on-screen label
disclose computer-generated speech and automated live UI actions. Captions are
burned into the MP4 and supplied separately as `screencast.srt`. Caption timing
uses proportional word timing within each generated audio utterance; it is not
forced-aligned speech recognition.

Each actual browser capture is 1280×620. It is placed unchanged between a 44-pixel
chapter strip and a 56-pixel caption strip, producing a **1280×720** movie. Video
uses H.264 with a capped bitrate; audio uses AAC; MP4 metadata is moved to the
front for playback. `video-verification.json` records the actual duration, size,
hash, codecs and full-stream decode result. `video-chapters.md` lists navigation
timestamps. These files are generated from the real capture timeline.

## Reproduction on macOS

Start both servers against the canonical guarded seed state as described in
`recording-steps.md`. A prerequisite checks that the running API's stall ID
matches that database. No developer database is modified. New demonstration
orders/items are removed, and only touched fixtures are restored from their
original documents. Before/after equality is verified; the database is not dropped.

The capture uses the backend development environment. The encoding helpers use
the workspace's existing isolated tool environment with `imageio-ffmpeg`, or a
separate environment created from `requirements-video.txt`. No application
dependencies were added. `say` must provide the macOS Samantha voice.

From the workspace root:

```bash
.local/qwen-tools/.venv/bin/python backend/q7-screencast/video_tools.py prepare
backend/.venv/bin/python backend/q7-screencast/record_video.py
.local/qwen-tools/.venv/bin/python backend/q7-screencast/video_tools.py render
.local/qwen-tools/.venv/bin/python backend/q7-screencast/video_tools.py verify
```

Speech files, sampled frames, raw timelines, full decode logs and review previews
stay under `.local/demo-video/`, outside Git. The encoded MP4, captions, chapter
list, production sources and verification record belong under `q7-screencast/`.
Failed takes must stay retained and disclosed; do not trim a real error or retry
out of a recording to present it as an uninterrupted successful run.

## Review and access

Watch the complete MP4 before choosing it for submission. This recording uses
synthetic narration and automated actions, as disclosed; it is not evidence of a
student speaking or operating the controls personally. The original human
recording runbook remains available for a personally narrated replacement.

An accessible video link still requires publishing the authorized branch and
checking playback from outside the owner's account. Local encoding/decoding does
not establish marker access. No push, hosting, or Canvas submission is authorized
by this video request or performed by this workflow.
