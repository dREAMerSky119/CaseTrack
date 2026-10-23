# CaseTrack 360 — Full-stack prototype

CaseTrack 360 is a local AICTE complaint-intelligence prototype with a React/Vite frontend and a Flask + SQLite API. All included records are synthetic; this is not connected to live AICTE systems.

## Features included

- Persistent institutions and complaint records in SQLite.
- Session-based prototype login and logout; the login form takes a display name.
- Complaint create/read/update, input validation, search/filter API support, and stable IDs.
- Separate manual priority and frequency classification.
- Server-calculated explainable attention score (0–100), based on status, assigned priority, due date, last update, and age. It is a prototype heuristic, not an official decision.
- Rule-based recurring issue flags using institution/category and the previous 90 days.
- Potential related-case suggestions based on shared institution/category/keywords. Records are never auto-merged or deleted; suggestions remain reviewable.
- Case history and audit logs for key changes, related-case review, login/logout, and institution creation.
- Institution directory and complaint counts.
- Optional inter-bureau handover request endpoint.
- Analytics endpoint for summary counts.

## Requirements

- Node.js 18+ (Node.js 20+ recommended)
- Python 3.10+

## Start the backend (PowerShell / Windows)

Open a terminal in the project root, then:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

The first start creates `backend/instance/casetrack.db` and seeds five synthetic institutions and ten synthetic complaints. Keep this terminal open. API health check: `http://127.0.0.1:5000/api/health`.

If PowerShell blocks activation, run this in the same terminal and retry activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Start the frontend

Open a second terminal in the project root (the folder containing `package.json`):

```powershell
Copy-Item .env.example .env
npm install
npm run dev
```

`.env.example` sets `VITE_DEMO_MODE=false` and `VITE_API_BASE_URL=/api`. Vite proxies `/api` to Flask on port 5000, which keeps session cookies working across local frontend requests. Restart Vite after changing `.env`. Open the URL Vite prints, usually `http://localhost:5173`.

Login accepts a valid email, any non-empty password, and a display name for this prototype. This is intentionally convenient prototype authentication, **not production-grade authentication**. Do not use real passwords or sensitive complaint data.

## API endpoints

- `GET /api/health`
- `POST /api/auth/login` with `{ "email", "password", "displayName" }`
- `GET /api/auth/me`, `POST /api/auth/logout`
- `GET /api/complaints` (supports `q`, `status`, `priority`, `frequency`, `bureau`, `category`, `institutionId`)
- `GET /api/complaints/:id`, `POST /api/complaints`, `PATCH /api/complaints/:id`
- `GET /api/complaints/:id/history`
- `GET /api/institutions`, `POST /api/institutions`
- `GET /api/related-cases`, `POST /api/related-cases/:id/review`
- `GET /api/analytics`, `GET /api/audit-logs`
- `POST /api/complaints/:id/handovers`

All data endpoints except health and login/logout require a session. The frontend sends cookies with `credentials: include`; Flask CORS is configured for Vite on ports 5173.

## Data and safety notes

- The database is local at `backend/instance/casetrack.db`. Back it up before deleting or replacing it.
- Delete that database file only if you intentionally want to reset the prototype to its seeded synthetic data; stop Flask first.
- The demo identity/login must be replaced by proper password hashing, account provisioning, CSRF protections, secure cookie configuration, and organisation-approved identity integration before deployment.
- Server-side role-based permissions are not yet a complete multi-role authorization policy. This build is suitable for local demonstration and development, not production use with real complaint data.
- Frequency and related-case rules are heuristics. Officials must review suggestions; the system does not automatically merge cases or assign official determinations.

## Project layout

```text
CaseTrack360/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   └── run.ps1
├── src/
├── .env.example
├── package.json
└── README.md
```
