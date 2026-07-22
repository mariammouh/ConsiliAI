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
from ingestion.chroma_client import cache_collection
from ingestion.embedding_model import embed
import json
import base64
load_dotenv()

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
                "source": "arxiv"
            })
    except Exception as e:
        print(f"arXiv search error: {e}")

    # --- Semantic Scholar ---
    ss_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    headers = {"x-api-key": ss_api_key} if ss_api_key else {}
    try:
        ss_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,authors,abstract,url"
        }
        resp = requests.get(ss_url, params=params, headers=headers)
        if resp.status_code == 429:
            time.sleep(2)
            resp = requests.get(ss_url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        for paper in data.get("data", []):
            fresh_papers.append({
                "title": paper.get("title", "N/A"),
                "authors": [a["name"] for a in paper.get("authors", [])],
                "abstract": paper.get("abstract", "No abstract available."),
                "url": paper.get("url", ""),
                "source": "semantic_scholar"
            })
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

import requests
import numpy as np

def filter_papers_hybrid(papers: List[Dict], user_idea: str, embed_top_k: int = 10, llm_top_n: int = 10) -> List[Dict]:
    """
    Two-stage hybrid filter:
    1. Embedding pre-filter: keep top embed_top_k papers by cosine similarity.
    2. LLM re-rank: from those, select the final llm_top_n most relevant.
    """
    if not papers:
        return []

    # Stage 1: Embedding similarity
    idea_emb = np.array(embed(user_idea))
    scored = []
    for p in papers:
        text = p['title'] + " " + (p['abstract'] or "")
        paper_emb = np.array(embed(text))
        sim = np.dot(idea_emb, paper_emb) / (np.linalg.norm(idea_emb) * np.linalg.norm(paper_emb))
        scored.append((sim, p))
    
    # Sort descending by similarity, take top embed_top_k
    scored.sort(key=lambda x: x[0], reverse=True)
    pre_filtered = [p for _, p in scored[:embed_top_k]]

    # Stage 2: LLM re-rank (using Groq)
    papers_text = "\n\n".join(
        f"Paper {i+1}:\nTitle: {p['title']}\nAbstract: {(p['abstract'] or '')[:500]}"
        for i, p in enumerate(pre_filtered)
    )
    prompt = f"""User's project idea: "{user_idea}"

Below are {len(pre_filtered)} papers pre‑selected by semantic similarity. From these, choose exactly the {llm_top_n} most directly relevant to the user's idea. Return ONLY their numbers, separated by commas (e.g., "2,5,7").

Papers:
{papers_text}"""

    response = _groq_llm.invoke(prompt)
    content = response.content.strip()
    import re
    numbers = re.findall(r'\d+', content)
    indices = [int(n) - 1 for n in numbers if 1 <= int(n) <= len(pre_filtered)]
    if not indices:
        indices = list(range(min(llm_top_n, len(pre_filtered))))
    return [pre_filtered[i] for i in indices[:llm_top_n]]
def search_openalex(query: str, max_results: int = 5) -> List[Dict]:
    base_url = "https://api.openalex.org/works"
    params = {
        "filter": f"title.search:{query}",   # raw query, no manual encoding
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
        papers.append({
            "title": work.get("title", "N/A"),
            "authors": [a["author"]["display_name"] for a in work.get("authorships", [])],
            "abstract": abstract,
            "url": work.get("id", ""),
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

    response = _groq_llm.invoke(prompt)
    content = response.content.strip()
    # Extract numbers from the response
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

    response = _groq_llm.invoke(prompt)
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
        response = _groq_llm.invoke(prompt)
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

# Common paper section headers, normalized. Order matters for detection.
SECTION_HEADER_PATTERNS = {
    "abstract": r"abstract",
    "introduction": r"introduction",
    "related_work": r"related\s+work|background|prior\s+work|literature\s+review",
     "methodology": r"method(ology|s)?|approach|proposed\s+(method|approach|model)",
    "experimental_setup": r"experimental\s+(implementation|setup|details)|implementation\s+details|datasets?(\s+and\s+.*)?",
    "results": r"results?(\s+and\s+discussion)?|experiments?(\s+and\s+results)?|evaluation",
    "discussion": r"discussion",
    "conclusion": r"conclusion(s)?|future\s+work",
    "references": r"references|bibliography",
}

def heuristic_split_sections(text: str) -> Dict[str, str]:
    """
    Detect section boundaries using common academic headers.
    Looks for short standalone lines (likely headers) matching known patterns,
    optionally prefixed with a number (e.g. '3. Methodology', 'III. Results').
    """
    lines = text.split("\n")
    header_line_regex = re.compile(
        r"^\s*(?:\d+\.?\d*\.?|\bI{1,3}V?\.?|\bIV\.?|\bV\.?)?\s*([A-Za-z][A-Za-z\s]{2,40})\s*$"
    )

    found_headers = []  # list of (line_index, normalized_section_name, raw_header)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 60:
            continue
        match = header_line_regex.match(stripped)
        if not match:
            continue
        candidate = match.group(1).strip().lower()
        for section_name, pattern in SECTION_HEADER_PATTERNS.items():
            if re.fullmatch(pattern, candidate) or re.match(pattern, candidate):
                found_headers.append((i, section_name, stripped))
                break

    if len(found_headers) < 2:
        return {}  # not enough signal, trigger LLM fallback

    sections = {}
    for idx, (line_no, section_name, _) in enumerate(found_headers):
        start = line_no + 1
        end = found_headers[idx + 1][0] if idx + 1 < len(found_headers) else len(lines)
        content = "\n".join(lines[start:end]).strip()
        if content:
            # if the same section name appears twice, keep the longer chunk
            if section_name in sections and len(sections[section_name]) >= len(content):
                continue
            sections[section_name] = content

    return sections


def llm_split_sections(text: str) -> Dict[str, str]:
    """
    Fallback: ask the LLM to segment the paper when heuristics fail
    (e.g. no clear headers, messy PDF extraction).
    """
    # Truncate to keep prompt manageable; papers are long
    truncated = text
    prompt = f"""You are analyzing a scientific paper. Split the text below into its logical sections.
Use these exact keys where applicable: abstract, introduction, related_work, methodology, results, discussion, conclusion.
If a section is missing, omit its key. Return ONLY valid JSON, no markdown fences, no explanation.

Format:
{{"introduction": "...", "methodology": "...", "results": "..."}}

Paper text:
{truncated}
"""
    response = _groq_llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = "".join(block.get('text', '') if isinstance(block, dict) else str(block) for block in content)

    return _safe_json_parse(content)


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


def split_paper_sections(text: str) -> Dict[str, str]:
    """
    Main entry point: try heuristic split first (fast, free),
    fall back to LLM split only if heuristics fail.
    """
    sections = heuristic_split_sections(text)
    if len(sections) >= 2:
        return sections

    print("Heuristic splitting failed or incomplete, falling back to LLM.")
    return llm_split_sections(text)
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

def analyze_section(section_text: str, section_type: str) -> Dict:
    """
    Given a section's text and its type, extract structured fields
    according to that section's schema. Falls back to a generic schema
    if the section type isn't recognized.
    """
    schema = SECTION_SCHEMAS.get(section_type, {
        "fields": ["summary"],
        "instructions": "Summarize the key points of this section."
    })

    fields_list = ", ".join(schema["fields"])
    prompt = f"""You are analyzing the "{section_type}" section of a scientific paper.

{schema['instructions']}

Return ONLY valid JSON with exactly these keys: {fields_list}.
Use empty string or empty list if a field isn't present in the text. No markdown fences, no explanation.

Section text:
{section_text}
"""
    response = _groq_llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = "".join(block.get('text', '') if isinstance(block, dict) else str(block) for block in content)

    parsed = _safe_json_parse(content)
    if not parsed:
        parsed = {field: "" for field in schema["fields"]}
        parsed["_error"] = "LLM output could not be parsed"
    return parsed


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