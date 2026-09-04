import os
import json
import urllib.request
from contextvars import ContextVar
from typing import Optional, Tuple, Any, List
from langchain_core.language_models.chat_models import BaseChatModel


# Context variables to track active provider and fallback status per request/invocation thread
active_provider_var: ContextVar[str] = ContextVar("active_provider_var", default="cloud")
fallback_note_var: ContextVar[Optional[str]] = ContextVar("fallback_note_var", default=None)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
DEFAULT_OLLAMA_CODER_MODEL = os.getenv("OLLAMA_CODER_MODEL", "qwen2.5-coder:7b")

_ollama_llm_cache = {}


def set_active_provider(provider: str) -> None:
    """Set the active LLM provider for the current context ('cloud' | 'local')."""
    if provider in ("cloud", "local"):
        active_provider_var.set(provider)
        fallback_note_var.set(None)


def get_active_provider() -> str:
    """Get the active LLM provider for the current context."""
    return active_provider_var.get()


def set_fallback_note(note: Optional[str]) -> None:
    """Record a fallback note for user notification."""
    fallback_note_var.set(note)


def get_fallback_note() -> Optional[str]:
    """Retrieve any active fallback note for the current context."""
    return fallback_note_var.get()


def get_available_ollama_models() -> List[str]:
    """Fetch list of installed models from local Ollama server."""
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
    if task_type == "coder":
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


def get_ollama_llm(model_name: str = DEFAULT_OLLAMA_MODEL, temperature: float = 0.2, timeout: int = 180) -> BaseChatModel:
    """Lazy initialize and return a ChatOllama instance."""
    from langchain_ollama import ChatOllama
    cache_key = f"{model_name}_{temperature}_{timeout}_{OLLAMA_BASE_URL}"
    if cache_key not in _ollama_llm_cache:
        _ollama_llm_cache[cache_key] = ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=model_name,
            temperature=temperature,
            timeout=timeout,
            num_ctx=2048,
        )
    return _ollama_llm_cache[cache_key]



def get_active_llm(user: Any = None, task_type: str = "reasoning") -> Tuple[BaseChatModel, Optional[str]]:
    """
    Returns the active LLM instance and any fallback note based on user preference and availability.

    task_type:
      - 'reasoning': Cloud -> Groq, Local -> Ollama (llama3.2:3b / gemma2:9b / phi3.5)
      - 'lightweight': Cloud -> Gemini, Local -> Ollama (llama3.2:3b / gemma2:9b)
      - 'coder': Cloud -> Groq, Local -> Ollama (qwen2.5-coder:7b / deepseek-coder-v2:16b)
    """
    from agents.tools import _get_groq_llm, _get_gemini_llm

    provider = "cloud"
    if user and hasattr(user, "llm_provider") and user.llm_provider:
        provider = user.llm_provider
    else:
        provider = get_active_provider()

    if provider == "local":
        requested_model = DEFAULT_OLLAMA_CODER_MODEL if task_type == "coder" else DEFAULT_OLLAMA_MODEL
        resolved_model = get_best_local_model(requested_model, task_type=task_type)

        if resolved_model:
            try:
                llm = get_ollama_llm(model_name=resolved_model)
                return llm, None
            except Exception as e:
                print(f"[llm_router] Error constructing Ollama LLM for model {resolved_model}: {e}")

        # Local requested but unavailable — fall back to Cloud
        note = " Local Ollama model is offline or unreachable. Used Cloud provider for this response."
        set_fallback_note(note)
        print(f"[llm_router] {note}")
        if task_type == "lightweight":
            return _get_gemini_llm(), note
        return _get_groq_llm(), note

    # Default cloud provider
    if task_type == "lightweight":
        return _get_gemini_llm(), None
    return _get_groq_llm(), None


def invoke_ollama_safe(prompt: str, model_name: str = DEFAULT_OLLAMA_MODEL) -> Tuple[str, Optional[str]]:
    """
    Safely invoke local Ollama. If it fails or is offline, gracefully fall back to Groq.
    Returns (response_text, fallback_note).
    """
    from agents.tools import _groq_invoke_safe_cloud_direct

    resolved_model = get_best_local_model(model_name, task_type="coder" if "coder" in model_name else "reasoning")
    if resolved_model:
        try:
            ollama_llm = get_ollama_llm(model_name=resolved_model)
            response = ollama_llm.invoke(prompt)
            print(f"[llm_router] Ollama invocation successful for model {resolved_model}.")
            content = response.content
            if isinstance(content, list):
                content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
            return content, None
        except Exception as e:
            print(f"[llm_router] Ollama invocation failed for model {resolved_model} ({e}). Falling back to Cloud.")

    note = " Local Ollama model failed or was unreachable. Fell back to Cloud provider for this generation."
    set_fallback_note(note)
    print(f"[llm_router] {note}")
    cloud_result = _groq_invoke_safe_cloud_direct(prompt)
    return cloud_result, note

