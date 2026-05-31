# Meroq Frontend Scaffold

This is an early Next.js scaffold for the Meroq FastAPI backend. It does not replace the Streamlit app yet.

## Run locally

Start the API from the project root:

```powershell
python scripts/run_api.py --reload
```

Then start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Configuration

Copy `.env.example` to `.env.local` if the API runs somewhere else:

```powershell
Copy-Item .\.env.example .\.env.local
```

```env
NEXT_PUBLIC_MEROQ_API_URL=http://127.0.0.1:8000
```

## Current pages

- `/` — migration dashboard and backend status
- `/ticker` — single ticker analysis
- `/watchlist` — watchlist scan
- `/portfolio` — portfolio exposure view

This frontend intentionally starts simple. Streamlit remains the main production/prototype UI while the API contract stabilizes.
