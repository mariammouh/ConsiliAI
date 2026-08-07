from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os, shutil
import requests
from dotenv import load_dotenv
from ingestion.pdf_processor import process_pdf, UPLOAD_DIR
from agents.tools import _hash_text, retrieve_from_knowledge_base,broaden_idea,get_papers_with_analysis
from agents.tools import search_papers, filter_relevant_papers,filter_papers_hybrid, summarize_papers_with_groq
from agents.tools import search_papers_formatted,fetch_full_text,extract_text_from_pdf_bytes
load_dotenv()

app = FastAPI()
import tempfile
import os

def get_pptx_output_path(idea: str) -> str:
    """Cross-platform temp path for generated course pptx files."""
    output_dir = os.path.join(tempfile.gettempdir(), "consiliai_courses")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"course_{_hash_text(idea)[:8]}.pptx"
    return os.path.join(output_dir, filename)
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    num_chunks = process_pdf(file_path)
    return {"message": f"✅ {file.filename} uploaded and indexed.", "chunks": num_chunks}

@app.post("/ask")
async def ask_question(question: str = Form(...)):
    answer = retrieve_from_knowledge_base(question)
    return {"answer": answer}

# Optional: keep debug endpoint
@app.post("/debug_chunks")
async def debug_chunks(question: str = Form(...)):
    from ingestion.chroma_client import query_chroma
    chunks = query_chroma(question)
    return {"chunks": chunks}


@app.post("/search")
async def search_papers_endpoint(query: str = Form(...)):
    result = search_papers_formatted(query)
    return {"result": result}

@app.post("/smart_search")
async def smart_search(idea: str = Form(...)):
    # 1. Retrieve (cache or fresh)
    raw_papers = search_papers(idea, max_results=20)   # get more for filtering
    if not raw_papers:
        return {"summary": "No papers found."}
    
    # 2. Hybrid filter (embedding + LLM)
    relevant = filter_papers_hybrid(raw_papers, idea, embed_top_k=10, llm_top_n=5)
    
    # 3. Summarize with Groq
    summary = summarize_papers_with_groq(relevant)
    
    return {
        "summary": summary,
        "papers_used": [{"title": p["title"], "url": p["url"]} for p in relevant]
    }
@app.get("/history")
async def search_history():
    conn = sqlite3.connect("research_cache.db")
    rows = conn.execute("SELECT query, timestamp FROM search_cache ORDER BY timestamp DESC").fetchall()
    conn.close()
    return [{"query": r[0], "date": datetime.fromtimestamp(r[1]).isoformat()} for r in rows]
from agents.tools import search_similar_projects, compute_similarity_scores, analyze_novelty,diversify_top

@app.post("/similar")
async def similar_projects_endpoint(idea: str = Form(...)):
    projects = search_similar_projects(idea, max_results=20)
    scored = compute_similarity_scores(idea, projects)
    top = scored   # list of (score, proj) tuples

    # Apply diversity if you want (explained below)
    # top = diversify_top(scored, max_results=5)

    novelty = analyze_novelty(idea, top)

    top_matches = []
    for item in top:
        if isinstance(item, tuple) and len(item) == 2:
            score, proj = item
        else:
            proj = item
            score = 0.5
        top_matches.append({
            "score": round(score * 100, 1),
            "name": proj["name"],
            "url": proj["url"],
            "source": proj["source"]
        })

    return {
        "novelty_analysis": novelty,
        "top_matches": top_matches
    }

""" from agents.orchestrator import executor

@app.post("/chat")
async def chat_endpoint(message: str = Form(...)):
    result = executor.invoke({"input": message})
    return {"reply": result["output"]}
     """
from agents.tools import split_paper_sections, analyze_all_sections
import os
import fitz  # PyMuPDF
import re
@app.post("/analyze_paper")
async def analyze_paper_endpoint(file: UploadFile = File(...)):
    """
    Takes raw paper text (e.g. extracted from an uploaded PDF via PyMuPDF),
    splits it into sections, and runs the section-analysis agent on each.
    """
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        # 1. Extract text
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text("text")
    doc.close()

    # Basic cleaning
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    text = "\n".join(lines)
    if not text.strip():
        return 0
    sections = split_paper_sections(text)
    if not sections:
        return {"error": "Could not detect any sections in the provided text."}

    analysis = analyze_all_sections(sections)
    return {
        "sections_detected": list(sections.keys()),
        "analysis": analysis
    }
import tempfile

def arxiv_url_to_pdf_url(url: str) -> str:
    """Convert an arXiv abstract URL to its PDF URL."""
    # e.g. https://arxiv.org/abs/2501.09635 -> https://arxiv.org/pdf/2501.09635
    return url.replace("/abs/", "/pdf/")


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text("text")
    doc.close()
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]

    return "\n".join(lines)


@app.post("/test_search_and_analyze")
async def test_search_and_analyze(idea: str = Form(...), max_papers: int = Form(1)):
    """
    TEMPORARY test endpoint: search across all sources, try to fetch full
    text for each paper (arXiv/Semantic Scholar/OpenAlex via pdf_url),
    and run section analysis. Falls back to abstract-only summary when
    no full text is available.
    """
    raw_papers = search_papers(idea, max_results=10)[:max_papers]
    if not raw_papers:
        return {"error": "No papers found for this query."}

    results = []
    for paper in raw_papers:
        full_text = fetch_full_text(paper)

        if not full_text.strip():
            results.append({
                "title": paper["title"],
                "url": paper["url"],
                "source": paper["source"],
                "note": "No full text available (no open-access PDF); analyzed abstract only.",
                "analysis": {"abstract": {"summary": paper.get("abstract", "")}}
            })
            continue

        sections = split_paper_sections(full_text)
        if not sections:
            results.append({
                "title": paper["title"],
                "url": paper["url"],
                "source": paper["source"],
                "error": "PDF fetched but no sections could be detected."
            })
            continue

        analysis = analyze_all_sections(sections)
        results.append({
            "title": paper["title"],
            "url": paper["url"],
            "source": paper["source"],
            "sections_detected": list(sections.keys()),
            "analysis": analysis
        })

    return {"results": results}
from agents.tools import detect_gaps

@app.post("/gaps")
async def gaps_endpoint(idea: str = Form(...), max_papers: int = Form(3)):
    """
    Full pipeline: search -> filter -> fetch full text -> split -> analyze -> detect gaps.
    """
    papers_with_analysis = get_papers_with_analysis(idea, max_papers)
    result = detect_gaps(idea, papers_with_analysis) if papers_with_analysis else {"gaps": []}

    result["papers_used"] = [p["title"] for p in papers_with_analysis]
    return result
from agents.tools import generate_technical_plan, search_similar_projects, compute_similarity_scores

@app.post("/technical_plan")
async def technical_plan_endpoint(idea: str = Form(...), max_papers: int = Form(2)):
    # Reuse the same paper analysis pipeline as /gaps
    papers_with_analysis = get_papers_with_analysis(idea, max_papers)
    gaps_result = detect_gaps(idea, papers_with_analysis) if papers_with_analysis else {"gaps": []}

    similar = search_similar_projects(idea, max_results=15)
    scored_similar = compute_similarity_scores(idea, similar)
    #top_similar = [proj for p, proj in scored_similar[:8]]
    top_similar=scored_similar[:8]
    novelty = analyze_novelty(idea, top_similar)  

    plan = generate_technical_plan(idea, gaps_result.get("gaps", []), top_similar, novelty_analysis=novelty)

    return {
        "plan": plan,
        "novelty_analysis": novelty,
        "gaps_used": gaps_result.get("gaps", []),
        "similar_projects_used": [proj["name"] for score, proj in top_similar]
    }

from agents.tools import generate_teaching_plan

@app.post("/teaching_plan")
async def teaching_plan_endpoint(idea: str = Form(...), max_papers: int = Form(2)):
    # Same pipeline as /gaps and /technical_plan
    papers_with_analysis = get_papers_with_analysis(idea, max_papers)
    gaps_result = detect_gaps(idea, papers_with_analysis) if papers_with_analysis else {"gaps": []}

    plan = generate_teaching_plan(idea, gaps_result.get("gaps", []), papers_with_analysis)

    return {
        "teaching_plan": plan,
        "gaps_used": gaps_result.get("gaps", []),
        "papers_used": [p["title"] for p in papers_with_analysis]
    }


@app.post("/check_relevance")
async def check_relevance_endpoint(idea: str = Form(...), relevance_threshold: float = Form(0.30)):
    """
    First step: check if direct literature exists for this idea.
    If not, return a prompt asking whether to explore adjacent fields,
    rather than silently proceeding or failing.
    """
    raw_papers = search_papers(idea, max_results=15)
    scored_papers = filter_papers_hybrid(raw_papers, idea, embed_top_k=8, llm_top_n=5, return_scores=True)
    direct_relevant = [(s, p) for s, p in scored_papers if s >= relevance_threshold]

    if direct_relevant:
        return {
            "status": "relevant_found",
            "papers_found": len(direct_relevant)
        }

    return {
        "status": "no_direct_match",
        "message": "No directly relevant literature was found for this idea.",
        "suggestion": "Would you like to explore adjacent fields for this idea?"
    }


@app.post("/explore_niche")
async def explore_niche_endpoint(idea: str = Form(...)):
    """
    Second step: only called if the user explicitly confirms they want
    to explore adjacent fields after /check_relevance returned no_direct_match.
    """
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

    return {
        "honest_assessment": broadening.get("honest_assessment", ""),
        "core_concepts": broadening.get("core_concepts", []),
        "adjacent_fields": broadening.get("adjacent_fields", []),
        "papers_found": [{"title": p["title"], "matched_via": p.get("matched_via_query")} for p in analogous_papers],
        "_papers_for_downstream": analogous_papers  # pass to /gaps or /teaching_plan if user proceeds
    }


from agents.tools import generate_course, export_course_to_pptx_per_lesson,export_course_to_pptx, generate_teaching_plan

@app.post("/generate_course")
async def generate_course_endpoint(idea: str = Form(...), max_papers: int = Form(3), split_by_lesson: bool = Form(False)):
    papers_with_analysis = get_papers_with_analysis(idea, max_papers)
    if not papers_with_analysis:
        return {"error": "No papers could be analyzed for this idea."}

    gaps_result = detect_gaps(idea, papers_with_analysis)
    teaching_plan = generate_teaching_plan(idea, gaps_result.get("gaps", []), papers_with_analysis)
    course = generate_course(teaching_plan, papers_with_analysis)

    single_path = get_pptx_output_path(idea)
    output_dir = os.path.join(tempfile.gettempdir(), "consiliai_courses")
    if split_by_lesson:
        paths = export_course_to_pptx_per_lesson(course, output_dir)
        return {"course": course, "lesson_files": paths}
    else:
        path = export_course_to_pptx(course, single_path)
        return {"course": course, "download_url": path}

from fastapi.responses import FileResponse

@app.get("/download_course/{idea_hash}")
async def download_course(idea_hash: str):
    output_dir = os.path.join(tempfile.gettempdir(), "consiliai_courses")
    filepath = os.path.join(output_dir, f"{idea_hash}.pptx")
    if not os.path.exists(filepath):
        return {"error": "File not found."}
    return FileResponse(filepath, filename=f"{idea_hash}.pptx",
                         media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")


@app.get("/download_lab/{idea_hash}")
async def download_course(idea_hash: str):
    output_dir = os.path.join(tempfile.gettempdir(), "consiliai_labs", "06b43f13")
    #06b43f13
    filepath = os.path.join(output_dir, f"{idea_hash}.ipynb")
    print(f"Looking for lab file at: {filepath}")
    if not os.path.exists(filepath):
        return {"error": "File not found."}
    return FileResponse(filepath, filename=f"{idea_hash}.ipynb",
                         media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")



from agents.tools import (
    generate_lab_exercise,
    export_lab_to_notebook,
    search_similar_projects,
    compute_similarity_scores,
)
import re as _re
 
 
def _slug(text: str, max_len: int = 50) -> str:
    """Simple filename-safe slug — same word-boundary-truncation fix already
    flagged as pending for the PPTX per-lesson exporter, applied here from
    the start rather than inheriting the same bug."""
    slug = _re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    if len(slug) <= max_len:
        return slug or "lesson"
    truncated = slug[:max_len]
    return truncated.rsplit("_", 1)[0] if "_" in truncated else truncated
 
 
@app.post("/generate_lab")
async def generate_lab_endpoint(
    idea: str = Form(...),
    max_papers: int = Form(3),
    generate_code: bool = Form(True),
    export_notebooks: bool = Form(True),
):
    """
    Full pipeline: search -> filter -> analyze -> gaps -> teaching_plan ->
    course -> one lab exercise per lesson.
 
    generate_code=False gives a fast preview (Groq scaffolds only, no Qwen
    calls, no notebooks) so you can sanity-check exercise framing before
    spending time on code generation.
    """
    papers_with_analysis = get_papers_with_analysis(idea, max_papers)
    if not papers_with_analysis:
        return {"error": "No papers could be analyzed for this idea."}
 
    gaps_result = detect_gaps(idea, papers_with_analysis)
    teaching_plan = generate_teaching_plan(idea, gaps_result.get("gaps", []), papers_with_analysis)
    course = generate_course(teaching_plan, papers_with_analysis)
 
    # One similar-projects search per idea, reused across all modules/lessons —
    # same simplification as Technical Plan Agent's global relevance gate.
    # Known limitation: a single idea-level search may not surface the best
    # matched repo for every individual module's specific technique.
    similar = search_similar_projects(idea, max_results=15)
    scored_similar = compute_similarity_scores(idea, similar)
 
    output_dir = os.path.join(tempfile.gettempdir(), "consiliai_labs", _hash_text(idea)[:8])
 
    modules_output = []
    for tp_module, course_module in zip(teaching_plan.get("modules", []), course.get("modules", [])):
        lessons_output = []
        for lesson in course_module.get("lessons", []):
            try:
                lab = generate_lab_exercise(
                    lesson=lesson,
                    module=tp_module,
                    papers_with_analysis=papers_with_analysis,
                    similar_projects_scored=scored_similar,
                    generate_code=generate_code,
                )
            except Exception as e:
                print(f"[generate_lab] failed for lesson '{lesson.get('lesson_title','')}': {e}")
                lab = {"_error": str(e)}
 
            notebook_paths = None
            if export_notebooks and generate_code and not lab.get("_error"):
                filename_base = _slug(f"{tp_module.get('title','')}_{lesson.get('lesson_title','')}")
                try:
                    notebook_paths = export_lab_to_notebook(lab, output_dir, filename_base)
                except Exception as e:
                    print(f"[generate_lab] notebook export failed for '{filename_base}': {e}")
 
            lessons_output.append({"lab": lab, "notebook_files": notebook_paths})
 
        modules_output.append({
            "module_title": tp_module.get("title", ""),
            "lessons": lessons_output,
        })
 
    return {
        "idea": idea,
        "modules": modules_output,
        "papers_used": [p["title"] for p in papers_with_analysis],
    }