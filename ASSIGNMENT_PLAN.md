# ICT381 SkipQ assignment plan

**Deadline: 19 October 2026, 23:55 Singapore time.** Target completion is 18 October, leaving one day to resolve submission problems.

Both repositories have been cloned and their origins checked:

- `backend/` → [devops-assignment-BE](https://github.com/ArellaKoo/devops-assignment-BE)
- `frontend/` → [devops-assignment-FE](https://github.com/ArellaKoo/devops-assignment-FE)

The user selected **adapt lab code**. Both repositories now contain startup foundations on `setup/lab-adaptation`: a Flask/MongoEngine backend and a React SPA adapted from the public StaycationX labs. Clean dependency installations, four startup regression cases, MongoDB connectivity, frontend production build and browser startup/navigation/API access have passed. Domain models, seed accounts, sign-in, diner/vendor flows, and assessed feature tests are still planned. Confirm these are the course-intended submission repositories before final handover.

The proposed app covers diner ordering/tracking, vendor menu/order/trading operation, seeded role-based sign-in, and **US10: current/past orders** as the extra story. Stack is Flask + MongoEngine + local MongoDB, with a separate React SPA. The TMA assesses local building/testing rather than deployment.

Read these in order:

1. [Proposed design, scope corrections, models, API and routes](docs/superpowers/specs/2026-10-06-skipq-design.md)
2. [Complete implementation plan: all 100 marks, 13 tasks, dates and verification](docs/superpowers/plans/2026-10-06-skipq-tma.md)
3. [Local setup guide and observed environment](docs/assessment/setup-guide.md)
4. [Four GBA audits, architecture reasoning and report word budget](docs/assessment/report-workbook.md)
5. [Seed coverage, tests and evidence worksheet](docs/assessment/testing-and-evidence.md)
6. [AI prompt disclosure starter](docs/assessment/ai-prompts.md)
7. [Actual foundation verification and current limitations](docs/assessment/foundation-verification.md)

Estimated work: roughly 45–55 focused hours. Prioritize functioning persona flows, model-owned rules, real repeatable tests, and specific evidence. Keep styling simple. Collect report notes, screenshots, prompt verification and commits throughout the build.

The source choice is settled: [StaycationX_Backend](https://github.com/ArellaKoo/StaycationX_Backend) at `153ce9004ceb6fde84c35873b53b4957c76062a3` and [StaycationX_Frontend](https://github.com/ArellaKoo/StaycationX_Frontend) at `bc3367629ff31b920634dc3c046684f8c3877059`. The setup guide records the compatibility changes and commands. Next implementation task is typed models and repeatable seed data. US10 and the canonical lifecycle `Pending → Preparing → Ready → Collected` plus rejection/refund/no-show remain proposed business decisions for review. Seeded sign-in and simulated payment follow the TMA; no registration or real gateway is needed.

Task 1 is verified and committed locally in both repositories. A fresh check of the user's synced lab sources found only an excluded Docker image pin in backend commit `7d509db`; the frontend and all backend application/dependency/test/seed files match the adaptation baselines. Local work has not been pushed or submitted.

This plan maps every published marking requirement to a deliverable and verification step. It does not promise a grade or substitute for the working application and actual evidence.
