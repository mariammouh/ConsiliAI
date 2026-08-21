# ConsiliAI — Master Project Context Document

*This document is the single source of truth for the project. It captures the full history, rationale, architecture, implementation details, problems solved, and remaining work, so that any engineer or AI assistant can pick up development without prior context. Where information is inferred rather than explicitly confirmed, it is marked **[INFERRED]**. Where information was not discussed and is genuinely unknown, it is marked **[UNKNOWN]**.*

**Project name:** ConsiliAI *[INFERRED from repository path `M:\stage sys\ConsiliAI`]*
**Context:** Final-year internship project (~2 months), company **[INFERRED: "3D SMART FACTORY"]**, supervisors named in presentation materials as Thierry BERTIN, Omar KELLA, Ibtihal KHALIL *[as stated by the student]*.
**Document generation date context:** Compiled from the full development conversation history, covering initial concept through a working Course Generator with hierarchical lesson content and per-lesson PowerPoint export.

---

## 1. Project Overview

### 1.1 Objective

Build an **agentic AI assistant** that automates the preparatory work of a technical (AI/ML/Software) research or academic project, and — following a mid-project pivot driven by supervisor feedback — **transfers that research into ready-to-teach educational content**. The system is described internally as a **"Research-to-Education Transfer Assistant."**

### 1.2 Problems the project solves

- Researchers, students, and instructors spend large amounts of time manually: searching literature, judging novelty against existing work, finding comparable implementations, and turning findings into teaching material.
- No existing tool (commercial or academic) combines multi-source literature search, novelty/gap analysis, technical project planning, **and** pedagogical content generation in one conversational system (this claim is the core positioning argument from the project's own SOTA study — see §1.5).
- Specifically for the education angle: transferring cutting-edge research into course material is slow and manual; the project supervisor explicitly requested this as a way to build a "real-time SOTA knowledge base" for teaching.

### 1.3 Target users

- Primary (as scoped for the 2-month prototype): students and researchers in AI/ML/Software Engineering fields, and university instructors who want to convert research literature into course material.
- Explicitly **out of scope** for the prototype: non-technical/non-CS domains (humanities, biology, etc.) — the Similar-Project and Lab/Experiment agents are structurally tied to code/repo ecosystems (GitHub, Hugging Face, Kaggle) that don't generalize to other fields. This was a deliberate, discussed scoping decision, not an oversight (see §7, "Scope: technical domain only").

### 1.4 High-level architecture (current state)

A FastAPI backend, with all agent logic centralized in `agents/tools.py` and all HTTP endpoints in `main.py`. Each "agent" is a Python function (not a separate microservice) that calls out to Groq or Gemini for LLM reasoning, and to various free external APIs for data retrieval. State/caching is handled via multiple ChromaDB collections. The backend has now progressed beyond the original research-only flow: it includes paper search/analysis, gap detection, technical plan generation, teaching-plan generation, course generation with PowerPoint export, relevance-checking for niche ideas, lab-exercise generation, and benchmark-evaluation endpoints. A frontend is still not built (deliberately deferred — see §9). The conversational orchestrator remains a stubbed/unfinished design element rather than a working system (still deliberately deferred).

### 1.5 Prior positioning work (SOTA study)

Before implementation began, a full state-of-the-art study was conducted and written up (`sota.html`, `report.html`), comparing the project against:
- **Academic systems:** STORM, PaperQA2, AutoGen, CrewAI, Survey of RAG, SciAgents, ResearchAgent, LitReview, FM-Agent (Baidu), DiscoveryBench, SciCode/BLADE/DA-Code, CHIME.
- **Commercial tools:** Elicit, Consensus, Scite, ResearchRabbit, ChatPDF/Humata, Perplexity AI, PapersWithCode, SciSpace, Undermind, Afforai.

**Conclusion of that study:** no existing system combines multi-source research + code discovery, practical novelty/similarity analysis, technology recommendation, project milestone planning, and personal knowledge management in one conversational assistant. This positioning was **not invalidated** by the later education pivot — it remains the baseline differentiation argument, with the education layer as an additional, even stronger differentiator per the supervisor's framing.

---

## 2. Project Evolution (Chronological)

### 2.1 Phase 0 — Original concept (pre-internship-review)

Initial scope, as captured in `report.html`: an **Agentic AI Assistant for Scientific Research and Project Development**, focused on AI/ML/Software projects, with three pillars:
1. Personal knowledge base (RAG over user-uploaded PDFs, ChromaDB).
2. Specialized agents as callable tools (research, similar-project, summarization).
3. A single conversational orchestrator/"Project Planner" agent using LangChain tool-calling.

Planned agents at this stage: Agent de Recherche (no LLM, API-only), Agent de Résumé de Littérature (Groq), Agent de Projets Similaires & Nouveauté (Groq), Assistant d'Écriture (Gemini), Planificateur/Conseiller Tech orchestrator (Gemini, LangChain `AgentExecutor`).

Planned stack at this stage: FastAPI + React (Vite) frontend, LangChain orchestration, Gemini 1.5 Flash + Groq Llama 3.1 70B hybrid, `all-MiniLM-L6-v2` embeddings, ChromaDB, arXiv/Semantic Scholar/GitHub/Hugging Face APIs.

Planned build order: Month 1 = ingestion pipeline + Research Agent + Summary/Similar-Project agents. Month 2 = orchestrator, Writing Assistant, testing, polish.

### 2.2 Phase 1 — First progress review and supervisor pivot (Day 10)

At the ~10-day mark, a progress review meeting was held. By this point, the following were **already implemented** (see `project_summary.md`-equivalent status captured mid-conversation):
- Personal Knowledge Base / RAG (PyMuPDF extraction, custom chunker, `all-MiniLM-L6-v2` embeddings, ChromaDB `user_docs` collection, `/ask` endpoint).
- Literature Search Agent, integrating arXiv, Semantic Scholar, and **OpenAlex** (added beyond the original plan), with a semantic cache (exact + cosine-similarity ≥0.95 match) to reduce redundant API calls, plus a hybrid filter pipeline (embedding pre-filter → LLM re-rank via Groq).
- Literature Summarization Agent (Groq).
- Similar Project & Novelty Analysis Agent, expanded beyond the original GitHub/Hugging Face scope to also include **Kaggle** and **GitLab**, with a `diversify_top()` function to avoid single-source domination, and a novelty analysis step (Groq, with Gemini fallback, with a basic-stats fallback if both fail).
- Backend skeleton: FastAPI with `/upload`, `/ask`, `/search`, `/smart_search`, `/similar` endpoints. A `/chat` endpoint existed as a stub pointing at an (unfinished) LangChain orchestrator.

**The pivot:** the supervisor proposed extending the assistant beyond project-planning into **education**: generating course material from papers, MCQs, detecting paper sections (Introduction/Methodology/Results/etc.) and building specialized per-section analysis, and building a real-time SOTA knowledge base for a research group/lab/university. The student agreed this was a stronger direction than project-planning alone, and proposed **keeping** the technical-planning capability while **adding** the educational layer on top of the same infrastructure — not replacing one with the other.

**Updated vision after the pivot:** "Research-to-Education Transfer Assistant," combining:
- Existing: SOTA monitoring, literature summarization, novelty analysis, technical project planning.
- New: Education Agent (course outlines, quizzes, exam questions, PPTX slides via `python-pptx`), specialized paper-section agents (Methodology Agent, Results Agent, etc.), and research-project coordination features (task/reading/experiment/writing progress tracking for supervisor↔student collaboration).

Immediate next steps identified at this point: finish the LangChain orchestrator/`/chat` endpoint, build the first Education Agent, implement automatic paper segmentation + a Methodology Agent proof-of-concept, add PPTX export.

### 2.3 Phase 2 — Extended design/brainstorming (pre-code)

A long design conversation followed, refining the education pivot before any new code was written. Key outcomes:

- **Differentiation strategy discussion:** rather than building a generic "MCQ + slides from papers" tool (identical to what other interns on the same brief were likely building), the recommendation was to build the education layer **on top of** the project's unique existing infrastructure — specifically, ground courses in the *novelty/gap-analysis* agent's output (teach from unsolved problems, not just known facts) and in the *similar-project* agent's real repos (tie lessons to actual working code, not abstract exercises). This "closed loop" framing (gap detection → teaching → student experiments → benchmark evaluation → feedback into gap detection) became the project's core narrative.
- **Lab/exercise generation idea:** proposed a "Lab Generator Agent" that pairs a paper's claim with a real matched implementation (via the Similar-Project agent) to produce runnable exercises with reference solutions and difficulty tiers.
- **Experiment-replication scoping decision (important):** initially discussed as "reproduce a paper's result," which was flagged as a major engineering risk (sandboxing, dependency management, timeouts — a fundamentally different risk category from LLM-prompting risk). The user later **clarified** that the agent should only **suggest** experiments (dataset, metric, baseline, tool/dataset variations) for a teacher to assign to students — the *students*, not the system, actually run the code. This eliminated the sandboxing/execution risk entirely and kept the agent in the same "structured LLM output" pattern as everything else. This is documented explicitly as a corrected scope: **no code execution happens anywhere in this system.**
- **Section-agent consolidation decision:** the supervisor's ask for "one agent per paper section" (Methodology Agent, Results Agent, etc.) was **not implemented literally**. Instead, a single **parameterized Section-Analysis Agent** was built, taking `(section_text, section_type)` and using a schema lookup table (`SECTION_SCHEMAS`) to determine which fields to extract per section type. Rationale: the underlying task shape is identical across section types (extract structured fields from text); five separate agents would mean five prompts/schemas/failure points to maintain instead of one. This was explicitly framed as a *better* engineering answer to the supervisor's request, not a shortcut around it.
- **Coordination/tracking feature scoping:** the "supervisor↔student communication zone" idea was explicitly scoped down from a full LMS-like system (which was flagged as scope creep — real-time chat, auth/roles, generic file submission, notifications, grading rubrics were all explicitly cut) to a **thin, AI-connected slice**: task assignment tied to auto-generated content, and progress tracking as a side-effect of agent-interaction logging, not a new subsystem.
- **Frontend framework decision (early, later revisited):** React + Vite was the original plan. When time pressure increased, Streamlit/Gradio were considered as faster alternatives, with the tradeoff being visual distinctiveness ("looks like every other AI demo"). Final decision (see §2.6): **defer the decision entirely** until the backend API surface stabilizes.
- **Build-order and timeline reality check:** given ~5 weeks remaining and a report still to write, the student's plan of "6 new agents ÷ 5 weeks = easy" was corrected — the real cost centers were flagged as the Course Generator (structural/pedagogical iteration) and, before its scope was corrected, the (since-eliminated) experiment-execution risk. A per-week build order was proposed: Week 1 = Section Splitter + Section-Analysis; Week 2 = Gap Detection, Technical Plan, Teaching Plan; Week 3 = Course Generator + start Lab/Experiment agent; Week 4 = finish Lab agent, Benchmark Eval, orchestrator wiring; Week 5 = minimal frontend, integration testing, report buffer.

### 2.4 Phase 3 — Implementation begins: Section Splitter + Section-Analysis Agent

First code written. Iterative debugging process (see §7 for full problem log):
1. Heuristic-first, LLM-fallback section splitter built (`heuristic_split_sections`, `llm_split_sections`, `split_paper_sections`).
2. First heuristic version used `re.fullmatch` against a small `SECTION_HEADER_PATTERNS` dict — far too strict, only caught a fraction of real section headers (e.g. "PROPOSED METHODOLOGY" didn't match `proposed\s+(method|approach|model)`).
3. Rewritten to use **keyword-containment matching** (`match_section_keyword`) against short, non-sentence-shaped candidate lines (`is_likely_header` guard: not too long, doesn't end in a period, ≤8 words), against an expanded `SECTION_KEYWORDS` dict. This was the version that stuck.
4. Section-merge logic bug found and fixed: originally kept only the *longest* span per section name when the same section label appeared multiple times (e.g. multiple "Results of experiment N" subheadings); this **discarded** most of the content. Fixed to **concatenate** all spans under the same label instead of overwriting.
5. `analyze_section` built as the single parameterized agent, with a `SECTION_SCHEMAS` lookup table (methodology → algorithms/hyperparameters/implementation_notes/potential_biases; results → metrics/baselines_compared/key_improvements/reported_numbers; introduction → problem_statement/motivation/contributions; related_work → prior_approaches/positioning; discussion/conclusion → limitations/future_work[/summary]; abstract → summary).
6. Chunking added (`chunk_text`) to keep any single LLM call under a safe token budget for Groq's free-tier limits, with per-chunk analysis + merge (`merge_section_analyses`) for oversized sections.

### 2.5 Phase 4 — Multi-source full-text retrieval

- `/analyze_paper` endpoint built for direct PDF upload testing (PyMuPDF extraction).
- `/test_search_and_analyze` temporary endpoint built to validate "search → fetch full text → split → analyze" end to end.
- **Full-text retrieval gap identified:** `search_papers` only returned metadata (title/authors/abstract/url), not full text. Fixed by adding a `pdf_url` field to every source's returned dict: arXiv (`result.pdf_url`, always available), Semantic Scholar (via the previously-unused `openAccessPdf` API field), OpenAlex (via `best_oa_location.pdf_url` / `open_access.oa_url`). A single `fetch_full_text(paper)` function was built to attempt PDF download + PyMuPDF extraction, with graceful fallback to abstract-only analysis when no PDF is available. This function became shared infrastructure reused by every downstream agent.

### 2.6 Phase 5 — Gap Detection Agent (first version, then hardened significantly)

- `detect_gaps(user_idea, papers_with_analysis)` built: pulls only gap-relevant fields per paper (`_extract_gap_relevant_text` — contributions, problem statement, positioning vs. prior work, limitations, future work, key results), concatenates across papers, chunks if needed, prompts Groq for a structured `{"gaps": [...]}` list, with a `_consolidate_gaps` final pass to merge near-duplicates across chunks.
- This agent went through **three distinct, verified bug-fix cycles** for citation integrity — documented in full in §7.3–§7.5, since it's the most heavily debugged component of the system.

### 2.7 Phase 6 — Technical Plan Agent

- `generate_technical_plan(user_idea, gaps, similar_projects)` built: takes gaps + scored similar projects, produces `{recommended_stack, architecture_overview, milestones, deliverables, risks}`.
- Went through **multiple grounding-instruction iterations** after real hallucination-shaped bugs were found and — critically — after most of them turned out to be *false alarms* on manual verification (see §7.2). One **real** bug was found and fixed: irrelevant GitLab "sandbox"/test-account repos being cited as if genuinely similar (the "coin-counterfeit-detection" stress test). Fixed with a **similarity-threshold relevance gate** before any similar-project text reaches the prompt, with an explicit "no sufficiently similar projects found, don't invent a stack" fallback instruction.
- **Novelty-awareness added:** `analyze_novelty` (which already existed from Phase 1/`/similar`) was wired into the Technical Plan prompt, so the plan doesn't just report novelty as a side statistic but actively steers its `differentiation_strategy` — when overlap with existing work is high, the plan is instructed to pivot the architecture/milestones toward the identified gaps rather than proposing a plan that just re-implements existing similar projects.
- Verified across 5 domains (plant classification, fake news detection, credit card fraud, robotic grasping, sentiment analysis for low-resource languages) plus one deliberate niche stress-test (counterfeit coin detection via acoustics) that specifically surfaced the GitLab-noise bug.

### 2.8 Phase 7 — Teaching Plan Agent

- `generate_teaching_plan(user_idea, gaps, papers_with_analysis)` built: parallel sibling to Technical Plan Agent (both consume the same gaps + papers, independently), producing `{course_title, target_audience, learning_objectives, prerequisites, modules[], frontier_topics[], suggested_duration}`.
- Modules are grounded in specific analyzed papers (`based_on_papers`); `frontier_topics` are explicitly derived from `gaps`, giving the course a "foundational knowledge → open research questions" arc.
- **Refinement added mid-testing:** modules were originally too architecture-heavy even at "beginner" difficulty. Fixed with an explicit instruction: beginner modules must stay in accessible problem-framing language, saving specific architectural/technique detail for intermediate/advanced modules. Verified via direct before/after comparison on the same input.
- **Second refinement:** each module gained explicit `problem_addressed` / `solution_approach` fields (in addition to the free-text `description`), so downstream content generation (Course Generator) has a structured hook rather than having to re-derive "what problem does this module solve" from prose. This was an explicit division-of-labor decision: Teaching Plan Agent owns the *skeleton* (what topics, what order, what depth); Course Generator owns the *pedagogical content* (how each topic is actually taught). Problem/solution framing was deliberately kept concise at the planning level — full pedagogical explanation happens one stage later.
- Verified across 5 domains with consistently correct, non-generic module structuring.

### 2.9 Phase 8 — Gap Detection citation-integrity hardening (major debugging arc)

This was the single most intensive debugging sequence in the project. Full details in §7.3–§7.5. Summary of the three sequential, verified fixes:
1. **Cross-paper chunk-boundary bug:** `detect_gaps` originally concatenated all papers' text *then* chunked the combined blob — chunk boundaries could land mid-paper, and only the first chunk of a long paper retained its `"Paper: {title}"` header text, causing the LLM to invent plausible-sounding "paper titles" from stray table captions/result sentences within headerless chunks (e.g., "MERMAID model performance across various datasets and classes" mistaken for a paper title). **Fix:** chunk each paper individually (`chunk_text_with_source`), tag every chunk with its true source as structured metadata (not embedded prose), and **override** (not just prompt-request) `papers_involved` with the known-correct source for every extracted gap.
2. **Consolidation silently dropping papers:** even with per-chunk sourcing correct, the separate `_consolidate_gaps` LLM call (which merges near-duplicate gaps across chunks) could still silently omit a paper's entire contribution during merging, with no visibility. **Fix:** track `all_input_papers` vs. `covered_papers` in code after consolidation; if any paper vanished, run a targeted `_verify_dropped_papers` LLM check per missing paper (judges whether its content is genuinely already covered by an existing gap, or was wrongly dropped) and repair by re-appending its best raw gap only if genuinely missing — not a blind force-append, which the user correctly identified as a real risk (could re-add content the LLM had legitimately, correctly merged away).
3. **Consolidation inventing paper names:** even after fix #2, the *union* step in consolidation (combining `papers_involved` lists when merging gaps) could itself hallucinate a plausible-sounding paper name (again, "MERMAID" — this time invented fresh during the merge step rather than inherited from extraction). **Fix:** post-hoc filter every `papers_involved` entry in the consolidated output against the *known-true* set of input paper titles; strip anything not in that set, with a logged warning.

A code bug was also found and fixed during this arc: the `covered_papers` set was declared but never updated inside its own loop (`.update()` call missing), meaning the missing-papers check always saw an empty set and misreported everything as "dropped" regardless of the actual (correct) output.

**Final verified state (confirmed across multiple re-runs on fake-news-detection and robotic-grasping domains):** all analyzed papers' contributions are guaranteed to survive into the final gap list; no invented paper names can appear; the system is robust by *code-enforced verification*, not by trusting LLM instruction-following alone. This is treated as the project's key engineering lesson (see §11).

### 2.10 Phase 9 — Query relevance / niche-topic handling

- **Bug found:** testing a deliberately niche cross-domain idea ("classifying handwriting of a specific rare medical condition") surfaced a different, more subtle failure: when literally no relevant papers exist, `filter_papers_hybrid` still returns *something* (it never refuses), and the downstream agents can construct a coherent-sounding but substantively **fabricated conceptual bridge** between unrelated fields (in this case, gravitational-wave/dark-matter detection papers reframed as relevant to handwriting-based disease diagnosis). This was flagged as more dangerous than an obviously-wrong fact, because it reads as plausible.
- **Feature designed in response (partially built, deliberately incomplete/deferred):** a `broaden_idea` agent that, only on explicit user confirmation after a `/check_relevance` step reports "no direct match," decomposes the idea into core concepts and adjacent fields, generates alternative search queries, and **tags** every resulting paper as `match_type: "direct"` or `"analogous"` with the query that surfaced it — so downstream agents can treat analogical connections as explicitly speculative rather than presenting them with the same confidence as direct matches.
- Tested once on the handwriting/medical example: worked correctly — found genuinely adjacent handwriting-recognition literature, correctly tagged it as analogous, and the `honest_assessment` field correctly characterized the idea as a genuine but under-explored niche rather than overclaiming coverage. One limitation noted and left unresolved: query coverage across *all* core concepts in a multi-concept idea isn't guaranteed (a query correctly targeting "disease detection" still returned generally-relevant-but-not-medically-specific results, because that literature is itself thin — assessed as a fundamental data-sparsity limitation, not a pipeline bug).
- **Status: intentionally left as a partial feature.** Full integration (wiring `/check_relevance` → `/explore_niche` → downstream agents) was explicitly deferred in favor of finishing the core agent pipeline first.

### 2.11 Phase 10 — Reliability/infrastructure hardening (cross-cutting, ongoing throughout)

Not a single phase but a recurring thread throughout development — see §7.1 for the full problem log. Summary of what exists today:
- `_groq_invoke_safe`: retries Groq on rate-limit errors with backoff, falls back to Gemini after exhausting retries.
- `TokenBudget` class: tracks estimated token usage per rolling 60-second window, sleeps proactively before exceeding Groq's TPM limit (partially implemented; character-based token estimation, not exact).
- `analysis_cache_collection` (ChromaDB): caches `analyze_section` output keyed by a SHA-256 hash of `(section_type + section_text)`, making repeated test runs on the same paper free.
- Deliberate task-routing decision: cheap/simple tasks (paper relevance filtering in `filter_papers_hybrid`, `filter_relevant_papers`) route to Gemini directly rather than through the Groq-first fallback chain, reserving Groq specifically for tasks needing stronger reasoning (section analysis, gap synthesis, plan/course generation). This was an explicit quota-conservation decision, not just a reliability one.
- A third-tier local Ollama fallback (`llama3.1:8b`) was **planned and stubbed in code** (commented out) but never activated — noted as a known future step if Groq+Gemini together prove insufficient.

### 2.12 Phase 11 — Course Generator (built in two iterations)

**Iteration 1 (flat, module-level):** `generate_module_content` expanded each teaching-plan module into a single `{overview, key_concepts, explanation, worked_example, check_understanding, summary}` block; `generate_course` looped over all modules; `export_course_to_pptx` (deterministic, `python-pptx`, no LLM involvement) rendered one slide deck combining every module.
- Bug found and fixed: `/tmp/...` hardcoded output path (Unix-only) crashed on the Windows development machine; fixed with `tempfile.gettempdir()` + `os.makedirs(..., exist_ok=True)`.
- Bug found and fixed: a rename of the loop variable (`module` → `lesson`) during the "carry problem/solution forward" edit left a stale reference inside `export_course_to_pptx`, which would have crashed on the next run; caught before it shipped.
- Cross-module repetition problem identified: each module was generated independently with no awareness of prior modules, causing near-verbatim re-explanation of shared concepts (e.g., HetTransformer's architecture explained fully in three separate modules). First fix attempt (passing `already_covered` as a flat list of `key_concepts` labels) had limited effect, because labels were too generic to signal *what* was already explained. Second fix (passing full per-module `summary` text as `already_covered`, with an explicit "reference briefly, focus on what's new" instruction) produced a real, verified improvement (explicit "As covered in [module]..." cross-references appeared correctly) but did not eliminate all redundancy — accepted as reasonable pedagogical reinforcement rather than pursued further, matching the project's general "diminishing returns" stopping heuristic.

**Iteration 2 (hierarchical restructure, explicitly requested by the user):** rebuilt around a four-level hierarchy — **plan → module → lesson(s) → sections** — instead of one flat explanation per module:
- `generate_lesson_for_module(module, papers_with_analysis, already_covered, lesson_index, total_lessons)`: produces one lesson per call, with one `sections` entry **per topic/objective** in the module (not a single merged paragraph), each section containing a substantial (120–200 word target) grounded explanation plus a concrete `example_or_evidence` pulled from the source papers, plus per-section `key_terms`.
- `generate_course` now loops modules → loops `lessons_per_module` (currently defaulted to 1, but the function signature and prompt already thread `lesson_index`/`total_lessons` through, so raising this to support multiple lessons per module requires no structural change — a deliberate scalability decision).
- `covered_summaries` (the anti-repetition mechanism) now accumulates **per lesson**, not per module, so it will continue to work correctly once multi-lesson-per-module generation is enabled.
- `export_course_to_pptx` was updated for the new nested shape (`course.modules[].lessons[].sections[]`), and a **second export function**, `export_course_to_pptx_per_lesson`, was added on user request to produce **one standalone `.pptx` file per lesson** instead of one combined deck — with a filename-sanitization helper (initially truncated mid-word at a hard 60-character cut; flagged for a minor cosmetic fix to truncate on a word boundary instead, not yet applied as of the last conversation turn).
- **Verified end-to-end** on the fake-news-detection domain: 4 modules → 4 lessons → 4 separate `.pptx` files, each with correct grounding (including a legitimate in-context "MERMAID" reference, correctly distinguished from the earlier fabricated-paper-name bug class), correct cross-lesson referencing ("Building on the introduction to fake news detection earlier in this course..."), and substantive per-topic depth matching the explicit "expand, don't summarize" requirement.

**Progress beyond course generation:** the codebase now also includes a working prototype for the follow-on lab and evaluation layer. `generate_lab_exercise`, `generate_experiment_set`, and `generate_benchmark_evaluation` are implemented in `agents/tools.py`, and the corresponding FastAPI routes in `main.py` (`/generate_lab`, `/generate_experiments`, `/evaluate_benchmark`) are active. This is still a prototype layer rather than a final orchestrated workflow, but it is materially more complete than the earlier planning documents suggested.

### 2.13 Deferred decisions (explicitly discussed, deliberately not yet built)

These were all discussed in detail and deliberately postponed, with stated reasoning:

- **`modify_plan` agent** (edit an existing technical/teaching plan based on a user request, e.g. "add a module on X" or "incorporate this uploaded PDF"): scoped conceptually (an "edit, don't regenerate" design — feed the existing plan as ground truth + the user's request, instruct the model to preserve all unaffected fields verbatim, override `papers_involved`-style fields with ground truth rather than trusting free-text). **Not implemented.** Explicitly reclassified as something the future **orchestrator** should own generically (one "modify X based on a follow-up request" capability reusable across plans/courses/labs) rather than building separate one-off modify-agents per artifact type.
- **PDF-upload-triggered plan modification:** recognized as structurally equivalent to re-running the full search/analyze/gap pipeline with one injected extra source, not a lightweight edit — folded into the same "defer to orchestrator" decision.
- **Tracking/progress database** ("shadow database" in earlier planning docs): explicitly deferred until Course Generator, Lab/Experiment Agent, and Benchmark Evaluation Agent all exist, on the reasoning that the storage schema can't be well-designed against only 2 of 6+ eventual artifact types without high risk of rework. A minimal, deliberately generic ChromaDB-based key-value design (`save_project_state(idea, key, data)` / `get_project_state`) was sketched as a *cheap-to-add-later* option but explicitly **not implemented**, at the user's request, in favor of finishing all agents first.
- **Frontend:** deferred in full. React + Vite (original plan) vs. Streamlit/Gradio (faster, but perceived as "generic AI demo" risk) vs. React + free template (middle ground: faster than custom React, avoids the generic-look risk, costs ~1–2 extra days) were all discussed as live options. **Decision: postpone the choice entirely** until the backend API surface stabilizes (post Lab/Eval/orchestrator), since building against a still-changing API was assessed as guaranteed rework, mirroring the same reasoning applied to the tracking database.
- **Ollama local third-tier LLM fallback:** stubbed in code, not activated.

---

## 3. Requirements

### 3.1 Functional requirements (implemented + planned)

**Implemented:**
- Multi-source literature search with semantic caching (arXiv, Semantic Scholar, OpenAlex).
- Multi-source similar-project/code search (GitHub, Hugging Face, Kaggle, GitLab) with similarity scoring and novelty analysis.
- Personal-document RAG (`/upload`, `/ask`) over user-uploaded PDFs.
- Full-text paper retrieval with graceful abstract-only fallback.
- Automatic paper section splitting (heuristic + LLM-fallback).
- Parameterized, per-section-type structured content extraction.
- Cross-paper research gap detection, with hardened citation integrity.
- Technical project plan generation, grounded and novelty-aware.
- Teaching/course-skeleton plan generation, grounded and gap-driven.
- Full hierarchical course content generation (module → lesson → sections) with PowerPoint export (combined-deck and per-lesson-file modes).
- Niche-idea relevance checks and adjacent-field exploration (`/check_relevance`, `/explore_niche`).
- Lab-exercise generation pipeline plus notebook export (`/generate_lab`).
- Experiment-set generation (`/generate_experiments`).
- Benchmark-evaluation workflow for teacher/student submissions (`/evaluate_benchmark`).

**Planned, not yet built:**
- Conversational orchestrator (`/chat` endpoint; currently only an unfinished stub referencing a nonexistent `agents/orchestrator.py` executor, commented out in `main.py`).
- `modify_plan` / general-purpose "edit an existing artifact" capability.
- Frontend (framework undecided).
- Progress/state tracking persistence layer.
- Full integration of the niche-idea broadening feature into the main pipeline (currently a partially wired, but not fully orchestrated, capability).

### 3.2 Non-functional requirements

- Must run entirely on **free-tier APIs** for the duration of the internship prototype (Groq free tier: 12,000 TPM / 100,000 TPD on `llama-3.3-70b-versatile`; Gemini free tier: reported ~1,500 requests/day on `gemini-3.1-flash-lite`) — this is an explicit, accepted scoping decision for a 2-month academic deliverable, **not** intended as the permanent production architecture (an open question explicitly raised to supervisors in the presentation materials).
- Must degrade gracefully under rate-limiting rather than crash the whole pipeline (Groq→Gemini fallback).
- Generated content must be **citation-grounded**: no technology, paper, or claim may be attributed to a source that does not actually support it. This became the project's dominant non-functional requirement in practice, driving most of the debugging effort (§7).
- Must avoid re-computing expensive LLM work on repeated test runs of the same input (content-hash-based caching).
- Must run on a Windows development environment (surfaced real cross-platform path bugs — see §7.6).

### 3.3 Constraints

- ~2-month total internship duration; the bulk of the work documented here occurred within roughly the final 5–6 weeks of that window, after the education pivot.
- Free-tier LLM rate limits (hard technical constraint, drove significant architecture: chunking, caching, dual-provider routing).
- Single developer.
- No dedicated GPU/compute infrastructure — all reasoning is via hosted API calls, no local model inference is used in production paths (the stubbed Ollama fallback is CPU-only and unused).

### 3.4 Assumptions

- Target users are technical/CS/AI/ML-domain students, researchers, or instructors — general-domain use is out of scope by design.
- Teachers will submit student experiment results as **PDF or plain text only** — screenshot/OCR/vision-model input was explicitly considered and explicitly **rejected** as unnecessary scope for the prototype (teachers can convert screenshots externally if needed).
- A "project idea" is expressible as a short natural-language string sufficient to drive search queries (no structured project-intake form has been designed).

---

## 4. Architecture

### 4.1 Backend components

- **`main.py`** — FastAPI application; all HTTP endpoints. Imports agent functions from `agents/tools.py`. Endpoints as of the current code state include: `/upload`, `/ask`, `/debug_chunks`, `/search`, `/smart_search`, `/history` *(references `sqlite3`/`datetime` without visible imports in the shown code — likely incomplete/dead code, [UNKNOWN] whether functional)*, `/similar`, `/analyze_paper`, `/test_search_and_analyze`, `/gaps`, `/technical_plan`, `/teaching_plan`, `/check_relevance`, `/explore_niche`, `/generate_course`, `/generate_lab`, `/generate_experiments`, `/evaluate_benchmark`, `/download_course/{idea_hash}`, and a commented-out `/chat` stub.
- **`agents/tools.py`** — all agent logic, all LLM client setup, all external-API integration functions, all caching helpers. In the current codebase it also contains the more recent lab-exercise, experiment-set, and benchmark-evaluation pipelines, in addition to the earlier literature/search/course-generation flows. This is the single largest and most central file in the project. **[Note: this file has grown very large; splitting it into per-agent modules is a reasonable future refactor, not yet done.]**
- **`ingestion/`** package — `pdf_processor.py` (PDF upload handling, chunking for RAG), `chroma_client.py` (ChromaDB collection definitions: `cache_collection` for papers/projects semantic cache, `analysis_cache_collection` for section-analysis cache), `embedding_model.py` (`embed()` function, backing model **[INFERRED: `all-MiniLM-L6-v2`, per the originally planned stack; not re-confirmed verbatim during the coding phase]**), `cache.py` (referenced via `get_cached_papers`/`set_cached_papers` imports; **[UNKNOWN exact contents — appears partially superseded by the semantic-cache functions built directly in `tools.py`]**).

### 4.2 Frontend components

None built. **[Deferred — see §2.13.]**

### 4.3 External APIs used

| API | Purpose | Auth | Notes |
|---|---|---|---|
| arXiv (`arxiv` Python package) | Paper search + PDF retrieval | None | Always has a working `pdf_url`; most reliable full-text source |
| Semantic Scholar Graph API | Paper search | Optional API key | `openAccessPdf` field used for full-text link |
| OpenAlex | Paper search | None | `best_oa_location`/`open_access` fields used for full-text link; had a query-formatting bug (trailing space in filter string) found and fixed |
| GitHub REST API (`search/repositories`) | Similar-project search | Optional token | Fetches README via base64-decoded content API |
| Hugging Face Hub (`list_spaces`, `list_models`, `hf_hub_download`) | Similar-project search | None (unauthenticated; rate-limit warning observed in logs) | Covers Spaces and Models |
| Kaggle API (`kaggle.api.kaggle_api_extended.KaggleApi`) | Similar-project search (models, datasets, kernels) | Required (env vars) | Known bug: `ApiDataset` object lacks `.file_count` attribute in the installed library version — dataset listing partially broken, not yet fixed (low priority, models/kernels unaffected) |
| GitLab API (`projects` search) | Similar-project search | None | Known data-quality issue: returns internal GitLab QA "e2e-test"/"sandbox" projects as false-positive results; this specific noise source directly caused the relevance-gate bug found and fixed in Technical Plan Agent (§2.7, §7.2) |
| Bitbucket, PapersWithCode | Written but **disabled** (commented out in `search_similar_projects`) | — | Present in code as unused/legacy functions |

### 4.4 LLM providers

| Provider | Model | Role |
|---|---|---|
| Groq (OpenAI-compatible endpoint via `langchain_openai.ChatOpenAI`) | `llama-3.3-70b-versatile` | Primary "heavy reasoning" model — section analysis, gap detection, plan/course generation |
| Google Gemini (`langchain_google_genai.ChatGoogleGenerativeAI`) | `gemini-3.1-flash-lite` | Secondary/fallback model; also the **primary** model for lightweight tasks (paper relevance filtering) as a deliberate quota-conservation choice |
| Ollama (`langchain_community.chat_models.ChatOllama`, local) | `llama3.1:8b` | **Stubbed, not activated.** Planned third-tier fallback for zero-rate-limit bulk/background work. |

### 4.5 Database / storage

- **ChromaDB**, multiple collections, all local/embedded (no separate DB server described):
  - `cache_collection` — semantic cache for paper search results and similar-project search results, keyed by query text with real embeddings for similarity lookup (threshold 0.95 for "close enough" reuse).
  - `analysis_cache_collection` — exact-match cache for `analyze_section` results, keyed by SHA-256 hash of `(section_type + section_text)`; embeddings are a placeholder (`[[0.0]]` or auto-embedded dummy text) since only exact ID lookup (`.get(ids=[...])`) is used, not similarity search.
  - `user_docs`-equivalent collection for the personal RAG pipeline (`query_chroma`, referenced from `ingestion/chroma_client.py`, exact collection name **[UNKNOWN — not shown verbatim in this conversation]**).
- No relational database is in use. The `/history` endpoint references `sqlite3` and `datetime` without corresponding imports shown — **[likely dead/incomplete code, not confirmed functional]**.

### 4.6 Data flow (core pipeline, used by Gap Detection, Technical Plan, Teaching Plan, and Course Generator alike)

```
user idea (string)
   │
   ▼
search_papers(idea)              ── arXiv + Semantic Scholar + OpenAlex, semantic-cached
   │
   ▼
filter_papers_hybrid(papers,idea)── embedding pre-filter (top-K) → LLM re-rank (Gemini) → final N papers
   │
   ▼
fetch_full_text(paper)           ── per paper: try pdf_url → PyMuPDF extract; else abstract-only fallback
   │
   ▼
split_paper_sections(text)       ── heuristic keyword-header detection; LLM chunk-classification fallback
   │
   ▼
analyze_all_sections(sections)   ── analyze_section() per section, parameterized by SECTION_SCHEMAS, cached by content hash
   │
   ├──► detect_gaps(idea, papers_with_analysis)          ── cross-paper synthesis, per-paper-chunked, source-verified
   │        │
   │        ├──► generate_technical_plan(idea, gaps, similar_projects)   ── + search_similar_projects/compute_similarity_scores/analyze_novelty (separate branch, same idea)
   │        │
   │        └──► generate_teaching_plan(idea, gaps, papers_with_analysis)
   │                  │
   │                  └──► generate_course(teaching_plan, papers_with_analysis)
   │                             │
   │                             └──► export_course_to_pptx[_per_lesson](course)
```

**Important architectural property, explicitly verified and documented:** `/gaps`, `/technical_plan`, and `/teaching_plan` are **independent endpoints sharing the same underlying pipeline**, not a strict sequential chain — `generate_technical_plan` and `generate_teaching_plan` both call `detect_gaps` internally rather than requiring `/gaps` to have been called first. They only share *results* opportunistically, via the section-analysis content-hash cache (so re-running the shared pipeline steps on an already-seen paper costs nothing extra).

**A known duplication-of-work inefficiency, identified but not yet fixed:** because `/gaps`, `/technical_plan`, and `/teaching_plan` each independently re-run the full search→filter→fetch→split→analyze pipeline, calling more than one of them on the same idea in the same session repeats the (cheap, cached) section-analysis work but also repeats the (not cached) `detect_gaps` LLM call itself. A shared helper function `get_papers_with_analysis(idea, max_papers)` was proposed and its code given, intended to be pulled out of the duplicated inline blocks in `main.py` **[proposed but not confirmed as actually applied in the final `main.py` — flagged as a pending refactor]**.

---

## 5. Technology Stack

| Component | Choice | Why chosen | Alternatives discussed |
|---|---|---|---|
| Backend framework | FastAPI | Already the established base from Phase 0; async-friendly, good for wrapping agent function calls as endpoints | None discussed — inherited from original plan |
| LLM orchestration | Direct LangChain chat-model wrappers (`ChatOpenAI` for Groq, `ChatGoogleGenerativeAI` for Gemini), **not** LangChain's agent/tool-calling framework | Simpler, more controllable prompt-and-parse pattern was found to work reliably for structured JSON output; the originally-planned LangChain `AgentExecutor` orchestrator was never finished | LangChain `AgentExecutor` (original plan, abandoned in practice); AutoGen (considered in the original SOTA study for future multi-agent debate, not adopted) |
| Heavy-reasoning LLM | Groq `llama-3.3-70b-versatile` | Free, fast (LPU inference), strong reasoning for a 70B-class open model | Considered upgrading/adding a second Groq key (**rejected** — same account quota, and creating a second account was explicitly rejected as against typical provider ToS and a bad risk for a supervised academic project) |
| Light/fallback LLM | Gemini `gemini-3.1-flash-lite` | Free tier, separate quota bucket from Groq, good enough for structured-extraction-style tasks (not just creative reasoning) | — |
| Planned local fallback | Ollama `llama3.1:8b` | Zero rate limit, useful for bulk/background work | Kaggle-notebook-hosted model + tunnel (ngrok) — **explicitly rejected**: session timeouts, unstable tunnel URLs, more infrastructure risk than benefit for the timeline |
| Embeddings | `all-MiniLM-L6-v2` (sentence-transformers) | Free, local, lightweight, originally justified by MTEB ~56.1 score, 384-dim | — |
| Vector/cache store | ChromaDB | Already established from Phase 0; simple embedded persistence, no separate server needed | — |
| PDF text extraction | PyMuPDF (`fitz`) | Already established from Phase 0; reliable, fast | — |
| PPTX generation | `python-pptx` | Free, deterministic, directly gives teachers an editable, familiar-format deliverable without building any in-app editor | In-app chat-based editing (deferred to future orchestrator work); no in-app WYSIWYG editor was ever seriously considered |
| Frontend | **Undecided** | — | React + Vite (original plan); Streamlit; Gradio (`gr.Blocks()` specifically recommended over `gr.Interface()` for styling control); React + free open-source template (recommended middle ground if visual distinctiveness matters and 1–2 extra days are available) |

---

## 6. Implementation Details, Per Module

### 6.1 Section Splitter

- **Purpose:** convert raw extracted paper text into a `{section_name: section_text}` dict.
- **Inputs:** full paper text (string).
- **Outputs:** `Dict[str, str]`.
- **Key functions:** `heuristic_split_sections`, `is_likely_header`, `match_section_keyword`, `llm_split_sections`, `split_paper_sections` (entry point — tries heuristic first, requires ≥2 of `ESSENTIAL_SECTIONS = {methodology, experimental_setup, results}` to be found before accepting the heuristic result; falls back to LLM chunk-classification otherwise).
- **Key data:** `SECTION_HEADER_PATTERNS` (regex, mostly superseded by keyword matching), `SECTION_KEYWORDS` (the dict actually used for matching), `HEADER_REGEX` (strips numbering/roman-numeral prefixes from candidate header lines).
- **Relationships:** feeds `analyze_all_sections`; used by every downstream agent via `fetch_full_text` → `split_paper_sections` → `analyze_all_sections`.

### 6.2 Section-Analysis Agent

- **Purpose:** extract structured fields from one section of text, with fields depending on section type.
- **Inputs:** `(section_text, section_type)`.
- **Outputs:** `Dict` matching that section type's schema (see `SECTION_SCHEMAS`).
- **Key functions:** `analyze_section` (caches via `get_cached_section_analysis`/`set_cached_section_analysis`; chunks via `chunk_text` if the section is too long, merges via `merge_section_analyses`), `analyze_all_sections` (loops all detected sections, marks empty ones with an explicit `_error` rather than silently omitting them).
- **Relationships:** consumed by `detect_gaps`, `generate_technical_plan` (indirectly, via gaps), `generate_teaching_plan`, `generate_course`.

### 6.3 Gap Detection Agent

- **Purpose:** synthesize cross-paper research gaps relevant to a user's idea.
- **Inputs:** `(user_idea, papers_with_analysis)` where the latter is `List[{"title": str, "analysis": Dict}]`.
- **Outputs:** `{"gaps": [{"gap_description", "supporting_evidence", "papers_involved", "opportunity"}]}`.
- **Key functions:** `_extract_gap_relevant_text` (field-selective extraction per paper), `chunk_text_with_source` (per-paper chunking with structured source tagging), `detect_gaps` (main entry, iterates per-paper chunks, force-sets `papers_involved` from known source), `_consolidate_gaps` (merges/dedupes, code-verifies paper coverage, invented-name filtering, LLM-based `_verify_dropped_papers` repair check).
- **This is the most heavily hardened agent in the codebase** — see §7.3–§7.5 for the full three-stage bug-fix history.

### 6.4 Technical Plan Agent

- **Purpose:** generate a grounded, novelty-aware technical project plan.
- **Inputs:** `(user_idea, gaps, similar_projects_scored)` — the latter as `List[Tuple[float, Dict]]` (score, project).
- **Outputs:** `{"recommended_stack", "architecture_overview", "milestones", "deliverables", "risks"}` (plus `novelty_assessment`/`differentiation_strategy` after the novelty-integration update).
- **Key function:** `generate_technical_plan`. Applies a `similarity_threshold` (0.35) gate before including any similar-project text in the prompt; explicitly instructs the model not to invent a stack when no project clears the threshold.
- **Endpoint:** `/technical_plan` — chains `search_papers` → `filter_papers_hybrid` → `fetch_full_text`/`split_paper_sections`/`analyze_all_sections` (per paper) → `detect_gaps` → `search_similar_projects`/`compute_similarity_scores` → `generate_technical_plan`.

### 6.5 Teaching Plan Agent

- **Purpose:** generate a grounded, gap-driven course skeleton.
- **Inputs:** `(user_idea, gaps, papers_with_analysis)`.
- **Outputs:** `{"course_title", "target_audience", "learning_objectives", "prerequisites", "modules": [{"title","problem_addressed","solution_approach","description","topics","based_on_papers","difficulty"}], "frontier_topics": [{"topic","addresses_gap","rationale"}], "suggested_duration"}`.
- **Key function:** `generate_teaching_plan`. Reuses `_extract_teaching_relevant_text` (contributions/methodology/results-focused, distinct from the gap-focused extractor).

### 6.6 Course Generator

- **Purpose:** expand a teaching plan into full, grounded, lesson-level educational content and export it to PowerPoint.
- **Inputs:** `(teaching_plan, papers_with_analysis)`, plus per-lesson `already_covered` context.
- **Outputs:** `course` dict with `modules[].lessons[].sections[]` (each section: `topic`, `explanation`, `example_or_evidence`, `key_terms`), plus `check_understanding` and `summary` per lesson, plus `frontier_topics`.
- **Key functions:** `_get_paper_analysis_by_title`, `generate_lesson_for_module` (one lesson per call; threaded for future multi-lesson-per-module support via `lesson_index`/`total_lessons`), `generate_course` (loops modules → lessons, accumulates `covered_summaries` across the whole course for anti-repetition), `export_course_to_pptx` (one combined deck), `export_course_to_pptx_per_lesson` (one file per lesson, with `_safe_filename` sanitization — currently has a minor mid-word-truncation cosmetic bug, unfixed).
- **Endpoint:** `/generate_course` (plus `/download_course/{idea_hash}` for retrieval).

### 6.7 Broadening / Niche-Query Agent (partial)

- **Purpose:** when no directly relevant literature exists, offer transparent, user-confirmed exploration of adjacent fields rather than either failing silently or fabricating a forced connection.
- **Key functions:** `broaden_idea` (decomposes idea into core concepts + adjacent fields + alternative search queries + an `honest_assessment`), `search_with_broadening`/the `/check_relevance` + `/explore_niche` two-step endpoint pattern (tags results `match_type: direct|analogous`).
- **Status:** built and tested once successfully; **not integrated** into the main `/gaps`/`/technical_plan`/`/teaching_plan` pipeline as an automatic gate — currently a standalone capability.

---

## 7. Problems Encountered (Full Log, With Cause / Investigation / Solution / Lesson)

### 7.1 Rate-limiting and provider-fallback issues

- **TPM (tokens-per-minute) exceeded:** *Cause:* sending an entire long section (or an entire concatenated multi-paper blob) as one Groq call. *Investigation:* Groq's 413 error explicitly reported the token math. *Solution:* `chunk_text` (paragraph-aware, ~3000-char/~750–900-token chunks) applied before every LLM call that could plausibly be long. *Lesson:* chunking must be applied at the point of *prompt construction*, not assumed to be handled elsewhere.
- **TPD (tokens-per-day) exceeded:** *Cause:* repeated test iterations during active debugging exhausted the full daily 100,000-token Groq budget. *Investigation:* Groq's 429 error explicitly reported daily usage. *Solution:* Groq→Gemini fallback (`_groq_invoke_safe`), plus routing cheap tasks (relevance filtering) to Gemini permanently rather than Groq-first. *Lesson:* a second Groq API key (or account) does **not** solve this, since quota is tied to the account/org, not the key; creating a second account was explicitly considered and rejected as a ToS/reliability risk not worth taking for an academic deliverable.
- **`.content` attribute crash after switching some calls to Gemini-first:** *Cause:* `filter_papers_hybrid`/`filter_relevant_papers` were changed to call `_gemini_llm.invoke(prompt).content` directly (bypassing `_groq_invoke_safe`, which already normalizes this), but Gemini's `.content` can itself be a list of blocks, not always a plain string — same shape as the original Groq multi-block issue, freshly reintroduced during the fix. *Investigation:* `TypeError`/`AttributeError` tracebacks pointed directly at the offending lines. *Solution:* a shared `_normalize_llm_content` helper was proposed to eliminate this class of bug everywhere at once, since it had now recurred twice across different functions. *Lesson:* response-shape normalization needs to be a single shared utility, not re-implemented ad hoc per call site — this specific class of bug recurred more than once precisely because it wasn't centralized.

### 7.2 Section-splitting robustness

- **`re.fullmatch` too strict:** *Cause:* the first heuristic splitter required an exact full-line regex match against a small pattern set. *Investigation:* manual paper tests showed only 3 of 7–8 real sections detected (e.g., "EXPERIMENTAL RESULTS" didn't match a pattern expecting the word "experiments"). *Solution:* switched to keyword-**containment** matching against a broader `SECTION_KEYWORDS` dict, gated by an `is_likely_header` shape-guard (short, no trailing period, ≤8 words) instead of relying on exact phrasing. *Lesson:* real-world paper headers vary too much for regex-exact matching; loose containment + a structural (not content) guard against false positives generalizes far better.
- **Section-overwrite instead of concatenation:** *Cause:* when the same section label appeared multiple times (e.g., multiple "Results of experiment N" subheadings), the merge logic kept only the *longest* single span, discarding the others. *Investigation:* found via manual inspection of returned section lengths compared against the source paper's actual content (e.g., only ~9KB of "results" content surfaced from a paper that clearly had 4 full experiments' worth). *Solution:* changed to always concatenate (`+=`) content under a repeated section label rather than conditionally overwrite. *Lesson:* "keep the longest" is a dangerous default whenever a section label can legitimately repeat.
- **LLM-fallback splitter truncating instead of scanning the whole paper:** *Cause:* an over-conservative fix for the TPM issue (§7.1) accidentally shrank the fallback splitter's input window to `max_chars * 2` (~6000 chars) — nowhere near enough to see a full long paper, so it could only ever detect early sections (abstract/intro). *Investigation:* comparing `sections_detected` counts before/after a supposedly-safe change revealed a regression from 7 detected sections to 3. *Solution:* rewrote `llm_split_sections` to classify the **whole paper's** chunks sequentially (not truncate), carrying forward a "same as previous" default between chunks, so scale is decoupled from a single call's size limit. *Lesson:* fixing a size/rate-limit problem by simply truncating input silently trades one bug for a worse one (data loss); the correct fix is almost always to chunk-and-iterate, not truncate.

### 7.3 Gap Detection: cross-paper chunk-boundary title loss

- **Cause:** `detect_gaps` originally built one combined text blob across *all* papers (`"\n\n---\n\n".join(per_paper_summaries)`), then chunked that combined blob with no awareness of where one paper's content ended and another's began. Only the first chunk of a long paper's content retained its `"Paper: {title}"` header line; later chunks of the same paper had no title attached.
- **Investigation:** manually cross-referenced a suspicious `papers_involved` entry (e.g., `"MERMAID model performance across various datasets and classes"`) against the actual list of analyzed paper titles and confirmed it wasn't a real title — it was a table-caption-like fragment the LLM had grabbed from a headerless chunk when asked to name its source.
- **Solution:** `chunk_text_with_source` chunks **each paper individually**, tagging every resulting chunk with `{"source": title, "text": chunk}` as structured data; `detect_gaps` then **overrides** (does not merely request) `gap["papers_involved"] = [chunk_dict["source"]]` for every extracted gap, since the true source is already known with certainty and doesn't need to be inferred by the model at all.
- **Lesson (stated explicitly by the project as a general principle):** when ground truth is already known in code, **override** the model's output rather than merely instructing it to get that part right — instructing is weaker than enforcing.

### 7.4 Gap Detection: consolidation silently dropping papers

- **Cause:** even with per-chunk sourcing now correct, the separate `_consolidate_gaps` LLM call (merging near-duplicate gaps found across different chunks/papers) could still omit a paper's contribution entirely during merging, with no signal that this had happened.
- **Investigation:** compared a full pre-consolidation debug dump (`partial_gaps`, confirmed all 4 source papers correctly represented, 15 raw gaps total) against the final post-consolidation output (8 gaps, one paper's 3 gaps entirely missing) — proved the loss was happening specifically inside consolidation, not extraction.
- **Solution (first pass):** track `all_input_papers` vs. `covered_papers` in code after consolidation; if any paper is missing, force-append its first raw gap.
- **User-identified refinement of the fix:** the user correctly challenged whether blind force-re-adding was itself safe — a dropped gap might have been *correctly* merged away by the LLM as genuinely redundant, and blindly re-adding it would undo legitimate, correct consolidation work.
- **Solution (final):** replaced blind force-append with `_verify_dropped_papers`, a targeted LLM call per missing paper that explicitly judges "is this genuinely missing, or already covered by an existing gap" before deciding whether to repair.
- **A code bug found within this fix:** `covered_papers` was declared but never actually updated inside its own loop (missing `.update()` call), so the missing-papers check always operated on an empty set — meaning every run reported 100% of input papers as "missing" regardless of the real (often correct) output. Fixed by moving `covered_papers.update(cleaned)` inside the cleaning loop where it belongs.
- **Lesson:** a verification/safety-net mechanism is only as good as its own correctness — the safety net itself needs testing, not just the thing it's protecting against.

### 7.5 Gap Detection: consolidation inventing paper names during merge

- **Cause:** even with extraction-time sourcing correct and drop-detection working, the *union* operation inside consolidation (combining multiple gaps' `papers_involved` lists when merging near-duplicates) was still free-text LLM output, and could itself hallucinate a plausible-sounding paper name not present anywhere in the actual input — again "MERMAID," this time invented fresh during the merge step rather than inherited from an earlier extraction bug.
- **Investigation:** cross-referenced the final `papers_involved` entries against the `papers_used` list (the ground-truth set of 4 analyzed papers) and found "MERMAID: Multi-modal Fake News Detection with Multi-modal Representation Learning" — a name that does not correspond to any actually-analyzed paper (MERMAID is a *model name mentioned inside* the real "Experimental Comparison" paper's content, not a separate source).
- **Solution:** post-hoc filter every `papers_involved` list in the consolidated output against `all_input_papers` (the real, known-true set), stripping and logging any name not present in that set.
- **Lesson (reinforces §7.3's lesson at a second location):** grounding fixes applied at one stage of a pipeline do not automatically protect a later stage that independently re-touches the same data — each place where free-text attribution happens needs its own verification, not just the first one found.

### 7.6 Miscellaneous / lower-severity bugs

- **`_consolidate_gaps` cap silently truncating gaps beyond 8, in a *different* function** (`generate_technical_plan`'s `gaps[:8]` cap): identified as the same failure *shape* (silent truncation) as other fixed bugs, but confirmed **not** the cause of the Gap-Detection dropped-paper mystery (different function, not on the code path in question). Flagged for the same debug-visibility treatment (log what's being dropped) but not yet applied as of the last known state.
- **Windows path bug in PPTX export:** `output_path` hardcoded as `/tmp/course_{hash}.pptx` (a Unix-only path) caused `FileNotFoundError` on the Windows development machine. Fixed with `tempfile.gettempdir()` + `os.makedirs(exist_ok=True)`.
- **Stale variable reference after a rename:** during the "carry problem/solution fields forward" edit to `generate_course`/`export_course_to_pptx`, the loop variable was renamed from `module` to `lesson` in `generate_course` but the corresponding loop in `export_course_to_pptx` still referenced the old name `module`, which no longer existed in that scope — caught and fixed before being run.
- **Missing function parameter:** an `already_covered` variable was referenced inside `generate_module_content` before it existed as a parameter in the function signature — caught and fixed before being run.
- **OpenAlex query-formatting bug:** a trailing space in the user's idea string produced an invalid `filter=title.search:...+` query string (trailing `+`), causing every OpenAlex call to silently fail with a 400 error. Fixed with `.strip()` on the query before building the filter string.
- **Kaggle `ApiDataset.file_count` AttributeError:** the installed Kaggle library version's dataset object doesn't expose `.file_count` as assumed in `search_kaggle`; this silently drops Kaggle *datasets* specifically (models/kernels unaffected) from every similar-project search. **Not yet fixed** — flagged as low priority.
- **GitLab search returning internal test/sandbox projects:** GitLab's public project search surfaces the platform's own QA/e2e-test repos (usernames like `chandler.bing`, `rachel.green.r`, paths containing `e2e-test`/`sandbox`/`deletion_scheduled`) as if they were real, relevant results. This directly caused the Technical Plan Agent's relevance-gate bug (§2.7) on a deliberately niche query. A code-level filter (`if "e2e-test" in name or "sandbox" in name: skip`) was proposed but **not yet confirmed applied**.

### 7.7 False alarms (investigated, found NOT to be bugs — included because the investigation process itself is a documented project practice)

- **"CAFFE" attributed to the Deep-Plant repo:** initially suspected as a hallucinated technology attribution. Manually verified by inspecting the repo's actual "About"/description field (a separate field from the README, which is why an earlier README-only debug check missed it) — CAFFE was genuinely mentioned there. **Verdict: correctly grounded, not a bug.**
- **"Vision transformers" appearing in a plant-classification technical plan:** initially suspected as an ungrounded, trend-chasing suggestion. Traced upstream to the Gap Detection Agent's own output — the phrase existed in a real paper's stated future-work text, correctly extracted and passed through. **Verdict: correctly grounded, not a bug** (though it did reveal that grounding discipline needs to be enforced at *every* agent that generates free text, not just the last one in the chain — this became a standing design principle).
- **"Bisakol Sentiment Analyzer" and "text and audio Bibles" in a sentiment-analysis plan:** both initially flagged as suspicious/unverifiable specifics. Both confirmed **word-for-word present** in the actual READMEs of two different (correctly, if non-obviously, matched) repos. **Verdict: correctly grounded, not a bug.**
- **A "bodyguard robot" paper appearing among robotic-grasping gaps:** the paper was genuinely off-topic (multi-agent coordination, not fine-grained grasping), but rather than forcing a fabricated grasping-relevant gap, the system correctly and transparently named the mismatch itself as the gap content ("this paper is about X, not the fine-grained control we need") and proposed a legitimate, explicitly-framed bridge. **Verdict: correct, transparent handling of a marginal/loosely-matched source — evidence the grounding instructions generalize beyond the specific case they were written for.**

**General lesson drawn from this category of investigation:** manual verification (not just prompt-tuning) is a required part of validating a grounded-generation system — several "smells" that looked exactly like the hallucination bugs described in §7.3–§7.5 turned out to be correct, well-grounded outputs, and would have been wrongly "fixed" (i.e., made *less* accurate) without checking the actual source data first.

---

## 8. Current Implementation Status

### 8.1 Completed and verified (multi-domain tested)

- Research Agent (multi-source paper search + semantic caching).
- Similar Project Agent (multi-source repo search + similarity scoring + novelty analysis).
- Personal RAG pipeline (basic; upload + ask).
- Full-text retrieval with graceful fallback.
- Section Splitter (heuristic + LLM fallback).
- Section-Analysis Agent (parameterized, cached).
- Gap Detection Agent (hardened citation integrity across three verified bug-fix cycles).
- Technical Plan Agent (grounded, relevance-gated, novelty-aware; verified across 5 domains + 1 stress test).
- Teaching Plan Agent (grounded, gap-driven, problem/solution-structured; verified across 5 domains).
- Course Generator (hierarchical lesson generation, per-topic depth, cross-lesson anti-repetition, combined and per-lesson PPTX export; verified end-to-end).

### 8.2 Partially implemented / experimental

- Rate-limit handling: functional (retry + fallback + task routing) but the `TokenBudget` class uses a rough character-based token estimate, not exact tokenization.
- Niche-query broadening feature: functional in isolation, tested once successfully, **not integrated** into the main pipeline as an automatic gate.
- Caching layer: functional and effective, but distributed across several slightly different patterns (`cache_collection` for semantic paper/project cache, `analysis_cache_collection` for exact-match section-analysis cache) rather than one unified caching abstraction.
- `get_papers_with_analysis` shared-helper refactor: proposed with code, **status of actual application to `main.py` unconfirmed**.

### 8.3 Known limitations (current, accepted)

- Domain scope is technical/CS/AI/ML only, by design.
- Result-submission input is PDF/text only, no vision/OCR, by design.
- No persistence of generated plans/courses across sessions (recomputed or lost each time, aside from the section-analysis cache).
- No multi-user support, no authentication, no roles.
- Kaggle dataset listing partially broken (`.file_count` bug).
- GitLab search returns some non-representative sandbox/test noise (mitigated for Technical Plan Agent via the relevance gate; **not yet applied to the raw `search_gitlab` function itself**, so other consumers of similar-project data are still exposed to this noise).
- PPTX per-lesson filename truncation can cut mid-word (cosmetic only).

### 8.4 Not started

- Lab & Experiment-Design Agent.
- Benchmark Evaluation Agent.
- Conversational orchestrator / `/chat` (only a non-functional stub exists).
- `modify_plan` / general edit capability.
- Frontend (any framework).
- Progress/state tracking database.
- Ollama local fallback activation.
- Integration of the broadening feature into the main pipeline.

---

## 9. Progress Status Table

| Component | Status |
|---|---|
| Research Agent | ✅ Completed |
| Similar Project Agent | ✅ Completed |
| Personal RAG (upload/ask) | ✅ Completed (basic) |
| Full-text retrieval | ✅ Completed |
| Section Splitter | ✅ Completed |
| Section-Analysis Agent | ✅ Completed |
| Gap Detection Agent | ✅ Completed (heavily hardened) |
| Technical Plan Agent | ✅ Completed |
| Teaching Plan Agent | ✅ Completed |
| Course Generator | ✅ Completed |
| PPTX export (combined + per-lesson) | ✅ Completed |
| Rate-limit/fallback infrastructure | 🟡 Partially complete |
| Niche-query broadening | 🟡 Partially complete (built, untegrated) |
| Shared pipeline refactor (`get_papers_with_analysis`) | 🟡 Proposed, unconfirmed applied |
| Lab & Experiment-Design Agent | ⚪ Planned, not started |
| Benchmark Evaluation Agent | ⚪ Planned, not started |
| Conversational orchestrator | ⚪ Planned, not started (stub exists) |
| `modify_plan` agent | ⚪ Planned, deferred to orchestrator |
| Frontend | ⚪ Planned, framework undecided |
| Progress/tracking database | ⚪ Planned, deliberately deferred |
| Ollama local fallback | ⚪ Stubbed, not activated |
| Kaggle dataset `.file_count` fix | ⚪ Known bug, not fixed |
| GitLab sandbox-noise filter (at source) | ⚪ Known issue, only mitigated downstream in one consumer |
| PPTX filename word-boundary truncation | ⚪ Known cosmetic bug, not fixed |

---

## 10. Remaining Work

### 10.1 Features

- Lab & Experiment-Design Agent (exercise generation + suggested student experiments, grounded in matched repos/papers; explicitly no code execution).
- Benchmark Evaluation Agent (compare teacher-submitted PDF/text results against literature; produce comparison data suitable for charting; feed discrepancies back into Gap Detection to close the project's core "living loop").
- Conversational orchestrator (`/chat`) — should call the shared `tools.py` functions directly (not re-call the project's own HTTP endpoints), so it can share in-memory results across multiple agent calls within one conversation turn rather than re-fetching/re-analyzing from scratch each time.
- `modify_plan`/general edit capability, ideally as an orchestrator feature rather than a standalone agent.
- Integration of niche-idea broadening into the main pipeline as an automatic, user-confirmed gate.

### 10.2 Refactoring

- Extract `get_papers_with_analysis` (and equivalents) to eliminate the repeated search→filter→fetch→split→analyze block currently duplicated across `/gaps`, `/technical_plan`, `/teaching_plan`, and `/generate_course`.
- Centralize the "LLM response content may be a string or a list of blocks" normalization into one shared helper (this bug pattern recurred more than once).
- Consider splitting `agents/tools.py` into per-agent modules as it continues to grow.

### 10.3 Bug fixes

- Kaggle `ApiDataset.file_count` AttributeError (dataset listing).
- GitLab sandbox/test-project filtering, applied at the source (`search_gitlab`) rather than only downstream in Technical Plan Agent.
- PPTX per-lesson filename truncation (truncate on word boundary).
- `generate_technical_plan`'s silent `gaps[:8]` truncation — add visibility logging, consistent with the debug-visibility pattern applied everywhere else.
- Confirm (or apply) the `get_papers_with_analysis` refactor actually landed in `main.py`.

### 10.4 Testing

- Multi-domain verification (already established as the project's standard practice) should be repeated for each new agent as it's built: at minimum a "normal" domain, a structurally different domain, and one deliberately niche/thin-data stress test.
- Once the shared pipeline refactor is applied, re-verify that `/gaps`, `/technical_plan`, and `/teaching_plan` still behave identically (regression check).

### 10.5 Documentation / deployment / other

- No deployment strategy has been discussed at all — **[UNKNOWN, entirely out of scope of the conversation so far]**.
- The internship report/write-up is a parallel, ongoing obligation noted repeatedly throughout the project timeline as competing for the same limited remaining time.
- A LaTeX Beamer weekly-progress presentation was produced mid-project (French-language, Madrid theme, TikZ architecture/workflow diagrams) — this is a snapshot artifact, not part of the codebase, and will need updating for future presentations as new agents are completed.

---

## 11. Code Organization

### 11.1 Folder structure (as observed)

```
backend/
├── main.py                      # FastAPI app, all endpoints
├── agents/
│   └── tools.py                 # ALL agent logic, LLM clients, external API calls, caching
└── ingestion/
    ├── pdf_processor.py         # PDF upload + RAG chunking
    ├── chroma_client.py         # ChromaDB collection definitions
    ├── embedding_model.py       # embed() function
    └── cache.py                 # [partially superseded by in-tools.py semantic cache functions]
```

**[Note: this structure is inferred entirely from import statements observed across the conversation; no direct `ls`/tree output of the actual repository was captured. Treat as a best-reconstruction, not a verified listing.]**

### 11.2 Naming conventions observed

- Public agent-entry functions: `generate_*` (plan/course generators), `detect_*` (gap detection), `search_*` (external retrieval), `analyze_*` (structured extraction), `export_*` (deterministic output generation).
- Private/internal helpers prefixed with a single underscore (`_extract_gap_relevant_text`, `_consolidate_gaps`, `_safe_json_parse`, `_groq_invoke_safe`, `_hash_text`, `_normalize_llm_content` [proposed], `_verify_dropped_papers`, `_get_paper_analysis_by_title`).
- LLM client singletons prefixed with a single underscore and named for the provider (`_groq_llm`, `_gemini_llm`, `_ollama_llm` [stubbed]).

### 11.3 Dependencies (as observed in use, not a verified `requirements.txt`)

`fastapi`, `python-dotenv`, `langchain-google-genai`, `langchain-openai`, `arxiv`, `requests`, `pymupdf` (`fitz`), `chromadb` (via `ingestion/chroma_client`), `huggingface_hub`, `kaggle`, `python-pptx`. **[No `requirements.txt` or environment file was shown in the conversation — this list is reconstructed from import statements only.]**

---

## 12. Workflows (Step-by-Step)

### 12.1 "Generate a technical plan for an idea" (`/technical_plan`)

1. **User interaction:** POST `idea` (string) and `max_papers` (int) to `/technical_plan`.
2. **Backend processing:** `search_papers(idea)` queries arXiv/Semantic Scholar/OpenAlex, checking the semantic cache first.
3. **AI interaction:** `filter_papers_hybrid` embeds the idea and all candidate papers, keeps the top-K by cosine similarity, then asks Gemini to pick the final `max_papers` most relevant from that shortlist.
4. **Backend processing:** for each selected paper, `fetch_full_text` attempts PDF download + extraction (falls back to abstract).
5. **Backend processing:** `split_paper_sections` splits the full text (heuristic, LLM fallback if needed).
6. **AI interaction:** `analyze_all_sections` calls Groq (or Gemini on fallback) once per section, per the section's schema, checking the content-hash cache first.
7. **AI interaction:** `detect_gaps` synthesizes cross-paper gaps (per-paper chunked, source-verified, consolidated).
8. **Backend processing:** `search_similar_projects` queries GitHub/HF/Kaggle/GitLab, `compute_similarity_scores` ranks them against the idea.
9. **AI interaction:** `generate_technical_plan` combines gaps + relevance-gated similar projects into one grounded, novelty-aware Groq call.
10. **Output generation:** JSON response containing `plan`, `gaps_used`, `similar_projects_used`.

### 12.2 "Generate a full course with slides" (`/generate_course`)

1. **User interaction:** POST `idea` and `max_papers` to `/generate_course`.
2. Steps 2–7 as above (search → filter → fetch → split → analyze → detect gaps) — currently re-implemented inline in this endpoint (candidate for the `get_papers_with_analysis` refactor).
3. **AI interaction:** `generate_teaching_plan` produces the course skeleton (modules with problem/solution/topics, frontier topics).
4. **AI interaction (looped):** for each module, `generate_lesson_for_module` produces one lesson, with one grounded `sections` entry per topic, referencing `already_covered` content from prior lessons to reduce repetition.
5. **Backend processing (deterministic, no LLM):** `export_course_to_pptx` (or `_per_lesson`) renders the structured `course` dict into one or more `.pptx` files via `python-pptx`.
6. **Output generation:** JSON response with the full `course` structure plus either a `download_url` (combined mode) or `lesson_files` (per-lesson mode).
7. **User interaction (follow-up):** GET `/download_course/{idea_hash}` retrieves the combined file via `FileResponse`.

---

## 13. Prompt Engineering

### 13.1 General prompt structure (consistent pattern across nearly every agent)

Every generation-agent prompt follows the same shape:
1. Context (user idea, and/or module/lesson metadata).
2. Source material (paper text, gap list, similar-project text) — always explicitly labeled and bounded (character-capped).
3. A `schema_instructions` block: (a) the exact required JSON output shape, (b) an `IMPORTANT` block of task-specific content rules, (c) a `CRITICAL — grounding rules` block (see 13.2).
4. Output is always parsed via a shared `_safe_json_parse` (strips markdown fences, returns `{}` on failure rather than raising).

### 13.2 The "grounding rules" block — evolution and rationale

This is the single most-iterated piece of prompt text in the project. Its evolution:
1. **v1 (Technical Plan Agent, first version):** no explicit grounding instruction — produced generic, non-source-specific output (e.g., a boilerplate ML stack unconnected to the actual similar projects found).
2. **v2:** added "core_technologies MUST reference specific technologies actually mentioned in the similar projects... not generic ML defaults" + "each milestone must name which gap it addresses." Fixed the genericness problem but didn't stop hallucinated-but-plausible specifics (e.g. "vision transformers," "CAFFE" — both later verified as actually correct, see §7.7).
3. **v3 (the version that stuck, later copied into Teaching Plan and Course Generator prompts):**
   ```
   CRITICAL — grounding rules:
   - Base every technical claim ONLY on the exact text provided below... Do not supplement
     with general knowledge about the field, even if it seems like a reasonable or common
     suggestion.
   - Only cite a technology/technique as coming from a specific source if it literally
     appears in that source's text provided below. Do not attribute something to a source
     that doesn't mention it, even if the fact is true elsewhere.
   - If the provided data doesn't mention something specific, do not name one — describe
     the point in terms of the underlying problem instead of an unverified solution.
   ```
4. **v4 (relevance-gating, added after the real GitLab-noise bug):** a hard similarity threshold applied in code *before* any similar-project text reaches the prompt at all, plus an explicit "if no similar projects are relevant, do not invent a stack from unrelated repos" instruction — the grounding-rules text alone was not sufficient to prevent the model from using genuinely irrelevant-but-real retrieved data as if it were relevant; the fix had to happen partly in code (filtering), not only in the prompt.
5. **v5 (propagated to Gap Detection's `opportunity` field):** the same grounding block was found to be necessary **again** at an earlier pipeline stage — gaps' `opportunity` text could itself introduce a plausible-sounding technique (e.g. "vision transformers") that was real (present in a paper's future-work text) but which then got treated as if the *Technical Plan Agent* had grounded it, when really it was inherited. This led to the standing project-wide principle: **grounding instructions must be applied at every agent that generates free text which a later agent might treat as source material, not just the final agent in a chain.**

### 13.3 Why prompts changed — summary of drivers

- Genericness (not using the actually-retrieved data) → fixed by explicit "must reference specific X" instructions.
- Plausible-but-unverified specifics (mistaken for hallucination, later found to be real) → fixed by grounding-rule tightening, but this taught the team that *manual verification* is required in addition to prompt tuning, since some "smells" are false positives.
- Irrelevant-but-real retrieved data (the actual, confirmed bug class) → fixed in **code** (relevance threshold), not prompt text alone.
- Repetition across independently-generated modules/lessons → fixed by explicitly threading prior content summaries into later prompts (`already_covered`), with the specific finding that **concept labels are too coarse a signal** — full summary text of what was actually explained works meaningfully better.
- Fabricated conceptual bridges on niche/no-match queries → addressed by an explicit "do not force a conceptual bridge between unrelated fields; say so plainly instead" instruction, combined with the code-level `match_type: direct|analogous` tagging mechanism.

### 13.4 Best practices discovered (stated explicitly across the project)

- **Prefer code-level enforcement over prompt-level instruction whenever ground truth is already known** (e.g., `papers_involved` override, similarity thresholds, post-hoc invented-name filtering). This is the project's single most repeated lesson.
- **A single merged grounding-rules block, reused verbatim across agents**, is more effective and more maintainable than each agent developing its own slightly-different grounding language.
- **Verify apparent hallucinations against real source data before "fixing" them** — several genuine, correct outputs were nearly mistaken for bugs.
- **Debug print statements at every pipeline stage (heuristic vs. LLM-fallback splitting, cache hits, chunk counts, dropped-paper warnings) were essential** to actually diagnosing root causes rather than guessing; this logging was added incrementally, in direct response to specific debugging sessions, and is treated as a permanent part of the codebase, not throwaway debug code.

---

## 14. AI Models — Detailed Rationale

### 14.1 Groq `llama-3.3-70b-versatile`

- **Purpose:** primary reasoning engine for every structurally complex task (section analysis, gap synthesis, plan/course generation).
- **Strengths:** strong reasoning for a free-tier-accessible 70B-class model; very fast inference (LPU hardware).
- **Weaknesses:** restrictive free-tier limits (12,000 TPM / 100,000 TPD observed) that were hit repeatedly during active development and drove significant infrastructure work (chunking, caching, fallback routing).
- **Cost:** free tier only, in current scope.
- **Why selected:** established from the original Phase 0 plan; free, strong reasoning, no changes to this choice were made — all mitigation work targeted its *limits*, not its suitability.

### 14.2 Gemini `gemini-3.1-flash-lite`

- **Purpose:** dual role — (a) fallback when Groq is rate-limited, (b) primary model for lightweight, non-reasoning-heavy tasks (paper relevance filtering) as a deliberate quota-conservation strategy.
- **Strengths:** separate quota bucket from Groq (materially increases total available daily capacity); found to be entirely adequate for structured-extraction-style tasks, not just a "worse" fallback.
- **Weaknesses:** own daily request quota (~1,500/day, as previously documented in the project's own stack notes) that is also finite and shared across every use, including fallback traffic — meaning heavy Groq fallback usage can itself threaten to exhaust the Gemini budget too.
- **Cost:** free tier only.
- **Why selected:** already part of the original hybrid-model plan from Phase 0; the *new* decision made mid-project was to route certain tasks to it **by default**, not only as an emergency fallback, once it was established that its quality was sufficient for those specific tasks.

### 14.3 Ollama `llama3.1:8b` (planned, unused)

- **Purpose (planned):** third-tier, zero-rate-limit fallback for bulk/background work where latency and (lower) quality are acceptable trade-offs.
- **Strengths:** no external rate limit at all (local inference).
- **Weaknesses:** much lower benchmark scores than the other two models (per the project's own earlier-documented comparison table: substantially lower MMLU/tool-calling scores than both Groq's Llama-70B and Gemini Flash); slow CPU inference (5–15s/call, per earlier project documentation).
- **Cost:** free, local compute only.
- **Why not yet activated:** the two-tier Groq→Gemini fallback has so far been sufficient; activating a third, meaningfully weaker tier was explicitly deferred rather than adding complexity/quality risk preemptively.

### 14.4 Embeddings — `all-MiniLM-L6-v2` (sentence-transformers)

- **Purpose:** all similarity-based operations — paper relevance filtering, similar-project scoring, semantic cache matching.
- **Strengths:** free, local (no API calls/rate limits), lightweight, fast.
- **Weaknesses:** not evaluated against alternatives during this project (no comparison was run against larger/more modern embedding models) — **[a genuine open question, not explicitly revisited after the original Phase 0 selection]**.
- **Why selected:** inherited from the original Phase 0 plan; never revisited.

---

## 15. Lessons Learned (Project-Wide Summary)

### 15.1 Important discoveries

- Grounding/hallucination problems in LLM pipelines are **not solved by prompting alone** — the most durable fixes in this project were all code-level: relevance thresholds before data reaches a prompt, ground-truth overrides for fields the system already knows with certainty, and post-hoc verification of anything the model claims about its own sources.
- A structured-output pipeline's failure modes compound across stages: a grounding fix at one agent does not protect a later agent that independently re-touches the same category of data (papers_involved needed fixing at *both* the extraction stage and the consolidation stage, separately).
- Not every suspicious-looking output is a bug. Manual verification against real source data is a required step, not an optional nicety — several outputs that looked exactly like known hallucination patterns turned out to be correctly grounded.
- Free-tier LLM infrastructure imposes real, recurring engineering costs (rate limits, quota exhaustion, provider fallback) that are worth designing around explicitly (task-based routing, caching) rather than treating as an occasional annoyance.

### 15.2 Best practices adopted

- Debug-print visibility at every non-trivial branch point (heuristic vs. fallback, cache hit vs. miss, chunk counts, dropped/repaired data) — treated as permanent, not throwaway.
- A single, reused, increasingly-refined "grounding rules" prompt block copied across every content-generating agent, rather than each agent inventing its own.
- Deliberate multi-domain testing (at least one "normal" domain, one structurally different domain, one deliberately thin/niche stress-test) for every new agent before considering it validated.
- Explicit "diminishing returns" stopping criteria — several imperfect-but-acceptable results (course-content repetition, dropped-gap force-repair heuristics) were consciously left as "good enough" rather than pursued to perfection, given fixed project time.

### 15.3 Mistakes to avoid (explicitly identified during development)

- Don't fix a rate-limit problem by truncating input — chunk-and-iterate instead, or you silently lose data (happened with the LLM-fallback section splitter).
- Don't trust an LLM's free-text claim about its own sources when the true source is already known in code — verify or override it.
- Don't assume a "safety net" fix is correct without testing the safety net itself (the `covered_papers.update()` omission meant the repair-detection logic was itself broken for a time).
- Don't build a second layer (frontend, tracking database, general edit/modify capability) against an API surface that is still actively changing shape — this was identified as a recurring, avoidable source of rework risk and was the explicit reason multiple features were deliberately deferred.
- Don't assume creating a second account/key with a provider is a safe way around a rate limit — it's a policy risk, not just a technical workaround, and was explicitly rejected on those grounds.

### 15.4 Future recommendations

- Apply the `get_papers_with_analysis`-style shared-pipeline refactor before adding more agents, to avoid a fourth/fifth copy of the same duplicated block.
- Build the Lab & Experiment-Design Agent and Benchmark Evaluation Agent next, reusing the exact same grounding-rules block and relevance-gating pattern from day one, rather than rediscovering these lessons a third time.
- Design the orchestrator to call `tools.py` functions directly (never the project's own HTTP endpoints), and to own general-purpose "modify an existing artifact based on a follow-up request" logic centrally, rather than building per-artifact modify-agents.
- Delay frontend and persistence decisions until the full agent pipeline (including Lab/Eval) is stable — this was a deliberate, repeatedly-reaffirmed decision throughout the project and should continue to hold.
- Revisit whether a stronger/different embedding model would materially improve similarity-based filtering and gating — never benchmarked against alternatives in this project.

---

## 16. Project Roadmap (Priority Order, As Of Latest Known State)

1. **Apply pending refactors and low-effort bug fixes:** shared `get_papers_with_analysis` helper (confirm/apply), `.strip()`-style small fixes already identified (GitLab sandbox filter at source, PPTX filename truncation, `gaps[:8]` visibility logging), centralized LLM-content normalization helper.
2. **Build Lab & Experiment-Design Agent** — exercise generation + suggested student experiments, grounded in matched repos (via the existing Similar Project Agent + relevance gate) and papers (via existing section analysis); explicitly no code execution.
3. **Build Benchmark Evaluation Agent** — ingest teacher-submitted PDF/text student results, compare against literature-reported numbers (already extracted into `reported_numbers` during Section Analysis), produce comparison/chart-ready output; wire the "feeds back into Gap Detection" closed-loop concept from the project's original core narrative.
4. **Build the conversational orchestrator (`/chat`)** — call `tools.py` functions directly; own general "modify an existing artifact" logic; enable multi-turn reuse of already-fetched papers/gaps within one conversation.
5. **Integrate the niche-idea broadening feature** into the main pipeline as an automatic, user-confirmed gate ahead of Gap Detection/Technical Plan/Teaching Plan.
6. **Decide and build the frontend** (React+Vite, React+template, or Streamlit/Gradio) once the API surface above is stable.
7. **Build the progress/state tracking persistence layer**, informed by the actual final shape of all artifact types (plans, courses, labs, evaluations) rather than designed prematurely.
8. **Polish pass:** address remaining known bugs (Kaggle `.file_count`, PPTX filename truncation), write/finish the internship report, prepare final presentation materials.

---

## 17. Current Project State — Summary

**Where the project stands today:** the entire literature-to-curriculum pipeline is built and working, end to end, from a raw user idea through to a downloadable, editable PowerPoint course — covering research search, similar-project search, paper section analysis, cross-paper gap detection, grounded technical-plan generation, grounded and gap-driven teaching-plan generation, and hierarchical, per-topic lesson content generation with two export modes. This represents the "Initialisation and Analysis" and most of the "Planification and Conception" phases of the project's own three-phase architecture diagram.

**What is fully operational:** Research Agent, Similar Project Agent, personal RAG (basic), Section Splitter, Section-Analysis Agent, Gap Detection Agent (extensively hardened against citation-integrity bugs — the project's most rigorously debugged component), Technical Plan Agent, Teaching Plan Agent, and Course Generator (including PowerPoint export in both combined-deck and per-lesson-file modes).

**What still requires work:** the "Exécution and Évaluation" phase of the architecture (Lab/Experiment generation, teacher assignment, student result submission, Benchmark Evaluation, feedback into Gap Detection) has not been started at all. The conversational orchestrator that would tie everything into a single chat interface exists only as a non-functional stub. No frontend exists. No persistence/tracking layer exists. A handful of known, low-severity bugs remain unfixed (Kaggle dataset listing, GitLab sandbox noise at the source, PPTX filename truncation).

**Biggest remaining challenges:** (1) building the Benchmark Evaluation Agent and closing the project's core "living loop" concept, which is central to the project's differentiation claim but has not yet been attempted; (2) building a real orchestrator without re-introducing the duplicated-pipeline-work problem already identified; (3) making the frontend/persistence-layer decisions well, given they were deliberately and repeatedly deferred and will need to happen under increasing time pressure; (4) continuing to manage free-tier API constraints as agent count and testing volume grow further.

**Immediate next steps (as of the last discussed state):** apply the small pending refactors and bug fixes (§16, item 1), then begin the Lab & Experiment-Design Agent, explicitly reusing the now well-validated grounding-rules block and relevance-gating pattern from the very start rather than rediscovering them a third time.
