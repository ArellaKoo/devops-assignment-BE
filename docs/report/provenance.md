# Lab adaptation provenance — ICT381 Q1(b)

This records the declared lab reuse and the final distinction between copied scaffolding and newly implemented SkipQ logic. Original source commits were recorded during adaptation; the reference clones are no longer present in this workspace at final inspection.

Backend source: [ArellaKoo/StaycationX_Backend](https://github.com/ArellaKoo/StaycationX_Backend), commit `153ce9004ceb6fde84c35873b53b4957c76062a3`.

Freshness check after the user synced the lab folders: backend `main` is now `7d509dbcdeac18020a47677b79107805cd0f31cb` (2 October 2026). The only change from the recorded adaptation baseline is `DockerfileMongo`: `FROM mongo` becomes `FROM mongo:7`, plus a final newline. Application modules, requirements, tests, README and seed files are identical. Docker is outside this local TMA build, so no new application adaptation is required. That was the source snapshot checked during adaptation.

Frontend source: [ArellaKoo/StaycationX_Frontend](https://github.com/ArellaKoo/StaycationX_Frontend), commit `bc3367629ff31b920634dc3c046684f8c3877059`. Its manifest and file structure identify the lab React application described in the assignment as myReactApp.

The frontend source snapshot checked during adaptation matched that commit. Assignment implementation is in `backend/` and `frontend/`.

| Source module | Actual reuse/adaptation | What it does and why SkipQ needs it |
|---|---|---|
| Backend `app/__init__.py` | Factory structure substantially rewritten in the same target path; no hardcoded lab secrets or hotel Blueprint imports copied | `create_app` assembles a configured Flask application. Development and tests configure their own database in separate processes; fixtures explicitly release the global MongoEngine alias before creating a differently configured app. |
| Backend `app/extensions.py` | Separate initialization pattern retained; rewritten for direct MongoEngine and a configured CORS origin | Database and browser-origin setup remain separate from routes. Direct MongoEngine avoids the old Flask-MongoEngine JSON encoder adapter while retaining the required document model approach. |
| Backend `requirements.txt` | Dependencies reviewed and reduced to the REST stack, with versions pinned after installation | Replaces legacy Flask/Werkzeug/form/Selenium dependencies with the libraries this local REST application needs. This is adapted dependency scaffolding, not original SkipQ domain logic. |
| Frontend `public/index.html` | Copied shell, adapted metadata/title and removed unused template assets | Provides the one HTML document mounting the React SPA. |
| Frontend `src/index.js` | React 18 `createRoot` entry pattern retained; removed unused web-vitals instrumentation | Starts the React application and supports client-rendered screens. |
| Frontend `src/index.css` | Base font/smoothing styles copied | Provides readable system fonts without extra styling scope. |
| Frontend `src/App.js` | BrowserRouter/Routes/Route pattern substantially rewritten; hotel/OneMap imports and routes omitted | Defines the final nested diner/vendor routes and their shared role gates/layouts. |
| Frontend `package.json` | CRA/React/React Router/Bootstrap basis adapted; regenerated lockfile; react-scripts updated to 5.0.1 and compatible TypeScript 4.9.5 build peer pinned | Keeps the lab build approach while resolving the manifest/lock mismatch, Webpack 4/OpenSSL failure and incompatible optional peer observed on Node 22. Scaffold generator and unused frontend test packages/scripts were removed; JavaScript app code remains JavaScript. |

No hotel models, booking/package endpoints, lab seed BSON/users CSV, hardcoded keys, OneMap components, Selenium tests, Docker images or deployment files are imported. Their absence is intentional adaptation to the TMA scope.

The lab factory, extension, React-entry and routing scaffolding above is the declared reuse. SkipQ domain models (`app/models/`), signed-token/role enforcement (`app/auth.py`), REST persona controllers, fixture seed data and assessed tests are new application-specific implementations, not copied hotel models or test files. The lab’s legacy hashing/session approach was not retained; credentials use the current Werkzeug hash API and tokens use itsdangerous. Frontend persona pages, the shared API client, authentication/feedback contexts and mutation guards are new SkipQ code within the adapted CRA/router structure.

AI assistance is recorded separately in `docs/assessment/ai-prompts.md`; the student must retain exact prompts and verify/explain submitted code.

Foundation error handling follows the response-preserving pattern in the [Flask error-handling documentation](https://flask.palletsprojects.com/en/stable/errorhandling/). Explicit fixture teardown follows [MongoEngine's documented connection lifecycle](https://docs.mongoengine.org/guide/connecting.html#disconnecting-an-existing-connection). Startup regression cases prove these two integration assumptions; they are not the assignment's domain/lifecycle coverage.
