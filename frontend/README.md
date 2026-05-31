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


## 1.8.1 UX notes

The ticker page now follows an evidence-first workflow:

1. show the signal and confidence,
2. summarize risk and sentiment,
3. show source-linked headline cards,
4. keep raw headline tables behind disclosure.

Article links open in a new browser tab using `target="_blank"` and `rel="noopener noreferrer"`.

## 1.8.2 forecast UX

The ticker page now renders a forecast range from API `risk_percentiles` details:

- current close reference line,
- median simulated path,
- 10th to 90th percentile range,
- plain-English direction/evidence/risk panel.

The chart is intentionally implemented as a lightweight SVG component before adding D3. This keeps the UI stable while the API data contract matures.
