# Frontend Scaffold

The frontend scaffold has evolved into an API-connected Next.js client as of release 1.8.0.

Streamlit is still the complete Meroq interface. The frontend exists to validate the future FastAPI + Next.js architecture without disrupting the working Streamlit app.

## Run

Start the backend:

```powershell
python scripts/run_api.py --reload
```

Start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Environment

The frontend calls:

```text
http://127.0.0.1:8000
```

Override with:

```env
NEXT_PUBLIC_MEROQ_API_URL=http://127.0.0.1:8000
```

Use local frontend env files only. Do not commit secrets.
