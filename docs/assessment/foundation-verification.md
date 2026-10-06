# Lab-adapted foundation verification — 6 October 2026

Scope: startup foundation for Task 1. The plan, report/testing worksheets and lab provenance are prepared. Domain models, seeded accounts, sign-in, persona screens, ordering rules and assessed feature/lifecycle/performance tests are not implemented yet.

## Verified environment

Python 3.12.15, Node 22.17.0/npm 10.9.2, local MongoDB Community 8.0.32 on `127.0.0.1:27017`. Backend is Flask 3.1.3 with MongoEngine 0.29.3; frontend retains CRA with `react-scripts` 5.0.1 and JavaScript application code. The actual versions are pinned in requirement files, `.nvmrc` and the npm lockfile.

| Check | Actual result |
|---|---|
| Fresh temporary Python 3.12 virtual environment; install `requirements.txt` and `requirements-dev.txt` | Installation completed successfully |
| `python -m pip check` in fresh environment | `No broken requirements found.` |
| Bare `python -m pytest -q` in project and fresh environment | Four startup regression cases passed; network connection sentinel active |
| `npm ci --no-audit --no-fund` after compatible peer pin | Clean install completed successfully |
| `npm ls typescript --all` | All listed consumers resolve TypeScript 4.9.5; no invalid peer |
| `npm ci --dry-run --no-audit --no-fund` after removing unused proxy | Lockfile still valid |
| `npm run build` | `Compiled successfully.` |
| `npm start` using project `.env` | Development server compiled and listened on `127.0.0.1:5173` |
| Flask CLI startup on `127.0.0.1:5001` | Startup succeeded; live unknown API request returned JSON 404 / `not_found` |
| Live API CORS | Configured frontend origin allowed; unrelated origin receives no allow-origin header |
| Local MongoDB driver `ping` and `server_info` | Ping `ok: 1`; version `8.0.32` |
| Headless system Chrome through Python Playwright | Landing visible; unknown deep link and refresh visible; return link navigates home; direct API fetch succeeds through CORS; zero JavaScript page errors |
| Git ignore rules and local secret | `.env`, `.venv`, caches, node_modules and frontend build excluded; example/lockfiles and q6/q7 artifact paths remain trackable; backend `.env` mode 600 |

The temporary browser smoke script is separate from the required Q6 lifecycle suite. It used installed system Chrome, not a claimed course-browser installation. Its startup screenshot is local at workspace `.local/verification/skipq-foundation.png`, outside both repositories; it is not a Q5 persona-flow screenshot.

## Failures found and corrected

- The source frontend manifest/lockfile mismatch made `npm ci` fail. After repairing only the temporary source checkout's lockfile, its CRA 4/Webpack 4 build failed with `ERR_OSSL_EVP_UNSUPPORTED`. The target retains CRA and upgrades its build tool to 5.0.1.
- The first target lockfile auto-selected an incompatible TypeScript 7.0.2 optional peer. The build happened to succeed, but a clean install failed. Explicitly pinning CRA-compatible TypeScript 4.9.5 fixed installation and dependency-tree validation. Application code remains JavaScript.
- A proxy plus loopback `HOST` produced CRA's invalid `allowedHosts[0]` option. The unused proxy is removed; future browser API calls use the configured backend URL with backend CORS. Development startup then passed.
- Independent review showed JSON HTTP refusals discarded protocol headers. Both `Allow` and `Retry-After` assertions failed before the fix. Replacing the body on the original exception response preserves headers/status and passes both cases.
- MongoEngine registers the default alias globally. Sequential fixture initialization with different databases failed before teardown cleanup. The fixture now permits test-only DB names, forbids network connections and explicitly disconnects its alias after use, without deleting any data. It proves sequential reconfiguration, not simultaneous independent live apps.
- Homebrew MongoDB installation was blocked by the current macOS Command Line Tools. An official 8.0.32 archive was verified against the formula SHA-256 and extracted to workspace `.local/tools/`. The MongoDB process runs locally; no system tool deletion was performed.

## Current limits

After the user synced the labs, a fresh upstream check found one newer backend commit (`7d509dbcdeac18020a47677b79107805cd0f31cb`): only `DockerfileMongo` pins `mongo:7`. App code/dependencies/tests/seeds are unchanged. Frontend is unchanged at the recorded baseline. The clean new workspace lab folders match those latest commits. Both assignment origins were still empty at this check; local foundation work had not been published. See [provenance](../report/provenance.md).

The three local processes are foreground development processes, not installed auto-start services. Their restart commands are in [setup guide](setup-guide.md) and each README. The CRA dependency tree emits deprecation notices, and its dev server emits deprecated middleware warnings; verified install/start/build commands still succeeded on the pinned runtime. A later change requires appropriate re-verification.

These four unit cases establish startup integration behavior. They do not cover the assignment's business-rule allow/refuse cases, real-DB order lifecycle, two-persona browser lifecycle, load measurements or screencast. Those remain unchecked tasks in the implementation plan. Nothing has been submitted or pushed to GitHub during this setup.
