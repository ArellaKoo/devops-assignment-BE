# Lab adaptation provenance — ICT381 Q1(b)

This is the initial foundation record, not a claim that the SkipQ feature implementation is complete. Update it as further modules are adapted.

Backend source: [ArellaKoo/StaycationX_Backend](https://github.com/ArellaKoo/StaycationX_Backend), commit `153ce9004ceb6fde84c35873b53b4957c76062a3`.

Freshness check after the user synced the lab folders: backend `main` is now `7d509dbcdeac18020a47677b79107805cd0f31cb` (2 October 2026). The only change from the recorded adaptation baseline is `DockerfileMongo`: `FROM mongo` becomes `FROM mongo:7`, plus a final newline. Application modules, requirements, tests, README and seed files are identical. Docker is outside this local TMA build, so no new application adaptation is required. The clean workspace `StaycationX_Backend/` clone matches this latest commit.

Frontend source: [ArellaKoo/StaycationX_Frontend](https://github.com/ArellaKoo/StaycationX_Frontend), commit `bc3367629ff31b920634dc3c046684f8c3877059`. Its manifest and file structure identify the lab React application described in the assignment as myReactApp.

The fresh frontend fetch and clean workspace `StaycationX_Frontend/` clone still match that commit, with no upstream changes. The source folders remain reference repositories; the adapted assignment work is in `backend/` and `frontend/`.

| Source module | Actual reuse/adaptation in the foundation | What it does and why SkipQ needs it |
|---|---|---|
| Backend `app/__init__.py` | Factory structure substantially rewritten in the same target path; no hardcoded lab secrets or hotel Blueprint imports copied | `create_app` assembles a configured Flask application. Development and tests configure their own database in separate processes; fixtures explicitly release the global MongoEngine alias before creating a differently configured app. |
| Backend `app/extensions.py` | Separate initialization pattern retained; rewritten for direct MongoEngine and a configured CORS origin | Database and browser-origin setup remain separate from routes. Direct MongoEngine avoids the old Flask-MongoEngine JSON encoder adapter while retaining the required document model approach. |
| Backend `requirements.txt` | Dependencies reviewed and reduced to the REST stack, with versions pinned after installation | Replaces legacy Flask/Werkzeug/form/Selenium dependencies with the libraries this local REST application needs. This is adapted dependency scaffolding, not original SkipQ domain logic. |
| Frontend `public/index.html` | Copied shell, adapted metadata/title and removed unused template assets | Provides the one HTML document mounting the React SPA. |
| Frontend `src/index.js` | React 18 `createRoot` entry pattern retained; removed unused web-vitals instrumentation | Starts the React application and supports client-rendered screens. |
| Frontend `src/index.css` | Base font/smoothing styles copied | Provides readable system fonts without extra styling scope. |
| Frontend `src/App.js` | BrowserRouter/Routes/Route pattern substantially rewritten; hotel/OneMap imports and routes omitted | Supplies the React Router structure that later diner/vendor screens will extend. |
| Frontend `package.json` | CRA/React/React Router/Bootstrap basis adapted; regenerated lockfile; react-scripts updated to 5.0.1 and compatible TypeScript 4.9.5 build peer pinned | Keeps the lab build approach while resolving the manifest/lock mismatch, Webpack 4/OpenSSL failure and incompatible optional peer observed on Node 22. Scaffold generator and unused frontend test packages/scripts were removed; JavaScript app code remains JavaScript. |

No hotel models, booking/package endpoints, lab seed BSON/users CSV, hardcoded keys, OneMap components, Selenium tests, Docker images or deployment files are imported. Their absence is intentional adaptation to the TMA scope.

The legacy backend uses Flask-MongoEngine and old hashing/token/session behavior. Its User/auth/test-client patterns are useful references for later work, but are not yet imported or claimed as implemented. When those modules are adapted, add exact files and explanations here. Do not imply this foundation includes sign-in, seed data, lifecycle or test evidence that has not been built.

AI assistance is recorded separately in `docs/assessment/ai-prompts.md`; the student must retain exact prompts and verify/explain submitted code.

Foundation error handling follows the response-preserving pattern in the [Flask error-handling documentation](https://flask.palletsprojects.com/en/stable/errorhandling/). Explicit fixture teardown follows [MongoEngine's documented connection lifecycle](https://docs.mongoengine.org/guide/connecting.html#disconnecting-an-existing-connection). Startup regression cases prove these two integration assumptions; they are not the assignment's domain/lifecycle coverage.
