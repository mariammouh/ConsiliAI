import os
import json
import urllib.request
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional, Tuple, Any, List, Dict
from langchain_core.language_models.chat_models import BaseChatModel


# Task Category Constants
TASK_ANALYTICAL = "analytical"
TASK_PLANNING = "planning"
TASK_CONTENT_GENERATION = "content_generation"
TASK_GENERAL_CHAT = "general_chat"

TASK_CATEGORIES = [
    TASK_ANALYTICAL,
    TASK_PLANNING,
    TASK_CONTENT_GENERATION,
    TASK_GENERAL_CHAT,
]

TASK_CATEGORIES_METADATA = [
    {
        "key": TASK_ANALYTICAL,
        "label": "Analytical Tasks",
        "description": "Paper analysis, literature synthesis, section extraction, and research gap detection.",
    },
    {
        "key": TASK_PLANNING,
        "label": "Planning Tasks",
        "description": "Technical project plans, architecture design, course syllabi, and teaching plans.",
    },
    {
        "key": TASK_CONTENT_GENERATION,
        "label": "Content Generation",
        "description": "Course content, student experiments, practical coding exercises, and runnable Jupyter notebooks.",
    },
    {
        "key": TASK_GENERAL_CHAT,
        "label": "General Chat",
        "description": "Conversational orchestration, intent classification, and direct user Q&A.",
    },
]

DEFAULT_TASK_MODELS_CLOUD = {
    TASK_ANALYTICAL: "groq:qwen/qwen3.6-27b",               # fast analytical extraction
    TASK_PLANNING: "gemini:gemini-3.1-flash-lite",           # large JSON (teaching plan) — 1500 req/day
    TASK_CONTENT_GENERATION: "gemini:gemini-3.1-flash-lite", # large JSON (course content) — 1500 req/day
    TASK_GENERAL_CHAT: "groq:qwen/qwen3.6-27b",
}

DEFAULT_TASK_MODELS_LOCAL = {
    TASK_ANALYTICAL: "ollama:llama3.2:3b",
    TASK_PLANNING: "ollama:llama3.2:3b",
    TASK_CONTENT_GENERATION: "ollama:qwen2.5-coder:7b",
    TASK_GENERAL_CHAT: "ollama:llama3.2:3b",
}


# Context variables to track active provider, task models, active task category, and fallback status per request
active_provider_var: ContextVar[str] = ContextVar("active_provider_var", default="cloud")
active_task_models_var: ContextVar[Dict[str, str]] = ContextVar("active_task_models_var", default={})
current_task_category_var: ContextVar[str] = ContextVar("current_task_category_var", default=TASK_GENERAL_CHAT)
fallback_note_var: ContextVar[Optional[str]] = ContextVar("fallback_note_var", default=None)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
DEFAULT_OLLAMA_CODER_MODEL = os.getenv("OLLAMA_CODER_MODEL", "qwen2.5-coder:7b")

_llm_cache: Dict[str, BaseChatModel] = {}
_ollama_llm_cache = {}


def set_active_provider(provider: str) -> None:
    """Set the active LLM provider for the current context ('cloud' | 'local')."""
    if provider in ("cloud", "local"):
        active_provider_var.set(provider)
        fallback_note_var.set(None)


def get_active_provider() -> str:
    """Get the active LLM provider for the current context."""
    return active_provider_var.get()


def set_active_task_models(task_models: Optional[Dict[str, str]]) -> None:
    """Set custom task model mappings for the current context."""
    if isinstance(task_models, dict):
        active_task_models_var.set(task_models)
    else:
        active_task_models_var.set({})


def get_active_task_models() -> Dict[str, str]:
    """Get custom task model mappings for the current context."""
    return active_task_models_var.get() or {}


def set_task_category(category: str) -> None:
    """Set the active task category in current context."""
    if category in TASK_CATEGORIES:
        current_task_category_var.set(category)


def get_current_task_category() -> str:
    """Get the active task category in current context."""
    return current_task_category_var.get() or TASK_GENERAL_CHAT


@contextmanager
def task_category_context(category: str):
    """Context manager for scoping execution to a specific task category."""
    token = current_task_category_var.set(category)
    try:
        yield
    finally:
        current_task_category_var.reset(token)


def set_fallback_note(note: Optional[str]) -> None:
    """Record a fallback note for user notification."""
    fallback_note_var.set(note)


def get_fallback_note() -> Optional[str]:
    """Retrieve any active fallback note for the current context."""
    return fallback_note_var.get()


def get_available_ollama_models() -> List[str]:
    """Fetch list of installed model names from local Ollama server."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        pass
    return []


def is_ollama_available() -> bool:
    """Check if local Ollama server is reachable."""
    return len(get_available_ollama_models()) > 0 or bool(get_available_ollama_models_raw())


def get_available_ollama_models_raw() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_available_models_catalog() -> Dict[str, Any]:
    """
    Dynamically discovers and catalogs available models across all configured providers
    (local Ollama, cloud Groq, and cloud Gemini).
    """
    # 1. Local Ollama models
    ollama_models = []
    ollama_online = False
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                ollama_online = True
                data = json.loads(resp.read().decode("utf-8"))
                for m in data.get("models", []):
                    raw_name = m.get("name", "")
                    if not raw_name:
                        continue
                    size_bytes = m.get("size", 0)
                    size_str = f"{size_bytes / (1024**3):.1f} GB" if size_bytes else ""
                    details = m.get("details", {})
                    param_size = details.get("parameter_size", "")
                    quant = details.get("quantization_level", "")
                    details_str = f"{param_size} ({quant})".strip() if param_size else "Local Ollama model"
                    caps = m.get("capabilities", [])
                    ollama_models.append({
                        "id": f"ollama:{raw_name}",
                        "name": raw_name,
                        "provider": "ollama",
                        "is_local": True,
                        "size": size_str,
                        "details": details_str,
                        "capabilities": caps,
                    })
    except Exception:
        ollama_online = False

    # 2. Cloud Groq models (Strictly verified, reliable, free-tier chat models)
    groq_models = []
    groq_online = False
    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {groq_key}", "User-Agent": "ConsiliAI/1.0"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    groq_online = True
                    gdata = json.loads(resp.read().decode("utf-8"))
                    # Explicit exclusion of audio, preview, guard, and non-chat models
                    excluded_groq = ["whisper", "guard", "vision", "orpheus", "canopylabs", "gpt-oss", "safeguard"]
                    verified_groq_mids = {
                        "qwen/qwen3.6-27b": "Qwen 2.5 27B - High throughput reasoning (Default)",
                        "qwen/qwen3.8-27b": "Qwen 2.5 27B - Fast cloud inference",
                        "groq/compound": "Groq Compound reasoning",
                        "groq/compound-mini": "Groq Compound lightweight",
                        "allam-2-7b": "Allam 2 7B bilingual model",
                    }
                    for gm in gdata.get("data", []):
                        mid = gm.get("id", "")
                        if not mid or any(skip in mid.lower() for skip in excluded_groq):
                            continue
                        if mid in verified_groq_mids:
                            groq_models.append({
                                "id": f"groq:{mid}",
                                "name": mid,
                                "provider": "groq",
                                "is_local": False,
                                "details": verified_groq_mids[mid],
                            })
        except Exception:
            pass
    if not groq_models and groq_key:
        groq_online = True
        default_groqs = [
            ("qwen/qwen3.6-27b", "Qwen 2.5 27B - High throughput reasoning (Default)"),
            ("qwen/qwen3.8-27b", "Qwen 2.5 27B - Fast cloud inference"),
            ("groq/compound", "Groq Compound reasoning"),
            ("groq/compound-mini", "Groq Compound lightweight"),
        ]
        for mid, desc in default_groqs:
            groq_models.append({
                "id": f"groq:{mid}",
                "name": mid,
                "provider": "groq",
                "is_local": False,
                "details": desc,
            })

    # 3. Cloud Gemini models (Strictly verified, reliable, free-tier text chat models)
    gemini_models = []
    gemini_online = False
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    gemini_online = True
                    gmdata = json.loads(resp.read().decode("utf-8"))
                    # Exclude non-chat, audio, experimental preview, robotics, and deprecated models
                    excluded_gemini = [
                        "deep-research", "lyria", "robotics", "antigravity", "banana",
                        "image", "transcribe", "computer-use", "preview", "audio",
                        "tts", "embedding", "imagen", "aqa", "customtools", "omni",
                        "pro-latest", "1.5", "2.0"
                    ]
                    verified_gemini_mids = {
                        "gemini-3.1-flash-lite":"Google Gemini-3.1-flash-lite - Fast",
                        "gemini-2.5-flash": "Google Gemini 2.5 Flash - Fast & multimodal",
                        "gemini-2.5-flash-lite": "Google Gemini 2.5 Flash Lite - Ultra fast",
                        "gemini-flash-latest": "Google Gemini Flash (Latest stable)",
                        "gemini-flash-lite-latest": "Google Gemini Flash Lite (Latest stable)",
                        "gemma-4-26b-a4b-it": "Google Gemma 4 26B instruction-tuned",
                        "gemma-4-31b-it": "Google Gemma 4 31B instruction-tuned",
                    }
                    discovered_gemini = set()
                    for gm in gmdata.get("models", []):
                        methods = gm.get("supportedGenerationMethods", [])
                        if "generateContent" in methods:
                            gmid = gm.get("name", "").replace("models/", "")
                            if any(skip in gmid.lower() for skip in excluded_gemini):
                                continue
                            if gmid in verified_gemini_mids:
                                discovered_gemini.add(gmid)
                                gemini_models.append({
                                    "id": f"gemini:{gmid}",
                                    "name": gmid,
                                    "provider": "gemini",
                                    "is_local": False,
                                    "details": verified_gemini_mids[gmid],
                                })
                    # Ensure all verified models are listed if the key is valid
                    for vmid, desc in verified_gemini_mids.items():
                        if vmid not in discovered_gemini:
                            gemini_models.append({
                                "id": f"gemini:{vmid}",
                                "name": vmid,
                                "provider": "gemini",
                                "is_local": False,
                                "details": desc,
                            })
        except Exception:
            pass
    if not gemini_models and gemini_key:
        gemini_online = True
        default_geminis = [
            ("gemini-3.1-flash-lite","Google Gemini-3.1-flash-lite - Fast"),
            ("gemini-2.5-flash", "Google Gemini 2.5 Flash - Fast & multimodal"),
            ("gemini-2.5-flash-lite", "Google Gemini 2.5 Flash Lite - Ultra fast"),
            ("gemini-flash-latest", "Google Gemini Flash (Latest stable)"),
            ("gemini-flash-lite-latest", "Google Gemini Flash Lite (Latest stable)"),
        ]
        for gmid, desc in default_geminis:
            gemini_models.append({
                "id": f"gemini:{gmid}",
                "name": gmid,
                "provider": "gemini",
                "is_local": False,
                "details": desc,
            })

    # Return structured catalog
    return {
        "ollama_available": ollama_online,
        "providers": {
            "ollama": {
                "name": "Ollama (Local)",
                "available": ollama_online,
                "models": ollama_models,
            },
            "groq": {
                "name": "Groq (Cloud)",
                "available": groq_online,
                "models": groq_models,
            },
            "gemini": {
                "name": "Gemini (Cloud)",
                "available": gemini_online,
                "models": gemini_models,
            },
        },
        "all_models": ollama_models + groq_models + gemini_models,
        "default_models": DEFAULT_TASK_MODELS_CLOUD,
        "default_local_models": DEFAULT_TASK_MODELS_LOCAL,
        "categories": TASK_CATEGORIES_METADATA,
    }


def parse_model_id(model_id: str) -> Tuple[str, str]:
    """Parse 'provider:model_name' into (provider, model_name)."""
    if not model_id or model_id == "default":
        return ("default", "default")
    if ":" in model_id:
        parts = model_id.split(":", 1)
        if parts[0] in ("ollama", "groq", "gemini"):
            return (parts[0], parts[1])
    if model_id.startswith("gemini"):
        return ("gemini", model_id)
    if any(q in model_id for q in ["qwen3.", "llama-3.3", "llama-3.1-8b-instant"]):
        return ("groq", model_id)
    return ("ollama", model_id)


def resolve_model_for_task(category: str) -> Tuple[str, str, bool]:
    """
    Returns (provider, model_name, is_custom).
    Respects:
      1. Explicit task model configuration for this category from active_task_models_var.
      2. If unset or 'default', uses active provider's default for this category.
    """
    category = category or TASK_GENERAL_CHAT
    task_models = get_active_task_models()
    configured = task_models.get(category)
    if configured and configured != "default":
        provider, model_name = parse_model_id(configured)
        return provider, model_name, True

    active_prov = get_active_provider()
    if active_prov == "local":
        def_id = DEFAULT_TASK_MODELS_LOCAL.get(category, "ollama:llama3.2:3b")
    else:
        def_id = DEFAULT_TASK_MODELS_CLOUD.get(category, "groq:qwen/qwen3.6-27b")
    provider, model_name = parse_model_id(def_id)
    return provider, model_name, False


def get_best_local_model(requested_model: str, task_type: str = "reasoning") -> Optional[str]:
    """
    Find the best available local model:
    1. Returns requested_model if installed.
    2. Otherwise picks best installed candidate for task_type.
    """
    installed = get_available_ollama_models()
    if not installed:
        return requested_model if get_available_ollama_models_raw() else None

    # Check exact or prefix match
    for inst in installed:
        if inst == requested_model or inst.startswith(f"{requested_model}:") or requested_model.startswith(f"{inst}:"):
            return inst

    # Task-specific fallback preferences
    if task_type in ("coder", TASK_CONTENT_GENERATION):
        coder_priority = ["qwen2.5-coder:7b", "deepseek-coder-v2:16b", "qwen2.5-coder", "deepseek-coder"]
        for cand in coder_priority:
            for inst in installed:
                if cand in inst:
                    return inst

    reasoning_priority = ["llama3.2:3b", "gemma2:9b", "phi3.5", "llama3.1:8b"]
    for cand in reasoning_priority:
        for inst in installed:
            if cand in inst:
                return inst

    return installed[0]


def get_llm_instance(provider: str, model_name: str, temperature: float = 0.2, timeout: int = 120) -> BaseChatModel:
    """Lazy initialize and cache chat models across Ollama, Groq, and Gemini."""
    cache_key = f"{provider}:{model_name}:{temperature}:{timeout}"
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=model_name,
            temperature=temperature,
            timeout=timeout,
            num_ctx=2048,
        )
    elif provider == "groq":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        llm = ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
            model=model_name,
            temperature=temperature,
            timeout=timeout,
            max_retries=1,
            max_tokens=1000,
            extra_body={
                "reasoning_format": "hidden",
                "reasoning_effort": "none",
            },
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
            timeout=timeout,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    _llm_cache[cache_key] = llm
    return llm


def get_ollama_llm(model_name: str = DEFAULT_OLLAMA_MODEL, temperature: float = 0.2, timeout: int = 180) -> BaseChatModel:
    """Lazy initialize and return a ChatOllama instance (backward compatible)."""
    return get_llm_instance("ollama", model_name, temperature=temperature, timeout=timeout)


def get_task_llm(task_category: Optional[str] = None) -> Tuple[BaseChatModel, Optional[str]]:
    """
    Resolves and constructs the LLM for a given task category.
    If the requested model is unavailable, gracefully falls back and sets a user notification note.
    """
    cat = task_category or get_current_task_category()
    provider, model_name, is_custom = resolve_model_for_task(cat)
    cat_meta = next((c for c in TASK_CATEGORIES_METADATA if c["key"] == cat), None)
    cat_label = cat_meta["label"] if cat_meta else cat.replace("_", " ").title()

    # 1. Handle Ollama local model
    if provider == "ollama":
        if is_ollama_available():
            installed = get_available_ollama_models()
            is_installed = any(
                inst == model_name or inst.startswith(f"{model_name}:") or model_name.startswith(f"{inst}:")
                for inst in installed
            )
            if is_installed:
                try:
                    llm = get_llm_instance("ollama", model_name)
                    return llm, None
                except Exception as e:
                    print(f"[llm_router] Error initializing Ollama model {model_name}: {e}")
            elif is_custom:
                fallback_model = "qwen/qwen3.6-27b"
                note = f" Configured model '{model_name}' for {cat_label} is not installed in local Ollama. Fell back to Cloud ({fallback_model})."
                set_fallback_note(note)
                print(f"[llm_router] {note}")
                try:
                    return get_llm_instance("groq", fallback_model), note
                except Exception:
                    return get_llm_instance("gemini", "gemini-3.1-flash-lite"), note
            else:
                # Default selection: pick best installed candidate
                task_type = "coder" if cat == TASK_CONTENT_GENERATION else "reasoning"
                best_model = get_best_local_model(model_name, task_type=task_type)
                if best_model:
                    try:
                        llm = get_llm_instance("ollama", best_model)
                        return llm, None
                    except Exception as e:
                        print(f"[llm_router] Error initializing Ollama model {best_model}: {e}")

        # Local requested but offline/failed -> fall back to Cloud
        fallback_model = "qwen/qwen3.6-27b"
        note = f" Local model '{model_name}' for {cat_label} is offline or unreachable. Fell back to Cloud ({fallback_model})."
        set_fallback_note(note)
        print(f"[llm_router] {note}")
        try:
            return get_llm_instance("groq", fallback_model), note
        except Exception:
            return get_llm_instance("gemini", "gemini-3.1-flash-lite"), note

    # 2. Handle Groq cloud model
    if provider == "groq":
        try:
            llm = get_llm_instance("groq", model_name)
            return llm, None
        except Exception as e:
            note = f" Groq model '{model_name}' for {cat_label} failed to load ({e}). Fell back to Gemini."
            set_fallback_note(note)
            print(f"[llm_router] {note}")
            try:
                return get_llm_instance("gemini", "gemini-3.1-flash-lite"), note
            except Exception:
                raise

    # 3. Handle Gemini cloud model
    if provider == "gemini":
        try:
            llm = get_llm_instance("gemini", model_name)
            return llm, None
        except Exception as e:
            note = f" Gemini model '{model_name}' for {cat_label} failed to load ({e}). Fell back to Groq."
            set_fallback_note(note)
            print(f"[llm_router] {note}")
            try:
                return get_llm_instance("groq", "qwen/qwen3.6-27b"), note
            except Exception:
                raise

    # Default fallback
    return get_llm_instance("groq", "qwen/qwen3.6-27b"), None


def get_active_llm(user: Any = None, task_type: str = "reasoning") -> Tuple[BaseChatModel, Optional[str]]:
    """
    Returns the active LLM instance and any fallback note based on user preference and availability
    (backward compatible helper).
    """
    category_map = {
        "reasoning": TASK_ANALYTICAL,
        "lightweight": TASK_GENERAL_CHAT,
        "coder": TASK_CONTENT_GENERATION,
    }
    cat = category_map.get(task_type, TASK_GENERAL_CHAT)
    return get_task_llm(task_category=cat)


def invoke_task_llm(prompt: str, task_category: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Invokes the LLM configured for a given task category with runtime fallback safety.
    Retries up to 3 times on 503/UNAVAILABLE before falling back to cloud-direct.
    Returns (response_text, fallback_note).
    """
    import time
    cat = task_category or get_current_task_category()
    llm, initial_note = get_task_llm(cat)
    model_name = (
        getattr(llm, "model_name", None)
        or getattr(llm, "model", None)
        or getattr(llm, "model_id", None)
        or type(llm).__name__
    )
    print(f"[llm_router] Invoking LLM for task category '{cat}' using model '{model_name}'")
    print(f"[llm_router] Prompt: {prompt[:200]}{'...' if len(prompt) > 200 else ''}")

    _RETRY_DELAYS = [5, 10, 20]
    last_err = None
    for attempt, delay in enumerate([0] + _RETRY_DELAYS, start=1):
        if delay:
            print(f"[llm_router] 503 retry #{attempt} for '{cat}' after {delay}s...")
            time.sleep(delay)
        try:
            resp = llm.invoke(prompt)
            content = resp.content
            if isinstance(content, list):
                content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
            return content, initial_note
        except Exception as e:
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str.lower():
                print(f"[llm_router] 503 UNAVAILABLE on attempt {attempt} for '{cat}': {e}")
                last_err = e
                continue
            # Non-503 error → fall through to cloud fallback immediately
            last_err = e
            break

    print(f"[llm_router] Task invocation failed for {cat} ({last_err}). Falling back to safe Cloud direct.")
    cat_meta = next((c for c in TASK_CATEGORIES_METADATA if c["key"] == cat), None)
    cat_label = cat_meta["label"] if cat_meta else cat.replace("_", " ").title()
    runtime_note = f" Model execution for {cat_label} failed ({last_err}). Fell back to Cloud provider for this generation."
    set_fallback_note(runtime_note)
    from agents.tools import _groq_invoke_safe_cloud_direct
    cloud_res = _groq_invoke_safe_cloud_direct(prompt)
    return cloud_res, runtime_note


def invoke_ollama_safe(prompt: str, model_name: str = DEFAULT_OLLAMA_MODEL) -> Tuple[str, Optional[str]]:
    """
    Safely invoke local Ollama. If it fails or is offline, gracefully fall back to Groq.
    (backward compatible helper)
    """
    resolved_model = get_best_local_model(model_name, task_type="coder" if "coder" in model_name else "reasoning")
    if resolved_model and is_ollama_available():
        try:
            ollama_llm = get_llm_instance("ollama", resolved_model)
            response = ollama_llm.invoke(prompt)
            content = response.content
            if isinstance(content, list):
                content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
            return content, None
        except Exception as e:
            print(f"[llm_router] Ollama invocation failed for model {resolved_model} ({e}). Falling back to Cloud.")

    note = " Local Ollama model failed or was unreachable. Fell back to Cloud provider for this generation."
    set_fallback_note(note)
    print(f"[llm_router] {note}")
    from agents.tools import _groq_invoke_safe_cloud_direct
    cloud_result = _groq_invoke_safe_cloud_direct(prompt)
    return cloud_result, note


