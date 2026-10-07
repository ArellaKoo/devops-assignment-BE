# ICT381 SkipQ assignment plan and current status

**Deadline: 19 October 2026, 23:55 Singapore time.**

The application and independent verification work are complete and published on the default `main` branch. Qwen completed the planned implementation, and Codex continued with code/report review, concrete fixes, fresh verification and assembled submission drafts on 7 October 2026. Task 13 remains partially complete because personal details, original prompt exports, video review and submission need the student.

The two repositories are `backend/` ([devops-assignment-BE](https://github.com/ArellaKoo/devops-assignment-BE)) and `frontend/` ([devops-assignment-FE](https://github.com/ArellaKoo/devops-assignment-FE)). The app adapts the StaycationX labs using Flask, MongoEngine, local MongoDB and a separate React SPA. It covers diner ordering/tracking, vendor menu/trading/fulfillment, seeded role-based sign-in and US10 All/Current/Past orders. Payments are simulated, as scoped for the assignment.

Earlier fresh-clone verification: **306 unit passed; functional 10 passed twice; browser lifecycle 1 passed twice; frontend production build passed.** Both suite pairs ran without a reset between their runs. Four additional frontend diagnostic checks and the complete two-persona demonstration rehearsal passed in the working repositories. Original Locust data records 395 successful menu requests; its measurement interpretation has been corrected without rewriting the raw evidence.

Read these for the actual results and next actions:

1. [Final continuation handover and remaining human actions](docs/assessment/codex-handover.md)
2. [Editable Word report draft](docs/report/SkipQ_Report_Draft.docx) and [PDF preview](docs/report/SkipQ_Report_Draft.pdf)
3. [Complete implementation plan and reconciled acceptance checklist](docs/superpowers/plans/2026-10-06-skipq-tma.md)
4. [Approved design, models, API and routes](docs/superpowers/specs/2026-10-06-skipq-design.md)
5. [Recording instructions](q7-screencast/recording-steps.md) and [narration script](q7-screencast/script.md)
6. [AI disclosure and explicitly identified historical gaps](docs/assessment/ai-prompts.md)

Before submission, fill the cover details, export missing original prompt records, review the completed narrated MP4 and confirm marker playback. The DOCX/PDF are drafts with these pending items visible. Both repositories have been pushed; Canvas submission remains pending, and no grade is guaranteed.

Adaptation sources: StaycationX_Backend at `153ce9004ceb6fde84c35873b53b4957c76062a3` and StaycationX_Frontend at `bc3367629ff31b920634dc3c046684f8c3877059`. Historical preparation and Qwen milestones remain in the [continuation record](docs/assessment/continuation.md).

Frontend quality follow-up: **313 unit tests; 24 targeted browser checks; functional and assessed browser pairs; production build and full demo all passed.** Thirty desktop/mobile layouts had no horizontal overflow or uncaught page errors. See [frontend review checklist](docs/assessment/frontend-quality-review.md). Final frontend/report changes are published on `main`; human submission actions remain pending.

Video production follow-up: [completed narrated MP4](q7-screencast/screencast.mp4) is **6:26, 720p, 7.9 MB**, using disclosed computer-generated speech and actual automated browser actions. All recorded UI checks and full media decoding passed; expectations were spoken before both violations; elapsed waits and payment failure/retry were preserved; guarded fixtures were restored exactly. The video is linked in both READMEs and the report. Student review and remote marker playback/access remain pending; no publication or submission occurred.

Default-branch update (7 October 2026): the user set both repositories to `main`. Both contain the final code and video; local branches already track `origin/main`. Current README/report hyperlinks use `main`. Anonymous public access and full video-download hash equality passed; see `docs/assessment/published-main-access.json` in the backend. Video review, personal cover inputs, missing historical prompts and Canvas submission remain pending. Earlier production notes describe their pre-publication state.
