Complete my ICT381 SkipQ assignment implementation and evidence package by executing the existing complete plan. Work in:
/Users/arellakoo/Documents/DevOpsAss

I approve US10 (current/past orders) as the extra story and the scope/lifecycle corrections documented in the design. Proceed through Tasks 2–13; Task 1 is already completed. Make routine implementation decisions independently. Do not stop after producing another plan, a skeleton, or one milestone. Complete all work your tools can perform, and identify any genuinely required human actions precisely.

Read these before editing, with paths relative to the workspace:
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
- Do not invent my PI number, personal details or submission status. Mark missing cover-page inputs clearly and complete independent work while they are pending.

Final handover:
- Finish both READMEs with verified install/config/seed/run/token/test commands, demo accounts and cross-links. Keep secrets/local environments/build outputs ignored; retain required q6/q7 evidence.
- Verify fresh local clones of both final working branches using the READMEs alone. Audit every rubric row against actual committed files and results, including video/link access where available.
- Make local commits. Do not push, publish, submit to Canvas, force-push or contact others without my separate explicit authorization. Prepare concrete publishing/submission steps for my review. Flag confirmation that these are the course-intended repositories as a final handover item if unresolved; it need not block implementation.
- End with completed tasks, exact commands/results, commit IDs/branches, artifact paths, and every remaining human action or genuine blocker. Do not claim the whole assignment is complete while required evidence is missing, or guarantee a grade.

Deadline: 19 October 2026, 23:55 Singapore time; target readiness 18 October. Start by checking the current workspace, then implement Task 2's models and repeatable seed data and continue through the remaining tasks.
