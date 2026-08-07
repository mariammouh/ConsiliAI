import os
import sys
import requests
import time
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
for path in [str(BACKEND_DIR), str(REPO_ROOT)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from ingestion.chroma_client import query_chroma
from ingestion.cache import get_cached_papers, set_cached_papers
import arxiv
from ingestion.chroma_client import cache_collection,analysis_cache_collection
from ingestion.embedding_model import embed
import json
import base64

import numpy as np
load_dotenv()

from course_pptx_exporter import (
    TOKENS,
    ContentSplitter,
    build_title_slide,
    build_objectives_slide,
    build_context_slide,
    build_divider_slide,
    build_content_slide,
    build_example_slide,
    build_key_terms_slide,
    build_summary_slide,
    build_quiz_slide,
    build_references_slide,
    build_closing_slide,
    export_course_to_pptx_per_lesson as _reference_export_course_to_pptx_per_lesson,
)
#from langchain_community.chat_models import ChatOllama  # or langchain_ollama

#_ollama_llm = ChatOllama(model="llama3.1:8b", temperature=0.2)
# LLM instance for this tool (can be reused)
def _get_gemini_llm():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY/GOOGLE_API_KEY is not configured")
    return ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=api_key,
        temperature=0,
        timeout=60,        
    )


def _get_groq_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured")
    return ChatOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        timeout=60,        
        max_retries=1,      
    )


_gemini_llm = None
_groq_llm = None


def _ensure_llm_clients():
    global _gemini_llm, _groq_llm
    if _gemini_llm is None:
        _gemini_llm = _get_gemini_llm()
    if _groq_llm is None:
        _groq_llm = _get_groq_llm()
    return _gemini_llm, _groq_llm


def _invoke_gemini(prompt: str):
    gemini_llm = _ensure_llm_clients()[0]
    return gemini_llm.invoke(prompt)


def _invoke_groq(prompt: str):
    groq_llm = _ensure_llm_clients()[1]
    return groq_llm.invoke(prompt)
def retrieve_from_knowledge_base(question: str) -> str:
    """
    Retrieve relevant information from the user's uploaded PDFs
    and answer the question.
    """
    chunks = query_chroma(question, n_results=3)
    if not chunks:
        return "No relevant documents found."

    context = "\n\n".join(chunks)
    prompt = f"""You are a helpful research assistant. Use the context below to answer the question. If the context doesn't contain the answer, say you don't know.

Context:
{context}

Question: {question}
Answer:"""

    response = _invoke_gemini(prompt)
    # Extract clean text
    content = response.content
    if isinstance(content, list):
        content = "".join(block.get('text', '') if isinstance(block, dict) else str(block) for block in content)
    return content
def set_cached_papers_semantic(query: str, papers: List[Dict]):
    query_embedding = embed(query)
    metadata = {
        "papers": json.dumps(papers),
        "timestamp": time.time()          # store current time
    }
    cache_collection.delete(ids=[query])   # remove old entry
    cache_collection.add(
        documents=[query],
        embeddings=[query_embedding],
        metadatas=[metadata],
        ids=[query]
    )

def get_cached_papers_combined(query: str, similarity_threshold: float = 0.95) -> List[Dict] | None:
    """
    Combine exact match and semantic similarity cache.
    No freshness check – any cached result is used.
    Returns a list of deduplicated papers, or None if nothing is cached.
    """
    collected_papers = []

    # 1. Exact match
    exact = cache_collection.get(ids=[query])
    if exact and exact['metadatas']:
        meta = exact['metadatas'][0]
        collected_papers.extend(json.loads(meta.get('papers', '[]')))

    # 2. Semantic similarity (top 3)
    query_embedding = embed(query)
    results = cache_collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )
    if results['ids'] and results['ids'][0]:
        for i, doc_id in enumerate(results['ids'][0]):
            if doc_id == query:
                continue  # déjà traité en exact match
            distance = results['distances'][0][i]
            if 1 - distance >= similarity_threshold:
                meta = results['metadatas'][0][i]
                collected_papers.extend(json.loads(meta.get('papers', '[]')))

    # Déduplication (par URL ou titre)
    seen_urls = set()
    unique = []
    for p in collected_papers:
        url = p.get('url') or ''
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(p)
        elif not url:
            title = p.get('title', '')
            if title not in seen_urls:
                seen_urls.add(title)
                unique.append(p)
    return unique if unique else None

def search_papers(query: str, max_results: int = 15) -> List[Dict]:
    # 1. Check combined cache
    cached = get_cached_papers_combined(query)
    if cached and len(cached) >= max_results:
        return cached[:max_results]

    # 2. Use whatever cache we have as a base
    base_papers = cached if cached else []
    
    # 3. Fetch fresh from APIs
    fresh_papers = []

    # --- arXiv ---
    try:
        client = arxiv.Client()
        search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
        for result in client.results(search):
            fresh_papers.append({
                "title": result.title,
                "authors": [a.name for a in result.authors],
                "abstract": result.summary,
                "url": result.entry_id,
                "pdf_url": result.pdf_url,   # arxiv library gives this directly
                "source": "arxiv"
            })
    except Exception as e:
        print(f"arXiv search error: {e}")

    # --- Semantic Scholar ---
    try:
        semantic_papers = search_semantic_scholar(query, max_results)
        fresh_papers.extend(semantic_papers)
    except Exception as e:
        print(f"Semantic Scholar error: {e}")

    # --- OpenAlex ---
    try:
        openalex_papers = search_openalex(query, max_results)
        fresh_papers.extend(openalex_papers)
    except Exception as e:
        print(f"OpenAlex integration error: {e}")

    # 4. Merge cache + fresh, deduplicate by URL
    seen = {p.get('url') for p in base_papers if p.get('url')}
    combined = list(base_papers)
    for p in fresh_papers:
        if p.get('url') not in seen:
            seen.add(p.get('url'))
            combined.append(p)

    # 5. Update cache with the combined list
    if combined:
        set_cached_papers_semantic(query, combined)

    return combined[:max_results]
def search_semantic_scholar(query: str, max_results: int = 5) -> List[Dict]:
    # --- Semantic Scholar (updated fields) ---
        ss_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        headers = {"x-api-key": ss_api_key} if ss_api_key else {}
    
        ss_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,authors,abstract,url,openAccessPdf"
        }
        resp = requests.get(ss_url, params=params, headers=headers)
        if resp.status_code == 429:
            time.sleep(2)
            resp = requests.get(ss_url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        fresh_papers= []
        for paper in data.get("data", []):
            oa_pdf = paper.get("openAccessPdf") or {}
            fresh_papers.append({
                "title": paper.get("title", "N/A"),
                "authors": [a["name"] for a in paper.get("authors", [])],
                "abstract": paper.get("abstract", "No abstract available."),
                "url": paper.get("url", ""),
                "pdf_url": oa_pdf.get("url", ""),   # NEW
                "source": "semantic_scholar"
            })
        return fresh_papers
    

def filter_papers_hybrid(papers: List[Dict], user_idea: str, embed_top_k: int = 10, llm_top_n: int = 10, return_scores=False) -> List[Dict]:
    if not papers:
        return []

    idea_emb = np.array(embed(user_idea))
    scored = []
    for p in papers:
        text = p['title'] + " " + (p['abstract'] or "")
        paper_emb = np.array(embed(text))
        sim = np.dot(idea_emb, paper_emb) / (np.linalg.norm(idea_emb) * np.linalg.norm(paper_emb))
        scored.append((sim, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    pre_filtered = [p for _, p in scored[:embed_top_k]]

    papers_text = "\n\n".join(
        f"Paper {i+1}:\nTitle: {p['title']}\nAbstract: {(p['abstract'] or '')[:500]}"
        for i, p in enumerate(pre_filtered)
    )
    prompt = f"""User's project idea: "{user_idea}"

Below are {len(pre_filtered)} papers pre‑selected by semantic similarity. From these, choose exactly the {llm_top_n} most directly relevant to the user's idea. Return ONLY their numbers, separated by commas (e.g., "2,5,7").

Papers:
{papers_text}"""

    content = _invoke_gemini(prompt).content
    if isinstance(content, list):
        content = "".join(b.get('text', '') if isinstance(b, dict) else str(b) for b in content)
    content = content.strip()

    numbers = re.findall(r'\d+', content)
    indices = [int(n) - 1 for n in numbers if 1 <= int(n) <= len(pre_filtered)]
    if not indices:
        indices = list(range(min(llm_top_n, len(pre_filtered))))
    selected = [pre_filtered[i] for i in indices[:llm_top_n]]
    if return_scores:
        score_map = {id(p): s for s, p in scored}
        return [(score_map.get(id(p), 0.0), p) for p in selected]
    return selected

def search_openalex(query: str, max_results: int = 5) -> List[Dict]:
    base_url = "https://api.openalex.org/works"
    params = {"q": f"title.search:{query.strip()}", "per_page": max_results}
    try:
        resp = requests.get(base_url, params=params)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"OpenAlex error: {e}")
        return []

    papers = []
    for work in data.get("results", []):
        abstract = work.get("abstract") or ""
        oa = work.get("open_access", {}) or {}
        best_oa_location = work.get("best_oa_location") or {}
        pdf_url = best_oa_location.get("pdf_url") or oa.get("oa_url") or ""
        papers.append({
            "title": work.get("title", "N/A"),
            "authors": [a["author"]["display_name"] for a in work.get("authorships", [])],
            "abstract": abstract,
            "url": work.get("id", ""),
            "pdf_url": pdf_url,   # NEW
            "source": "openalex"
        })
    return papers



def search_papers_formatted(query: str, max_results: int = 5) -> str:
    papers = search_papers(query, max_results)
    if not papers:
        return "No papers found."
    output = []
    for i, p in enumerate(papers, 1):
        output.append(
            f"{i}. [{p['source'].upper()}] {p['title']}\n"
            f"   Authors: {', '.join(p['authors'])}\n"
            f"   Abstract: {p['abstract']}\n"
            f"   URL: {p['url']}\n"
        )
    return "\n".join(output)
def filter_relevant_papers(papers: List[Dict], user_idea: str, top_n: int = 5) -> List[Dict]:
    """
    Use Groq to keep only the top‑N papers most relevant to the user's project.
    """
    if not papers:
        return []

    # Prepare a compact representation for the LLM
    papers_text = "\n\n".join(
    f"Paper {i+1}:\nTitle: {p['title']}\nAbstract: {(p['abstract'] or '')[:500]}"
    for i, p in enumerate(papers)
)
    prompt = f"""User's project idea: "{user_idea}"

Below is a list of {len(papers)} papers. Identify the {top_n} papers that are **most directly relevant** to the user's idea. Return ONLY the numbers of the chosen papers, separated by commas, e.g., "2,5,7".

Papers:
{papers_text}"""

    content = _invoke_gemini(prompt).content
    if isinstance(content, list):
        content = "".join(b.get('text', '') if isinstance(b, dict) else str(b) for b in content)
    content = content.strip()


    import re
    numbers = re.findall(r'\d+', content)
    indices = [int(n) - 1 for n in numbers if 1 <= int(n) <= len(papers)]
    # Fallback: if parsing fails, return first top_n
    if not indices:
        indices = list(range(min(top_n, len(papers))))
    return [papers[i] for i in indices]


# ---------- SUMMARISATION AGENT (heavy) ----------
def summarize_papers_with_groq(papers: List[Dict]) -> str:
    """
    Use Groq (Llama 3.1 70B) to produce a structured literature summary from the filtered papers.
    """
    if not papers:
        return "No papers to summarize."

    papers_text = "\n\n".join(
        f"Paper {i+1}:\nTitle: {p['title']}\nAbstract: {(p['abstract'] or '')}"
        for i, p in enumerate(papers)
    )
    prompt = f"""You are a research assistant. Given the following papers, write a structured summary (max 300 words) covering:
- Key methods used (mention specific models like CNN, ViT, etc. if present)
- Main findings
- Gaps or limitations
- How these papers relate to each other

Papers:
{papers_text}

Summary:"""

    response = _groq_invoke_safe(prompt)
    content = response.content
    if isinstance(content, list):
        content = "".join(block.get('text', '') if isinstance(block, dict) else str(block) for block in content)
    return content
def get_cached_projects_semantic(query: str, threshold: float = 0.95) -> List[Dict] | None:
    """
    Try exact match, then semantic similarity for project queries.
    """
    # Exact match
    exact = cache_collection.get(ids=[query])
    if exact and exact['metadatas']:
        return json.loads(exact['metadatas'][0].get('projects', '[]'))

    # Semantic
    query_emb = embed(query)
    results = cache_collection.query(query_embeddings=[query_emb], n_results=1)
    if results['distances'] and results['distances'][0]:
        dist = results['distances'][0][0]
        if 1 - dist >= threshold:
            return json.loads(results['metadatas'][0][0].get('projects', '[]'))
    return None


def set_cached_projects_semantic(query: str, projects: List[Dict]):
    query_emb = embed(query)
    cache_collection.delete(ids=[query])  # remove old
    cache_collection.add(
        documents=[query],
        embeddings=[query_emb],
        metadatas=[{"projects": json.dumps(projects)}],
        ids=[query]
    )
# ---------- SIMILAR PROJECTS AGENT (GitHub + Hugging Face) ----------
import requests
from typing import List, Dict, Tuple

def search_similar_projects(query: str, max_results: int = 15) -> List[Dict]:
    """
    Search GitHub and Hugging Face for repositories/spaces matching the query.
    Returns a list of projects with name, description, url, source, and readme text.
    """
    # Check cache first
    cached = get_cached_projects_semantic(query)
    if cached:
        return cached[:max_results]

    projects = []

    projects.extend(search_github(query, max_results))
    projects.extend(search_huggingface(query, max_results)) 
    projects.extend(search_kaggle(query, max_results))
    projects.extend(search_gitlab(query, max_results))
    
    #projects.extend(search_bitbucket(query, max_results))
    #projects.extend(search_paperswithcode(query, max_results))
    for p in projects:
        print(f"[debug] {p.get('name')}: readme={p.get('readme', '')[:200]!r}")
    if projects:
        set_cached_projects_semantic(query, projects)

    return projects[:max_results]


def compute_similarity_scores(user_idea: str, projects: List[Dict]) -> List[Tuple[float, Dict]]:
    """
    Compute cosine similarity between user idea embedding and each project's text representation.
    Returns a list of (score, project) sorted descending.
    """
    if not projects:
        return []
    idea_emb = np.array(embed(user_idea))
    scored = []
    for proj in projects:
        # Combine description and readme for richer representation
        desc = proj.get("description") or ""
        readme = proj.get("readme") or ""
        lang = f"language:{proj['language']}" if "language" in proj else ""
        ktype = f"type:{proj['kernel_type']}" if "kernel_type" in proj else ""
        topics = " ".join(proj.get("topics", []))
        architecture = f"architecture:{proj['architecture']}" if "architecture" in proj else ""
        votes = f"votes:{proj['votes']}" if "votes" in proj else ""

        text = f"{desc} {readme} {lang} {ktype} {topics} {architecture} {votes}"




        if not text.strip():
            continue
        proj_emb = np.array(embed(text))
        sim = np.dot(idea_emb, proj_emb) / (np.linalg.norm(idea_emb) * np.linalg.norm(proj_emb))
        scored.append((sim, proj))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored

def analyze_novelty(user_idea: str, top_projects: List) -> str:
    """
    Accepts either a list of (score, project) tuples or a list of project dicts.
    """
    if not top_projects:
        return "No similar projects found."

    # Determine if we have scored tuples or plain dicts
    if isinstance(top_projects[0], tuple) and len(top_projects[0]) == 2:
        scores = [s for s, _ in top_projects]
        projects = [p for _, p in top_projects]
    else:
        # Assume plain dicts, assign a neutral score for analysis
        scores = [0.5] * len(top_projects)
        projects = top_projects

    avg_score = sum(scores) / len(scores)
    max_score = max(scores)
    basic_analysis = (
        f"Found {len(top_projects)} similar projects. "
        f"Highest similarity: {max_score:.1%}, average: {avg_score:.1%}. "
        "Your idea overlaps with existing work, but may still have unique aspects."
    )
    #for p in top_projects:
          #print(f"[debug] {p.get('name')}: readme={p.get('readme', '')[:200]!r}")
    # Build description text for the LLM
    projects_text = "\n".join(
        f"{i+1}. [{proj['source']}] {proj['name']} — {proj.get('description','')}"
        for i, proj in enumerate(projects)
    )

    prompt = f"""User's project idea: "{user_idea}"

The following existing projects were found to be similar (sorted by embedding similarity). Analyze the novelty of the user's idea. Is it overlapping significantly with existing work, or does it appear relatively unexplored? Give a concise assessment (2-3 sentences) and an estimated overlap percentage.

Existing projects:
{projects_text}

Novelty analysis:"""

    # Try Groq first, then Gemini, then basic
    try:
        response = _groq_invoke_safe(prompt)
        content = response.content
        if isinstance(content, list):
            content = "".join(block.get('text', '') if isinstance(block, dict) else str(block) for block in content)
        return content
    except Exception as e:
        print(f"Groq error ({e}), falling back to Gemini...")
        try:
            response = _invoke_gemini(prompt)
            content = response.content
            if isinstance(content, list):
                content = "".join(block.get('text', '') if isinstance(block, dict) else str(block) for block in content)
            return content
        except Exception as e2:
            print(f"Gemini also failed ({e2}). Returning basic analysis.")
            return basic_analysis
def search_kaggle(query: str, max_results: int =15 ) -> List[Dict]:
    """
    Search Kaggle for relevant datasets and notebooks.
    Requires KAGGLE_USERNAME and KAGGLE_KEY in .env.
    """
    import os
    from kaggle.api.kaggle_api_extended import KaggleApi

    projects = []
    try:
        api = KaggleApi()
        api.authenticate()  # uses env vars or ~/.kaggle/kaggle.json
        models = api.model_list(search=query, page_size=max_results)
        for m in models:
            
            projects.append({
                "name": m.title,
                "description": m.description or "",
                "url": f"https://www.kaggle.com/{m.ref}",
                "source": "kaggle_model",

                "readme": (m.description or "")[:500]
            })
            print(f"kaggle models: {len(projects)} results added")
        # --- Datasets ---
        datasets = api.dataset_list(search=query, max_size=max_results)
        for ds in datasets:
            projects.append({
                "name": str(ds),
                "description": ds.title,
                "url": f"https://www.kaggle.com/datasets/{ds.ref}",
                "source": "kaggle_dataset",
                #"file_count": ds.file_count,
                "size": ds.size,
                "tags": ds.tags,
                "readme": str(ds.description)[:500] if ds.description else ""
            })

        # --- Notebooks ---
        kernels = api.kernels_list(search=query, page_size=max_results)
        for k in kernels:
            projects.append({
                "name": k.title,
                "description": k.description or "",
                "url": f"https://www.kaggle.com/{k.ref}",
                "source": "kaggle_kernel",
                "readme": (k.description or "")[:500],
                 "language": k.language,
    "kernel_type": k.kernel_type,
    "votes": k.total_votes,
    "readme": (k.description or "")[:500] 
            })
            print(f"kaggle kernels: {len(projects)} results added")
        models = api.model_list(search=query, page_size=max_results)
        for m in models:
            
            projects.append({
                "name": m.title,
                "description": m.description or "",
                "url": f"https://www.kaggle.com/{m.ref}",
                "source": "kaggle_model",
                "readme": (m.description or "")[:500]
            })
            print(f"kaggle models: {len(projects)} results added")
    except Exception as e:
        print(f"Kaggle error: {e}")
    return projects

def search_github(query, max_results):
        # ---- GitHub ----
    projects = []
    github_token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    try:
        gh_url = "https://api.github.com/search/repositories"
        params = {"q": query, "per_page": max_results, "sort": "stars", "order": "desc"}
        resp = requests.get(gh_url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        for repo in data.get("items", []):
            # Get readme (if available)
            readme_url = f"https://api.github.com/repos/{repo['full_name']}/readme"
            readme_text = ""
            try:
                readme_resp = requests.get(readme_url, headers=headers)
                if readme_resp.status_code == 200:
                    import base64
                    readme_text = base64.b64decode(readme_resp.json()["content"]).decode("utf-8", errors="ignore")[:1000]
            except:
                pass
            projects.append({
                "name": repo["full_name"],
                "description": repo.get("description", ""),
                "url": repo["html_url"],
                "source": "github",
                "topics": repo.get("topics", []),
                "readme": readme_text
            })
            print(f"github: {len(projects)} results added")
    except Exception as e:
        print(f"GitHub error: {e}")
    return projects

def search_huggingface(query, max_results):
        
    projects = []
    # --- Hugging Face (Spaces + Models) ---
    try:
        from huggingface_hub import list_spaces, list_models
        # Search Spaces
        spaces = list_spaces(search=query, limit=max_results)
        for space in spaces:
            # Try to get README for richer embedding
            readme_text = ""
            try:
                from huggingface_hub import hf_hub_download
                path = hf_hub_download(repo_id=space.id, filename="README.md", repo_type="space")
                with open(path, "r", encoding="utf-8") as f:
                    readme_text = f.read()[:1000]
            except Exception:
                pass
            projects.append({
                "name": space.id,
                "description": space.tags if hasattr(space, "tags") else "",
                "url": f"https://huggingface.co/spaces/{space.id}",
                "source": "huggingface",
                "readme": readme_text
            })
        # Search Models (optional – adds more variety)
        models = list_models(search=query, limit=max_results)
        for model in models:
            projects.append({
                "name": model.id,
                "description": model.tags if hasattr(model, "tags") else "",
                "url": f"https://huggingface.co/{model.id}",
                "source": "huggingface_model",
                "architecture":model.config.architectures[0] if hasattr(model, "config") and hasattr(model.config, "architectures") else "",    
                "readme": ""   # Models don't have a README directly
            })
        print(f"Hugging Face: {len(projects)} results added")
    except Exception as e:
        print(f"Hugging Face error: {e}")
    return projects
def diversify_top(scored, max_results=20):

    from collections import OrderedDict
    source_picked = {}
    final = []
    # first pass: pick one best from each source
    for sim, proj in scored:
        src = proj["source"]
        if src not in source_picked:
            source_picked[src] = (sim, proj)
    final.extend([p for _, p in source_picked.values()])
    # second pass: fill remaining slots with highest that aren't already picked
    for sim, proj in scored:
        if proj not in final and len(final) < max_results:
            final.append(proj)
    return final[:max_results]
def search_paperswithcode(query: str, max_results: int = 5) -> List[Dict]:
    projects = []
    try:
        url = "https://paperswithcode.com/api/v1/papers/"
        params = {"q": query, "items_per_page": max_results}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"PapersWithCode status {resp.status_code}: {resp.text[:200]}")
            return projects
        # The response should now be JSON
        try:
            data = resp.json()
        except Exception as je:
            print(f"PapersWithCode JSON decode error: {je}, body was: {resp.text[:200]}")
            return projects
        for paper in data.get("results", []):
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
            repo_url = paper.get("repository_url", "")
            if repo_url:
                projects.append({
                    "name": title,
                    "description": abstract[:200],
                    "url": repo_url,
                    "source": "paperswithcode",
                    "readme": abstract[:1000]
                })
        print(f"PapersWithCode: {len(projects)} results added")
    except Exception as e:
        print(f"PapersWithCode error: {e}")
    return projects

def search_gitlab(query, max_results):
    projects = []
    try:
        gl_url = "https://gitlab.com/api/v4/projects"
        params = {"q": f"title.search:{query.strip()}", "items_per_page": max_results} 
        resp = requests.get(gl_url, params=params)
        print(f"GitLab status: {resp.status_code}")
        if resp.status_code == 200:
            for proj in resp.json():
                projects.append({
                    "name": proj["path_with_namespace"],
                    "description": proj.get("description", ""),
                    "url": proj["web_url"],
                    "source": "gitlab",
                    "readme": ""
                })
    except Exception as e:
        print(f"GitLab error: {e}")
    return projects

def search_bitbucket(query, max_results):
    projects = []
    # --- Bitbucket ---
    bitbucket_user = os.getenv("BITBUCKET_USERNAME")
    bitbucket_pass = os.getenv("BITBUCKET_APP_PASSWORD")
    if bitbucket_user and bitbucket_pass:
        try:
            bb_url = "https://api.bitbucket.org/2.0/repositories"
            params = {"q": f'name~"{query}"', "sort": "-updated_on", "pagelen": max_results}
            resp = requests.get(bb_url, params=params, auth=(bitbucket_user, bitbucket_pass))
            if resp.status_code == 200:
                for repo in resp.json().get("values", []):
                    projects.append({
                        "name": repo["full_name"],
                        "description": repo.get("description", "") or "",
                        "url": repo["links"]["html"]["href"],
                        "source": "bitbucket",
                        "readme": ""
                    })
        except Exception as e:
            print(f"Bitbucket error: {e}")
        return projects
# ---------- SECTION SPLITTER ----------

import re
from typing import Dict

SECTION_HEADER_PATTERNS = {
    "abstract": r"abstract",
    "introduction": r"introduction",
    "related_work": (
    r"related\s+work|background|prior\s+work|"
    r"literature\s+review|state\s+of\s+the\s+art"
),

"methodology": (
    r"method(ology)?|approach|framework|system|"
    r"architecture|pipeline|algorithm|model|"
    r"feature\s+extraction"
),

"experimental_setup": (
    r"experiments?|experimental\s+setup|"
    r"implementation|datasets?|materials?|"
    r"evaluation\s+protocol"
),

"results": (
    r"results?|evaluation|performance|analysis"
),

"discussion": (
    r"discussion|limitations?|challenges?"
),
    "conclusion": r"(conclusion(s)?|future\s+works?)",
    "references": r"(references|bibliography)",
}


HEADER_REGEX = re.compile(
    r"""
    ^
    \s*
    (?:                 # optional numbering
        \d+(?:\.\d+)*   # 1  2.1  3.4.5
        |
        [IVXLCDM]+      # Roman numerals
    )?
    \.?
    \s*
    (?P<title>.+?)      # entire remaining line
    \s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)

def is_likely_header(line: str) -> bool:
    """Heuristic guard: does this line LOOK like a header, independent of content?"""
    if not line or len(line) > 70:
        return False
    if line.endswith("."):  # body sentences end in periods, headers rarely do
        return False
    word_count = len(line.split())
    if word_count > 8:
        return False
    return True


SECTION_KEYWORDS = {
    "abstract": ["abstract"],
    "introduction": ["introduction"],
    "related_work": ["related work", "background", "prior work", "literature review"],
    "methodology": [
        "methodology", "proposed methodology", "proposed method", "proposed approach",
        "proposed model", "approach", "materials and methods", "model architecture",
        "system architecture", "cnn architecture", "network architecture"
    ],
    "experimental_setup": [
        "experimental setup", "implementation details", "dataset", "datasets",
        "evaluation metrics", "training and testing", "experimental implementation"
    ],
    "results": [
        "results", "experimental results", "results and discussion",
        "performance evaluation", "evaluation results"
    ],
    "discussion": ["discussion"],
    "conclusion": ["conclusion", "conclusions", "future work", "future works"],
    "references": ["references", "bibliography"],
}


def match_section_keyword(candidate: str) -> str | None:
    """
    Loose match: does the candidate header line CONTAIN a known keyword
    (not require an exact fullmatch)? Longer keywords checked first so
    'experimental results' beats a bare 'results' collision if both fit.
    """
    candidate = candidate.lower().strip()
    best_match = None
    best_len = 0
    for section_name, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if kw in candidate and len(kw) > best_len:
                best_match = section_name
                best_len = len(kw)
    return best_match


def heuristic_split_sections(text: str) -> Dict[str, str]:
    lines = text.splitlines()
    found_headers = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or not is_likely_header(stripped):
            continue

        m = HEADER_REGEX.match(stripped)
        if not m:
            continue

        candidate = m.group("title").strip().lower()
        candidate = re.sub(r"[:\-–]+$", "", candidate)
        candidate = re.sub(r"\s+", " ", candidate)

        section_name = match_section_keyword(candidate)
        if section_name:
            found_headers.append((i, section_name, stripped))

    print("headers from heuristic:", found_headers)

    if len(found_headers) < 2:
        return {}

    sections = {}
    for idx, (line_no, section_name, _) in enumerate(found_headers):
        start = line_no + 1
        end = found_headers[idx + 1][0] if idx + 1 < len(found_headers) else len(lines)
        content = "\n".join(lines[start:end]).strip()
        if content:
            if section_name not in sections:
                sections[section_name] = content
            else:
                sections[section_name] += "\n\n" + content  # concatenate instead of overwrite

    return sections
def llm_split_sections(text: str, chunk_chars: int = 3000) -> Dict[str, str]:
    """
    Chunk-based fallback: classify each chunk of the FULL paper into a
    known section type, then merge chunks belonging to the same section.
    This scales to any paper length without truncating content away.
    """
    known_sections = list(SECTION_HEADER_PATTERNS.keys())
    chunks = chunk_text(text, max_chars=chunk_chars)

    aggregated: Dict[str, str] = {}
    last_section = "introduction"  # sensible default for the very first chunk

    for i, chunk in enumerate(chunks):
        prompt = f"""This is part {i+1} of {len(chunks)} of a scientific paper, in order.
Identify which section this text primarily belongs to. Choose exactly ONE from this list: {known_sections}.
If this chunk continues the same section as the previous part with no new header, respond with "same_as_previous".

Return ONLY valid JSON: {{"section": "..."}}

Text:
{chunk}
"""
        content = _groq_invoke_safe(prompt)
        parsed = _safe_json_parse(content)
        section = (parsed.get("section", "") if parsed else "").strip().lower()

        if section == "same_as_previous" or section not in known_sections:
            section = last_section

        aggregated.setdefault(section, "")
        aggregated[section] += ("\n\n" if aggregated[section] else "") + chunk
        last_section = section
        time.sleep(2)  # rate-limit spacing, same as analyze_section

    return aggregated


def _safe_json_parse(raw: str) -> Dict:
    """Strip markdown fences and parse JSON, return {} on failure."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception as e:
        print(f"JSON parse error: {e}, raw content: {cleaned[:200]}")
        return {}
ESSENTIAL_SECTIONS = {
    "methodology",
    "experimental_setup",
    "results",
}

OPTIONAL_SECTIONS = {
    "abstract",
    "introduction",
    "related_work",
    "discussion",
    "conclusion",
    "references",
}
def split_paper_sections(text: str) -> Dict[str, str]:
    sections = heuristic_split_sections(text)
    found = set(sections.keys())
    essential_found = len(found & ESSENTIAL_SECTIONS)
    heuristic_success = essential_found >= 2

    if heuristic_success:
        print(f"[split] heuristic succeeded: {[(k, len(v)) for k, v in sections.items()]}")
        return sections

    print(f"[split] heuristic found only {essential_found} essential section(s), falling back to LLM chunk classification.")
    llm_sections = llm_split_sections(text)   # actually call it now
    print(f"[split] LLM fallback result: {[(k, len(v)) for k, v in llm_sections.items()]}")
    return llm_sections
# ---------- SECTION-ANALYSIS AGENT ----------

SECTION_SCHEMAS = {
    "methodology": {
        "fields": ["algorithms", "hyperparameters", "implementation_notes", "potential_biases"],
        "instructions": "Extract the algorithms/models used, any hyperparameters mentioned "
                         "(learning rate, batch size, architecture size, etc.), notable "
                         "implementation details, and any potential methodological biases "
                         "or limitations in the experimental design."
    },
    "results": {
        "fields": ["metrics", "baselines_compared", "key_improvements", "reported_numbers"],
        "instructions": "Extract the evaluation metrics used, baselines compared against, "
                         "the key claimed improvements, and the specific reported numbers "
                         "(as a list of {metric, value, dataset} if identifiable)."
    },
    "introduction": {
        "fields": ["problem_statement", "motivation", "contributions"],
        "instructions": "Extract the core problem being addressed, the motivation for the work, "
                         "and the paper's stated contributions."
    },
    "related_work": {
        "fields": ["prior_approaches", "positioning"],
        "instructions": "Extract the prior approaches discussed and how this paper positions "
                         "itself relative to them."
    },
    "discussion": {
        "fields": ["limitations", "future_work"],
        "instructions": "Extract the limitations acknowledged by the authors and any suggested future work."
    },
    "conclusion": {
        "fields": ["limitations", "future_work", "summary"],
        "instructions": "Summarize the conclusion, extract acknowledged limitations and future work."
    },
    "abstract": {
        "fields": ["summary"],
        "instructions": "Summarize the abstract in 2-3 sentences."
    },
}


def analyze_section(section_text: str, section_type: str, max_chars: int = 3000) -> Dict:
    # Check cache first
    cached = get_cached_section_analysis(section_text, section_type)
    if cached:
        print(f"[cache hit] section '{section_type}' — skipping Groq call")
        return cached

    schema = SECTION_SCHEMAS.get(section_type, {
        "fields": ["summary"],
        "instructions": "Summarize the key points of this section."
    })
    fields_list = ", ".join(schema["fields"])

    chunks = chunk_text(section_text, max_chars=max_chars)

    if len(chunks) == 1:
        prompt = f"""You are analyzing the "{section_type}" section of a scientific paper.

{schema['instructions']}

Return ONLY valid JSON with exactly these keys: {fields_list}.
Use empty string or empty list if a field isn't present in the text. No markdown fences, no explanation.

Section text:
{chunks[0]}
"""
        content = _groq_invoke_safe(prompt)
        parsed = _safe_json_parse(content)
        if not parsed:
            parsed = {field: "" for field in schema["fields"]}
            parsed["_error"] = "LLM output could not be parsed"
        set_cached_section_analysis(section_text, section_type, parsed)
        return parsed

    # Multiple chunks: analyze each, then merge
    print(f"Section '{section_type}' split into {len(chunks)} chunks for rate-limit safety.")
    partial_results = []
    for i, chunk in enumerate(chunks):
        prompt = f"""You are analyzing part {i+1} of {len(chunks)} of the "{section_type}" section of a scientific paper.

{schema['instructions']}

Return ONLY valid JSON with exactly these keys: {fields_list}.
Use empty string or empty list if a field isn't present in this part. No markdown fences, no explanation.

Section text (part {i+1}/{len(chunks)}):
{chunk}
"""
        content = _groq_invoke_safe(prompt)
        parsed = _safe_json_parse(content)
        if parsed:
            partial_results.append(parsed)
        time.sleep(2)  # small buffer between chunk calls, in addition to backoff on errors

    if not partial_results:
        result = {field: "" for field in schema["fields"]}
        result["_error"] = "All chunks failed to parse"
        set_cached_section_analysis(section_text, section_type, result)
        return result

    result = merge_section_analyses(partial_results, schema["fields"])
    set_cached_section_analysis(section_text, section_type, result)
    return result


def analyze_all_sections(sections: Dict[str, str]) -> Dict[str, Dict]:
    """
    Run analyze_section over every detected section.
    Returns {section_name: analysis_dict}.
    """
    results = {}
    for section_name, section_text in sections.items():
        if not section_text.strip():
            results[section_name] = {"_error": "no content extracted for this section"}
            continue
        results[section_name] = analyze_section(section_text, section_name)
    return results



import time

# ---------- CHUNKING UTILITY ----------
def chunk_text(text: str, max_chars: int = 3000) -> List[str]:
    """
    Split text into chunks under max_chars, breaking on paragraph
    boundaries where possible to avoid cutting sentences mid-way.
    ~3000 chars ≈ 750-900 tokens, leaving headroom for prompt + response
    under Groq's free-tier 12,000 TPM limit.
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current += ("\n\n" if current else "") + para
        else:
            if current:
                chunks.append(current)
            # paragraph itself too long, hard-split it
            if len(para) > max_chars:
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i:i + max_chars])
                current = ""
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks

import time

class TokenBudget:
    def __init__(self, tpm_limit: int = 11000):  # stay under 12000 with margin
        self.tpm_limit = tpm_limit
        self.used = 0
        self.window_start = time.time()

    def consume(self, estimated_tokens: int):
        now = time.time()
        if now - self.window_start >= 60:
            self.used = 0
            self.window_start = now
        if self.used + estimated_tokens > self.tpm_limit:
            wait = 60 - (now - self.window_start)
            if wait > 0:
                print(f"Approaching TPM limit, waiting {wait:.1f}s...")
                time.sleep(wait)
            self.used = 0
            self.window_start = time.time()
        self.used += estimated_tokens

_groq_budget = TokenBudget()
def _groq_invoke_safe(prompt: str, retries: int = 1, wait_seconds: float = 8.0) -> str:
    """
    Try Groq first (best reasoning). On rate-limit exhaustion, fall back to
    Gemini so the pipeline doesn't crash — not because Gemini is preferred.
    """
    for attempt in range(retries):
        try:
            _groq_budget.consume(len(prompt)//4)
            response = _invoke_groq(prompt)
            content = response.content
            if isinstance(content, list):
                content = "".join(b.get('text', '') if isinstance(b, dict) else str(b) for b in content)
            return content
        except Exception as e:
            err = str(e)
            if "429" in err or "413" in err or "rate_limit" in err:
                print(f"Groq rate-limited (attempt {attempt+1}), retrying after {wait_seconds}s...")
                time.sleep(wait_seconds)
                continue
            raise

    print("Groq exhausted retries — falling back to Gemini for this call only.")
    try:
        response = _invoke_gemini(prompt)
        content = response.content
        if isinstance(content, list):
            content = "".join(b.get('text', '') if isinstance(b, dict) else str(b) for b in content)
        return content
    except Exception as e:
        print(f"Gemini also failed: {e}")
        raise
"""         try:
            response = _ollama_llm.invoke(prompt)
            return response.content
        except Exception as e3:
            raise RuntimeError(f"All three providers failed: {e3}") """
        

def merge_section_analyses(partial_results: List[Dict], fields: List[str]) -> Dict:
    """
    Merge multiple chunk-level analyses into one dict per the schema's fields.
    List-type values get concatenated + deduplicated; string values get joined.
    """
    merged = {field: [] for field in fields}
    for result in partial_results:
        for field in fields:
            val = result.get(field, "")
            if isinstance(val, list):
                merged[field].extend(val)
            elif isinstance(val, str) and val.strip():
                merged[field].append(val.strip())

    # Clean up: dedupe lists, join strings into one paragraph where sensible
    final = {}
    for field, values in merged.items():
        if not values:
            final[field] = ""
            continue
        # dedupe while preserving order
        seen = set()
        deduped = []
        for v in values:
            key = v if isinstance(v, str) else json.dumps(v, sort_keys=True)
            if key not in seen:
                seen.add(key)
                deduped.append(v)
        final[field] = deduped if len(deduped) > 1 else deduped[0]
    return final
def fetch_full_text(paper: Dict, timeout: int = 20) -> str:
    """
    Attempt to fetch and extract full text for a paper. Tries pdf_url if
    present; returns empty string if no PDF is available or extraction fails.
    Caller should fall back to abstract-only analysis when this returns "".
    """
    pdf_url = paper.get("pdf_url", "")
    if not pdf_url:
        return ""

    try:
        resp = requests.get(pdf_url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type and not pdf_url.lower().endswith(".pdf"):
            print(f"Skipping non-PDF content at {pdf_url} (Content-Type: {content_type})")
            return ""
        return extract_text_from_pdf_bytes(resp.content)
    except Exception as e:
        print(f"Failed to fetch/extract PDF from {pdf_url}: {e}")
        return ""

import fitz  
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text("text")
    doc.close()
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(lines)
# ---------- GAP DETECTION AGENT ----------

def _extract_gap_relevant_text(paper_title: str, analysis: Dict) -> str:
    """
    Pull the fields most useful for gap detection from a paper's section
    analysis: stated limitations, future work, and what the paper claims
    to contribute (to infer what's NOT yet covered elsewhere).
    """
    parts = [f"Paper: {paper_title}"]

    intro = analysis.get("introduction", {})
    if intro.get("contributions"):
        parts.append(f"Contributions: {intro['contributions']}")
    if intro.get("problem_statement"):
        parts.append(f"Problem addressed: {intro['problem_statement']}")

    related = analysis.get("related_work", {})
    if related.get("positioning"):
        parts.append(f"Positioning vs prior work: {related['positioning']}")

    for key in ("discussion", "conclusion"):
        sec = analysis.get(key, {})
        if sec.get("limitations"):
            parts.append(f"Limitations ({key}): {sec['limitations']}")
        if sec.get("future_work"):
            parts.append(f"Future work ({key}): {sec['future_work']}")

    results = analysis.get("results", {})
    if results.get("key_improvements"):
        parts.append(f"Key results: {results['key_improvements']}")

    return "\n".join(parts)

# ---------- CHUNKING WITH SOURCE TRACKING ----------

def chunk_text_with_source(text: str, source: str, max_chars: int = 3000) -> List[Dict]:
    """
    Chunk a single paper's text, tagging every resulting chunk with its
    source (paper title) as structured metadata. This must be called
    PER PAPER, not on a concatenation of multiple papers, so a chunk
    boundary never crosses between two different papers' content.
    """
    raw_chunks = chunk_text(text, max_chars=max_chars)  # existing paragraph-aware splitter
    return [{"source": source, "text": chunk} for chunk in raw_chunks]


# ---------- GAP DETECTION AGENT (fixed) ----------

def detect_gaps(user_idea: str, papers_with_analysis: List[Dict], max_chars: int = 3000) -> Dict:
    """
    papers_with_analysis: list of {"title": str, "analysis": Dict}

    Fix applied: each paper is chunked INDIVIDUALLY (not concatenated then
    chunked), and every chunk carries its source paper title as structured
    metadata rather than relying on it being written into the chunk text.
    This prevents chunks from losing their paper attribution when a long
    paper's content spans multiple chunks.
    """
    if not papers_with_analysis:
        return {"gaps": [], "_error": "No papers provided for gap analysis."}

    all_chunks = []  # list of {"source": title, "text": chunk}
    for p in papers_with_analysis:
        paper_text = _extract_gap_relevant_text(p["title"], p["analysis"])
        all_chunks.extend(
            chunk_text_with_source(paper_text, source=p["title"], max_chars=max_chars)
        )

    if not all_chunks:
        return {"gaps": [], "_error": "No content available to analyze."}

    schema_instructions = """Return ONLY valid JSON with this exact structure, no markdown fences:
{
  "gaps": [
    {
      "gap_description": "...",
      "supporting_evidence": "...",
      "opportunity": "..."
    }
  ]
}
Each gap should describe something unsolved, under-explored, or contradictory in this paper.
"opportunity" should briefly state what a new project/experiment could do to address it.

CRITICAL: The "opportunity" field must stay grounded in what the paper actually discusses or
implies — do not suggest a specific named technique or technology unless it is explicitly
mentioned in the paper text provided. Do not include a "papers_involved" field — the source
paper is already known and will be attached automatically."""

    def build_prompt(chunk_dict: Dict, part_num: int = None, total: int = None) -> str:
        part_note = f" (part {part_num} of {total} for this paper)" if part_num else ""
        return f"""User's project idea: "{user_idea}"

You are analyzing text from the paper "{chunk_dict['source']}"{part_note} to identify gaps
relevant to this idea.

{schema_instructions}

Paper text:
{chunk_dict['text']}
"""

    print(f"Gap detection: {len(all_chunks)} chunk(s) across {len(papers_with_analysis)} paper(s).")
    partial_gaps = []
    for i, chunk_dict in enumerate(all_chunks):
        prompt = build_prompt(chunk_dict, part_num=i + 1, total=len(all_chunks))
        content = _groq_invoke_safe(prompt)
        parsed = _safe_json_parse(content)
        if parsed and parsed.get("gaps"):
            for gap in parsed["gaps"]:
                gap["papers_involved"] = [chunk_dict["source"]]
            partial_gaps.extend(parsed["gaps"])
        else:
            print(f"[debug] chunk from '{chunk_dict['source']}' produced NO gaps: {parsed}")
        time.sleep(2)

    # NEW: see exactly what's going into consolidation, per paper
    print(f"[debug] partial_gaps BEFORE consolidation ({len(partial_gaps)} total):")
    for g in partial_gaps:
        print(f"  - {g.get('papers_involved')}: {g.get('gap_description', '')[:80]}")

    if not partial_gaps:
        return {"gaps": [], "_error": "No gaps extracted from any chunk."}

    return _consolidate_gaps(user_idea, partial_gaps)


def _consolidate_gaps(user_idea: str, raw_gaps: List[Dict]) -> Dict:
    """
    Merge/deduplicate gaps across papers. Two safeguards, protecting two
    different failure points:
    1. Strip any paper name the LLM invents during merging that wasn't in
       the actual source data (protects against hallucinated attribution
       introduced DURING consolidation, e.g. "MERMAID" as a fake paper title).
    2. Guarantee no real source paper is silently dropped from the final
       output (protects against the LLM over-merging and losing a paper's
       distinct contribution entirely).
    """
    all_input_papers = set()
    for g in raw_gaps:
        all_input_papers.update(g.get("papers_involved", []))

    gaps_text = json.dumps(raw_gaps, indent=2)[:6000]
    prompt = f"""User's project idea: "{user_idea}"

Below is a raw list of research gaps extracted from different papers. Some may be duplicates or
near-duplicates. Consolidate them into a clean, deduplicated final list, merging similar gaps
and keeping the most specific/useful description.

CRITICAL: The "papers_involved" field for each raw gap is already correct and verified. When
merging two or more gaps into one, COMBINE their "papers_involved" lists (union, no duplicates).
Do NOT invent, guess, or drop any paper titles. EVERY paper that appears in the raw gaps below
MUST appear in at least one gap in your final output — do not omit a paper's contribution
entirely just because it seems less significant than others; merge it into a related gap or
keep it as its own entry instead.

Return ONLY valid JSON in this format:
{{"gaps": [{{"gap_description": "...", "supporting_evidence": "...", "papers_involved": [...], "opportunity": "..."}}]}}

Raw gaps:
{gaps_text}
"""
    content = _groq_invoke_safe(prompt)
    parsed = _safe_json_parse(content)

    if not parsed or "gaps" not in parsed:
        return {"gaps": raw_gaps, "_note": "Consolidation failed, returning raw merged list."}

    consolidated = parsed["gaps"]

    # Safeguard 1: strip invented paper names, tracking coverage AS we clean
    covered_papers = set()
    for g in consolidated:
        original = g.get("papers_involved", [])
        cleaned = [p for p in original if p in all_input_papers]
        if len(cleaned) != len(original):
            invented = set(original) - set(cleaned)
            print(f"[warning] Consolidation invented paper name(s) not in source data, removing: {invented}")
        g["papers_involved"] = cleaned
        covered_papers.update(cleaned)  # <-- the missing line, now populated correctly

    # Safeguard 2: verify no real paper vanished entirely, repair if so
    missing_papers = all_input_papers - covered_papers
    if missing_papers:
        print(f"[warning] Consolidation appears to have dropped papers: {missing_papers}")
        verification = _verify_dropped_papers(user_idea, missing_papers, raw_gaps, consolidated)
        for paper, verdict in verification.items():
            if verdict.get("genuinely_missing"):
                print(f"[repair] '{paper}' was genuinely dropped, re-adding: {verdict['gap_to_add']['gap_description'][:60]}")
                consolidated.append(verdict["gap_to_add"])
            else:
                print(f"[ok] '{paper}' content is legitimately covered by existing gap: {verdict.get('covered_by','')[:60]}")

    return {"gaps": consolidated}


def _verify_dropped_papers(user_idea, missing_papers, raw_gaps, consolidated) -> Dict:
    """
    For each paper that disappeared during consolidation, ask the LLM to
    judge whether its content is genuinely already represented in the
    consolidated list, or whether it was wrongly dropped.
    """
    results = {}
    for paper in missing_papers:
        paper_raw_gaps = [g for g in raw_gaps if paper in g.get("papers_involved", [])]
        prompt = f"""User's project idea: "{user_idea}"

A paper titled "{paper}" contributed these raw gaps during initial analysis:
{json.dumps(paper_raw_gaps, indent=2)}

The final consolidated gap list (after merging near-duplicates across all papers) is:
{json.dumps(consolidated, indent=2)[:3000]}

This paper's contribution does not appear explicitly in the final list. Determine:
1. Is this paper's content genuinely already covered by an existing gap in the consolidated list
   (even if the paper isn't explicitly named)? If so, which gap?
2. Or was this paper's distinct contribution wrongly dropped and should be added back?

Return ONLY valid JSON:
{{"genuinely_missing": true/false, "covered_by": "gap_description if covered, else empty", "gap_to_add": {{...one of the raw gaps to re-add if genuinely missing, else null}}}}
"""
        content = _groq_invoke_safe(prompt)
        parsed = _safe_json_parse(content)
        results[paper] = parsed if parsed else {"genuinely_missing": True, "gap_to_add": paper_raw_gaps[0]}
    return results



import hashlib
# ingestion/chroma_client.py (add alongside your existing collections)

def _hash_text(text: str) -> str:
    """Stable hash for cache keys, independent of text length."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_cached_section_analysis(section_text: str, section_type: str) -> Dict | None:
    """
    Look up a cached analysis result for this exact section text + type.
    Uses a hash of (type + text) as the ID — no embedding needed since
    we want exact matches only (same paper, same section, re-run).
    """
    key = _hash_text(section_type + "::" + section_text)
    try:
        result = analysis_cache_collection.get(ids=[key])
        if result and result["metadatas"]:
            return json.loads(result["metadatas"][0]["analysis"])
    except Exception:
        pass
    return None


def set_cached_section_analysis(section_text: str, section_type: str, analysis: Dict):
    key = _hash_text(section_type + "::" + section_text)
    try:
        analysis_cache_collection.delete(ids=[key])  # clear old entry if present
    except Exception:
        pass
    analysis_cache_collection.add(
        documents=[key],          # dummy doc content, we're not doing similarity search here
        embeddings=[[0.0]],       # placeholder; see note below if your Chroma setup requires real embeddings
        metadatas=[{"analysis": json.dumps(analysis), "section_type": section_type}],
        ids=[key]
    )
# ---------- TECHNICAL PLAN AGENT ----------

def generate_technical_plan(
    user_idea: str,
    gaps: List[Dict],
    similar_projects: List[Dict],
    novelty_analysis: str = "",
    max_chars: int = 4000,
    similarity_threshold: float = 0.35
) -> Dict:
    """
    Synthesize a technical project plan from the user's idea, detected
    research gaps, and similar existing projects/repos.
    """
    
    gaps_text = "\n".join(
        f"- {g.get('gap_description', '')} (opportunité : {g.get('opportunity', '')})"
        for g in gaps[:8]  # cap to avoid bloating the prompt
    )
    #similar_text = "\n".join(
    #    f"- [{p.get('source', '')}] {p.get('name', '')}: {(p.get('description') or '')[:150]}"
     #   for p in similar_projects[:8] )
    relevant_similar = [(s, p) for s, p in similar_projects if s >= similarity_threshold]

    if relevant_similar:
        similar_text = "\n".join(
            f"- [{p.get('source','')}] {p.get('name','')} (similarity: {s:.0%})\n"
            f"  About: {(p.get('description') or 'N/A')}\n"
            f"  README excerpt: {(p.get('readme') or '')[:300]}"
            for s, p in relevant_similar[:8]
        )
    else:
        similar_text = "No sufficiently similar existing projects were found for this idea."

    novelty_text = novelty_analysis or "No novelty analysis available."
    schema_instructions = """Return ONLY valid JSON with this exact structure, no markdown fences:
{
  "novelty_assessment": "...",
  "differentiation_strategy": "...",
  "recommended_stack": {
    "core_technologies": ["..."],
    "justification": "..."
  },
  "architecture_overview": "...",
  "milestones": [
    {"title": "...", "description": "...", "estimated_duration": "...", "addresses_gap": "..."}
  ],
  "deliverables": ["..."],
  "risks": [
    {"risk": "...", "mitigation": "..."}
  ]
}

IMPORTANT:
- "novelty_assessment" must restate, in one sentence, how overlapping or novel this idea is,
  based on the novelty analysis provided below.
- "differentiation_strategy" must explain how this plan differentiates the project from existing
  work. If overlap with existing projects is high, this field MUST explicitly steer the project
  toward the identified research gaps as the primary source of novelty — do not propose a plan
  that simply re-implements what already exists. If overlap is low, state that the idea already
  occupies relatively unexplored territory and the plan can proceed on its original direction.
- The "architecture_overview" and "milestones" must reflect the differentiation_strategy — i.e.
  if a pivot toward a specific gap is recommended, the milestones should center on that gap, not
  on replicating the existing similar projects.
- "core_technologies" and their "justification" MUST reference specific technologies actually
  mentioned in the similar projects provided below (e.g. cite a repo name if its README mentions
  a specific framework), not generic ML defaults.
- Each milestone's "addresses_gap" field must name which specific gap (from the list below) that
  milestone is designed to address. If a milestone doesn't address any listed gap, don't include it.
- Do not produce a generic ML project template — this plan must be clearly differentiated by the
  specific gaps and repos provided.

CRITICAL — grounding rules:
- Base every technical claim ONLY on the exact text provided below (repo descriptions, readmes,
  gap descriptions). Do not supplement with general knowledge about the field, even if it seems
  like a reasonable or common suggestion .
- Only cite a technology, framework, or technique as coming from a specific repo if it literally
  appears in that repo's description or readme text provided below. Do not attribute a technology
  to a repo that doesn't mention it, even if the technology is real and used elsewhere.
- If the provided data doesn't mention a specific technique or technology for a given point, do
  not name one — describe the milestone or recommendation in terms of the underlying problem
  instead, without filling in an unverified solution. 
  - If no similar projects are relevant (marked "No sufficiently similar existing projects were
  found"), do NOT invent a stack based on unrelated repos. Instead, recommend a stack based only
  on what the research papers/gaps imply is needed, and note explicitly that no comparable
  implementations were found."""

    prompt = f"""User's project idea: "{user_idea}"

Novelty analysis (overlap with existing work):
{novelty_text}

Identified research gaps and opportunities:
{gaps_text or "None identified."}

Similar existing projects found:
{similar_text or "None found."}

Based on this idea, its novelty relative to existing work, the identified gaps, and existing similar projects, generate a technical project plan that steers toward genuine novelty.

{schema_instructions}
"""

    content = _groq_invoke_safe(prompt)
    parsed = _safe_json_parse(content)
    return parsed if parsed else {"_error": "LLM output could not be parsed"}
# ---------- TEACHING PLAN AGENT ----------

def _extract_teaching_relevant_text(paper_title: str, analysis: Dict) -> str:
    """
    Pull the fields most useful for building a course: what the paper teaches
    (contributions, methodology, key results) rather than what's missing
    (that's what _extract_gap_relevant_text is for).
    """
    parts = [f"Paper: {paper_title}"]

    intro = analysis.get("introduction", {})
    if intro.get("contributions"):
        parts.append(f"Contributions: {intro['contributions']}")
    if intro.get("problem_statement"):
        parts.append(f"Problem addressed: {intro['problem_statement']}")

    methodology = analysis.get("methodology", {})
    if methodology.get("algorithms"):
        parts.append(f"Algorithms/methods: {methodology['algorithms']}")
    if methodology.get("implementation_notes"):
        parts.append(f"Implementation notes: {methodology['implementation_notes']}")

    results = analysis.get("results", {})
    if results.get("metrics"):
        parts.append(f"Evaluation metrics used: {results['metrics']}")
    if results.get("key_improvements"):
        parts.append(f"Key results: {results['key_improvements']}")

    abstract = analysis.get("abstract", {})
    if abstract.get("summary"):
        parts.append(f"Summary: {abstract['summary']}")

    return "\n".join(parts)


def generate_teaching_plan(
    user_idea: str,
    gaps: List[Dict],
    papers_with_analysis: List[Dict],
    max_chars: int = 4000
) -> Dict:
    """
    Synthesize a teaching plan (course structure) from the user's idea,
    the papers analyzed, and the research gaps identified. Gaps become
    explicit "frontier topics" so the course teaches both established
    knowledge and open research questions.
    """
    if not papers_with_analysis:
        return {"_error": "No analyzed papers provided for teaching plan generation."}

    per_paper_summaries = [
        _extract_teaching_relevant_text(p["title"], p["analysis"])
        for p in papers_with_analysis
    ]
    papers_text = "\n\n---\n\n".join(per_paper_summaries)
    papers_text = papers_text[:max_chars]  # cap, same safety margin as other agents

    gaps_text = "\n".join(
        f"- {g.get('gap_description', '')} (opportunité : {g.get('opportunity', '')})"
        for g in gaps[:8]
    )

    schema_instructions = """Return ONLY valid JSON with this exact structure, no markdown fences:
{
  "course_title": "...",
  "target_audience": "...",
  "learning_objectives": ["..."],
  "prerequisites": ["..."],
  "modules": [
    {
      "title": "...",
      "problem_addressed": "...",
      "solution_approach": "...",
      "description": "...",
      "topics": ["..."],
      "based_on_papers": ["paper title 1"],
      "difficulty": "beginner|intermediate|advanced"
    }
  ],
  "frontier_topics": [
    {
      "topic": "...",
      "addresses_gap": "...",
      "rationale": "..."
    }
  ],
  "suggested_duration": "..."
}

IMPORTANT:
- the beginner module should describe the problem in accessible terms, saving specific architectural approaches for intermediate/advanced modules.
- "problem_addressed" should state, in one or two sentences, the specific problem or question
  the module's source paper(s) were trying to solve.
- "solution_approach" should briefly state the method or approach the paper(s) used to address it.
  This is a summary for planning purposes only — the full pedagogical explanation is generated
  separately, so keep this concise.
- Each module's "based_on_papers" MUST reference papers actually provided below. Do not invent
  a module topic that isn't grounded in the analyzed papers' contributions, methodology, or results.
- "frontier_topics" MUST be derived from the research gaps provided below — this section should
  teach students what remains unsolved, not just established knowledge. Each frontier topic must
  name which specific gap it addresses.
- Order modules from foundational to advanced. Foundational modules should cover established
  methods/contributions from the papers; frontier_topics come last, as the "beyond the state of
  the art" section of the course.
- Do not produce a generic course outline — this must be clearly built from the specific papers
  and gaps provided, not a template course on the general topic.


CRITICAL — grounding rules:
- Base every module and topic ONLY on the exact text provided below (paper contributions,
  methodology, results, gap descriptions). Do not supplement with general knowledge about the
  field, even if it seems like a reasonable or common topic to include.
- Only cite a paper as the basis for a module if the module's content is genuinely traceable to
  that paper's provided text. Do not attribute a topic to a paper that doesn't cover it.
- If the provided data doesn't cover a foundational concept you'd normally expect in such a course,
  do not invent content to fill the gap — keep the module list limited to what the source material
  actually supports, and note in "target_audience" or a module description if foundational prior
  knowledge is assumed rather than taught.
  - If the provided papers are not genuinely relevant to the user's idea (e.g. from a completely
  different field), do NOT construct a forced conceptual bridge between them and the idea. Instead,
  state clearly that no relevant literature was found and avoid generating gaps or content based
  on tangential or unrelated papers."""

    prompt = f"""User's project/learning idea: "{user_idea}"

Analyzed papers (source material for course content):
{papers_text}

Identified research gaps (source material for frontier topics):
{gaps_text or "None identified."}

Based on this idea and the analyzed papers and gaps, generate a teaching plan that builds a
course from established knowledge (in the papers) toward open research questions (the gaps).

{schema_instructions}
"""

    content = _groq_invoke_safe(prompt)
    parsed = _safe_json_parse(content)
    return parsed if parsed else {"_error": "LLM output could not be parsed"}
# ---------- QUERY BROADENING AGENT (for niche/underserved ideas) ----------

def broaden_idea(user_idea: str) -> Dict:
    """
    When direct search returns no sufficiently relevant results, decompose
    the idea into underlying concepts and suggest adjacent/analogous fields
    that share methodology, even if not the same subject domain.
    """
    prompt = f"""A user wants to research or build a project on: "{user_idea}"

A direct literature search for this exact topic returned no sufficiently relevant results —
it may be too niche, novel, or interdisciplinary for current sources.

Break this idea down and suggest a path forward:
1. What are the core underlying concepts or methodologies involved (independent of the specific
   application domain)?
2. What adjacent fields or established research areas use similar methodologies, even if applied
   to a different subject? (e.g. if the idea involves classifying rare time-series patterns, fields
   like signal processing, anomaly detection, or gesture recognition might share relevant methods)
3. Suggest 2-4 alternative search queries that could surface genuinely useful literature, even if
   not an exact topical match.

Return ONLY valid JSON, no markdown fences:
{{
  "core_concepts": ["..."],
  "adjacent_fields": ["..."],
  "suggested_queries": ["..."],
  "honest_assessment": "..."
}}
"honest_assessment" should state plainly whether this idea appears to be a genuinely novel/niche
combination, or just an unusual phrasing of a more common topic.
ensure suggested_queries collectively cover all core_concepts identified, not just the most search-friendly one"""

    content = _groq_invoke_safe(prompt)
    parsed = _safe_json_parse(content)
    return parsed if parsed else {"_error": "Could not broaden idea"}
def search_with_broadening(idea: str, max_results: int = 15, relevance_threshold: float = 0.30):
    """
    Try direct search first. If nothing clears the relevance threshold,
    broaden the query and search adjacent fields, but TAG results so
    downstream agents know they're analogical, not direct matches.
    """
    raw_papers = search_papers(idea, max_results=max_results)
    scored_papers = filter_papers_hybrid(raw_papers, idea, embed_top_k=8, llm_top_n=5, return_scores=True)
    direct_relevant = [(s, p) for s, p in scored_papers if s >= relevance_threshold]

    if direct_relevant:
        for _, p in direct_relevant:
            p["match_type"] = "direct"
        return [p for _, p in direct_relevant], None  # (papers, broadening_info)

    # Nothing directly relevant — broaden
    broadening = broaden_idea(idea)
    analogous_papers = []
    for query in broadening.get("suggested_queries", [])[:3]:
        raw = search_papers(query, max_results=8)
        scored = filter_papers_hybrid(raw, query, embed_top_k=5, llm_top_n=2, return_scores=True)
        for score, p in scored:
            if score >= relevance_threshold:
                p["match_type"] = "analogous"
                p["matched_via_query"] = query
                analogous_papers.append(p)

    return analogous_papers, broadening
def _format_papers_with_match_type(papers_with_analysis: List[Dict]) -> str:
    direct = [p for p in papers_with_analysis if p.get("match_type", "direct") == "direct"]
    analogous = [p for p in papers_with_analysis if p.get("match_type") == "analogous"]

    parts = []
    if direct:
        parts.append("DIRECTLY RELEVANT PAPERS:\n" + "\n\n---\n\n".join(
            _extract_gap_relevant_text(p["title"], p["analysis"]) for p in direct
        ))
    if analogous:
        parts.append(
            "ANALOGOUS-FIELD PAPERS (same methodology, different application domain — "
            "use with caution, do not assume direct applicability):\n" +
            "\n\n---\n\n".join(
                f"[from adjacent field, matched via query '{p.get('matched_via_query','')}']\n"
                + _extract_gap_relevant_text(p["title"], p["analysis"])
                for p in analogous
            )
        )
    return "\n\n===\n\n".join(parts)

def get_papers_with_analysis(idea: str, max_papers: int = 2) -> List[Dict]:
    """Shared pipeline: search -> filter -> fetch full text -> split -> analyze."""
    raw_papers = search_papers(idea, max_results=15)
    relevant_papers = filter_papers_hybrid(raw_papers, idea, embed_top_k=8, llm_top_n=max_papers)

    papers_with_analysis = []
    for paper in relevant_papers:
        full_text = fetch_full_text(paper)
        if not full_text.strip():
            papers_with_analysis.append({
                "title": paper["title"],
                "analysis": {"abstract": {"summary": paper.get("abstract", "")}}
            })
            continue
        sections = split_paper_sections(full_text)
        if not sections:
            continue
        papers_with_analysis.append({"title": paper["title"], "analysis": analyze_all_sections(sections)})

    return papers_with_analysis



# ---------- COURSE GENERATOR ----------

def _get_paper_analysis_by_title(papers_with_analysis: List[Dict], titles: List[str]) -> str:
    """
    Given a list of paper titles referenced by a module (based_on_papers),
    pull their full analysis text back out for grounding the lesson content.
    """
    by_title = {p["title"]: p["analysis"] for p in papers_with_analysis}
    parts = []
    for title in titles:
        analysis = by_title.get(title)
        if analysis:
            parts.append(_extract_teaching_relevant_text(title, analysis))
    return "\n\n---\n\n".join(parts)
def generate_module_content(
    module: Dict,
    papers_with_analysis: List[Dict],
    already_covered: List[str] = None,   # NEW parameter
    max_chars: int = 4000
) -> Dict:
    """
    Expand one teaching-plan module into actual lesson content:
    explanation, key concepts, a worked example/illustration, and a
    check-for-understanding — grounded in the same papers the module
    is based on.
    """
    already_covered = already_covered or []

    source_text = _get_paper_analysis_by_title(papers_with_analysis, module.get("based_on_papers", []))
    source_text = source_text[:max_chars]

    schema_instructions = """Return ONLY valid JSON with this exact structure, no markdown fences:
{
  "overview": "...",
  "key_concepts": ["..."],
  "explanation": "...",
  "worked_example": "...",
  "check_understanding": ["..."],
  "summary": "..."
}

IMPORTANT:
- "overview" is a 1-2 sentence intro to the module's topic, written for the target audience.
- "explanation" should teach the actual content — the problem, the approach, and why it works —
  in clear prose, based on the module's problem_addressed/solution_approach and the paper content
  provided below. Aim for 150-250 words.
- "worked_example" should walk through a concrete illustration of the method/finding, grounded in
  the source papers. If the source material doesn't support a full worked example, describe the
  paper's actual experimental setup or a real reported result instead of inventing one.
- "check_understanding" is a list of 2-3 short questions or exercises a student could use to test
  their grasp of the module.

CRITICAL — grounding rules:
- Base all content ONLY on the paper text provided below. Do not supplement with general domain
  knowledge or textbook explanations not grounded in the source material.
- Do not invent specific numbers, results, or technical details not present in the source text."""

    already_covered_note = (
    "\n\nIMPORTANT — avoiding redundancy: the following modules have ALREADY been taught in this "
    "course, with these summaries:\n" +
    "\n".join(f"- {s}" for s in already_covered) +
    "\n\nIf this module's content overlaps with any of the above (e.g. the same model architecture "
    "or technique), do NOT re-explain it in detail again. Instead, write ONE brief sentence like "
    "'As covered in [module title], ...' and then focus this module's explanation on what is NEW "
    "or ADDS DEPTH beyond what was already taught."
    if already_covered else ""
)

    prompt = f"""You are creating lesson content for a course module titled "{module.get('title', '')}".

Problem addressed: {module.get('problem_addressed', '')}
Solution approach: {module.get('solution_approach', '')}
Target difficulty: {module.get('difficulty', 'intermediate')}
Topics to cover: {', '.join(module.get('topics', []))}
{already_covered_note}

Source material from the paper(s) this module is based on:
{source_text or 'No detailed source text available — use the problem/solution summary above only.'}

{schema_instructions}
"""

    content = _groq_invoke_safe(prompt)
    parsed = _safe_json_parse(content)
    return parsed if parsed else {"_error": "LLM output could not be parsed"}

def generate_course(
    teaching_plan: Dict,
    papers_with_analysis: List[Dict],
    lessons_per_module: int = 1  # v1 default; raise later for multi-lesson modules
) -> Dict:
    """
    Hierarchical course generation:
    1. Iterate every module in the (already generated) teaching plan.
    2. For each module, generate `lessons_per_module` lesson(s).
    3. Each lesson expands the module's objectives into detailed sections,
       grounded in the module's source papers.
    4. Cross-lesson repetition is suppressed by threading a running summary
       of everything already taught into each new lesson's prompt.
    """
    modules_output = []
    covered_summaries = []  # accumulates across the WHOLE course, module after module

    for module in teaching_plan.get("modules", []):
        module_lessons = []
        for i in range(lessons_per_module):
            lesson = generate_lesson_for_module(
                module, papers_with_analysis,
                already_covered=covered_summaries,
                lesson_index=i + 1,
                total_lessons=lessons_per_module
            )
            module_lessons.append(lesson)
            if lesson.get("summary"):
                covered_summaries.append(f"{module.get('title','')} (lesson {i+1}): {lesson['summary']}")
            time.sleep(2)

        modules_output.append({
            "module_title": module.get("title", ""),
            "difficulty": module.get("difficulty", ""),
            "problem_addressed": module.get("problem_addressed", ""),
            "solution_approach": module.get("solution_approach", ""),
            "based_on_papers": module.get("based_on_papers", []),
            "lessons": module_lessons
        })

    frontier_content = [
        {
            "topic": ft.get("topic", ""),
            "addresses_gap": ft.get("addresses_gap", ""),
            "rationale": ft.get("rationale", "")
        }
        for ft in teaching_plan.get("frontier_topics", [])
    ]

    return {
        "course_title": teaching_plan.get("course_title", ""),
        "target_audience": teaching_plan.get("target_audience", ""),
        "learning_objectives": teaching_plan.get("learning_objectives", []),
        "modules": modules_output,   # each module now contains its own list of lessons
        "frontier_topics": frontier_content,
        "suggested_duration": teaching_plan.get("suggested_duration", "")
    }
# ---------- PPTX EXPORT (design system imported from reference exporter) ----------

from pptx import Presentation


def _resolve_module_title(module: Dict) -> str:
    return module.get("module_title") or module.get("title") or ""


def _resolve_lesson_title(lesson: Dict, default_title: str = "Lesson") -> str:
    return lesson.get("lesson_title") or lesson.get("title") or default_title


def export_course_to_pptx(course: Dict, output_path: str) -> str:
    """Export the generated course with the same design system as the reference exporter."""
    prs = Presentation()
    prs.slide_width = TOKENS.SLIDE_WIDTH
    prs.slide_height = TOKENS.SLIDE_HEIGHT

    course_title = course.get("course_title") or course.get("title") or "Course"
    learning_objectives = course.get("learning_objectives", [])
    modules = course.get("modules", [])

    slide_number = 1
    build_title_slide(prs, course_title, course_title, "", slide_number)
    slide_number += 1

    if learning_objectives:
        build_objectives_slide(prs, learning_objectives, slide_number, course_title)
        slide_number += 1

    for module_idx, module in enumerate(modules):
        if not isinstance(module, dict):
            continue

        module_title = _resolve_module_title(module)
        difficulty = module.get("difficulty", "")
        problem = module.get("problem_addressed", "")
        solution = module.get("solution_approach", "")
        based_on_papers = module.get("based_on_papers", [])
        lessons = module.get("lessons", [])

        if problem or solution or difficulty:
            build_context_slide(prs, problem, solution, difficulty, slide_number, course_title)
            slide_number += 1

        for lesson in lessons:
            if not isinstance(lesson, dict):
                continue

            sections = lesson.get("sections", [])
            summary = lesson.get("summary", "")
            check_understanding = lesson.get("check_understanding", [])

            for section in sections:
                if not isinstance(section, dict):
                    continue

                topic = section.get("topic", "")
                explanation = section.get("explanation", "")
                example = section.get("example_or_evidence", "")
                key_terms = section.get("key_terms", {})

                if not topic and not explanation:
                    continue

                if topic:
                    build_divider_slide(prs, topic, module_title, slide_number, course_title)
                    slide_number += 1

                if explanation:
                    groups = ContentSplitter.to_bullets(
                        explanation,
                        max_bullets=TOKENS.MAX_BULLETS_PER_SLIDE,
                        max_chars=TOKENS.MAX_CHARS_PER_BULLET,
                    )
                    for i, bullets in enumerate(groups):
                        if not bullets:
                            continue
                        build_content_slide(
                            prs,
                            topic,
                            bullets,
                            slide_number,
                            course_title,
                            is_continued=(i > 0),
                        )
                        slide_number += 1

                if example:
                    build_example_slide(prs, topic, example, slide_number, course_title)
                    slide_number += 1

                if key_terms and isinstance(key_terms, dict):
                    chunks = ContentSplitter.chunk_dict(key_terms, per_slide=TOKENS.MAX_TERMS_PER_SLIDE)
                    for chunk in chunks:
                        build_key_terms_slide(prs, chunk, slide_number, course_title)
                        slide_number += 1

            if summary:
                build_summary_slide(prs, summary, slide_number, course_title)
                slide_number += 1

            if check_understanding:
                questions = []
                if isinstance(check_understanding, list):
                    questions = [str(q) for q in check_understanding if q]
                elif isinstance(check_understanding, str):
                    questions = [check_understanding]

                if questions:
                    q_chunks = ContentSplitter.chunk_list(questions, per_slide=TOKENS.MAX_QUESTIONS_PER_SLIDE)
                    for chunk in q_chunks:
                        build_quiz_slide(prs, chunk, slide_number, course_title)
                        slide_number += 1

        if based_on_papers:
            build_references_slide(prs, based_on_papers, slide_number, course_title)
            slide_number += 1

    if course.get("frontier_topics"):
        build_references_slide(prs, course.get("frontier_topics", []), slide_number, course_title)
        slide_number += 1

    build_closing_slide(prs, course_title, slide_number)
    prs.save(output_path)
    return output_path


def export_course_to_pptx_per_lesson(course: Dict, output_dir: str) -> List[str]:
    """Produce one polished lesson deck per module lesson using the reference design system."""
    return _reference_export_course_to_pptx_per_lesson(course, output_dir)



# ---------- LESSON GENERATION (hierarchical: plan -> module -> lesson(s)) ----------

def generate_lesson_for_module(
    module: Dict,
    papers_with_analysis: List[Dict],
    already_covered: List[str] = None,
    lesson_index: int = 1,
    total_lessons: int = 1,
    max_chars: int = 5000
) -> Dict:
    """
    Generate ONE lesson for a module, expanding each objective/topic into
    substantial educational content (explanation + example + context per
    topic), rather than a single flattened summary paragraph.

    Designed to be called multiple times per module later (lesson_index/
    total_lessons already threaded through) even though v1 calls it once.
    """
    already_covered = already_covered or []
    source_text = _get_paper_analysis_by_title(papers_with_analysis, module.get("based_on_papers", []))
    source_text = source_text[:max_chars]

    topics = module.get("topics", [])
    objectives_note = (
        f"This lesson must cover ALL of these topics/objectives in depth: {', '.join(topics)}."
        if topics else "Cover the module's problem and solution approach in depth."
    )

    already_covered_note = (
        "\n\nIMPORTANT — avoiding redundancy: the following has already been taught earlier in "
        "this course:\n" + "\n".join(f"- {s}" for s in already_covered) +
        "\n\nDo not re-explain these from scratch. If this lesson's content builds on them, "
        "reference them briefly (e.g. 'building on X, introduced earlier...') and focus on what "
        "is NEW or goes DEEPER here."
        if already_covered else ""
    )

    schema_instructions = """Return ONLY valid JSON with this exact structure, no markdown fences:
{
  "lesson_title": "...",
  "objectives_covered": ["..."],
  "sections": [
    {
      "topic": "...",
      "explanation": "...",
      "example_or_evidence": "...",
      "key_terms": ["..."]
    }
  ],
  "check_understanding": ["..."],
  "summary": "..."
}

IMPORTANT:
- Create ONE entry in "sections" for EACH topic/objective listed for this module — do not merge
  multiple topics into a single section, and do not skip any.
- Each section's "explanation" must be a THOROUGH, substantive treatment of that specific topic
  (aim for 120-200 words per section) — not a one-line summary. Explain the concept, why it
  matters, and how it connects to the module's overall problem/solution.
- "example_or_evidence" must ground the explanation in something concrete from the source papers:
  a real experimental result, a specific reported number, or a described implementation detail.
  If the source material doesn't support a full example for that topic, describe the paper's
  actual relevant finding instead of inventing an illustrative example.
- "check_understanding" should have one question per section, testing that specific topic.

CRITICAL — grounding rules:
- Base all content ONLY on the paper text provided below. Do not supplement with general domain
  knowledge or textbook explanations not grounded in the source material.
- Do not invent specific numbers, results, or technical details not present in the source text."""

    prompt = f"""You are creating lesson {lesson_index} of {total_lessons} for a course module titled "{module.get('title', '')}".

Module problem: {module.get('problem_addressed', '')}
Module solution approach: {module.get('solution_approach', '')}
Target difficulty: {module.get('difficulty', 'intermediate')}
{objectives_note}
{already_covered_note}

Source material from the paper(s) this module is based on:
{source_text or 'No detailed source text available — use the problem/solution summary above only.'}

{schema_instructions}
"""

    content = _groq_invoke_safe(prompt)
    parsed = _safe_json_parse(content)
    return parsed if parsed else {"_error": "LLM output could not be parsed"}




"""
Lab Generator Agent
--------------------
Turns one course lesson (from Course Generator) into a hands-on exercise:
fill-in-the-blank code, or a small Kaggle-style notebook, grounded in the
lesson's source paper(s) and (optionally) a matched real repo.

Two-model split, consistent with the project's existing task-routing pattern
(cheap/structural tasks -> Gemini, heavy reasoning -> Groq):
  - Groq: produces the grounded PEDAGOGICAL scaffold (title, instructions,
    difficulty, hints) as structured JSON, using the same grounding-rules
    block as every other content-generating agent in the project.
  - Qwen (local, via Ollama): produces the CODE (starter w/ blanks +
    reference solution), since this is the one output nothing else in the
    pipeline can verify without execution — code-specialized models reduce
    the chance of subtly-wrong code slipping through ungrounded.

No code is ever executed anywhere in this system (same constraint as the
rest of the project). Students/teachers run the notebooks themselves.
"""

import os
import re
import json
from typing import Dict, List, Tuple, Optional

from langchain_ollama import ChatOllama

# These are assumed to already exist in agents/tools.py — imported here for
# clarity; when merging into tools.py just drop the import and use directly.
# from agents.tools import (
#     _groq_invoke_safe, _safe_json_parse, _get_paper_analysis_by_title,
# )


# ---------- Qwen (local) client ----------

_qwen_llm = None


def _get_qwen_llm():
    return ChatOllama(
        model="qwen2.5-coder:7b",
        temperature=0.1,
        timeout=180,   
    )


def _ensure_qwen():
    global _qwen_llm
    if _qwen_llm is None:
        _qwen_llm = _get_qwen_llm()
    return _qwen_llm


def _qwen_invoke_safe(prompt: str, retries: int = 2) -> str:
    """
    Local model, no external rate limit, but Ollama can be unreachable
    (server not running) or briefly busy — retry a couple times, then
    fail loudly rather than silently falling back to a cloud model for
    the code-generation step (defeats the point of using a coder model).
    """
    llm = _ensure_qwen()
    last_err = None
    for attempt in range(retries):
        try:
            response = llm.invoke(prompt)
            content = response.content
            if isinstance(content, list):
                content = "".join(
                    b.get("text", "") if isinstance(b, dict) else str(b) for b in content
                )
            return content
        except Exception as e:
            last_err = e
            print(f"[qwen] attempt {attempt+1} failed: {e}")
    raise RuntimeError(f"Qwen (Ollama) unreachable after {retries} attempts: {last_err}")


def _extract_code_block(text: str) -> str:
    """
    Coder-tuned models routinely wrap output in ```python fences even when
    told not to — strip them rather than trusting the instruction alone.
    """
    text = text.strip()
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


# ---------- PEDAGOGICAL SCAFFOLD (Groq) ----------

LAB_GROUNDING_RULES = """CRITICAL — grounding rules:
- Base every part of this exercise ONLY on the lesson content and paper text provided below.
  Do not supplement with generic textbook exercises not tied to this specific material.
- If a matched repository is provided, the exercise should build on what that repo actually
  does (per its description/readme), not a generic reimplementation of the paper from scratch.
- If no matched repository is provided or the lesson is purely conceptual (no algorithm,
  implementation, or dataset to work with), set "format" to "conceptual" and leave the code
  guidance fields empty rather than inventing an exercise that isn't supported by the material."""


def _build_scaffold_prompt(lesson: Dict, module: Dict, source_text: str, repo_text: str) -> str:
    schema_instructions = """Return ONLY valid JSON with this exact structure, no markdown fences:
{
  "exercise_title": "...",
  "format": "notebook" | "fill_in_blank" | "conceptual",
  "learning_objective": "...",
  "instructions": "...",
  "difficulty": "beginner" | "intermediate" | "advanced",
  "hints": ["..."],
  "code_generation_brief": "..."
}

IMPORTANT:
- "instructions" is what the student sees before starting — describe the task, not the solution.
- "code_generation_brief" is INTERNAL: a short, precise spec (what function/notebook to build,
  what inputs/outputs, what should be left blank for the student) that a code-generation step
  will use next. Only fill this in if format is "notebook" or "fill_in_blank".
- "difficulty" should match the module's stated difficulty unless the lesson content clearly
  suggests otherwise.
- "hints" should be 2-4 short nudges, not step-by-step answers."""

    return f"""You are designing a hands-on practice exercise for the lesson "{lesson.get('lesson_title', '')}"
in the module "{module.get('title', '')}".

Module problem: {module.get('problem_addressed', '')}
Module solution approach: {module.get('solution_approach', '')}
Target difficulty: {module.get('difficulty', 'intermediate')}

Lesson summary: {lesson.get('summary', '')}

Source material (paper content this lesson is grounded in):
{source_text or 'None available.'}

Matched real implementation (if any):
{repo_text or 'No sufficiently similar real implementation was found for this topic.'}

{LAB_GROUNDING_RULES}

{schema_instructions}
"""


def _generate_scaffold(lesson: Dict, module: Dict, source_text: str, repo_text: str) -> Dict:
    prompt = _build_scaffold_prompt(lesson, module, source_text, repo_text)
    content = _groq_invoke_safe(prompt)          # noqa: F821 — provided by tools.py
    parsed = _safe_json_parse(content)            # noqa: F821 — provided by tools.py
    return parsed if parsed else {"_error": "LLM output could not be parsed"}


# ---------- CODE GENERATION (Qwen, local) ----------

def _build_code_prompt(scaffold: Dict, source_text: str, repo_text: str) -> str:
    return f"""You are generating code for a student exercise.

Exercise: {scaffold.get('exercise_title', '')}
Brief: {scaffold.get('code_generation_brief', '')}
Instructions given to the student: {scaffold.get('instructions', '')}

Grounding material — paper implementation details:
{source_text or 'None available.'}

Grounding material — matched real implementation:
{repo_text or 'None available.'}

Produce TWO Python code blocks, clearly separated, and nothing else (no prose before/after):

### STARTER
A starter version of the code with the core learning step(s) replaced by
`# TODO: ...` comments describing what the student must fill in. Everything
else (imports, boilerplate, data loading if applicable) should be complete
and runnable as-is.

### SOLUTION
The complete reference solution filling in every TODO from the starter code.

Do not invent library calls, dataset names, or APIs that aren't implied by the
grounding material above. If the grounding material doesn't specify a dataset
or library, use a well-known, commonly available equivalent and say so in a
comment.
"""


def _generate_code(scaffold: Dict, source_text: str, repo_text: str) -> Dict:
    prompt = _build_code_prompt(scaffold, source_text, repo_text)
    raw = _qwen_invoke_safe(prompt)

    starter_match = re.search(r"###\s*STARTER\s*(.*?)###\s*SOLUTION", raw, re.DOTALL | re.IGNORECASE)
    solution_match = re.search(r"###\s*SOLUTION\s*(.*)", raw, re.DOTALL | re.IGNORECASE)

    starter_code = _extract_code_block(starter_match.group(1)) if starter_match else ""
    solution_code = _extract_code_block(solution_match.group(1)) if solution_match else ""

    if not starter_code or not solution_code:
        print("[lab] Qwen output didn't match expected STARTER/SOLUTION shape, storing raw output.")
        return {"starter_code": starter_code, "solution_code": solution_code, "_raw": raw}

    return {"starter_code": starter_code, "solution_code": solution_code}


# ---------- MAIN ENTRY POINT ----------

def generate_lab_exercise(
    lesson: Dict,
    module: Dict,
    papers_with_analysis: List[Dict],
    similar_projects_scored: Optional[List[Tuple[float, Dict]]] = None,
    similarity_threshold: float = 0.35,
    generate_code: bool = True,
) -> Dict:
    """
    lesson: one lesson dict from generate_lesson_for_module / course["modules"][i]["lessons"][j]
    module: the parent teaching-plan module dict
    papers_with_analysis: same shared list used everywhere else in the pipeline
    similar_projects_scored: List[(score, project_dict)] from compute_similarity_scores,
        same relevance-gate pattern as Technical Plan Agent — pass None/[] if not available.
    generate_code: if False, stops after the Groq scaffold (skips the Qwen call). Useful for
        a cheap "preview" pass before committing local-compute time to code + notebook export.
    """
    source_text = _get_paper_analysis_by_title(   # noqa: F821 — provided by tools.py
        papers_with_analysis, module.get("based_on_papers", [])
    )[:4000]

    repo_text = ""
    matched_repo = None
    if similar_projects_scored:
        relevant = [(s, p) for s, p in similar_projects_scored if s >= similarity_threshold]
        if relevant:
            relevant.sort(key=lambda x: x[0], reverse=True)
            score, matched_repo = relevant[0]
            repo_text = (
                f"[{matched_repo.get('source','')}] {matched_repo.get('name','')} "
                f"(similarity: {score:.0%})\n"
                f"About: {matched_repo.get('description','') or 'N/A'}\n"
                f"README excerpt: {(matched_repo.get('readme') or '')[:800]}"
            )

    scaffold = _generate_scaffold(lesson, module, source_text, repo_text)
    if scaffold.get("_error"):
        return scaffold

    result = {
        "exercise_title": scaffold.get("exercise_title", ""),
        "format": scaffold.get("format", "conceptual"),
        "learning_objective": scaffold.get("learning_objective", ""),
        "instructions": scaffold.get("instructions", ""),
        "difficulty": scaffold.get("difficulty", module.get("difficulty", "intermediate")),
        "hints": scaffold.get("hints", []),
        "based_on_module": module.get("title", ""),
        "based_on_lesson": lesson.get("lesson_title", ""),
        "based_on_repo": {
            "name": matched_repo.get("name", ""),
            "url": matched_repo.get("url", ""),
        } if matched_repo else None,
    }

    if generate_code and scaffold.get("format") in ("notebook", "fill_in_blank"):
        code = _generate_code(scaffold, source_text, repo_text)
        result.update(code)

    return result


# ---------- NOTEBOOK EXPORT (deterministic, no LLM) ----------

def export_lab_to_notebook(lab: Dict, output_dir: str, filename_base: str) -> Optional[Dict[str, str]]:
    """
    Renders a lab exercise into two .ipynb files: one for the student
    (starter code, blanks intact) and one for the teacher (solution).
    Returns None if the lab has no code (format == "conceptual").
    """
    if lab.get("format") not in ("notebook", "fill_in_blank") or not lab.get("starter_code"):
        return None

    import nbformat as nbf

    os.makedirs(output_dir, exist_ok=True)

    def _build(code: str) -> "nbf.NotebookNode":
        nb = nbf.v4.new_notebook()
        intro = f"# {lab.get('exercise_title','Exercise')}\n\n" \
                f"**Objective:** {lab.get('learning_objective','')}\n\n" \
                f"{lab.get('instructions','')}\n\n" \
                f"**Difficulty:** {lab.get('difficulty','')}"
        if lab.get("based_on_repo"):
            intro += f"\n\n**Reference implementation:** [{lab['based_on_repo']['name']}]({lab['based_on_repo']['url']})"
        cells = [nbf.v4.new_markdown_cell(intro)]
        if lab.get("hints"):
            hints_md = "**Hints:**\n" + "\n".join(f"- {h}" for h in lab["hints"])
            cells.append(nbf.v4.new_markdown_cell(hints_md))
        cells.append(nbf.v4.new_code_cell(code))
        nb["cells"] = cells
        return nb

    student_path = os.path.join(output_dir, f"{filename_base}_student.ipynb")
    solution_path = os.path.join(output_dir, f"{filename_base}_solution.ipynb")

    with open(student_path, "w", encoding="utf-8") as f:
        nbf.write(_build(lab["starter_code"]), f)
    with open(solution_path, "w", encoding="utf-8") as f:
        nbf.write(_build(lab.get("solution_code", "# solution not generated")), f)

    return {"student_notebook": student_path, "solution_notebook": solution_path}