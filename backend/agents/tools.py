import os
import requests
import time
from typing import List, Dict
from dotenv import load_dotenv
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
#from langchain_community.chat_models import ChatOllama  # or langchain_ollama

#_ollama_llm = ChatOllama(model="llama3.1:8b", temperature=0.2)
# LLM instance for this tool (can be reused)
_gemini_llm  = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",  # or the exact name you used successfully
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0
)
_groq_llm = ChatOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",   # <-- updated model
    temperature=0.2
)
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

    response = _gemini_llm .invoke(prompt)
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
    

def filter_papers_hybrid(papers: List[Dict], user_idea: str, embed_top_k: int = 10, llm_top_n: int = 10) -> List[Dict]:
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

    content = _gemini_llm.invoke(prompt).content
    if isinstance(content, list):
        content = "".join(b.get('text', '') if isinstance(b, dict) else str(b) for b in content)
    content = content.strip()

    numbers = re.findall(r'\d+', content)
    indices = [int(n) - 1 for n in numbers if 1 <= int(n) <= len(pre_filtered)]
    if not indices:
        indices = list(range(min(llm_top_n, len(pre_filtered))))
    return [pre_filtered[i] for i in indices[:llm_top_n]]

def search_openalex(query: str, max_results: int = 5) -> List[Dict]:
    base_url = "https://api.openalex.org/works"
    params = {
        "filter": f"title.search:{query}",
        "per-page": max_results,
        "sort": "relevance"
    }
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

    content = _gemini_llm.invoke(prompt).content
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
            response = _gemini_llm.invoke(prompt)
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
                "file_count": ds.file_count,
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
        params = {"q": query, "items_per_page": max_results}  
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
def _groq_invoke_safe(prompt: str, retries: int = 2, wait_seconds: float = 8.0) -> str:
    """
    Try Groq first (best reasoning). On rate-limit exhaustion, fall back to
    Gemini so the pipeline doesn't crash — not because Gemini is preferred.
    """
    for attempt in range(retries):
        try:
            _groq_budget.consume(len(prompt)//4)
            response = _groq_llm.invoke(prompt)
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
        response = _gemini_llm.invoke(prompt)
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


def detect_gaps(user_idea: str, papers_with_analysis: List[Dict], max_chars: int = 3000) -> Dict:
    """
    papers_with_analysis: list of {"title": str, "analysis": Dict}
    (the output of analyze_all_sections per paper, paired with its title)

    Returns a structured list of research gaps synthesized across all papers.
    """
    if not papers_with_analysis:
        return {"gaps": [], "_error": "No papers provided for gap analysis."}

    per_paper_summaries = [
        _extract_gap_relevant_text(p["title"], p["analysis"])
        for p in papers_with_analysis
    ]
    combined_text = "\n\n---\n\n".join(per_paper_summaries)

    chunks = chunk_text(combined_text, max_chars=max_chars)

    schema_instructions = """Return ONLY valid JSON with this exact structure, no markdown fences:
{
  "gaps": [
    {
      "gap_description": "...",
      "supporting_evidence": "...",
      "papers_involved": ["paper title 1", "paper title 2"],
      "opportunity": "..."
    }
  ]
}
Each gap should describe something unsolved, under-explored, or contradictory across the papers.
"opportunity" should briefly state what a new project/experiment could do to address it."""

    if len(chunks) == 1:
        prompt = f"""User's project idea: "{user_idea}"

You are analyzing a set of research papers to identify gaps in the current state of the art relevant to this idea.

{schema_instructions}

Papers analyzed:
{chunks[0]}
"""
        content = _groq_invoke_safe(prompt)
        parsed = _safe_json_parse(content)
        return parsed if parsed else {"gaps": [], "_error": "LLM output could not be parsed"}

    # Multi-chunk: detect gaps per chunk, then merge and deduplicate with a final pass
    print(f"Gap detection input split into {len(chunks)} chunks for rate-limit safety.")
    partial_gaps = []
    for i, chunk in enumerate(chunks):
        prompt = f"""User's project idea: "{user_idea}"

You are analyzing part {i+1} of {len(chunks)} of a set of research paper summaries to identify gaps relevant to this idea.

{schema_instructions}

Papers analyzed (part {i+1}/{len(chunks)}):
{chunk}
"""
        content = _groq_invoke_safe(prompt)
        parsed = _safe_json_parse(content)
        if parsed and parsed.get("gaps"):
            partial_gaps.extend(parsed["gaps"])
        time.sleep(2)

    if not partial_gaps:
        return {"gaps": [], "_error": "No gaps extracted from any chunk."}

    # Final consolidation pass: dedupe/merge overlapping gaps found across chunks
    return _consolidate_gaps(user_idea, partial_gaps)


def _consolidate_gaps(user_idea: str, raw_gaps: List[Dict]) -> Dict:
    """
    Merge/deduplicate gaps found across multiple chunks into a clean final list.
    """
    gaps_text = json.dumps(raw_gaps, indent=2)[:6000]  # cap in case of many gaps
    prompt = f"""User's project idea: "{user_idea}"

Below is a raw list of research gaps extracted from different parts of a literature batch. Some may be duplicates or near-duplicates. Consolidate them into a clean, deduplicated final list, merging similar gaps and keeping the most specific/useful description.

Return ONLY valid JSON in this format:
{{"gaps": [{{"gap_description": "...", "supporting_evidence": "...", "papers_involved": [...], "opportunity": "..."}}]}}

Raw gaps:
{gaps_text}
"""
    content = _groq_invoke_safe(prompt)
    parsed = _safe_json_parse(content)
    return parsed if parsed else {"gaps": raw_gaps, "_note": "Consolidation failed, returning raw merged list."}

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
