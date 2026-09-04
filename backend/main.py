from fastapi import FastAPI, UploadFile, File, Form
from fastapi import HTTPException
from fastapi.params import Depends
from fastapi.responses import JSONResponse, FileResponse
from starlette.background import BackgroundTask
import os, shutil
import asyncio
import requests
from dotenv import load_dotenv
from ingestion.pdf_processor import process_pdf, UPLOAD_DIR
from ingestion.chroma_client import delete_conversation_documents, delete_user_documents
from agents.tools import _hash_text,generate_experiment_set, retrieve_from_knowledge_base,broaden_idea,get_papers_with_analysis
from agents.tools import search_papers, filter_relevant_papers,filter_papers_hybrid, summarize_papers_with_groq
from agents.tools import search_papers_formatted,fetch_full_text,extract_text_from_pdf_bytes
from auth.db import create_db_and_tables, User, Conversation, get_async_session
from auth.schemas import UserRead, UserCreate, UserUpdate
from auth.users import fastapi_users, current_active_user, auth_backend
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
import tempfile
from agents.orchestrator import (
    run_orchestrator_turn,
    get_state_snapshot,
    record_uploaded_document,
    register_cancel_event,
    cancel_thread_execution,
    clear_cancel_event,
    ExecutionCancelledError,
    build_enriched_evaluation_record,
    record_benchmark_evaluation,
)
from export_project import build_project_zip_archive

load_dotenv()

# Active message generation tasks keyed by conversation_id
active_chat_tasks: dict[str, asyncio.Task] = {}



def _chat_state_response(state: dict) -> dict:
    papers_raw = state.get("papers_with_analysis") or []
    formatted_papers = []
    for p in papers_raw:
        analysis = p.get("analysis", {}) or {}
        sections_detected = list(analysis.keys()) if isinstance(analysis, dict) else []
        url_val = p.get("url", "")
        pdf_url_val = p.get("pdf_url", "")
        source_val = p.get("source", "N/A")
        # DEBUG: log what we're sending to the frontend
        print(f"[DEBUG _chat_state_response] title={p.get('title','?')!r} | url={url_val!r} | pdf_url={pdf_url_val!r} | source={source_val!r}")
        formatted_papers.append({
            "title": p.get("title", "Untitled Paper"),
            "authors": p.get("authors", []),
            "url": url_val,
            "pdf_url": pdf_url_val,
            "source": source_val,
            "sections_detected": sections_detected,
            "abstract": p.get("abstract", "") or (analysis.get("abstract", {}).get("summary", "") if isinstance(analysis, dict) else ""),
            "analysis": analysis,
        })

    scored_projects = state.get("similar_projects_scored") or state.get("similar_projects_raw") or []
    formatted_projects = []
    for item in scored_projects:
        if isinstance(item, (tuple, list)) and len(item) == 2 and isinstance(item[1], dict):
            score, proj = item[0], item[1]
        elif isinstance(item, dict):
            proj = item
            score = proj.get("similarity_score", proj.get("score", 0.5))
        else:
            continue
        formatted_projects.append({
            "name": proj.get("name") or proj.get("title", "Unnamed Repo"),
            "url": proj.get("url", "") or proj.get("html_url", ""),
            "source": proj.get("source", "N/A"),
            "description": proj.get("description", "") or proj.get("readme_snippet", "") or proj.get("readme", ""),
            "similarity_score": round(score * 100, 1) if isinstance(score, (int, float)) and score <= 1.0 else (round(score, 1) if isinstance(score, (int, float)) else score),
        })

    return {
        "idea": state.get("idea"),
        "papers": formatted_papers,
        "similar_projects": formatted_projects,
        "novelty_analysis": state.get("novelty_analysis"),
        "gaps": state.get("gaps"),
        "technical_plan": state.get("technical_plan"),
        "teaching_plan": state.get("teaching_plan"),
        "course": state.get("course"),
        "course_downloads": _course_downloads(state),
        "lab_downloads": _lab_downloads(state),
        "lab_exercises": state.get("lab_exercises"),
        "practical_exercises": state.get("lab_exercises") or state.get("practical_exercises"),
        "experiments": state.get("experiments"),
        "evaluations": state.get("evaluations") or [],
    }


def _course_downloads(state: dict) -> list[dict]:
    export_path = state.get("course_export_path")
    if not export_path or not isinstance(export_path, str):
        return []

    paths = [path.strip() for path in export_path.split(",") if path.strip()]
    return [
        {
            "label": f"Download lesson {index}",
            "filename": os.path.basename(path),
            "url": f"/chat/course-download/{os.path.basename(path)}",
        }
        for index, path in enumerate(paths, start=1)
    ]


def _lab_downloads(state: dict) -> list[dict]:
    downloads = []
    raw_labs = state.get("lab_exercises") or []
    if isinstance(raw_labs, dict):
        modules = raw_labs.get("modules") or raw_labs.get("lab_exercises") or []
    elif isinstance(raw_labs, list):
        modules = raw_labs
    else:
        modules = []

    if not isinstance(modules, list):
        return downloads

    for module in modules:
        if not isinstance(module, dict):
            continue
        lessons = module.get("lessons") or []
        if not isinstance(lessons, list):
            continue
        for lesson in lessons:
            if not isinstance(lesson, dict):
                continue
            lab_obj = lesson.get("lab") if isinstance(lesson.get("lab"), dict) else lesson
            lesson_title = (
                lab_obj.get("based_on_lesson")
                or lab_obj.get("exercise_title")
                or lab_obj.get("title")
                or "lesson"
            )
            notebook_files = lesson.get("notebook_files") or lab_obj.get("notebook_files") or {}
            if isinstance(notebook_files, dict):
                for notebook_type, path in notebook_files.items():
                    if path and isinstance(path, str):
                        filename = os.path.basename(path)
                        downloads.append({
                            "label": f"Download {lesson_title} ({notebook_type.replace('_', ' ')})",
                            "filename": filename,
                            "url": f"/chat/lab-download/{filename}",
                        })
    return downloads

app = FastAPI()
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"]
)


@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()



@app.post("/conversations")
async def create_conversation(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    new_conv = Conversation(user_id=user.id, title="New Conversation")
    session.add(new_conv)
    await session.commit()
    await session.refresh(new_conv)
    return {"id": new_conv.id, "title": new_conv.title, "created_at": new_conv.created_at.isoformat()}

@app.get("/conversations")
async def get_conversations(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc())
    )
    convs = result.scalars().all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()} for c in convs]

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 1. Cancel any active execution on this conversation
    cancel_thread_execution(conversation_id)
    task = active_chat_tasks.get(conversation_id)
    if task and not task.done():
        task.cancel()

    # 2. Delete LangGraph checkpoints in Postgres for this thread_id
    try:
        await session.execute(
            text("DELETE FROM checkpoint_writes WHERE thread_id = :tid"),
            {"tid": conversation_id}
        )
        await session.execute(
            text("DELETE FROM checkpoint_blobs WHERE thread_id = :tid"),
            {"tid": conversation_id}
        )
        await session.execute(
            text("DELETE FROM checkpoints WHERE thread_id = :tid"),
            {"tid": conversation_id}
        )
    except Exception as e:
        print(f"[delete_conversation] Warning deleting checkpoints for {conversation_id}: {e}")

    # 3. Delete ChromaDB document chunks associated with this conversation
    try:
        delete_conversation_documents(conversation_id)
    except Exception as e:
        print(f"[delete_conversation] Warning deleting Chroma chunks for {conversation_id}: {e}")

    # 4. Delete the conversation row
    await session.delete(conv)
    await session.commit()
    return {"message": "Deleted"}


@app.delete("/user/data")
async def delete_all_user_data(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Permanently delete ALL user-generated data for the current user:
    - All chats and conversation history
    - Generated plans, courses, labs, experiments in state/checkpoints
    - LangGraph checkpoint tables in Postgres
    - User document chunks in ChromaDB
    - User uploaded source files
    """
    result = await session.execute(
        select(Conversation).where(Conversation.user_id == user.id)
    )
    convs = result.scalars().all()
    conv_ids = [c.id for c in convs]

    # 1. Stop any currently active tasks for this user's conversations
    for cid in conv_ids:
        cancel_thread_execution(cid)
        task = active_chat_tasks.get(cid)
        if task and not task.done():
            task.cancel()

    # 2. Delete LangGraph checkpoints in Postgres for all user conversations and user_id
    threads_to_wipe = list(conv_ids) + [str(user.id)]
    if threads_to_wipe:
        try:
            await session.execute(
                text("DELETE FROM checkpoint_writes WHERE thread_id = ANY(:tids)"),
                {"tids": threads_to_wipe}
            )
            await session.execute(
                text("DELETE FROM checkpoint_blobs WHERE thread_id = ANY(:tids)"),
                {"tids": threads_to_wipe}
            )
            await session.execute(
                text("DELETE FROM checkpoints WHERE thread_id = ANY(:tids)"),
                {"tids": threads_to_wipe}
            )
        except Exception as e:
            print(f"[delete_all_user_data] Warning deleting Postgres checkpoints: {e}")

    # 3. Delete ChromaDB chunks for this user and their conversations
    deleted_sources = set()
    try:
        deleted_sources = delete_user_documents(str(user.id), conv_ids)
    except Exception as e:
        print(f"[delete_all_user_data] Warning deleting Chroma chunks: {e}")

    # 4. Remove physical uploaded files belonging to the deleted documents
    for src in deleted_sources:
        target_path = os.path.join(UPLOAD_DIR, src)
        if os.path.isfile(target_path):
            try:
                os.remove(target_path)
            except Exception as e:
                print(f"[delete_all_user_data] Could not remove file {target_path}: {e}")

    # 5. Delete all SQL conversation records
    for c in convs:
        await session.delete(c)
    await session.commit()

    return {
        "message": "All user data permanently deleted",
        "deleted_conversations_count": len(convs),
        "deleted_document_sources": list(deleted_sources),
    }


from pydantic import BaseModel, Field, field_validator


class SettingsPayload(BaseModel):
    llm_provider: str = Field(..., description="LLM provider choice: 'cloud' or 'local'")

    @field_validator("llm_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in ("cloud", "local"):
            raise ValueError("llm_provider must be 'cloud' or 'local'")
        return v


@app.get("/settings")
async def get_settings(user: User = Depends(current_active_user)):
    return {
        "llm_provider": getattr(user, "llm_provider", "cloud")
    }


@app.patch("/settings")
async def update_settings(
    payload: SettingsPayload,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    user.llm_provider = payload.llm_provider
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return {
        "llm_provider": user.llm_provider,
        "message": f"LLM provider updated to {user.llm_provider}"
    }


@app.post("/chat/{conversation_id}/stop")
async def stop_chat_endpoint(
    conversation_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Terminates the active message generation task for the given conversation.
    """
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 1. Signal cancellation event in orchestrator / worker threads
    cancel_thread_execution(conversation_id)

    # 2. Cancel running asyncio task
    task = active_chat_tasks.get(conversation_id)
    if task and not task.done():
        task.cancel()

    return {"status": "stopped", "message": "Execution stopped"}


@app.post("/chat/{conversation_id}")
async def chat_endpoint(
    conversation_id: str,
    message: str = Form(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    thread_id = conversation_id 

    # Truncate first message as title if it's the default
    if conv.title == "New Conversation":
        truncated = message[:30] + "..." if len(message) > 30 else message
        conv.title = truncated
        await session.commit()

    user_provider = getattr(user, "llm_provider", "cloud")

    # Register cancellation tracking
    register_cancel_event(conversation_id)
    current_task = asyncio.current_task()
    active_chat_tasks[conversation_id] = current_task

    try:
        reply = await asyncio.to_thread(
            run_orchestrator_turn,
            message=message,
            thread_id=thread_id,
            llm_provider=user_provider,
        )
    except (asyncio.CancelledError, ExecutionCancelledError) as e:
        print(f"[chat_endpoint] Execution cancelled for {conversation_id}")
        state = get_state_snapshot(thread_id)
        return JSONResponse(
            status_code=499,
            content={
                "detail": "Message execution stopped by user",
                "stopped": True,
                "state": _chat_state_response(state),
                "title": conv.title,
            }
        )
    finally:
        active_chat_tasks.pop(conversation_id, None)
        clear_cancel_event(conversation_id)

    state = get_state_snapshot(thread_id)

    return {
        "reply": reply,
        "state": _chat_state_response(state),
        "course_downloads": _course_downloads(state),
        "lab_downloads": _lab_downloads(state),
        "title": conv.title
    }


@app.get("/projects/{conversation_id}/download")
async def download_project_archive(
    conversation_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Generates and returns an organized ZIP archive containing all existing deliverables
    for a project (conversation).
    """
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Project/Conversation not found")

    state = get_state_snapshot(conversation_id)
    zip_path, filename = build_project_zip_archive(conv, state, str(user.id))

    return FileResponse(
        zip_path,
        filename=filename,
        media_type="application/zip",
        background=BackgroundTask(os.remove, zip_path)
    )


@app.get("/projects/download")
async def download_project_archive_query(
    conversation_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await download_project_archive(conversation_id, user, session)



@app.get("/chat/{conversation_id}/history")
async def chat_history_endpoint(
    conversation_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    thread_id = conversation_id
    state = get_state_snapshot(thread_id)

    messages = []
    for message in state.get("messages", []):
        message_type = getattr(message, "type", None)
        if message_type not in {"human", "ai"}:
            continue
        role = "user" if message_type == "human" else "assistant"

        content = message.content
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        if not str(content).strip():
            continue
        messages.append({"role": role, "content": str(content)})

    return {
        "messages": messages,
        "state": _chat_state_response(state),
        "course_downloads": _course_downloads(state),
        "lab_downloads": _lab_downloads(state),
    }


@app.get("/chat/course-download/{filename}")
async def chat_course_download_endpoint(
    filename: str,
    user: User = Depends(current_active_user),
):
    output_dir = os.path.abspath(os.path.join(tempfile.gettempdir(), "consiliai_courses"))
    requested_filename = os.path.basename(filename)
    target_path = os.path.abspath(os.path.join(output_dir, requested_filename))

    matching_path = None
    if target_path.startswith(output_dir) and os.path.isfile(target_path):
        matching_path = target_path
    else:
        for root, dirs, files in os.walk(output_dir):
            if requested_filename in files:
                candidate = os.path.abspath(os.path.join(root, requested_filename))
                if candidate.startswith(output_dir):
                    matching_path = candidate
                    break

    if not matching_path or not os.path.isfile(matching_path):
        raise HTTPException(status_code=404, detail="Course presentation file not found.")

    return FileResponse(
        matching_path,
        filename=requested_filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@app.get("/chat/lab-download/{filename}")
async def chat_lab_download_endpoint(
    filename: str,
    user: User = Depends(current_active_user),
):
    output_dir = os.path.abspath(os.path.join(tempfile.gettempdir(), "consiliai_labs"))
    requested_filename = os.path.basename(filename)
    target_path = os.path.abspath(os.path.join(output_dir, requested_filename))

    matching_path = None
    if target_path.startswith(output_dir) and os.path.isfile(target_path):
        matching_path = target_path
    else:
        for root, dirs, files in os.walk(output_dir):
            if requested_filename in files:
                candidate = os.path.abspath(os.path.join(root, requested_filename))
                if candidate.startswith(output_dir):
                    matching_path = candidate
                    break

    if not matching_path or not os.path.isfile(matching_path):
        raise HTTPException(status_code=404, detail="Lab notebook file not found.")

    return FileResponse(
        matching_path,
        filename=requested_filename,
        media_type="application/x-ipynb+json",
    )


def get_pptx_output_path(idea: str) -> str:
    """Cross-platform temp path for generated course pptx files."""
    output_dir = os.path.join(tempfile.gettempdir(), "consiliai_courses")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"course_{_hash_text(idea)[:8]}.pptx"
    return os.path.join(output_dir, filename)
@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    conversation_id: str = Form(None),
    user: User = Depends(current_active_user),
):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    num_chunks = process_pdf(
        file_path,
        user_id=str(user.id),
        conversation_id=str(conversation_id) if conversation_id else None
    )

    updated_state = None
    target_thread = str(conversation_id) if conversation_id else str(user.id)
    try:
        snap = record_uploaded_document(
            thread_id=target_thread,
            filename=file.filename,
            file_path=file_path,
            user_id=str(user.id)
        )
        updated_state = _chat_state_response(snap)
    except Exception as e:
        print(f"[upload_pdf] Warning recording uploaded document in state: {e}")

    return {
        "message": f"✅ {file.filename} uploaded and indexed.",
        "chunks": num_chunks,
        "state": updated_state,
        "idea": updated_state.get("idea") if updated_state else None,
    }


@app.post("/ask")
async def ask_question(
    question: str = Form(...),
    user: User = Depends(current_active_user)
):
    answer = retrieve_from_knowledge_base(question, user_id=str(user.id))
    return {"answer": answer}

# Optional: keep debug endpoint
@app.post("/debug_chunks")
async def debug_chunks(
    question: str = Form(...),
    user: User = Depends(current_active_user)
):
    from ingestion.chroma_client import query_chroma
    chunks = query_chroma(question, user_id=str(user.id))
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
    if teaching_plan.get("_error"):
        print(f"[generate_lab] teaching_plan failed: {teaching_plan['_error']}")
    course = generate_course(teaching_plan, papers_with_analysis)
    if not course.get("modules"):
        print(f"[generate_lab] course empty — teaching_plan had {len(teaching_plan.get('modules', []))} modules")
 
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


@app.post("/generate_experiments")
async def generate_experiments_endpoint(
    idea: str = Form(...),
    max_papers: int = Form(3),
    max_experiments: int = Form(6),
):
    papers_with_analysis = get_papers_with_analysis(idea, max_papers)
    if not papers_with_analysis:
        return {"error": "No papers could be analyzed for this idea."}

    gaps_result = detect_gaps(idea, papers_with_analysis)

    # CHANGED: no compute_similarity_scores(idea, similar) here anymore —
    # that idea-level scoring is what caused every gap to get the same repo.
    # Just fetch the raw candidate pool once (still one search per idea,
    # same cost as before) and let per-gap scoring happen downstream.
    similar_raw = search_similar_projects(idea, max_results=15)

    experiment_set = generate_experiment_set(
        idea=idea,
        gaps=gaps_result.get("gaps", []),
        papers_with_analysis=papers_with_analysis,
        similar_projects_raw=similar_raw,   # <-- renamed, raw not scored
        max_experiments=max_experiments,
    )

    return {
    "idea": idea,
    "experiments": experiment_set["experiments"],
    "gaps_used": experiment_set["gaps_used"],
    "papers_used": [p["title"] for p in papers_with_analysis],
    "papers_with_analysis": papers_with_analysis,   
}


import json as _json
from agents.tools import generate_benchmark_evaluation  
@app.post("/evaluate_benchmark")
async def evaluate_benchmark_endpoint(
    experiment: str = Form(...),              # JSON string, one experiment dict
    papers_with_analysis: str = Form("[]"),    # JSON string, list of {title, analysis}
    submission_text: str = Form(None),
    submission_file: UploadFile = File(None),
    conversation_id: str = Form(None),
):
    try:
        experiment_dict = _json.loads(experiment)
    except Exception:
        return {"error": "`experiment` must be a valid JSON string of one experiment object."}

    try:
        papers_dict = _json.loads(papers_with_analysis) if papers_with_analysis else []
    except Exception:
        papers_dict = []

    # If papers not explicitly provided, try to load from conversation state
    if not papers_dict and conversation_id:
        try:
            current_snap = get_state_snapshot(conversation_id)
            papers_dict = current_snap.get("papers_with_analysis") or []
        except Exception:
            papers_dict = []

    if submission_file is not None:
        pdf_bytes = await submission_file.read()
        text = extract_text_from_pdf_bytes(pdf_bytes)
    elif submission_text:
        text = submission_text
    else:
        return {"error": "Provide either submission_text or submission_file."}

    print(f"[evaluate_benchmark] received submission text length: {len(text)} characters for {experiment_dict.get('title')}")
    raw_result = generate_benchmark_evaluation(
        experiment=experiment_dict,
        papers_with_analysis=papers_dict,
        submission_text=text,
    )

    existing_evals = []
    if conversation_id:
        try:
            snap = get_state_snapshot(conversation_id)
            existing_evals = list(snap.get("evaluations") or [])
        except Exception:
            existing_evals = []

    enriched_eval = build_enriched_evaluation_record(
        experiment=experiment_dict,
        benchmark_result=raw_result,
        submission_text=text,
        existing_evaluations=existing_evals,
    )

    if conversation_id:
        try:
            updated_snap = record_benchmark_evaluation(conversation_id, enriched_eval)
            return {
                "evaluation": enriched_eval,
                "evaluations": updated_snap.get("evaluations", []),
                "state": _chat_state_response(updated_snap),
            }
        except Exception as e:
            print(f"[evaluate_benchmark] Warning: could not update checkpointer state: {e}")

    return {
        "evaluation": enriched_eval,
        "evaluations": [enriched_eval],
    }

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)