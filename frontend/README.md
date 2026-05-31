# Meroq Frontend

This is the Next.js frontend for the local Meroq FastAPI backend.

Streamlit remains the most complete UI, but this frontend now calls real API endpoints for:

- ticker analysis
- watchlist scanning
- portfolio exposure

## Run locally

Terminal 1, from the project root:

```powershell
python scripts/run_api.py --reload
```

Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## API URL

By default, the frontend calls:

```text
http://127.0.0.1:8000
```

Override it with:

```env
NEXT_PUBLIC_MEROQ_API_URL=http://127.0.0.1:8000
```

Keep local frontend env files out of Git.
