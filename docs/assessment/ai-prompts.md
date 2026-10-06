# AI disclosure starter — ICT381

**Status: planning and foundation setup log, 6 October 2026.** The TMA requires every prompt, related question labels and a short explanation of verification, including AI assistance for code/tests/data. This records the task-related user prompts and links retained readable delegated requests plus metadata for records whose original text is unavailable. Historical delegated-prompt disclosure gaps remain open. Export the conversation as an appendix if useful, and keep adding exact future prompts; this file is not a finished disclosure for the full application.

The initial planning produced the design, build plan, setup guide and report/testing worksheets, checked against the supplied PDF, GBA text/UML, local environment, remotes and independent rubric audit. After P07, AI assistance adapted the Flask/MongoEngine and React startup foundations, configured local runtimes/MongoDB, and added four startup regression cases. Domain models, authentication, seed records, persona/order flows, assessed feature suites, benchmark output and screencast are still pending. Startup checks must not be presented as those assessed results.

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
