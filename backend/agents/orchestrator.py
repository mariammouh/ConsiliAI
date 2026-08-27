"""
Conversational Orchestrator
============================

v1 scope (per PROJECT_MASTER_CONTEXT.md §16 item 4):
- Owns conversational routing/tool-calling across the complete agent set
  (research through benchmark evaluation).
- Reuses already-fetched papers/gaps/plans within one conversation instead
  of re-running the search->filter->fetch->split->analyze pipeline on every
  turn — this is the orchestrator-level fix for the duplicated-pipeline-work
  issue documented in §4.6 / §10.2 for /gaps, /technical_plan, /teaching_plan.
- Calls agents/tools.py functions DIRECTLY, never the project's own HTTP
  endpoints in main.py (per §10.1 / §15.4) — this file has no dependency on
  main.py, and main.py imports FROM this file, never the reverse.
- `modify_plan` / generic "edit an existing artifact" is explicitly OUT of
  scope for v1 (per §16 item 4) — not implemented here.

v2 change — intent gating (this revision):
A ReAct tool-calling loop with self-sufficient, eager tools will pick a
tool almost every turn, because that's the path of least resistance for a
routing LLM — prompt instructions alone don't reliably hold it back. This
is the same class of problem the project already solved three times in Gap
Detection (§7.3-§7.5): don't trust the model to self-limit when the
constraint can be enforced in code instead.

Fix: an explicit classification node runs BEFORE the tool-calling loop is
even reachable. It decides, in code, whether this turn is:
  - "idea_introduction": user is introducing/describing a project idea
    without asking for a specific deliverable -> respond with a brief
    understanding + a menu of what's available, ask what they want. NO
    tool is invoked, nothing is computed.
  - "general_chat": greetings/small talk/unrelated questions -> plain
    reply, no tools.
  - "action_request": an explicit ask for a specific deliverable (a plan,
    a course, gaps, experiments, a relevance check, etc.) -> enters the
    tool-calling loop, which picks the specific tool.
  - "info_question": a factual/informational question that likely needs
    the literature to answer well, but isn't a request for a full
    deliverable (e.g. "has F1-score been used for this before?") -> enters
    the tool-calling loop, where `answer_from_literature` (grounded, reuses
    already-analyzed papers, does NOT run gap detection or plan generation)
    is the expected tool, not the heavy plan/course agents.

Only "action_request" and "info_question" ever reach the tool-bound LLM.
This is a hard gate, not a prompt suggestion.

Design notes (carried over from v1):
- Built on LangGraph, NOT the old LangChain `AgentExecutor` that Phase 0
  abandoned (§5). The graph is now assembled manually (StateGraph + a
  classify node + a tool-bound agent node + ToolNode), rather than via the
  `create_react_agent` prebuilt, specifically so the classify gate can sit
  in front of the tool loop as its own node.
- State persistence uses LangGraph's checkpointer, keyed by `thread_id`
  (now derived from the authenticated user's id, not client-supplied — see
  main.py's /chat). Backed by Postgres via `PostgresSaver` (swapped from
  the original `MemorySaver` once real multi-user usage became a concrete
  near-term need, not just a future-proofing guess). This IS the "shadow
  database" from §2.13/§8.4.
- Groq-first, Gemini-fallback is preserved via `.with_fallbacks()`, but
  applied AFTER `.bind_tools()` on each underlying model individually —
  `RunnableWithFallbacks` does not itself implement `.bind_tools()`, so
  binding must happen on the two chat-model instances first, then the
  fallback wraps the two already-tool-bound runnables.
- Each pipeline tool is still self-sufficient (checks state for an idea
  match before recomputing, computes missing prerequisite stages inline),
  per §13.4 / §15.1 — the classify gate controls WHETHER the tool loop
  runs at all; once inside it, tools still avoid redundant recomputation.
"""

import os
import tempfile
from typing import Annotated, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import InjectedState, ToolNode, tools_condition
from langgraph.types import Command

from agents.tools import (
    _ensure_llm_clients,
    _groq_invoke_safe,
    _hash_text,
    _safe_json_parse,
    analyze_novelty,
    broaden_idea,
    compute_similarity_scores,
    detect_gaps,
    export_course_to_pptx,
    export_course_to_pptx_per_lesson,
    export_lab_to_notebook,
    filter_papers_hybrid,
    generate_benchmark_evaluation,
    generate_course,
    generate_experiment_set,
    generate_lab_exercise,
    generate_teaching_plan,
    generate_technical_plan,
    get_papers_with_analysis,
    search_papers,
    search_similar_projects,
    retrieve_from_knowledge_base,
)


# =============================================================================
# STATE SCHEMA
# =============================================================================
# Everything the pipeline would otherwise recompute on every call lives here.
# Keyed implicitly by "idea" (single active idea per thread for v1 — a
# thread switching topics mid-conversation will recompute, which is correct
# behavior, not a bug: state should not silently carry over between two
# different ideas).

class OrchestratorState(TypedDict):
    messages: Annotated[list, add_messages]
    idea: Optional[str]
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
    _route: Optional[str]   # internal: set by classify_node, consumed by the routing edge only


# =============================================================================
# INTERNAL "ENSURE" HELPERS
# Read-only against state; return freshly computed (or cached) values. Each
# tool merges what it needs into its own Command update — these helpers have
# no side effects on state themselves.
# =============================================================================

def _same_idea(state: dict, idea: str) -> bool:
    return (state.get("idea") or "").strip().lower() == (idea or "").strip().lower()


def _papers_have_metadata(papers: list) -> bool:
    """Return True only if every paper in the cached list has a non-empty url
    field. Rejects stale state saved before url/source were included."""
    return bool(papers) and all(bool(p.get("url")) for p in papers)


def _ensure_papers_only(state: dict, idea: str, max_papers: int = 3):
    """Like _ensure_papers_and_gaps but deliberately does NOT trigger gap
    detection — used for informational literature questions where full gap
    synthesis isn't needed. Still populates papers_with_analysis for later
    gap/plan tools to reuse without re-fetching."""
    cached = state.get("papers_with_analysis") if _same_idea(state, idea) else None
    if _papers_have_metadata(cached):
        return cached
    papers = get_papers_with_analysis(idea, max_papers=max_papers)
    return papers or []


def _ensure_papers_and_gaps(state: dict, idea: str, max_papers: int = 3):
    cached = state.get("papers_with_analysis") if _same_idea(state, idea) else None
    if _papers_have_metadata(cached) and state.get("gaps") is not None:
        return cached, state["gaps"]
    papers = get_papers_with_analysis(idea, max_papers=max_papers)
    if not papers:
        return [], []
    gaps_result = detect_gaps(idea, papers)
    return papers, gaps_result.get("gaps", [])


def _ensure_similar_projects(state: dict, idea: str, max_results: int = 15):
    if _same_idea(state, idea) and state.get("similar_projects_scored") is not None:
        return (
            state.get("similar_projects_raw", []),
            state["similar_projects_scored"],
            state.get("novelty_analysis", ""),
        )
    raw = search_similar_projects(idea, max_results=max_results)
    scored = compute_similarity_scores(idea, raw)
    novelty = analyze_novelty(idea, scored[:8])
    return raw, scored, novelty


def _ensure_teaching_plan(state: dict, idea: str):
    papers, gaps = _ensure_papers_and_gaps(state, idea)
    if _same_idea(state, idea) and state.get("teaching_plan"):
        return papers, gaps, state["teaching_plan"]
    if not papers:
        return papers, gaps, {"_error": "No papers could be analyzed for this idea."}
    teaching_plan = generate_teaching_plan(idea, gaps, papers)
    return papers, gaps, teaching_plan


def _ensure_course(state: dict, idea: str):
    papers, gaps, teaching_plan = _ensure_teaching_plan(state, idea)
    if _same_idea(state, idea) and state.get("course"):
        return papers, gaps, teaching_plan, state["course"]
    if teaching_plan.get("_error"):
        return papers, gaps, teaching_plan, {"_error": teaching_plan["_error"]}
    course = generate_course(teaching_plan, papers)
    return papers, gaps, teaching_plan, course


def _gaps_preview(gaps: List[Dict], limit: int = 5) -> str:
    if not gaps:
        return "(no gaps)"
    return "\n".join(f"- {g.get('gap_description', '')[:150]}" for g in gaps[:limit])


def _slug(text: str, max_len: int = 50) -> str:
    import re as _re
    slug = _re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    if len(slug) <= max_len:
        return slug or "item"
    truncated = slug[:max_len]
    return truncated.rsplit("_", 1)[0] if "_" in truncated else truncated


def _pptx_output_path(idea: str) -> str:
    output_dir = os.path.join(tempfile.gettempdir(), "consiliai_courses")
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, f"course_{_hash_text(idea)[:8]}.pptx")


def _lab_output_dir(idea: str) -> str:
    return os.path.join(tempfile.gettempdir(), "consiliai_labs", _hash_text(idea)[:8])


def _extract_literature_qa_text(papers: List[Dict], max_chars: int = 6000) -> str:
    """Field-selective extraction for grounded Q&A, same pattern as
    _extract_gap_relevant_text / _extract_teaching_relevant_text in
    tools.py — pull only the fields likely relevant to a factual question
    (metrics, baselines, algorithms, reported numbers, abstract summary)
    rather than dumping the full per-section analysis dict into the prompt."""
    parts = []
    for p in papers:
        analysis = p.get("analysis", {}) or {}
        results = analysis.get("results", {}) or {}
        methodology = analysis.get("methodology", {}) or {}
        abstract = analysis.get("abstract", {}) or {}

        piece = [f"Paper: {p.get('title', 'Unknown')}"]
        if p.get("url"):
            piece.append(f"URL: {p['url']}")
        if p.get("pdf_url"):
            print(f"[orchestrator] paper '{p.get('title','')}' has pdf_url: {p['pdf_url']}")
            piece.append(f"PDF Link: {p['pdf_url']}")
        if methodology.get("algorithms"):
            piece.append(f"Algorithms/methods: {methodology['algorithms']}")
        if results.get("metrics"):
            piece.append(f"Metrics used: {results['metrics']}")
        if results.get("baselines_compared"):
            piece.append(f"Baselines compared: {results['baselines_compared']}")
        if results.get("reported_numbers"):
            piece.append(f"Reported numbers: {results['reported_numbers']}")
        if abstract.get("summary"):
            piece.append(f"Summary: {abstract['summary']}")
        parts.append("\n".join(piece))

    return "\n\n---\n\n".join(parts)[:max_chars]


# =============================================================================
# TOOLS
# Each tool: (1) reads InjectedState, (2) computes/reuses via the helpers
# above, (3) returns a Command that updates state AND appends a ToolMessage
# summarizing the result back into the conversation (the model reasons over
# this summary, not the raw JSON dump, to keep tool-result tokens bounded).
#
# These tools are only ever reachable after classify_node has already
# decided this turn is an "action_request" or "info_question" — see the
# module docstring. They no longer need to defend against being called on
# a bare idea-introduction turn; that's handled upstream.
# =============================================================================

@tool
def answer_from_literature(
    idea: str,
    question: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Answer a specific factual/informational question using analyzed
    literature (e.g. 'has F1-score been used for this kind of project
    before?', 'what evaluation metrics are common here?', 'what datasets do
    these papers use?'). Reuses already-analyzed papers for this idea if
    available; otherwise fetches and analyzes a small set of papers first —
    this does NOT run gap detection or generate any plan. Use this INSTEAD
    of create_technical_plan / create_teaching_plan / find_research_gaps
    whenever the user is asking a question rather than requesting a full
    deliverable."""
    papers = _ensure_papers_only(state, idea)
    if not papers:
        msg = f"No papers could be found or analyzed for '{idea}', so I can't answer that from the literature."
        return Command(update={"messages": [ToolMessage(msg, tool_call_id=tool_call_id)]})

    source_text = _extract_literature_qa_text(papers)
    prompt = f"""Question: "{question}"

Answer this question using ONLY the paper information below. If the papers
don't contain enough information to answer confidently, say so plainly
rather than guessing or filling in with general knowledge.

CRITICAL — grounding rules:
- Base your answer only on the text below. Do not supplement with general
  knowledge about the field, even if it seems like a safe assumption.
- If you attribute a claim to a specific paper, only do so if that paper's
  text below actually supports it.

Paper information:
{source_text}

Answer in 2-4 sentences.
"""
    answer = _groq_invoke_safe(prompt)

    return Command(update={
        "idea": idea,
        "papers_with_analysis": papers,
        "messages": [ToolMessage(answer, tool_call_id=tool_call_id)],
    })


@tool
def find_research_gaps(
    idea: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Search literature for a project/learning idea and detect research
    gaps. Use this when the user explicitly asks what gaps or open problems
    exist for their idea. Other tools (technical plan, teaching plan,
    course, experiments) will call this internally if needed, so you do not
    need to call this first just to prime state."""
    papers, gaps = _ensure_papers_and_gaps(state, idea)
    if not papers:
        msg = f"No papers could be found or analyzed for the idea: '{idea}'."
        return Command(update={"messages": [ToolMessage(msg, tool_call_id=tool_call_id)]})

    summary = (
        f"Analyzed {len(papers)} paper(s) for '{idea}' and found {len(gaps)} research gap(s):\n"
        f"{_gaps_preview(gaps)}"
    )
    return Command(update={
        "idea": idea,
        "papers_with_analysis": papers,
        "gaps": gaps,
        "messages": [ToolMessage(summary, tool_call_id=tool_call_id)],
    })


@tool
def create_technical_plan(
    idea: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Generate a grounded, novelty-aware technical project plan (recommended
    stack, architecture, milestones, deliverables, risks) for the given
    idea. ONLY call this when the user explicitly asks for a technical plan
    / implementation plan — not for a general project introduction.
    Automatically finds research gaps and similar existing projects first if
    not already available for this idea."""
    papers, gaps = _ensure_papers_and_gaps(state, idea)
    if not papers:
        msg = f"No papers could be found or analyzed for the idea: '{idea}'."
        return Command(update={"messages": [ToolMessage(msg, tool_call_id=tool_call_id)]})

    raw, scored, novelty = _ensure_similar_projects(state, idea)
    top_similar = scored[:8]
    plan = generate_technical_plan(idea, gaps, top_similar, novelty_analysis=novelty)

    summary = (
        f"Technical plan generated for '{idea}'.\n"
        f"Novelty assessment: {plan.get('novelty_assessment', 'N/A')}\n"
        f"Recommended stack: {', '.join(plan.get('recommended_stack', {}).get('core_technologies', [])) or 'N/A'}\n"
        f"Milestones: {len(plan.get('milestones', []))}"
    )
    return Command(update={
        "idea": idea,
        "papers_with_analysis": papers,
        "gaps": gaps,
        "similar_projects_raw": raw,
        "similar_projects_scored": scored,
        "novelty_analysis": novelty,
        "technical_plan": plan,
        "messages": [ToolMessage(summary, tool_call_id=tool_call_id)],
    })


@tool
def create_teaching_plan(
    idea: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Generate a grounded, gap-driven course skeleton (learning objectives,
    modules with problem/solution framing, frontier topics) for the given
    idea. ONLY call this when the user explicitly asks for a teaching plan /
    course outline / curriculum. Automatically finds research gaps first if
    not already available."""
    papers, gaps, teaching_plan = _ensure_teaching_plan(state, idea)
    if teaching_plan.get("_error"):
        return Command(update={"messages": [ToolMessage(teaching_plan["_error"], tool_call_id=tool_call_id)]})

    modules = teaching_plan.get("modules", [])
    summary = (
        f"Teaching plan generated for '{idea}': \"{teaching_plan.get('course_title', '')}\"\n"
        f"Target audience: {teaching_plan.get('target_audience', 'N/A')}\n"
        f"Modules ({len(modules)}): " + ", ".join(m.get("title", "") for m in modules) + "\n"
        f"Frontier topics: {len(teaching_plan.get('frontier_topics', []))}"
    )
    return Command(update={
        "idea": idea,
        "papers_with_analysis": papers,
        "gaps": gaps,
        "teaching_plan": teaching_plan,
        "messages": [ToolMessage(summary, tool_call_id=tool_call_id)],
    })


@tool
def create_course(
    idea: str,
    export_per_lesson: bool,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Generate full hierarchical lesson content (module -> lesson ->
    sections) from the teaching plan and export it to PowerPoint. ONLY call
    this when the user explicitly asks for a full course / slides / lesson
    content to be generated. Automatically builds the teaching plan first if
    not already available. The chat application always exports one .pptx file
    per lesson; export_per_lesson is retained for tool compatibility."""
    papers, gaps, teaching_plan, course = _ensure_course(state, idea)
    if course.get("_error"):
        return Command(update={"messages": [ToolMessage(course["_error"], tool_call_id=tool_call_id)]})

    output_dir = os.path.join(tempfile.gettempdir(), "consiliai_courses")
    paths = export_course_to_pptx_per_lesson(course, output_dir)
    export_note = f"Exported {len(paths)} lesson PowerPoint file(s)."
    export_path_value = ", ".join(paths)

    num_modules = len(course.get("modules", []))
    num_lessons = sum(len(m.get("lessons", [])) for m in course.get("modules", []))
    summary = (
        f"Course generated for '{idea}': \"{course.get('course_title', '')}\"\n"
        f"{num_modules} module(s), {num_lessons} lesson(s).\n"
        f"{export_note}"
    )
    return Command(update={
        "idea": idea,
        "papers_with_analysis": papers,
        "gaps": gaps,
        "teaching_plan": teaching_plan,
        "course": course,
        "course_export_path": export_path_value,
        "messages": [ToolMessage(summary, tool_call_id=tool_call_id)],
    })


@tool
def create_lab_exercises(
    idea: str,
    generate_code: bool,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Generate a hands-on lab exercise (with optional starter/solution code
    and Jupyter notebooks) for each lesson of the course. ONLY call this
    when the user explicitly asks for lab exercises / practice exercises /
    notebooks. Automatically builds the course first if not already
    available. Set generate_code to false for a fast preview (exercise
    framing only, no code/notebooks)."""
    papers, gaps, teaching_plan, course = _ensure_course(state, idea)
    if course.get("_error"):
        return Command(update={"messages": [ToolMessage(course["_error"], tool_call_id=tool_call_id)]})

    raw, scored, novelty = _ensure_similar_projects(state, idea)
    output_dir = _lab_output_dir(idea)

    modules_output = []
    lesson_count = 0
    for tp_module, course_module in zip(teaching_plan.get("modules", []), course.get("modules", [])):
        lessons_output = []
        for lesson in course_module.get("lessons", []):
            try:
                lab = generate_lab_exercise(
                    lesson=lesson,
                    module=tp_module,
                    papers_with_analysis=papers,
                    similar_projects_scored=scored,
                    generate_code=generate_code,
                )
            except Exception as e:
                lab = {"_error": str(e)}

            notebook_paths = None
            if generate_code and not lab.get("_error"):
                filename_base = _slug(f"{tp_module.get('title','')}_{lesson.get('lesson_title','')}")
                try:
                    notebook_paths = export_lab_to_notebook(lab, output_dir, filename_base)
                except Exception as e:
                    print(f"[orchestrator] notebook export failed for '{filename_base}': {e}")

            lessons_output.append({"lab": lab, "notebook_files": notebook_paths})
            lesson_count += 1

        modules_output.append({"module_title": tp_module.get("title", ""), "lessons": lessons_output})

    summary = (
        f"Generated {lesson_count} lab exercise(s) across {len(modules_output)} module(s) for '{idea}'.\n"
        f"Notebook files (if any) written under: {output_dir}"
    )
    return Command(update={
        "idea": idea,
        "papers_with_analysis": papers,
        "gaps": gaps,
        "teaching_plan": teaching_plan,
        "course": course,
        "lab_exercises": modules_output,
        "similar_projects_raw": raw,
        "similar_projects_scored": scored,
        "novelty_analysis": novelty,
        "messages": [ToolMessage(summary, tool_call_id=tool_call_id)],
    })


@tool
def create_experiments(
    idea: str,
    max_experiments: int,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Generate one grounded, suggested student experiment per research gap
    (dataset, baselines, metrics, protocol, hypothesis) for a teacher to
    assign. ONLY call this when the user explicitly asks for experiments /
    suggested studies to assign students. No code is executed by this
    system — students run experiments themselves. Automatically finds
    research gaps first if not already available."""
    papers, gaps = _ensure_papers_and_gaps(state, idea)
    if not papers:
        msg = f"No papers could be found or analyzed for the idea: '{idea}'."
        return Command(update={"messages": [ToolMessage(msg, tool_call_id=tool_call_id)]})

    raw, scored, novelty = _ensure_similar_projects(state, idea)
    experiment_set = generate_experiment_set(
        idea=idea,
        gaps=gaps,
        papers_with_analysis=papers,
        similar_projects_raw=raw,
        max_experiments=max_experiments or 6,
    )

    titles = [e.get("title", "(untitled)") for e in experiment_set.get("experiments", [])]
    summary = (
        f"Generated {len(titles)} experiment(s) for '{idea}':\n" +
        "\n".join(f"- {t}" for t in titles)
    )
    return Command(update={
        "idea": idea,
        "papers_with_analysis": papers,
        "gaps": gaps,
        "similar_projects_raw": raw,
        "similar_projects_scored": scored,
        "novelty_analysis": novelty,
        "experiments": experiment_set,
        "messages": [ToolMessage(summary, tool_call_id=tool_call_id)],
    })


@tool
def evaluate_student_submission(
    experiment_title: str,
    submission_text: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Compare a student's submitted experiment results (plain text) against
    literature-reported numbers for a previously generated experiment,
    assess whether the results match the experiment's hypothesis, and flag
    any significant discrepancy as a candidate new research gap. Requires
    that create_experiments has already been run in this conversation for
    the relevant idea."""
    experiments = (state.get("experiments") or {}).get("experiments", [])
    if not experiments:
        msg = "No experiments have been generated yet in this conversation — run create_experiments first."
        return Command(update={"messages": [ToolMessage(msg, tool_call_id=tool_call_id)]})

    match = next(
        (e for e in experiments if experiment_title.strip().lower() in (e.get("title", "").lower())),
        None,
    )
    if not match:
        available = ", ".join(e.get("title", "") for e in experiments)
        msg = f"No experiment matching '{experiment_title}' found. Available experiments: {available}"
        return Command(update={"messages": [ToolMessage(msg, tool_call_id=tool_call_id)]})

    papers = state.get("papers_with_analysis") or []
    result = generate_benchmark_evaluation(
        experiment=match,
        papers_with_analysis=papers,
        submission_text=submission_text,
    )

    summary = f"Evaluation for '{match.get('title','')}': {result.get('summary', '')}\n"
    hyp = result.get("hypothesis_check", {})
    summary += f"Hypothesis match: {hyp.get('matches_expectation', 'unclear')} — {hyp.get('explanation', '')}\n"
    if result.get("proposed_gap"):
        summary += f"New candidate gap proposed: {result['proposed_gap'].get('gap_description', '')}"

    return Command(update={"messages": [ToolMessage(summary, tool_call_id=tool_call_id)]})


@tool
def check_topic_relevance(
    idea: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Check whether directly relevant literature exists for an idea before
    committing to the full pipeline. Use this for niche, unusual, or
    cross-domain ideas where the user explicitly asks whether literature
    exists, or seems unsure it will. Does not modify shared state — this is
    a lightweight pre-check."""
    raw_papers = search_papers(idea, max_results=15)
    scored_papers = filter_papers_hybrid(raw_papers, idea, embed_top_k=8, llm_top_n=5, return_scores=True)
    direct_relevant = [(s, p) for s, p in scored_papers if s >= 0.30]

    if direct_relevant:
        msg = f"Found {len(direct_relevant)} directly relevant paper(s) for '{idea}'. Safe to proceed normally."
    else:
        msg = (
            f"No directly relevant literature was found for '{idea}'. "
            f"This may be a niche or cross-domain idea. Ask the user if they'd like to explore "
            f"adjacent fields (use explore_adjacent_fields) instead of proceeding as if this were "
            f"a well-covered topic."
        )
    return Command(update={"messages": [ToolMessage(msg, tool_call_id=tool_call_id)]})


@tool
def explore_adjacent_fields(
    idea: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """For a niche idea with no direct literature match, decompose it into
    core concepts and search adjacent/analogous fields. Only call this after
    check_topic_relevance reports no direct match AND the user has confirmed
    they want to explore adjacent fields — do not call this unprompted."""
    broadening = broaden_idea(idea)
    analogous_papers = []
    for query in broadening.get("suggested_queries", [])[:3]:
        raw = search_papers(query, max_results=8)
        scored = filter_papers_hybrid(raw, query, embed_top_k=5, llm_top_n=2, return_scores=True)
        for score, p in scored:
            if score >= 0.30:
                p["match_type"] = "analogous"
                p["matched_via_query"] = query
                analogous_papers.append(p)

    summary = (
        f"Honest assessment: {broadening.get('honest_assessment', 'N/A')}\n"
        f"Core concepts: {', '.join(broadening.get('core_concepts', []))}\n"
        f"Adjacent fields: {', '.join(broadening.get('adjacent_fields', []))}\n"
        f"Found {len(analogous_papers)} analogous (not direct-match) paper(s): "
        + ", ".join(p.get("title", "") for p in analogous_papers[:5])
    )
    return Command(update={"messages": [ToolMessage(summary, tool_call_id=tool_call_id)]})


@tool
def summarize_progress(state: Annotated[dict, InjectedState]) -> str:
    """Report what has already been generated for the current idea in this
    conversation (papers, gaps, plans, course, experiments) without
    recomputing anything. Use this when the user asks what's been done so
    far, or before deciding whether another tool needs to run."""
    idea = state.get("idea")
    if not idea:
        return "No idea has been set yet in this conversation."

    parts = [f"Current idea: '{idea}'"]
    if state.get("papers_with_analysis"):
        parts.append(f"- {len(state['papers_with_analysis'])} paper(s) analyzed")
    if state.get("gaps") is not None:
        parts.append(f"- {len(state['gaps'])} research gap(s) found")
    if state.get("technical_plan"):
        parts.append("- Technical plan: generated")
    if state.get("teaching_plan"):
        parts.append("- Teaching plan: generated")
    if state.get("course"):
        parts.append("- Course: generated (the PowerPoint presentation is ready to download)")
    if state.get("experiments"):
        parts.append(f"- {len(state['experiments'].get('experiments', []))} experiment(s) generated")
    if len(parts) == 1:
        parts.append("- Nothing generated yet beyond the idea itself.")
    return "\n".join(parts)


@tool
def search_personal_documents(
    question: str,
    config: RunnableConfig,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Search through the user's uploaded personal documents to answer a question. 
    Use this when the user asks a question about their own documents or uploaded files."""
    user_id = config.get("configurable", {}).get("thread_id")
    if not user_id:
        return Command(update={"messages": [ToolMessage("Error: Could not identify user.", tool_call_id=tool_call_id)]})
    
    answer = retrieve_from_knowledge_base(question, user_id=user_id)
    return Command(update={"messages": [ToolMessage(answer, tool_call_id=tool_call_id)]})


TOOLS = [
    answer_from_literature,
    find_research_gaps,
    create_technical_plan,
    create_teaching_plan,
    create_course,
    create_lab_exercises,
    create_experiments,
    evaluate_student_submission,
    check_topic_relevance,
    explore_adjacent_fields,
    summarize_progress,
    search_personal_documents,
]


# =============================================================================
# INTENT CLASSIFICATION GATE
# Runs BEFORE the tool-calling loop is reachable. Cheap Gemini call (no
# tools bound), matching the project's existing "route cheap/simple tasks
# to Gemini" convention (§2.11). This is the code-level enforcement that
# stops idea-introduction / general-chat turns from ever reaching a tool.
# =============================================================================

_INTENT_SCHEMA_INSTRUCTIONS = """Return ONLY valid JSON, no markdown fences, in this exact shape:
{
  "intent": "idea_introduction" | "general_chat" | "action_request" | "info_question",
  "idea": "concise restatement of the project idea if one is present in the conversation, else null",
  "direct_reply": "a natural reply to send the user, ONLY if intent is idea_introduction or general_chat, else null"
}

Definitions:
- "idea_introduction": the user is introducing, describing, or mentioning a project/learning idea/topic WITHOUT explicitly asking for a specific deliverable (no request for a plan, course, gap list, experiments, comparison, relevance check, etc). This includes the very first mention of an idea, and casual elaboration on an idea already mentioned.
- "general_chat": greetings, thanks, small talk, or questions unrelated to any research/education pipeline.
- "action_request": the user explicitly asks for a specific deliverable to be generated or an explicit pipeline step to run (e.g. "generate a technical plan", "find research gaps", "build me a course", "create lab exercises", "design experiments", "check if this idea is niche", "evaluate this submission").
- "info_question": the user asks a factual/informational question that likely requires checking the literature, paper analysis, or their uploaded personal documents to answer well (e.g. "has X metric been used before for this?", "what approaches are common for this?", "what did my uploaded document say about Y?"), WITHOUT explicitly asking for a plan/course/gap-list/experiment-set as a deliverable.

For "idea_introduction", "direct_reply" MUST: (1) briefly restate your understanding of the idea in one sentence, (2) list the concrete things you can do next — literature search & gap analysis, a technical implementation plan, a teaching plan / full course, lab exercises, experiment design, or comparing existing approaches — (3) ask what they'd like to do. Do NOT perform any of these things yet, only offer them.

For "general_chat", give a short, normal conversational reply as "direct_reply".

For "action_request" and "info_question", set "direct_reply" to null — a tool-using step handles it next."""


def _classify_intent(state: dict) -> dict:
    history = state.get("messages", [])[-8:]
    convo_lines = []
    for m in history:
        content = getattr(m, "content", "")
        if isinstance(content, list):
            content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
        if content:
            role = getattr(m, "type", "user")
            convo_lines.append(f"{role}: {content}")
    convo_text = "\n".join(convo_lines) or "(no prior messages)"

    known_idea = state.get("idea") or "none set yet"

    prompt = f"""You are the intent-routing layer for a research-to-education assistant.

Known idea so far (if any): {known_idea}

Recent conversation:
{convo_text}

{_INTENT_SCHEMA_INSTRUCTIONS}
"""
    gemini_llm, _ = _ensure_llm_clients()
    raw = gemini_llm.invoke(prompt).content
    if isinstance(raw, list):
        raw = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in raw)
    parsed = _safe_json_parse(raw)

    if not parsed or "intent" not in parsed:
        # Fail open toward the tool loop rather than getting stuck — an
        # unparseable classification shouldn't block the user's turn, and
        # the tool-bound agent's own judgment is the fallback here, not a
        # silent no-op.
        return {"intent": "action_request", "idea": None, "direct_reply": None}
    return parsed


def classify_node(state: OrchestratorState) -> dict:
    result = _classify_intent(state)
    update: dict = {}

    if result.get("idea"):
        update["idea"] = result["idea"]

    if result.get("intent") in ("idea_introduction", "general_chat") and result.get("direct_reply"):
        update["messages"] = [AIMessage(content=result["direct_reply"])]
        update["_route"] = "end"
    else:
        update["_route"] = "tools"

    return update


def _route_after_classify(state: OrchestratorState) -> str:
    return "agent" if state.get("_route") == "tools" else "end"


# =============================================================================
# TOOL-CALLING AGENT NODE
# Only reachable when classify_node has already routed here.
# =============================================================================

SYSTEM_PROMPT = """You are the conversational assistant for ConsiliAI, a
Research-to-Education Transfer Assistant. You help students, researchers,
and instructors turn a project idea into: research gaps, a technical
project plan, a teaching plan, a full course with slides, lab exercises,
suggested experiments, and benchmark evaluation of student results.

You are only invoked when the user has either asked an informational
question about the literature, or explicitly requested a specific
deliverable — a prior step has already filtered out plain idea
introductions and small talk, so you do not need to re-check that.

Guidelines:
- For requests asking about "contributions", "novelty", "gaps", or "what does my project offer" regarding an uploaded document or paper:
  1. Call search_personal_documents FIRST to extract the user's project idea, proposed methodology, and objectives from their uploaded document.
  2. Call find_research_gaps (or create_technical_plan) using the extracted project idea to search published literature (arXiv, Semantic Scholar, OpenAlex) and detect actual research gaps comparing published papers against the user's project.
  3. Synthesize the response by combining the user's uploaded project text with the literature gap analysis to highlight true novel contributions!
- For direct factual questions specifically about what a user's uploaded document says, call search_personal_documents.
- For general factual/informational questions about public published literature, call answer_from_literature.
- Do NOT call create_technical_plan, create_teaching_plan, create_course, create_lab_exercises, or create_experiments for a basic question unless explicitly requested.
- Tools are self-sufficient: e.g. create_course will build the teaching plan itself if it doesn't exist yet.
- Prefer calling summarize_progress over re-running a tool if you're unsure whether something has already been generated for the current idea.
- Only call explore_adjacent_fields after check_topic_relevance has reported no direct match AND the user has confirmed they want that.
- Keep replies conversational and concise; tool results are already summarized for you, don't dump raw JSON back at the user."""

_llm_with_tools = None


def _get_llm_with_tools():
    """Bind tools to each underlying chat model FIRST, then wrap the
    fallback around the two already tool-bound runnables. `.bind_tools()`
    is only implemented on actual chat-model classes — calling it on a
    `RunnableWithFallbacks` (i.e. binding after wrapping) does not work."""
    global _llm_with_tools
    if _llm_with_tools is None:
        gemini_llm, groq_llm = _ensure_llm_clients()
        groq_with_tools = groq_llm.bind_tools(TOOLS)
        gemini_with_tools = gemini_llm.bind_tools(TOOLS)
        _llm_with_tools = groq_with_tools.with_fallbacks([gemini_with_tools])
    return _llm_with_tools


def agent_node(state: OrchestratorState) -> dict:
    llm_with_tools = _get_llm_with_tools()
    idea_note = f"\n\nCurrent known idea for this conversation: {state['idea']}" if state.get("idea") else ""
    system_msg = SystemMessage(content=SYSTEM_PROMPT + idea_note)

    non_system_messages = [m for m in state["messages"] if not isinstance(m, SystemMessage)]
    response = llm_with_tools.invoke([system_msg] + non_system_messages)
    return {"messages": [response]}


# =============================================================================
# GRAPH ASSEMBLY
# =============================================================================

_checkpointer_cm = None

def _build_checkpointer():
    global _checkpointer_cm

    db_uri = os.getenv("DATABASE_URL_SYNC")
    if not db_uri:
        raise ValueError("DATABASE_URL_SYNC is not set")

    from langgraph.checkpoint.postgres import PostgresSaver

    _checkpointer_cm = PostgresSaver.from_conn_string(db_uri)
    checkpointer = _checkpointer_cm.__enter__()
    checkpointer.setup()
    return checkpointer


_checkpointer = _build_checkpointer()
_graph = None


def _build_graph():
    global _graph
    if _graph is None:
        builder = StateGraph(OrchestratorState)
        builder.add_node("classify", classify_node)
        builder.add_node("agent", agent_node)
        builder.add_node("tools", ToolNode(TOOLS))

        builder.add_edge(START, "classify")
        builder.add_conditional_edges(
            "classify",
            _route_after_classify,
            {"agent": "agent", "end": END},
        )
        builder.add_conditional_edges("agent", tools_condition)
        builder.add_edge("tools", "agent")

        _graph = builder.compile(checkpointer=_checkpointer)
    return _graph


def run_orchestrator_turn(message: str, thread_id: str = "default") -> str:
    """Single entry point for main.py's /chat endpoint. Runs one user turn
    through the graph (classify -> maybe agent/tools loop), persists state
    under `thread_id` via the checkpointer, and returns the assistant's
    final text reply."""
    graph = _build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"messages": [{"role": "user", "content": message}]}, config=config)

    final_message = result["messages"][-1]
    content = final_message.content
    if isinstance(content, list):
        content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return content


def get_state_snapshot(thread_id: str = "default") -> dict:
    """Debug/inspection helper: returns the current stored state for a
    thread without invoking the graph."""
    graph = _build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    return dict(snapshot.values) if snapshot else {}