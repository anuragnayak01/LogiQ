# logiQ — Custom AI agent with RAG for internal knowledge base

A chat app that answers questions from your company's SOPs, policies, and training docs, with cited sources. Frontend on Vercel, backend (FastAPI + Postgres/pgvector) on Render.

## Required environment variables (Render)

| Key | Value |
|---|---|
| `DATABASE_URL` | Your Render Postgres connection string (must have the `vector` extension available) |
| `LLM_PROVIDER` | `groq` |
| `GROQ_API_KEY` | From console.groq.com → API Keys. No extra spaces/quotes when pasting. |
| `ALLOWED_ORIGINS` | Your Vercel domain, e.g. `https://your-site.vercel.app` |
| `ADMIN_API_KEY` | Any random string — protects `/admin/*` routes |
| `PYTHON_VERSION` | `3.11` |

## Frontend setup

In `index.html`, set your live Render URL:
```js
const API_BASE_URL = window.MANIFEST_API_BASE_URL || "https://your-app.onrender.com";
```

## First run

The app auto-seeds 3 sample documents (forklift SOP, PTO policy, forklift training) on first startup if the database is empty — no manual step needed.

To load your **real** documents later:
```bash
curl -X POST https://your-app.onrender.com/admin/ingest \
  -H "X-Admin-Key: YOUR_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "Doc Title", "doc_type": "sop", "content": "full text..."}'
```
`doc_type` must be `sop`, `policy`, or `training`.

Check what's loaded:
```bash
curl https://your-app.onrender.com/admin/documents -H "X-Admin-Key: YOUR_ADMIN_API_KEY"
```

## Known dependency pin

`requirements.txt` pins `httpx==0.27.2`. Don't remove this — newer `httpx` breaks `openai==1.51.0` (used as Groq's client) with `TypeError: unexpected keyword argument 'proxies'`.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Chat shows "couldn't reach backend" | Check `/health` directly in browser; check CORS origin matches Vercel domain exactly |
| `/chat` 500, mentions `vector <=> double precision[]` | Query embedding not cast to pgvector type — see `db.py` |
| `/chat` 500, mentions `proxies` | `httpx` pin missing/removed from `requirements.txt` |
| `/chat` 500, `AuthenticationError 401` | `GROQ_API_KEY` invalid/stale — regenerate at console.groq.com |
| Chat says "couldn't find anything in the KB" | Database empty — see First run above |
