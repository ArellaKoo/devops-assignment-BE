# Qwen CLI installation and overnight use

CLI installation verified on 7 October 2026: official `@qwen-code/qwen-code@0.25.0` from npm, under the existing nvm Node 22.17.0 installation. The registry's current version was 0.25.0 and requires Node >=22. The launcher is `/Users/arellakoo/.local/bin/qwen`; it selects Node 22 for the Qwen process. A PATH block was appended to `.zshrc`; its prior contents are backed up to `/Users/arellakoo/.local/qwen-install/zshrc.before` (private local file).

Verified: a fresh interactive login shell resolves `qwen`, prints version 0.25.0 and still reports Node 20.20.1 as its default. `npm ls -g @qwen-code/qwen-code --depth=0` passed. The CLI's read-only `-p /goal` command printed `No Goal is set.` No assignment worker was started and no model inference request was made.

The installed standalone runtime discovered/loaded all six personal skills and 18 bundled skills, with zero parse errors, and loaded the workspace QWEN.md plus its imported project briefing. The initial CLI control check left the settings digest unchanged. A later check detected a concurrent settings write with new `ui`/`ide` keys; it was preserved. Credentials/model/approval settings were not manually edited, and no complete-file unchanged claim is made for the whole session. `/skills` is interactive in this installed CLI; the headless check returned `The command "/skills" is not supported in this mode.` Use its interactive panel.

## Start with an interactive check

Open a new terminal so it reads the PATH update:

```bash
cd /Users/arellakoo/Documents/DevOpsAss
caffeinate -is qwen --approval-mode auto
```

Existing `~/.qwen` settings and skills are reused. Accept trust for this workspace if prompted. Use `/auth` inside Qwen if the provider reports missing/invalid authentication; live model authentication has not been tested. Check `/skills` and `/memory`, then paste the persistent Goal from `qwen-overnight-goal.txt`. Check `/goal` shows active and watch an actual edit/test succeed before leaving.

The `caffeinate` assertion lasts while Qwen runs. Plug in the Mac, leave its lid open and keep the terminal running. Pause any other Qwen worker modifying these repositories; VS Code can remain open as an editor.

## Optional headless run bounded to eight hours

After the interactive auth/trust check, exit that idle session or pause its active goal before starting this separate worker. From the workspace root:

```bash
mkdir -p .local
qwen_run_stamp="$(date +%Y%m%d-%H%M%S)"
caffeinate -is qwen \
  --approval-mode auto \
  --chat-recording \
  --max-wall-time 8h \
  --max-tool-calls 1500 \
  --output-format stream-json \
  -p "$(cat backend/docs/assessment/qwen-overnight-goal.txt)" \
  > ".local/qwen-overnight-${qwen_run_stamp}.jsonl" \
  2> ".local/qwen-overnight-${qwen_run_stamp}.stderr"
```

This starts real assignment work/model usage when executed and saves local logs/session history. Limits bound the run; they do not guarantee completion. Goal-generated continuation turns are not capped by `--max-session-turns`, so use wall-time/tool limits for a headless run.

Use the explicit session ID from the log with `qwen --resume '<session-id>' -p '/goal'` to inspect saved state, or replace `/goal` with `/goal resume` to continue real work. Avoid `--continue` if another VS Code/CLI session has since become the latest project chat.

Auto approval can still block or request intervention. Goals can pause on authentication/quota errors, limits, no progress or genuine blockers. Actual student narration, missing personal details, final review and publishing/submission remain human actions. Keep incomplete requirements openly pending.

Official references: [installation](https://github.com/QwenLM/qwen-code/blob/main/scripts/installation/INSTALLATION_GUIDE.md), [Goals](https://qwenlm.github.io/qwen-code-docs/en/users/features/goals/), [headless mode](https://qwenlm.github.io/qwen-code-docs/en/users/features/headless/), [approval modes](https://qwenlm.github.io/qwen-code-docs/en/users/features/approval-mode/) and [authentication](https://qwenlm.github.io/qwen-code-docs/en/users/configuration/auth/).
