# TechCheck Diagnostic Web App

This folder contains the FastAPI + React rewrite of the Streamlit-based TechCheck Pilot diagnostic tool. It lives on the `disgnostic_app` branch so the existing Streamlit implementation remains untouched on `main`.

## Project layout

```
disgnostic_app/
├── backend/        # FastAPI service exposing the diagnostic endpoints
│   ├── app/
│   │   ├── config.py
│   │   ├── diagnostics.py
│   │   └── main.py
│   ├── requirements.txt
│   └── env.example
├── frontend/       # Responsive React + Vite single-page application
│   ├── src/
│   │   ├── api.ts
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── styles.css
│   │   └── types.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── env.example
└── README.md       # You are here
```

## Prerequisites

- **Python** 3.10 or newer
- **Node.js** 18+ (with npm)
- An **OpenAI API key** with access to the `gpt-5` model (define via `OPENAI_API_KEY`)

---

## Backend (FastAPI)

1. Create and activate a virtual environment (recommended):

   ```bash
   cd /Users/anuragmishra/Documents/Development/Practice/untitled\ folder/disgnostic_app/backend
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install requirements:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure secrets by copying `env.example` to `.env` (or export the variables directly):

   ```bash
   cp env.example .env
   # then edit .env to include your OPENAI_API_KEY
   ```

   Alternatively, place an `api.txt` file at the project root (same location as the Streamlit app) containing just the API key.

4. Run the development server (hot reload enabled):

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### API overview

- `GET /health` — lightweight health probe
- `POST /diagnose` — body contains technician/job/model/symptom data; returns structured probabilities, part numbers, verification steps, and the raw analysis transcript
- `POST /diagnose/issue-details` — optional helper to parse issue details given the raw analysis and issue title

---

## Frontend (React + Vite)

1. Install dependencies:

   ```bash
   cd /Users/anuragmishra/Documents/Development/Practice/untitled\ folder/disgnostic_app/frontend
   npm install
   ```

2. Copy `env.example` to `.env` (or `.env.local`) and point `VITE_API_BASE_URL` at the FastAPI server:

   ```bash
   cp env.example .env
   # edit .env if the backend is served from a different host/port
   ```

3. Start the Vite dev server:

   ```bash
   npm run dev
   ```

4. Open the provided URL (defaults to `http://localhost:5173`). The interface is responsive and optimized for both desktop and mobile service technicians.

### Production build

- Frontend: `npm run build` (outputs to `frontend/build/`)
- Backend: run behind any ASGI server (e.g., `uvicorn`, `gunicorn`+`uvicorn.workers.UvicornWorker`, etc.)

---

## Branch workflow

- All new work for the FastAPI/React port stays on `disgnostic_app`
- To push the branch without affecting `main`:

  ```bash
  git push origin disgnostic_app
  ```

  Coordinate review/merge separately so both the Streamlit and web experiences coexist.

---

## Helpful tips

- The backend automatically looks for `OPENAI_API_KEY` in the environment. If absent, it falls back to `api.txt` at the repository root (shared with the Streamlit version).
- CORS is open (`*`) by default for ease of local development. Lock it down with environment-specific settings before production.
- Use the `/diagnose/issue-details` endpoint if the frontend ever needs to re-parse the raw LLM analysis without re-running the entire diagnosis.
- Remember to respect OpenAI rate limits. Caching or queuing at the API layer may be helpful for high-volume deployments.

