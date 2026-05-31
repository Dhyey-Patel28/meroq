# Frontend Scaffold

Release 1.7.0 adds a separate `frontend/` directory with an early Next.js app.

The frontend is intentionally a scaffold. It is not replacing Streamlit yet. Its purpose is to prove that the FastAPI service layer can support a future product UI.

## What is included

```text
frontend/
├── app/
│   ├── page.tsx
│   ├── ticker/page.tsx
│   ├── watchlist/page.tsx
│   └── portfolio/page.tsx
├── components/
├── lib/api.ts
├── package.json
├── tsconfig.json
└── next.config.ts
```

## Run order

From the project root, start FastAPI:

```powershell
python scripts/run_api.py --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## API configuration

By default, the frontend calls:

```text
http://127.0.0.1:8000
```

To change it:

```powershell
cd frontend
Copy-Item .\.env.example .\.env.local
```

Then edit:

```env
NEXT_PUBLIC_MEROQ_API_URL=http://127.0.0.1:8000
```

## What works now

- Backend status card
- Single ticker analysis page
- Watchlist scan page
- Portfolio analysis page
- Typed API helper functions in `frontend/lib/api.ts`

## What is intentionally not included yet

- Full chart parity with Streamlit
- Report download UI
- Auth
- Deployed hosting configuration
- Frontend CI/build checks

## Why keep Streamlit?

Streamlit is still the main research/product surface. The Next.js app is a migration path, not a replacement. The goal is to let the API contract mature before we spend time recreating every Streamlit view in React.
