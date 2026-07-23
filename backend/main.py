from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os, shutil
import requests
from dotenv import load_dotenv
from ingestion.pdf_processor import process_pdf, UPLOAD_DIR
from agents.tools import retrieve_from_knowledge_base
from agents.tools import search_papers, filter_relevant_papers,filter_papers_hybrid, summarize_papers_with_groq
from agents.tools import search_papers_formatted
load_dotenv()

app = FastAPI()

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
    TEMPORARY test endpoint: search for papers on the idea, download the
    first N arXiv results as PDFs, extract text, and run section analysis
    on each. Non-arXiv sources are skipped since they don't reliably
    expose a direct PDF link.
    """
    raw_papers = search_papers(idea, max_results=10)
    arxiv_papers = [p for p in raw_papers if p.get("source") == "arxiv"][:max_papers]

    if not arxiv_papers:
        return {"error": "No arXiv papers found for this query."}

    results = []
    for paper in arxiv_papers:
        pdf_url = arxiv_url_to_pdf_url(paper["url"])
        try:
            resp = requests.get(pdf_url, timeout=20)
            resp.raise_for_status()
            text = extract_text_from_pdf_bytes(resp.content)
        except Exception as e:
            results.append({"title": paper["title"], "error": f"Failed to fetch/extract PDF: {e}"})
            continue

        if not text.strip():
            results.append({"title": paper["title"], "error": "No text extracted from PDF."})
            continue

        print(f"Analyzing paper: {paper['title']} ({len(text)} characters of text)")
        with open("extracted_text.txt", "w", encoding="utf-8") as f:
            f.write(text)
        
        #return {"text": "just a debug"}
        sections = split_paper_sections(text)
        if not sections:
            results.append({"title": paper["title"], "error": "Could not detect sections."})
            continue

        analysis = analyze_all_sections(sections)
        results.append({
            "title": paper["title"],
            "url": paper["url"],
            "sections_detected": list(sections.keys()),
            "analysis": analysis
        })

    return {"results": results}