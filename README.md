# Manifest — Internal Knowledge Base RAG Agent

A RAG agent that answers employee questions from SOPs, policy manuals, and
training guides. This configuration runs **entirely free**: Groq for the LLM,
a local embedding model (no API key), and a free-tier Postgres instance.

Deploy-only workflow — no local Python environment, no `psql` shell required.

```
kb-agent/
├── backend/
│   ├── app/
│   │   ├── main.py         FastAPI app -- /health, /chat, /admin/*
│   │   ├── rag.py          retrieval + prompt assembly
│   │   ├── llm.py          swappable LLM provider (Groq / Claude / OpenAI)
│   │   ├── embeddings.py   swappable embeddings (fastembed local / OpenAI)
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

## Step 1 — Free Postgres with pgvector: Neon

[Neon](https://neon.tech) has a genuinely free tier (not a trial) with
pgvector supported out of the box.

1. Sign up at neon.tech → **Create a project**
2. Once created, go to the project **Dashboard** → copy the **Connection
   string** shown (starts with `postgresql://`). That's your `DATABASE_URL`.
3. Nothing else to configure — pgvector is available, and the app enables
   the extension automatically on first boot.

(Supabase's free tier also works identically if you prefer it — same
`postgresql://` connection string, same auto-setup on boot.)

## Step 2 — Free Groq API key

1. Sign up at [console.groq.com](https://console.groq.com)
2. **API Keys** → **Create API Key** → copy it (starts with `gsk_`)
3. Groq's free tier gives generous rate limits on models like
   `llama-3.3-70b-versatile` (the default here) — plenty for a demo.

## Step 3 — Deploy the backend (Render)

1. Push this repo to GitHub.
2. Render dashboard → New → Web Service → connect the repo, root directory
   `backend`.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Environment variables:

   ```
   DATABASE_URL=<from Step 1, Neon>
   LLM_PROVIDER=groq
   GROQ_API_KEY=<from Step 2>
   ADMIN_API_KEY=<any random string you make up>
   ALLOWED_ORIGINS=*
   ```

   Notice: **no OpenAI or Anthropic key needed** — embeddings default to
   `fastembed`, a small local model that downloads once on first boot and
   runs on CPU for free.

6. Deploy. First boot will take a bit longer than usual (~30-60s extra) the
   very first time, while fastembed downloads its model weights. Subsequent
   deploys reuse Render's build cache and are faster.

7. Verify:
   ```bash
   curl https://your-backend.onrender.com/health
   # {"status":"ok","llm_provider":"groq"}
   ```

## Step 4 — Load data (no local files needed)

```bash
curl -X POST https://your-backend.onrender.com/admin/seed \
  -H "X-Admin-Key: <your ADMIN_API_KEY>"
```

Verify:
```bash
curl https://your-backend.onrender.com/admin/documents \
  -H "X-Admin-Key: <your ADMIN_API_KEY>"
```

Ingest a real document later the same way:
```bash
curl -X POST https://your-backend.onrender.com/admin/ingest \
  -H "X-Admin-Key: <your ADMIN_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"title": "sop_returns_processing", "doc_type": "sop", "content": "full text here..."}'
```

## Step 5 — Test the RAG pipeline

```bash
curl -X POST https://your-backend.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What do I do if a shipment seal does not match the BOL?"}'
```

## Step 6 — Deploy the frontend (Vercel)

Add this line before `</head>` in `frontend/index.html`, pointing at your
Render URL:
```html
<script>window.MANIFEST_API_BASE_URL = "https://your-backend.onrender.com";</script>
```

```bash
cd frontend
vercel deploy --prod
```

Then go back to Render → Environment → set
`ALLOWED_ORIGINS=https://your-frontend.vercel.app` so the browser isn't
blocked by CORS, and Render will auto-redeploy.

## Swapping providers later (all still swappable)

- **LLM**: set `LLM_PROVIDER=claude` or `openai` + the matching API key —
  zero code changes.
- **Embeddings**: set `EMBEDDING_PROVIDER=openai`, `EMBEDDING_MODEL=text-embedding-3-small`,
  `EMBEDDING_DIM=1536` — but note you'll need to re-ingest all documents,
  since embeddings from different models/dimensions aren't compatible with
  each other in the same `kb_chunks` table. Easiest path: wipe `kb_chunks`
  and re-run `/admin/seed` + `/admin/ingest` after switching.

## Notes on scaling this past the demo

- **Render free tier** spins down after ~15 min idle; first request after
  a gap will be slow (cold start + fastembed model load). Fine for a demo,
  worth mentioning as a known limitation in your "key learnings" section.
- **Chunking**: sliding-window character chunker in `app/ingestion.py`.
- **Access control**: `/admin/*` routes share one key — fine for a demo,
  not for production; gate `/chat` behind real employee SSO before rollout.
- **Eval**: `kb_chat_log` captures every Q&A pair for later analysis.
