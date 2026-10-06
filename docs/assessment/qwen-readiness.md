# Qwen Code readiness — 6 October 2026

Qwen Code is prepared to execute the existing SkipQ plan. This is a setup record, not a claim that Tasks 2–13 or the assessed evidence are complete. Model authentication and a live model/tool turn were not exercised; checks used the installed runtime's local loaders and real supporting tools without sending a model request.

## Installed skills

Personal skills live in `/Users/arellakoo/.qwen/skills/`; each complete skill directory, including available helpers/references, is installed. Qwen Code 0.25.0's actual `SkillManager` discovered and loaded all six bodies with **zero parse errors**. It also discovered **18 bundled skills**, including `review`, `agent-delegation`, `browser-use`, `computer-use` and `simplify`.

| Added skill | Purpose | Source |
|---|---|---|
| test-driven-development | Meaningful failing backend business-rule tests before implementation | Local installed [Superpowers 6.4.2](https://github.com/obra/superpowers/tree/main/skills/test-driven-development) copy |
| systematic-debugging | Diagnose reproducible failures before proposing fixes | Local installed [Superpowers 6.4.2](https://github.com/obra/superpowers/tree/main/skills/systematic-debugging) copy |
| verification-before-completion | Require current command evidence before claiming success | Local installed [Superpowers 6.4.2](https://github.com/obra/superpowers/tree/main/skills/verification-before-completion) copy |
| webapp-testing | Python Playwright browser inspection, screenshots and testing | [Anthropic webapp-testing](https://github.com/anthropics/skills/tree/main/skills/webapp-testing) |
| pdf | Extract, create and visually check PDF documents | [OpenAI PDF](https://github.com/openai/skills/tree/main/skills/.curated/pdf) |
| docx | Read/create/manipulate DOCX and validate Office structure | [Anthropic DOCX](https://github.com/anthropics/skills/tree/main/skills/docx) |

The GitHub skills were installed with the Codex skill-installer helper's explicit `--dest /Users/arellakoo/.qwen/skills` option. Sources are linked for attribution; the hash table identifies the installed bodies, which need not match later upstream changes. No global Qwen model/auth/approval configuration was changed.

| Skill | Installed SKILL.md SHA-256 |
|---|---|
| test-driven-development | `64b03fce4aee5a97a93160cea8111f3ba13a17b7c001db4bd5836d67fd10705d` |
| systematic-debugging | `808fc5717aa88ad65efff312b11c186294d3e6ee301afb584e2f86599b137787` |
| verification-before-completion | `2befe7fc55bcadaa3d97dd9e8efeb633d2561c0ebe74c5a8b17c4d9e7e4520b3` |
| pdf | `d108cf2b36355ab37eb5962933f4d09785ec002f3105c506129320209306b9d2` |
| docx | `8017469ea95fb7d28225c62daf8e2f3492a7b516fc64c18c28977cbf8980b7fe` |
| webapp-testing | `51b7349e77ec63b7744a6f63647e7566a0b4d2e301121cc10e8c2113af6556a2` |

The Qwen VS Code extension is `qwenlm.qwen-code-vscode-ide-companion-0.25.0-darwin-arm64`. Its bundled CLI returned `0.25.0` under Node 22.17.0. A separate `qwen` shell command is not installed on PATH; use the existing VS Code extension. The loader check used a read-only configuration stub with normal skill discovery; it proves discovery/parsing/body loading, not automatic selection by a particular model or an interactive session's permission decisions.

## Project context

Workspace `QWEN.md` imports [qwen-project-context.md](qwen-project-context.md), and the backend and frontend each have their own `QWEN.md`. The installed runtime's `loadServerHierarchicalMemory` loaded the root QWEN.md and its imported briefing. The briefing points to the existing design, implementation checklist, handoff and marking worksheets.

The same native checks from each repository also loaded its QWEN.md plus the parent workspace QWEN.md and discovered all six personal skills.

Independent review identified and resolved generic-skill conflicts in project instructions: CRA/Flask commands, plain skill names instead of plugin prefixes, preserving the lab foundation, separate offline/real-database suites, Q4(c) design-only, no frontend component suite, locator waits for a polling app, masked debug output and genuine measured evidence. The skill bodies themselves were preserved.

## Supporting tools checked

| Capability | Actual result |
|---|---|
| Backend test/browser/load tooling | Installed pytest 9.1.1, pytest-playwright 0.9.0, Playwright 1.63.0 and Locust 2.46.7; Locust version command passed |
| Native browser | Playwright-managed Chromium 153.0.8010.12 installed and launched; opened `http://127.0.0.1:5173` and found the SkipQ heading/title |
| Browser helper | `backend/.venv/bin/python ~/.qwen/skills/webapp-testing/scripts/with_server.py --help` passed |
| Original documents | pypdf read all 16 TMA PDF pages; python-docx opened the GBA with 363 paragraphs and 35 tables; embedded UML still requires image inspection |
| PDF utilities | Created/extracted a ReportLab PDF, rendered it with PyMuPDF and inspected the PNG |
| DOCX utilities | python-docx created/reopened a document; isolated npm docx created another; the installed skill's Office validator passed the generated npm document |
| DOCX conversion | Pandoc 2.12 at `/opt/anaconda3/bin/pandoc`; Microsoft Word installed; LibreOffice/Poppler are absent, and Word visual export was not exercised |
| Video encoding | Isolated FFmpeg 7.1 encoded a one-second 1280×720 H.264/AAC MP4 successfully; this synthetic tooling smoke is not the required narrated demonstration |
| Dependency integrity | Isolated document environment `pip check` passed; no application dependency manifests changed |

Document tools use workspace `.local/qwen-tools/.venv`, with pypdf 6.19.0, pdfplumber 0.11.10, ReportLab 5.0.1, PyMuPDF 1.28.2, python-docx 1.2.0, PyYAML 6.0.3, defusedxml 0.7.1 and imageio-ffmpeg 0.6.0. The DOCX validator initially lacked defusedxml; installing it resolved the failure. Isolated npm packages are under `.local/qwen-tools/node_modules`; do not add document authoring packages to the React app.

FFmpeg is available to Python through:

```python
import imageio_ffmpeg
ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
```

Use PyMuPDF for PDF page rendering, so Poppler is unnecessary for this workflow. If delivering DOCX, actually export/inspect its Word layout; XML validation alone does not establish page layout. Audio capture/narration must be genuinely supplied and reviewed. Original assessed models/routes/lifecycle suites/Locust results/video remain pending.

Local smoke artifacts, the frozen document dependency list and native loader JSON are under workspace `.local/qwen-tools/`, outside the assignment Git repositories. Personal skills are installed on this computer, not bundled into the two submissions; reinstall them on another computer as needed.

## Start the implementation session

1. Open `/Users/arellakoo/Documents/DevOpsAss` in VS Code and start a new Qwen Code chat, keeping both repositories accessible.
2. Run `/skills` and confirm the six personal skills are visible. `/memory` should list the workspace QWEN.md. Normal Qwen sessions discover personal skills automatically; [official skills documentation](https://qwenlm.github.io/qwen-code-docs/en/users/features/skills/) and [memory documentation](https://qwenlm.github.io/qwen-code-docs/en/users/features/memory/) describe these interfaces.
3. Send the existing handoff, or tell Qwen: `Read QWEN.md and QWEN_HANDOFF_PROMPT.md, then execute that handoff through every remaining plan task. Use the installed skills and verify actual outputs. Save a continuation record if interrupted.`
4. Qwen should check current status/tools/processes and begin Task 2 when the handoff is authorized. A model/authentication error should be reported accurately rather than treated as a missing skill.

Keep missing historical delegated prompts labelled as disclosure gaps. User narration, missing cover-page details, course-repository confirmation and final publishing/submission may still require user action. Skills provide workflows; successful implementation and grades depend on the actual work and assessment.
