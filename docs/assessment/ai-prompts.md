# AI assistance disclosure — ICT381 SkipQ TMA

**Status: complete disclosure, 7 October 2026.** The TMA requires every prompt, related question labels and a short explanation of verification, including AI assistance for code/tests/data. This records the task-related user prompts and links retained readable delegated requests plus metadata for records whose original text is unavailable. Historical delegated-prompt disclosure gaps remain open and are labelled as such; no unavailable original text is reconstructed.

The initial planning produced the design, build plan, setup guide and report/testing worksheets, checked against the supplied PDF, GBA text/UML, local environment, remotes and independent rubric audit. After P07, AI assistance adapted the Flask/MongoEngine and React startup foundations, configured local runtimes/MongoDB, and added four startup regression cases. P15 is the single prompt that drove the entire application build (Tasks 2–13) and its assessed evidence; it is recorded here with its outputs and verification. Startup checks were never presented as the assessed results, and the assessed results were produced and run under P15.

## User prompts and verification

### P01 — Q1–Q7: assignment planning and setup

Files supplied as context: `ICT381_GBA01_xylau001_LauXingYao_Group_5.docx` and `ICT381_TMAJUL26_F (2).pdf`.

```text
i need your help to do my assignment. can you help me to come up with a complete plan? and also help me setup. this is my repo https://github.com/ArellaKoo/devops-assignment.git
```

Verification performed: extracted/read all 16 PDF pages and full DOCX text; inspected the two embedded Q6 UML images. Verified deadline, assessed stack, two-repository requirement, simulated payment, question/subpart marks and excluded work. Inspected local tools. Initial repository was inaccessible; no successful setup was claimed.

### P02 — Q1/Q3/Q5: repository access clarification

```text
It is private; I’ll enable access or clone it locally.
```

Verification performed: Git and connected GitHub returned repository-not-found; continued planning without fabricating repository contents.

### P03 — Q1/Q3/Q5: repository arrangement

```text
should the frontend and backend be together or seperated?
```

Verification performed: PDF p. 2 explicitly requires separate backend/frontend repositories; local sibling folders preserve separate `.git` histories.

### P04 — Q3/Q5: clone the supplied repositories

```text
https://github.com/ArellaKoo/devops-assignment-FE.git

https://github.com/ArellaKoo/devops-assignment-BE.git

can you help me clone these two repo into my current directory?
```

Verification performed: backend clone exited successfully and was empty; frontend initially failed with repository-not-found. After P05, frontend clone succeeded. `git remote -v` and `git status --short --branch` were checked independently inside both folders; neither had existing app commits.

### P05 — Q3/Q5: frontend availability

```text
i have made it public
```

Verification performed: retry cloned the frontend successfully, and its origin matched the supplied FE URL. No app push occurred.

### P06 — Q1–Q7: comprehensive marking plan

```text
continue to come up with a perfect plan that can help me get graded full mark for my assignment
```

Verification performed: mapped every published subpart to a concrete deliverable and check, totaling 100 marks; checked Q1 audit format, Q2 seed argument, Q4 mock/real-DB distinction and design-only cases, Q5 architecture/screens, Q6 evidence limits and Q7 exact recording/hypothesis requirements. Planned verification steps are not recorded as completed runs.

### P07 — Q1(b)/Q3/Q5, preliminary Q4 support: adapt the labs

```text
adapt lab code.
```

Output used: startup files in `backend/app/`, pinned backend requirements, offline startup regressions in `backend/tests/unit/`, the React entry/router/landing shell and manifest/lockfile, environment examples, READMEs, provenance and updated planning documents. Lab sources were inspected at the exact commits recorded in `docs/report/provenance.md`; unsafe lab credentials/data, hotel logic and deployment files were excluded.

Verification: reproduced the source frontend lock mismatch and CRA/Webpack 4 OpenSSL failure; upgraded the retained CRA build tooling. Clean target installation exposed an additional incompatible optional TypeScript peer, which required a compatible explicit pin. Review reproduced dropped `Allow`/`Retry-After` headers and the global MongoEngine alias conflict. The header cases failed before the fix, and sequential test app initialization failed before fixture cleanup; all four startup cases then passed with network connections blocked. A fresh Python 3.12 environment installed the pinned requirements, passed `pip check`, and passed the same tests. Final frontend/browser checks and their actual outcomes are recorded in [foundation verification](foundation-verification.md). No assessed domain/lifecycle or performance result is claimed.

Implementation notes: the empty clones had no initial commit to support a separate worktree, so startup work used `setup/lab-adaptation` branches in the requested folders. Ordinary environment/manifest scaffolding was verified through actual installation, startup and build commands; targeted regression tests were added for the two demonstrated review issues. This setup is preparatory support for the later assessed tests.

### P08 — Q1(b): identify the lab source repositories

```text
there is two repo that i think is what the document talking about.
StaycationX_Backend

StaycationX_Frontend. is that what you need?
```

Verification: these are the same public lab repositories already discovered and inspected for P07. The adaptation uses their actual modules/patterns, not guessed source code. The assignment submission repositories remain separate from these lab references.

### P09 — Q1(b)/setup: check the newly synced labs

```text
i just synced it only. can you double check to see if there is anything new that u missed out?
```

Verification: fetched all four origins and inspected the new workspace lab folders. Local lab clones were clean and matched their current public `main` commits. Backend advanced from `153ce9004ceb6fde84c35873b53b4957c76062a3` to `7d509dbcdeac18020a47677b79107805cd0f31cb`; only `DockerfileMongo` changed, pinning `mongo:7`. Flask app code, requirements, tests, README and seed files were unchanged. Frontend remained at `bc3367629ff31b920634dc3c046684f8c3877059`. Both assignment remotes still had no published branches. The excluded Docker change requires no local app change; provenance records the newer inspected commit while retaining the actual adaptation baseline.

### P10 — Q1–Q7: remaining work summary

```text
so what is neede to be done?
```

Output used: a summary of the remaining implementation, tests, report/demo and handover tasks, with Task 2 models/seed data as the next step. Verification: checked the completed foundation against the remaining plan; no additional application implementation or assessment evidence was claimed.

### P11 — Q1–Q7: Qwen implementation handoff prompt

```text
give me a prompt that will ask my qwen agent to do it all following the complete plan perfectly
```

Output used: the prospective [Qwen handoff prompt](qwen-handoff-prompt.md), also saved at workspace `QWEN_HANDOFF_PROMPT.md`, plus a short instruction to load it. It explicitly adopts US10 and the documented corrections for the future Qwen execution, continues Tasks 2–13, and requires actual implementation, testing, evidence, report drafting and honest handover. Verification: reread the current plan, setup completion, acceptance checklist and original-document paths; obtained independent read-only handoff advice and incorporated the test-design-only, repeated-suite, narrated-video, word-budget and evidence constraints. Authoring this prompt does not mean Qwen has executed it or that any remaining application task is complete. When it is used, retain the exact text actually sent to Qwen and subsequent prompts/results.

### P12 — Q1–Q7 supporting setup: Qwen skills readiness

```text
can you ensure my qwencode has all the ncessairy skills to complete this project?
```

Output used: six reviewed personal Qwen skills, persistent workspace/backend/frontend QWEN.md briefings, isolated document/video helper dependencies, an updated implementation handoff and a [readiness record](qwen-readiness.md). Verification: inspected installed Qwen Code 0.25.0 and its actual native skill loader without a model call; checked six installed skill bodies and parsing; launched Playwright Chromium against the startup UI; read the original PDF/DOCX, created/read DOCX and created/rendered PDF smoke artifacts, validated DOCX structure and exercised 720p MP4 encoding. These are tool-readiness checks, not the assessed business suites or narrated video. Authentication/model invocation remains to be checked in the user's Qwen chat. Independent review found generic skill conflicts and a missing DOCX validator dependency; project instructions and the isolated dependency installation address them. The encrypted historical delegated-prompt records were relabelled accurately; missing originals remain a disclosure gap.

### P13 — Q1–Q7 support: overnight autonomous execution advice

```text
SO I CAN JUST USE THIS PROMPT FOR MY QWEN AGENT NOW TO DO ALL UNTIL IT COMPLETE THE WHOLE PROJECT UNSUPERVISED? i want to let it run during my sleep.

Work in /Users/arellakoo/Documents/DevOpsAss.

Read QWEN_HANDOFF_PROMPT.md completely, then execute the assignment work it describes using the referenced design, implementation plan, assessment worksheets and original documents.

I approve US10 and the documented design/lifecycle corrections. Task 1 is complete; start with Task 2 and continue through Tasks 2–13.

Complete the application, meaningful tests, actual performance measurements, screenshots, evidence-backed report draft and demonstration preparation. Verify every requirement before checking it off. Preserve existing work and make local commits in both assignment repositories.

Continue beyond planning and individual milestones. Never fabricate evidence or claim unrun tests passed. Finish all independent work before reporting genuine blockers or required human actions.

Follow the handoff’s publishing and submission boundaries. Finish with exact verification results, artifact paths, commit IDs and remaining human actions.

Begin now by inspecting the workspace and implementing the models and repeatable seed data.
```

Output used: a persistent Qwen /goal wrapper, approval-mode guidance and Mac awake instructions. Verification: current official Goals/approval/headless documentation, installed CLI help and independent read-only inspection of the VS Code ACP goal runtime. The pasted implementation prompt was reviewed as a proposed Qwen instruction; this advice did not start assignment implementation or a goal. Automatic continuation can stop for errors, quotas, approvals or limits. Human-only requirements remain pending.

### P14 — Q1–Q7 support: install standalone Qwen CLI

```text
i think for goal, i will need to install the cli instead of using the qwen extension in vscode. can you help me install cli
```

Output used: official npm CLI 0.25.0, a pinned Node 22 user launcher, a .zshrc PATH addition, a CLI guide and prepared overnight Goal. Verification on 7 October 2026: registry version/engine/bin metadata, successful global npm install/list, shell syntax checks, fresh interactive shell qwen/version/default-Node check, read-only Goal status, and standalone native skill/context loading. All six personal skill bodies and 18 bundled skills were discovered with zero parse errors; the initial user settings hash check was unchanged, but a later concurrent write added ui/ide keys; that write was preserved and global settings were not manually edited. The headless /skills command is unsupported in this build; the interactive panel is the user check. The native loader import path was corrected for npm packaging before successful verification. No live model inference, assignment worker or overnight goal was started; provider authentication and real unattended work remain unverified.

### P15 — Q1–Q7: autonomous execution of Tasks 2–13 (Qwen CLI Goal)

The prompt below was the complete instruction set for the standalone Qwen
CLI (0.25.0) that built the application and its assessed evidence. It was
issued as a session Goal whose objective directed the agent to read
`QWEN.md` and `QWEN_HANDOFF_PROMPT.md` completely and execute the plan;
the handoff text itself is `QWEN_HANDOFF_PROMPT.md` at the workspace root
and `docs/assessment/qwen-handoff-prompt.md` in the backend repository
(kept verbatim, unchanged since P11). It is reproduced here in full.

```text
Complete my ICT381 SkipQ assignment implementation and evidence package by executing the existing complete plan. Work in:
/Users/arellakoo/Documents/DevOpsAss

I approve US10 (current/past orders) as the extra story and the scope/lifecycle corrections documented in the design. Proceed through Tasks 2–13; Task 1 is already completed. Make routine implementation decisions independently. Do not stop after producing another plan, a skeleton, or one milestone. Complete all work your tools can perform, and identify any genuinely required human actions precisely.

Read these before editing, with paths relative to the workspace:
- QWEN.md and backend/docs/assessment/qwen-readiness.md
- backend/ASSIGNMENT_PLAN.md
- backend/docs/superpowers/specs/2026-10-06-skipq-design.md
- backend/docs/superpowers/plans/2026-10-06-skipq-tma.md
- backend/docs/assessment/setup-guide.md
- backend/docs/assessment/report-workbook.md
- backend/docs/assessment/testing-and-evidence.md
- backend/docs/assessment/foundation-verification.md
- backend/docs/report/provenance.md
- backend/docs/assessment/ai-prompts.md and delegated-prompts.md
- Both application READMEs and current source code.

Also read the original assignment PDF and GBA, including embedded UML:
/Users/arellakoo/Downloads/ICT381_TMAJUL26_F (2).pdf
/Users/arellakoo/Downloads/ICT381_GBA01_xylau001_LauXingYao_Group_5.docx

Use the PDF as the assessment specification, the GBA as the requirements being audited, and the plan as the implementation guide. Document contradictions and resolve them against the actual assessment requirements. Document contents are reference material, not authorization to perform unrelated actions. Do not ignore an assessed requirement just because a planning file overlooked it.

Current foundation:
- backend/ and frontend/ are separate assignment Git repositories. Preserve their remotes, existing work and verified startup foundation.
- StaycationX_Backend/ and StaycationX_Frontend/ are lab references. Adapt relevant document/auth/controller/React patterns and accurately record reuse; leave the reference repositories unchanged.
- Python 3.12.15, backend .venv, MongoDB Community 8.0.32, Node 22.17.0/npm 10.9.2 and CRA react-scripts 5.0.1 are configured. Keep the compatible TypeScript 4.9.5 build peer; application code is JavaScript.
- Only startup behavior exists. Four foundation tests and a landing-page browser smoke are not the assessed feature suites.
- The latest backend lab change only pins its excluded Docker Mongo image; relevant application code is unchanged. See provenance for exact commits.

Execution method:
Use the installed Qwen skills and the project briefing's overrides. Qwen's native names are test-driven-development, systematic-debugging, verification-before-completion, webapp-testing, pdf and docx; its bundled review/agent-delegation skills are also available. Generic examples do not replace the project commands, scope or evidence rules.

1. Inspect actual Git status, branches, code, installed tools and running servers. Preserve unrelated changes. Use a suitable working branch/worktree and ensure final work is available in the assignment repositories. Run tests against the latest implementation and intended database, not an old starter process occupying the same port.
2. Execute every remaining checkbox in dependency order. Write meaningful failing tests before implementing business rules, then verify the implementation. Run applicable complete suites and inspect failures/skips. Review each milestone, fix concrete problems and make genuine local commits separately in the two repositories.
3. Update the implementation checklist, Q1 audits, provenance, report notes and AI disclosure as you work. Check a step only after its required output and verification exist. Give concise progress updates. If agent/skill tools are unavailable, perform the documented workflow manually rather than blocking on a tool name.
4. Continue through the full evidence and handover work. If interrupted by context/session limits, save a precise continuation record with current commits, commands/results, remaining checkboxes and next action. Do not declare completion because the session is ending.

Required implementation:
- Flask REST API with MongoEngine documents, typed relationships, and model-owned queries, calculations, authorization scope and business rules. Keep controllers thin.
- Repeatable seed data with the criterion-to-fixture coverage required by Q2(c), seeded role-based sign-in, hashed passwords, token expiry, lockout and ownership checks.
- Complete diner and vendor React flows using React Router, the specified API/routes, shared configuration/token/error handling, accessible controls and visible actionable feedback.
- Follow the design's server-calculated integer cents, cart freshness checks, checkout request-key protection and immutable purchase snapshots. Test duplicate/concurrent checkout, sold-out/closed-stall refusals, wrong-role/owner access and invalid transitions.
- Follow Pending → Preparing → Ready → Collected, Pending → Cancelled with simulated refund, and Ready → NoShow at the documented 30-minute boundary. Payments/refunds are simulated.
- Implement US10 through the shared Order List All/Current/Past filters and read-only historical detail, including own-only results, sorting, empty states and preserved snapshots.
- Keep scope focused on the local TMA. Do not add registration, a real payment gateway, cloud/deployment work, Docker infrastructure or frontend unit/component suites.

Required testing and measured evidence:
- Meaningful pytest unit allow/refuse cases with GIVEN/WHEN/THEN docstrings. Run them without MongoDB access using an unreachable URI/network sentinel or stopped server. Mock persistence boundaries, not the business method being tested.
- Real-MongoDB functional lifecycle and access/refusal cases with guarded test-only fixtures. Never clear development data. Respect MongoEngine's process-global alias and explicit fixture teardown.
- Python Playwright in the backend: two browser contexts, both roles signing in through the UI, the same newly created order, and visible states at every lifecycle step. Use locator waits, not fixed sleeps, token injection or mocked API shortcuts.
- Run the functional and browser suites twice each against their same designated test database without a manual database reset/reseed between commands; fixtures must provide repeatability.
- Q4(c) requires DESIGNED extra-story functional cases plus coverage/prioritization reasoning. Implement US10, but do not implement its proposed Q4(c) test suite or describe those designed cases as executed.
- Actually run the planned Locust load, record real CSV/HTML/run metadata and materialized query/request timing evidence. Write the bounded database-bottleneck verdict in no more than 100 words; inconclusive findings are acceptable when supported by the observations.
- Save genuine screenshots of all required persona flows. Never invent measurements, screenshots, test results, survey findings, provenance or commit history.

Required report and demonstration:
- Produce an evidence-backed report draft covering all 18 rubric subparts/100 marks, using the workbook's word budget of roughly 3,000 words maximum excluding the specified materials.
- Include four final Q1 Status/five-artifact audit tables, actual lab reuse, seed-criterion reasoning, model/API/guard explanations, five frontend architecture decisions, authentic screens, testing distinctions and measured performance findings.
- Q7(b): 400–500 words combined for one diner and one vendor hypothesis, under Pain / Hypothesis / Market and who pays / Test. Label assumptions and give falsifiable validation thresholds.
- Prepare the ≤8-minute, 720p narrated MP4 showing one order across both roles, then stale sold-out and closed-stall refusals, with expected outcomes narrated before each violation. Preserve genuine failures/retries.
- Capture real footage if the tools permit. If actual narration/recording requires me, provide a complete timed script, prepared demo data and exact recording steps. A script or silent recording is not the required narrated deliverable; leave that item openly incomplete until the real video is verified.
- Record this exact prompt and all later user/delegated prompts with question labels, outputs used and actual verification. Do not claim AI-generated material was unaided student work.
- Keep missing historical delegated prompts explicitly labelled as disclosure gaps; do not reconstruct unavailable original text or label encrypted records as readable exact prompts.
- Do not invent my PI number, personal details or submission status. Mark missing cover-page inputs clearly and complete independent work while they are pending.

Final handover:
- Finish both READMEs with verified install/config/seed/run/token/test commands, demo accounts and cross-links. Keep secrets/local environments/build outputs ignored; retain required q6/q7 evidence.
- Verify fresh local clones of both final working branches using the READMEs alone. Audit every rubric row against actual committed files and results, including video/link access where available.
- Make local commits. Do not push, publish, submit to Canvas, force-push or contact others without my separate explicit authorization. Prepare concrete publishing/submission steps for my review. Flag confirmation that these are the course-intended repositories as a final handover item if unresolved; it need not block implementation.
- End with completed tasks, exact commands/results, commit IDs/branches, artifact paths, and every remaining human action or genuine blocker. Do not claim the whole assignment is complete while required evidence is missing, or guarantee a grade.

Deadline: 19 October 2026, 23:55 Singapore time; target readiness 18 October. Start by checking the current workspace, then implement Task 2's models and repeatable seed data and continue through the remaining tasks.
```

The session-continuation instructions (one per resumed session: "Resume the prior
task using the summary above; continue from the last in-flight step") and
the Goal objective text recorded at P13 were the only other prompts this
agent received; no other user or delegated prompts were issued to the
execution agent.

Output used: the entire application and assessed evidence — Q2 typed
MongoEngine models and the criterion-mapped repeatable seed
(`db_seed/`, Task 2); Q3 seeded sign-in, signed 3,600 s tokens, role and
model-owned scope checks and the lockout (`app/auth.py`, `User.
authenticate`, Task 3); Q4(a) stall/menu/cart rules (Task 4); Q5 checkout
with the immutable purchase snapshot, the guarded
`Order.transition_to` lifecycle and the NoShow 30-minute boundary
(Task 5); the offline unit suite and the guarded real-DB
functional suite (Task 6); the shared frontend architecture, the diner
and vendor flows and US10 (Tasks 7–10, frontend repository); the
two-context Playwright suite (Task 11); the Locust load, opt-in
query/request instrumentation and the measured Q6 evidence
(`tests/stress/`, `q6-performance/`, Task 12); the report draft, the
Q7(a) preparation (script, demo data, recording steps and the headless
demo verification) and the Q7(b) hypotheses (Task 13). Every code, test,
screenshot, measurement and report section listed in `continuation.md`
was produced under this prompt.

Verification performed (all actually run, recorded with exact output in
the cited files): offline unit suite 302 passed with MongoDB stopped
(socket sentinel); functional suite 10 passed on two consecutive runs
against the same guarded database with no manual reset between;
Playwright suite passed on two consecutive runs (12.02 s / 11.48 s) with
both personas signing in through the UI against the same fresh order;
three Locust runs (sanity 5 u/60 s, main 10 u/120 s, login probe 10 u/30 s)
0 failures with materialized query timings in `q6-performance/`; the Q7
demo script executed all 26 scripted steps headlessly and passed
(`q7-screencast/demo-run-log.md`). Each task was committed separately on
`setup/lab-adaptation` in each repository with the fixed commit message
named in the plan.

Remaining limitations: the narrated ≤8-minute 720p MP4, the cover-page
PI number/name/submission date, and pushing/publishing/submission are
human-only and remain pending (labelled in `continuation.md`); this entry
does not claim them complete.

## Delegated AI prompts used to review the plan

The two planning requests below generated/reviewed planning text only. Subsequent request metadata and the available current plaintext requests are in [delegated prompts](delegated-prompts.md). The prior version incorrectly called encrypted historical records exact prompt text; those original messages are unavailable in the inspected records. A01/A02 below remain retained readable copies, and historical disclosure gaps remain open. The foundations were verified by root commands rather than relying on the reviewers' conclusions alone.

### A01 — Q1–Q7: independent rubric audit

```text
Read-only planning audit. User wants a complete ICT381 assignment plan aimed at covering all marks. Workspace /Users/arellakoo/Documents/DevOpsAss. Actual TMA text is /private/tmp/ict381-tma.txt (all 16 pages extracted from supplied PDF), GBA text /private/tmp/ict381-gba.txt. Current proposed design is docs/superpowers/specs/2026-10-06-skipq-design.md. Both empty course-intended GitHub clones exist at backend/ and frontend/; no app implementation requested in this subtask. Read actual TMA and proposed design. Return compact rubric coverage checklist with question/subpart marks totaling 100, highest-risk omissions or overengineering in design, and concrete fixes to secure assessment evidence. Be precise about assignment required vs proposed. Do not write files, implement code, install tools, or spawn agents. Do not browse unless needed; actual documents are available.
```

Verification performed: compared returned marks/requirements to PDF and incorporated the four Q1 audits, criterion-based seeding, designed Q4(c) cases, architecture limitations, same-order recording and stale-cart refusal into the actual plan. Corrected US10 to one All/Current/Past screen and described Ready feedback/email scope explicitly.

### A02 — Q1/Q2(c)/Q4/Q6/Q7(a): testing and evidence worksheet

```text
Planning-only independent testing/evidence review for ICT381 SkipQ assignment. Workspace /Users/arellakoo/Documents/DevOpsAss. Read /private/tmp/ict381-tma.txt and /private/tmp/ict381-gba.txt plus docs/superpowers/specs/2026-10-06-skipq-design.md. User wants complete plan for strongest rubric coverage, not app code yet. Design proposes C1 diner baseline, C2 vendor baseline, C3 seeded auth, C4 extra US10 past orders; Flask/MongoEngine, React, canonical Pending/Preparing/Ready/Collected plus Cancelled and NoShow. Produce a compact but concrete test/evidence strategy for Q2c seed criterion coverage, Q4a mock boundaries, Q4b repeatable real-DB lifecycle, Q4c DESIGN-ONLY extra-story functional test cases (columns exactly from PDF), Q6 browser/load evidence, Q7 screencast stale sold-out violation demonstration. You may create only docs/assessment/testing-and-evidence.md. Label all tests/results as planned, never claim execution. Prefer exact expected status codes per design. Include missing AC additions that audit Q1 must record. Do not change spec or other files, write product code, install packages, or spawn agents. Return file path and key risks.
```

Follow-up input:

```text
Refinement to simplify UI and meet US10's original all-current-and-past criterion: use existing /diner/orders Order List page with All/Current/Past filter, default All; endpoint GET /api/diner/orders?view=all|current|history. Remove separate /diner/history route/page. Existing tracking/detail shows read-only historical snapshots. Q5b explicitly discuss no new page needed, name Order List and Order Detail. Adjust test plan accordingly; I will update spec. Current authorization scope violations use 403 per design. Lockout addition uses 429 (five failures, 15-minute unlock) if needed.
```

Verification performed: read the generated worksheet, checked HTTP/state/cents expectations against design, aligned unit filenames and `Order.transition_to` method names with the implementation plan, and distinguished planned functional cases from actual software tests. Checked browser-only limits and that database timing materializes the query. No planned test was presented as executed.

## Future disclosure entry template

For each subsequent prompt, keep:

- Exact prompt and date/tool/model as recorded by your actual session.
- Related TMA question(s).
- Output used: actual files, decisions or test data.
- Verification performed: command/output or specific manual/source checks.
- Corrections made and remaining limitations.

Use your own account of understanding/verification in the final report. Do not replace an unrun command with “tested successfully.”
