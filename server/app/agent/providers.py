"""v0.741 MORE PROVIDERS (owner: "CHECK ALL MORE FREE POWERFUL OPTION" -> "GO"): the chat model can come from any
OpenAI-compatible provider whose key is in the VPS .env, not only from GLM_BASE_URL (OpenRouter).

A model id in the owner's list (`chat_models`) is either
  - a plain slug ("z-ai/glm-5.3-flash", "nvidia/nemotron-3.5-super-vl:free")  -> the GLM brain's own endpoint, or
  - "<provider>:<model>" ("gemini:gemini-2.5-flash", "groq:openai/gpt-oss-120b") -> that provider's endpoint + key.
Only the provider prefixes below count, so OpenRouter's own ":free" suffix is never mistaken for one.

Each provider's key lives ONLY in .env (never chat, never the repo). The Gemini chat key is its OWN setting
(GEMINI_CHAT_API_KEY): the voice call's GEMINI_API_KEY is prepaid and never spent by chat turns silently.
What each model can do is read by the model profile (v0.739) - from OpenRouter's public catalogue for the same model
when the provider itself publishes no capabilities.
"""
from __future__ import annotations

from ..config import get_settings

# id -> (label, base url, settings field holding the key, OpenRouter catalogue vendor used to match its models)
PROVIDERS: dict[str, tuple[str, str, str, str]] = {
    "gemini": ("Google Gemini", "https://generativelanguage.googleapis.com/v1beta/openai", "gemini_chat_api_key", "google"),
    "groq": ("Groq", "https://api.groq.com/openai/v1", "groq_api_key", ""),
    "mistral": ("Mistral", "https://api.mistral.ai/v1", "mistral_api_key", "mistralai"),
    "nvidia": ("NVIDIA", "https://integrate.api.nvidia.com/v1", "nvidia_api_key", ""),
    "zai": ("Z.ai", "https://api.z.ai/api/paas/v4", "zai_api_key", "z-ai"),
    "openrouter": ("OpenRouter", "https://openrouter.ai/api/v1", "openrouter_api_key", ""),
}


def split(model: str) -> tuple[str, str]:
    """('groq', 'openai/gpt-oss-120b') for 'groq:openai/gpt-oss-120b'; ('', slug) for a plain slug."""
    m = (model or "").strip()
    head, sep, rest = m.partition(":")
    if sep and head in PROVIDERS and rest:
        return head, rest
    return "", m


def key_of(provider: str) -> str:
    st = get_settings()
    if not provider:
        return st.glm_api_key or ""
    if provider == "openrouter":   # the GLM key when GLM itself is on OpenRouter
        return str(getattr(st, "openrouter_api_key", "") or "") or (
            st.glm_api_key if "openrouter.ai" in (st.glm_base_url or "") else "")
    return str(getattr(st, PROVIDERS[provider][2], "") or "")


def base_of(provider: str) -> str:
    if not provider:
        return (get_settings().glm_base_url or "").rstrip("/")
    return PROVIDERS[provider][1]


def label_of(provider: str) -> str:
    if not provider:
        base = get_settings().glm_base_url or ""
        return "OpenRouter" if "openrouter.ai" in base else ("NVIDIA" if "nvidia.com" in base else "GLM")
    return PROVIDERS[provider][0]


def ready(model: str) -> bool:
    p, _ = split(model)
    return bool(key_of(p))


def is_openrouter(model: str) -> bool:
    p, _ = split(model)
    return p == "openrouter" or (not p and "openrouter.ai" in (get_settings().glm_base_url or ""))
