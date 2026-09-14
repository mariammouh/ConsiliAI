# ConsiliAI

<p align="center">
  <img src="frontend/public/logo.png" alt="ConsiliAI logo" width="180"/>
</p>

ConsiliAI is a research-to-education assistant I built during a two-month engineering internship at 3D SMART FACTORY, under the supervision of Thierry BERTIN, Omar KELLA and Ibtihal KHALIL. The idea is simple to state and less simple to build: take a technical project idea, do the literature and code-ecosystem research a student or researcher would normally spend weeks on, and then turn what it finds into something you could actually teach from — a syllabus, slide decks, lab exercises with working code, and experiment protocols with benchmark grading.

It started as a plain research assistant (search papers, summarize, suggest a plan) and pivoted about ten days in, after supervisor feedback, toward the educational side — which ended up being the more interesting half of the project.

## What it actually does

Give it an idea like "federated learning on edge IoT devices" and, depending on what you ask for, it will:

- Pull papers from arXiv, Semantic Scholar and OpenAlex, filter them down with embeddings + an LLM rerank, and actually read the full text (not just abstracts) when it can get a PDF.
- Split each paper into sections and extract methodology, results, and limitations separately, instead of asking one prompt to summarize the whole thing.
- Look for research gaps across the papers it analyzed, with a couple of verification passes so it doesn't invent citations or quietly drop a paper that actually contradicted the others.
- Search GitHub, Hugging Face, Kaggle, GitLab and Bitbucket for existing implementations and score how similar they are to the idea, so a "technical plan" isn't proposing something that already exists on GitHub with 4k stars.
- Generate a technical plan (stack, architecture, milestones, risks) and a teaching plan (objectives, modules tied to the gaps it found).
- Build an actual course from the teaching plan — real `.pptx` files, one per lesson, with title/objective/content/code/quiz slides and a layout engine that splits content across slides instead of letting text overflow.
- Generate lab exercises with real starter and solution code, run it through Python's `ast` module to catch syntax errors and undefined names before the student ever sees it, and let the model repair its own code up to twice if validation fails. Everything gets packaged into student and teacher Jupyter notebooks.
- Propose experiment protocols tied to the gaps, and — when a student submits results — grade them against the literature baselines using plain Python arithmetic, not an LLM's guess at a percentage difference.

Everything above is grounded in whatever was actually retrieved and analyzed in that conversation; nothing pedagogical gets generated out of thin air without a literature/gap basis behind it.

## Why it's built this way

A few decisions shaped most of the architecture, and they're worth explaining up front because otherwise some of the code looks over-engineered for no reason.

**The agent doesn't get to decide when to call tools on its own.** Early versions used a normal ReAct loop, and the model would immediately fire off a full technical-plan pipeline the moment someone said "I'm thinking about doing something with transformers on mobile." That's expensive and annoying. So there's a hard classification step (`classify_node`) in front of the LangGraph agent that decides whether the turn is small talk, an idea introduction, an actual action request, or an info question — and only the last two can reach the tool-calling agent at all. It's a blunt fix, but it works better than prompting the agent to "please don't be eager."

**As little as possible is left to the LLM to get right on its own.** Citation checking in gap detection is a post-hoc whitelist filter against the real paper titles, not a prompt instruction. Benchmark scoring deltas are computed with actual Python subtraction. Generated code is checked with `ast.parse`, not trusted because the model said "this should work." This was mostly a reaction to early hallucination problems — models cited papers that were dropped from the context, or claimed accuracy numbers that weren't in any source. Moving the verification into code instead of the prompt fixed most of it.

**No generated code runs on the server, ever.** Labs and experiments are meant for the student to run in their own environment. The server's job is to statically validate the code (syntax, undefined variables, duplicate definitions, whether it matches what the lesson plan promised) and repair it if something's broken — not execute it.

**Cloud and local models are mixed on purpose.** Groq and Gemini are fast and free-tier friendly but rate-limited; Ollama running locally has no quota but needs a decent GPU/CPU. The router picks a model per task category (analytical / planning / content generation / general chat), and if the chosen one fails or the local one runs out of memory, it falls back automatically — Groq → Gemini → a safe direct call — and tells the user in the response that a fallback happened, rather than just quietly using a worse model.

## Architecture, roughly

```
React frontend (Chakra UI)
       │  fetch + JWT
       ▼
FastAPI backend (main.py)
       │
       ├── security/prompt_injection_guard.py   — scans everything untrusted before it touches an LLM
       ├── auth/                                 — fastapi-users on PostgreSQL
       ├── ingestion/                             — PDF → chunks → ChromaDB
       │
       ▼
LangGraph orchestrator (agents/orchestrator.py)
   classify_node ──► agent_node ──► ToolNode(12 tools) ──► back to agent_node ──► END
       │
       ▼
agents/tools.py (domain logic, ~4.7k lines)
       │
       ▼
agents/llm_router.py ──► Groq / Gemini / Ollama, with fallback
```

State for each conversation (papers found, gaps, plans, course content, lab code, evaluations — basically everything) lives in a typed `OrchestratorState` dict and gets checkpointed to PostgreSQL after every turn via LangGraph's `PostgresSaver`. That's what lets a later message in the same conversation say "make a course from that" without re-running the whole search pipeline — it just reuses what's already in state.

## Repo layout

```
ConsiliAI/
├── backend/
│   ├── main.py                        # FastAPI app, all REST endpoints
│   ├── agents/
│   │   ├── orchestrator.py            # LangGraph state machine
│   │   ├── tools.py                   # search, gaps, plans, course, labs, benchmarks
│   │   └── llm_router.py              # provider/task routing + fallback
│   ├── export/
│   │   ├── export_project.py          # zips everything into a project archive
│   │   └── course_pptx_exporter.py    # builds the actual .pptx files
│   ├── auth/                          # fastapi-users + PostgreSQL models
│   ├── ingestion/                     # PDF extraction, chunking, ChromaDB
│   └── security/
│       └── prompt_injection_guard.py
├── chroma_data/                       # persisted ChromaDB store
├── user_uploads/                      # uploaded PDFs
└── frontend/
    └── src/
        ├── pages/Chat.jsx             # main chat interface
        ├── components/Sidebar.jsx     # right-hand artifact ledger
        ├── components/LeftSidebar.jsx # conversations, settings, model config
        ├── components/EvaluationDashboard.jsx
        └── api.js                    # fetch wrapper, JWT, AbortController
```

## The LangGraph state

```python
class OrchestratorState(TypedDict):
    messages: Annotated[list, add_messages]
    idea: Optional[str]
    uploaded_documents: Optional[List[str]]
    papers_with_analysis: Optional[List[Dict]]
    gaps: Optional[List[Dict]]
    similar_projects_raw: Optional[List[Dict]]
    similar_projects_scored: Optional[List]
    novelty_analysis: Optional[str]
    technical_plan: Optional[Dict]
    teaching_plan: Optional[Dict]
    course: Optional[Dict]
    course_export_path: Optional[str]
    lab_exercises: Optional[List[Dict]]
    experiments: Optional[Dict]
    evaluations: Optional[List[Dict]]
    _route: Optional[str]
```

Twelve tools are bound to the agent: `answer_from_literature`, `find_research_gaps`, `create_technical_plan`, `create_teaching_plan`, `create_course`, `create_lab_exercises`, `create_experiments`, `evaluate_student_submission`, `check_topic_relevance`, `explore_adjacent_fields`, `summarize_progress`, `search_personal_documents`.

There's also a stop button — clicking it fires `POST /chat/{id}/stop`, which sets a `threading.Event` and cancels the running asyncio task. Anything mid-loop checks that flag and bails out cleanly, returning HTTP 499 with whatever partial state exists.

## Model routing

| Task | What it covers | Cloud default | Local default |
|---|---|---|---|
| `analytical` | paper analysis, gap detection | Groq `qwen/qwen3.6-27b` | Ollama `llama3.2:3b` |
| `planning` | technical/teaching plans | Gemini `gemini-2.5-flash-lite` | Ollama `llama3.2:3b` |
| `content_generation` | slides, experiments, lab code | Gemini / Groq | Ollama `qwen2.5-coder:7b` |
| `general_chat` | intent classification, chat | Groq `qwen/qwen3.6-27b` | Ollama `llama3.2:3b` |

Users can pick cloud vs. local globally, or override the model per task category from a live catalog (`/models/available`, which actually pings Ollama/Groq/Gemini rather than hardcoding a list). Request-scoped settings go through Python `ContextVar`s so concurrent users don't step on each other's provider preferences.

## Security

Anything that isn't the user typing directly into the system prompt — chat messages, uploaded PDFs, retrieved paper text, student submissions — goes through `prompt_injection_guard.py` first. It's a weighted regex scanner (critical patterns like "ignore all previous instructions" score 0.85–0.95, softer stuff like role-hijacking phrases score lower), with a discount applied when the text also looks like legitimate technical writing, so a paper discussing "instruction tuning" doesn't get flagged as an attack. Anything that clears a high confidence threshold with no legitimate technical content gets blocked outright (HTTP 400); anything lower gets sanitized and wrapped in an explicit `<document_content>` boundary telling the model to treat it as passive data, not instructions.

## Storage

- **PostgreSQL** — user accounts, conversation metadata, and LangGraph checkpoints.
- **ChromaDB** — three collections: `user_docs` (personal PDF RAG), `search_cache` (semantic cache for paper searches, cosine ≥ 0.95 counts as a hit), `analysis_cache` (SHA-256 hash of a section's text → its extracted analysis, so the same paper is never re-analyzed twice).
- **Disk** — uploaded PDFs, generated `.pptx` and `.ipynb` files.

Deleting a conversation removes its checkpoints and embeddings along with it. There's also a full account wipe (`DELETE /user/data`) that removes everything — conversations, checkpoints, embeddings, files — in one irreversible action.

## Exporting a project

`GET /projects/{conversation_id}/download` zips up everything generated in a conversation into one archive:

```
project_archive.zip
└── <project_slug>/
    ├── courses/        .pptx decks + syllabus
    ├── notebooks/       student/teacher .ipynb per lesson
    ├── labs/            exercise guide + schemas
    ├── plans/           technical & teaching plans, gaps, novelty analysis
    ├── experiments/     protocols
    ├── evaluations/     benchmark comparisons
    ├── documents/       uploaded PDFs + literature summary
    ├── code/            standalone starter/solution .py files
    └── other/           chat transcript
```

## A few of the API endpoints

| Method | Endpoint | What it does |
|---|---|---|
| `POST` | `/chat/{conversation_id}` | send a message to the orchestrator |
| `POST` | `/chat/{conversation_id}/stop` | cancel an in-flight generation |
| `POST` | `/upload` | upload + index a PDF |
| `POST` | `/evaluate_benchmark` | grade a student submission against literature baselines |
| `GET` | `/projects/{id}/download` | download the full project archive |
| `GET` | `/models/available` | live model catalog from Ollama/Groq/Gemini |
| `GET`/`PATCH` | `/settings` | provider + per-task model preferences |
| `DELETE` | `/user/data` | wipe everything |

The full list (registration, conversations CRUD, direct pipeline test endpoints like `/search`, `/gaps`, `/technical_plan`, etc.) is in `PROJECT_MASTER_CONTEXT.md`.

## Stack

FastAPI, LangGraph, LangChain Core, PostgreSQL (via SQLAlchemy/asyncpg + `fastapi-users` for auth), ChromaDB, `sentence-transformers/all-MiniLM-L6-v2` for embeddings, PyMuPDF for PDF text extraction, `python-pptx` for slide export, `nbformat` for notebooks, Python's built-in `ast` module for code validation. Groq and Google Gemini for cloud inference, Ollama for local. Frontend is React 18 + Vite + Chakra UI, with React Markdown for rendering assistant replies.

## Running it locally

**Prerequisites**
- Python 3.10+
- Node.js 18+ (for the Vite/React frontend)
- PostgreSQL running locally (or reachable via connection string)
- Optional: [Ollama](https://ollama.com/) installed locally if you want to run models offline instead of relying on Groq/Gemini
- API keys for whichever cloud providers you want (Groq, Google Gemini). arXiv/Semantic Scholar/OpenAlex/GitHub don't require keys for basic use, though GitHub's rate limits are much better with a token.

**1. Clone the repo**
```bash
git clone https://github.com/mariammouh/ConsiliAI.git
cd ConsiliAI
```

**2. Backend setup**
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd backend
```

Create a `.env` file in `backend/` with at least:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/consiliai
DATABASE_URL_SYNC=postgresql://user:password@localhost:5432/consiliai
AUTH_SECRET=some-long-random-string

GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
GITHUB_TOKEN=your_github_token        # optional, raises GitHub search rate limits
KAGGLE_USERNAME=your_kaggle_username  # optional
KAGGLE_KEY=your_kaggle_key            # optional
```
> Adjust variable names to match whatever `backend/.env` / `db.py` actually expects in your copy of the code — the ones above reflect what's referenced across the project docs, but double-check against the source before relying on them.

Create the PostgreSQL database, then run the app (FastAPI will create its own tables on startup if the models are set up with `create_all`, otherwise run whatever migration step the project uses):
```bash
uvicorn main:app --reload --port 8000
```

If you're planning to use local models, pull them in Ollama first:
```bash
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:7b
```

**3. Frontend setup**
```bash
cd ../frontend
npm install
npm run dev
```
This starts the Vite dev server (default `http://localhost:5173`), talking to the backend at `http://localhost:8000` — check `frontend/src/api.js` if you need to point it somewhere else.

**4. Using it**
- Open the frontend, register an account, log in.
- Start a new conversation and describe a project idea.
- Ask for what you want directly — "find research gaps for this", "build a technical plan", "generate a course", "create lab exercises" — the intent classifier only calls the heavier pipelines on an explicit request, not on a casual idea description.
- Generated artifacts (literature, gaps, plans, course, labs, experiments, evaluations) show up as cards in the right-hand sidebar; click one to see the full content and download links.
- Settings (top of the left sidebar) let you switch between cloud and local inference, and assign a specific model per task category if you don't want the defaults.
- Once you're done, `Export data` in the left sidebar gets you the full project ZIP.

## Where it stands

Everything described above is implemented and working: literature search, gap detection, similar-project/novelty analysis, technical and teaching plans, course + PPTX generation, AST-validated labs with notebook export, experiment generation, benchmark evaluation, the LangGraph orchestrator with cancellation, multi-conversation support, dynamic model routing with fallback, prompt injection defense, project export, and full data deletion. `PROJECT_MASTER_CONTEXT.md` has a section-by-section status matrix if you want the detail.

Known limitations / possible next steps: it's scoped to computational/technical fields on purpose (the code validator and benchmark math don't generalize to, say, wet-lab biology or humanities research). There's no support yet for bringing your own API keys instead of the shared free-tier quotas, and no way to edit an already-generated plan incrementally without regenerating it.