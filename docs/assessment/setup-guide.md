# SkipQ local setup guide

**Status on 6 October 2026:** the user selected lab adaptation. Both repositories contain startup foundations; dependencies and local MongoDB are installed. Backend app creation, JSON errors, configured CORS, MongoDB ping/version, a fresh Python dependency installation, four foundation regression tests, clean frontend installation, production build and browser startup/navigation/API access have passed. Domain models, seed accounts, token endpoints, persona screens, and assessed feature tests are not implemented yet. See [the foundation verification record](foundation-verification.md). The application READMEs are the handover instructions.

## Verified environment

| Item | Observed state | Project use |
|---|---|---|
| Backend repository | `backend/`, correct BE origin, `setup/lab-adaptation` | Adapted Flask/MongoEngine startup foundation |
| Frontend repository | `frontend/`, correct FE origin, `setup/lab-adaptation` | Adapted React entry/router and landing page |
| Git | `/usr/bin/git` | Separate repositories; parent is not a monorepo |
| Homebrew | `/opt/homebrew/bin/brew` | Python installed; MongoDB formula blocked by current Command Line Tools |
| Python | 3.12.15 at `/opt/homebrew/bin/python3.12` | Backend `.venv`; existing Python 3.14.4 was not replaced |
| Node/npm | nvm Node 22.17.0, npm 10.9.2 | Frontend `.nvmrc`; default Node for other projects was not changed |
| MongoDB | Official standalone Community 8.0.32 arm64 archive | Workspace-local process on `127.0.0.1:27017`; binary is not on PATH |
| Docker/AWS/Terraform | Unused for this TMA | No cloud or operations setup required |

```text
/Users/arellakoo/Documents/DevOpsAss/
  backend/      # its own Git repository and .venv
  frontend/     # its own Git repository and node_modules
  docs/         # workspace planning documents
  .local/
    tools/mongodb-macos-aarch64--8.0.32/bin/mongod
    mongodb/    # local database data
    mongodb.log
```

Both origins are already set. Check course repository provenance/access before submission. The source choice alone does not establish that the requested repositories are the course-provided submission repositories.

## Selected lab sources and compatibility changes

- Backend: [StaycationX_Backend](https://github.com/ArellaKoo/StaycationX_Backend), commit `153ce9004ceb6fde84c35873b53b4957c76062a3`.
- Frontend: [StaycationX_Frontend](https://github.com/ArellaKoo/StaycationX_Frontend), commit `bc3367629ff31b920634dc3c046684f8c3877059`.

Both public sources belong to the user. The backend preserves the factory/extension organization, with current Flask and direct MongoEngine replacing the old Flask adapter. The frontend preserves React 18's entry point, font CSS, HTML shell, and Router pattern. Hotel/OneMap pages, old credentials, database seeds, and Selenium code were not copied. Actual module reuse is recorded in `backend/docs/report/provenance.md`.

The user's synced reference folders are now also present at workspace `StaycationX_Backend/` and `StaycationX_Frontend/`. Fresh checks show the backend's latest commit `7d509dbcdeac18020a47677b79107805cd0f31cb` differs from the adaptation baseline only by pinning the excluded Docker Mongo image to version 7; app/dependency/test/seed files are unchanged. Frontend remains at the baseline above. Keep reference sources separate from the adapted assignment repositories.

The source frontend's manifest/lockfile mismatch prevented `npm ci`. Its CRA 4/Webpack 4 build then failed with `ERR_OSSL_EVP_UNSUPPORTED` on Node 22.17.0 after the temporary baseline lockfile was repaired. The target retains Create React App, upgrades `react-scripts` to 5.0.1, and pins its compatible TypeScript 4.9.5 build peer after npm selected an incompatible optional peer. A regenerated lockfile passed clean `npm ci`, dependency-tree validation and production build. Application source remains JavaScript. The unused proxy was removed after it produced an invalid `allowedHosts` setting with the loopback `HOST`; the planned API client uses the explicit backend URL and backend CORS. Vite is not used.

Homebrew successfully installed Python 3.12.15. The MongoDB Homebrew formula was blocked by the existing Command Line Tools version. The fallback uses the official [MongoDB 8.0.32 macOS arm64 archive](https://fastdl.mongodb.org/osx/mongodb-macos-arm64-8.0.32.tgz), extracted under `.local/tools/` after verifying SHA-256 `f81cb258434d548dca7244d599c82eb339043d8dedd0b1b807870c9d263117f2`. No system tool deletion or upgrade was performed. For another machine, use the [official MongoDB macOS installation instructions](https://www.mongodb.com/docs/v8.0/tutorial/install-mongodb-on-os-x/) appropriate to that machine, then record its actual successful binary path.

## Local MongoDB: terminal 1

The server was started and verified during setup. Start this foreground command only when there is no existing MongoDB process listening on port 27017:

```bash
cd /Users/arellakoo/Documents/DevOpsAss
mkdir -p .local/mongodb
./.local/tools/mongodb-macos-aarch64--8.0.32/bin/mongod \
  --dbpath "$PWD/.local/mongodb" \
  --bind_ip 127.0.0.1 \
  --port 27017 \
  --logpath "$PWD/.local/mongodb.log" \
  --logappend
```

MongoDB binds only to loopback. Stop a foreground process with Ctrl-C. Keep its binaries, data, and logs outside both repositories. `mongosh` is not needed for this setup; verify with the installed Python driver from the backend directory:

```bash
cd /Users/arellakoo/Documents/DevOpsAss/backend
.venv/bin/python - <<'PY'
from pymongo import MongoClient
client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=3000)
print(client.admin.command("ping"))
print(client.server_info()["version"])
client.close()
PY
```

The observed result was a successful ping and version `8.0.32`.

## Backend: terminal 2

The backend already has `.venv` and an ignored `.env` with a generated local secret. Use that existing environment:

```bash
cd /Users/arellakoo/Documents/DevOpsAss/backend
source .venv/bin/activate
python -m flask --app app:create_app run --host 127.0.0.1 --port 5001
```

Port 5001 avoids common macOS port-5000 conflicts. For a new checkout, create/install/configure the environment following `backend/README.md`:

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Copy `.env.example` only when no local `.env` exists, then generate a local secret using the README instructions. Do not overwrite the configured secret during a routine restart. The committed example contains this credential-free contract:

```dotenv
MONGODB_HOST=mongodb://127.0.0.1:27017
MONGODB_DB=skipq_dev
TEST_MONGODB_DB=skipq_test
FRONTEND_ORIGIN=http://127.0.0.1:5173
TOKEN_SECRET=replace-with-a-local-random-secret
```

The application factory loads dotenv/config and refuses the placeholder token secret. A JSON 404 for an unknown API route is a valid foundation smoke check; no business endpoints exist yet:

```bash
curl -i http://127.0.0.1:5001/api/nonexistent
```

MongoEngine's default connection alias permits one active database configuration per Python process. A future fixture must explicitly disconnect during teardown before creating an app with a different configuration. Do not automatically retarget a live app's connection. Run development and browser-test APIs as separate processes with their respective database settings.

Current foundation regression command:

```bash
python -m pytest tests/unit -q
```

Four startup cases passed without network access: JSON errors preserve `Allow` on 405 and `Retry-After` on 429, and sequential test apps release/reconfigure the default MongoEngine connection through fixture teardown. Fixtures permit only `skipq_unit_*` database names and do no database cleanup. These are foundation tests; the domain-rule cases required by Q4(a) remain planned. A fresh Python 3.12 environment installed both pinned requirement files, and `pip check` reported no dependency conflicts.

## Frontend: terminal 3

The frontend already has dependencies and an ignored `.env`. Select its project runtime in this terminal and start Create React App:

```bash
cd /Users/arellakoo/Documents/DevOpsAss/frontend
source "$HOME/.nvm/nvm.sh"
nvm use
npm start
```

The committed `.nvmrc` selects Node 22.17.0. For a new checkout, run `nvm install` if this version is missing, then `nvm use`, `npm ci`, and copy `.env.example` when no local `.env` exists. The frontend configuration is:

```dotenv
REACT_APP_API_BASE_URL=http://127.0.0.1:5001
HOST=127.0.0.1
PORT=5173
BROWSER=none
```

Open `http://127.0.0.1:5173`. The current app has a SkipQ landing page and a not-found route. A headless Chrome smoke check verified rendering, a refreshed unknown deep link, return navigation, and a direct browser request to the API through CORS, with zero JavaScript page errors. This temporary check used the installed system Chrome; the future assessed suite will install/use Playwright's browser. The base URL is configured for future shared API code; login, protected routes, and persona pages are pending. Build command: `npm run build`. CRA dependencies and dev middleware emit deprecation notices; installation, compilation and startup still passed on the pinned runtime.

## Future assignment commands: not implemented yet

Task 2 will add `python -m db_seed.seed`, demo account credentials, and repeatable data. Task 3 will add token acquisition and a protected endpoint example. Do not run guessed seed/login commands or treat them as current functionality.

After the domain and integration suites exist, assignment verification is planned as follows. The current four foundation cases do not establish the domain unit-suite requirement:

```bash
python -m pytest tests/unit -q
python -m pytest tests/functional -q
python -m pytest tests/functional -q
python -m playwright install chromium
python -m pytest tests/playwright -q
python -m pytest tests/playwright -q
```

Assessed unit tests must run without MongoDB. Functional tests use `skipq_test`; browser tests use `skipq_system_test`; neither cleans `skipq_dev`. The browser suite needs both servers running and its API pointed at the dedicated seeded database. Consecutive runs must use the same configured test database and produce fresh isolated orders. Locust commands and required output paths are in the implementation plan. Startup smoke checks and a production build are not evidence that these assessed suites pass.

## Git and handover

Use `git -C backend ...` and `git -C frontend ...`, or work from inside the corresponding directory. Both starter branches are `setup/lab-adaptation`. Each clone had no initial commit, so this foundation uses a branch rather than a worktree. Commit each real completed increment and push to its matching origin when publishing is authorized. Both READMEs must eventually cross-link each other and the screencast. Track lockfiles/examples; ignore `.env`, `.venv`, node_modules, caches, and normal builds. Keep required measured `q6-performance/` and `q7-screencast/` artifacts tracked.

Before submitting, fresh-clone both repositories into temporary folders and follow README alone. Verify marker access, demo credentials, install/config/seed/run/token/test instructions, and all recording links. That final application rehearsal remains planned; it has not yet been executed.
