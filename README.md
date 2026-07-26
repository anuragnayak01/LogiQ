# Manifest — Internal Knowledge Base RAG Agent

A RAG agent that answers employee questions from SOPs, policy manuals, and
training guides, backed by Postgres (pgvector) and a swappable LLM layer
(Claude or OpenAI).

Everything below is **deploy-only** — no local Python environment, no
`psql` shell, no local run required. Schema creation and data loading both
happen through the deployed API itself.

```
kb-agent/
├── backend/
│   ├── app/
│   │   ├── main.py         FastAPI app -- /health, /chat, /admin/*
│   │   ├── rag.py          retrieval + prompt assembly
│   │   ├── llm.py          swappable LLM provider (Claude / OpenAI)
│   │   ├── embeddings.py   OpenAI embeddings
│   │   ├── db.py           pgvector queries + schema auto-init
│   │   ├── ingestion.py    shared chunk/embed/store logic
│   │   ├── seed_data.py    3 baked-in sample docs (SOP/policy/training)
│   │   ├── ingest.py       optional local CLI (not required to deploy)
│   │   └── config.py       env-based settings
│   ├── sql/schema.sql      Postgres + pgvector schema (auto-applied on boot)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html          single-file chat UI (deploy to Vercel/Netlify)
│   ├── vercel.json
│   └── netlify.toml
└── sample_docs/            source text for the 3 baked-in seed docs
```

## Step 1 — Provision Postgres with pgvector

Any of these work; **Render Postgres** is the simplest if you're already
deploying the backend on Render:

1. Render dashboard → New → PostgreSQL → create an instance (free tier is
   fine for the demo).
2. Once it's up, copy the **External Database URL** shown on the instance
   page (starts with `postgresql://`). That's your `DATABASE_URL`.
3. pgvector ships pre-installed on Render Postgres — you don't need to do
   anything extra for the extension; the app creates it automatically on
   first boot (`CREATE EXTENSION IF NOT EXISTS vector;` runs at startup).

Other options: Supabase (enable "vector" under Database → Extensions),
Neon, or an existing self-hosted Postgres 15+ with pgvector installed at
the OS level.

## Step 2 — Deploy the backend (Render)

1. Push this repo to GitHub (or connect the folder directly if using
   Render's Git integration).
2. Render dashboard → New → Web Service → point at the repo, root
   directory `backend/`.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (Render → Environment tab):

   ```
   DATABASE_URL=<from Step 1>
   LLM_PROVIDER=claude
   ANTHROPIC_API_KEY=<your key>
   OPENAI_API_KEY=<your key>          # embeddings always use OpenAI
   ADMIN_API_KEY=<any random string>  # protects /admin/* routes
   ALLOWED_ORIGINS=https://your-frontend.vercel.app
   ```

6. Deploy. On boot, the app automatically runs `sql/schema.sql` against
   `DATABASE_URL` — tables exist the moment the service is live. Confirm:

   ```bash
   curl https://your-backend.onrender.com/health
   # {"status":"ok","llm_provider":"claude"}
   ```

## Step 3 — Load data (no local files needed)

**Option A — one call loads the 3 built-in sample docs** (warehouse
receiving SOP, PTO/attendance policy, forklift safety training):

```bash
curl -X POST https://your-backend.onrender.com/admin/seed \
  -H "X-Admin-Key: <your ADMIN_API_KEY>"
```

Response confirms each doc and its chunk count. Safe to re-run — it skips
titles already present.

Verify it landed:

```bash
curl https://your-backend.onrender.com/admin/documents \
  -H "X-Admin-Key: <your ADMIN_API_KEY>"
```

**Option B — ingest a real document** (once you're ready to swap in actual
company SOPs/policies), send its text directly as JSON:

```bash
curl -X POST https://your-backend.onrender.com/admin/ingest \
  -H "X-Admin-Key: <your ADMIN_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
        "title": "sop_returns_processing",
        "doc_type": "sop",
        "content": "Full text of the SOP goes here..."
      }'
```

No file upload plumbing needed for the demo — paste the doc text into the
JSON body. (For real PDFs/DOCX at scale later, extract text first, then
POST it the same way.)

## Step 4 — Test the RAG pipeline end-to-end

```bash
curl -X POST https://your-backend.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What do I do if a shipment seal does not match the BOL?"}'
```

You should get an answer citing `sop_warehouse_receiving` with a similarity
score.

## Step 5 — Deploy the frontend (Vercel or Netlify)

Before deploying, point `frontend/index.html` at your live backend by
adding this line right before `</head>`:

```html
<script>window.MANIFEST_API_BASE_URL = "https://your-backend.onrender.com";</script>
```

**Vercel:**
```bash
cd frontend
vercel deploy --prod
```

**Netlify:**
```bash
cd frontend
netlify deploy --prod
```

Open the deployed URL — you'll see the chat UI with suggested-question
chips pulled straight from the seeded sample docs. Ask one, confirm the
answer + source citation renders correctly, and you have a working demo.

## What data is loaded "for now," and how to swap it later

The 3 seed docs (`app/seed_data.py`) are realistic-but-fictional placeholders
covering the three required doc types (SOP, policy, training) — enough to
demo retrieval + citation behavior end-to-end. When you have real company
SOPs/policy manuals/training guides:

- Use `POST /admin/ingest` (Step 3, Option B) to add real ones alongside or
  instead of the seed docs.
- There's currently no delete route by design (avoids accidental data loss
  from a stray curl call) — if you need to remove the seed docs later, run
  `DELETE FROM kb_documents WHERE title IN ('sop_warehouse_receiving', 'policy_leave_and_attendance', 'training_forklift_safety');`
  directly against Postgres (cascades to `kb_chunks`), via Render's
  database dashboard SQL console — no local `psql` needed either.

## Notes on scaling this past the demo

- **Chunking**: sliding-window character chunker in `app/ingestion.py`. For
  longer/structured SOPs, a markdown-heading-aware or semantic chunker will
  improve retrieval precision.
- **Access control**: `/admin/*` routes are protected by a single shared
  key — fine for a demo, not for production. Gate `/chat` behind your real
  employee SSO before rolling this out company-wide.
- **Freshness**: `kb_documents`/`kb_chunks` have no versioning yet. Add an
  `is_current` flag and a re-ingestion job so outdated SOPs don't outrank
  updated ones in search.
- **Eval**: `kb_chat_log` captures every Q&A pair — use it to build a small
  golden-question set and track answer quality over time.
