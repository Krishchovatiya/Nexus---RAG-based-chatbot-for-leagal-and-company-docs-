"""
modules/llm_client.py
OpenRouter API client for NVIDIA Nemotron Nano 12B V2 VL.
Uses only Python stdlib (urllib) — zero external dependencies.
"""

from __future__ import annotations
import json
import urllib.request
import urllib.error
import ssl
import config


def build_system_prompt(knowledge_base: str, mode: str) -> str:
    """
    Assemble the full system prompt with the selected mode instruction
    and the compiled knowledge base corpus.
    """
    mode_cfg = config.MODES.get(mode, config.MODES["general"])

    if knowledge_base.strip():
        kb_section = (
            "\n\n═══════════════════════════════════════════\n"
            "KNOWLEDGE BASE (ingested documents)\n"
            "═══════════════════════════════════════════\n"
            + knowledge_base
        )
    else:
        kb_section = (
            "\n\n[No documents ingested. Advise the user to upload and "
            "ingest documents. You can still answer general questions "
            "from your training knowledge.]"
        )

    return (
        "You are Nexus, an elite Enterprise Knowledge & Contract Intelligence AI.\n"
        "You analyze corporate documents, contracts, HR policies, and financial "
        "filings with surgical precision and structured clarity.\n\n"
        "RESPONSE GUIDELINES:\n"
        "- Be precise, professional, and well-structured.\n"
        "- Use clear headings (##) when organizing multi-part answers.\n"
        "- Quote specific clauses or document text verbatim when relevant.\n"
        "- Use these inline markers for important items:\n"
        "    ✅  Compliant / positive finding\n"
        "    ⚠️  Warning / needs attention\n"
        "    ❌  Risk / non-compliant item\n"
        "- Always reference the document name when citing information.\n"
        "- For risk mode, use 🔴 HIGH / 🟡 MEDIUM / 🟢 LOW risk tags.\n"
        f"{mode_cfg['instruction']}"
        f"{kb_section}"
    )


def chat(
    api_key: str,
    messages: list[dict],
    mode: str,
    knowledge_base: str,
) -> str:
    """
    Send a chat completion request to OpenRouter.

    Args:
        api_key:        OpenRouter API key (sk-or-v1-...)
        messages:       List of {"role": str, "content": str} dicts
        mode:           Analysis mode key (general/legal/finance/risk)
        knowledge_base: Compiled document corpus string

    Returns:
        The assistant reply text.

    Raises:
        ValueError: On API-level errors (bad key, rate limit, etc.)
        RuntimeError: On network or parsing failures
    """
    system = build_system_prompt(knowledge_base, mode)

    # Trim history to limit
    history = messages[-(config.HISTORY_LIMIT * 2):]

    payload = json.dumps({
        "model":       config.MODEL,
        "max_tokens":  config.MAX_TOKENS,
        "temperature": config.TEMPERATURE,
        "messages": [
            {"role": "system", "content": system},
            *history,
        ],
    }).encode("utf-8")

    req = urllib.request.Request(
        url=config.API_BASE_URL,
        data=payload,
        method="POST",
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer":  config.SITE_URL,
            "X-Title":       config.SITE_NAME,
        },
    )

    # Accept self-signed certs in local dev; use default context in prod
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        _handle_http_error(exc)
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Network error — check your connection: {exc.reason}"
        ) from exc
    except TimeoutError:
        raise RuntimeError("Request timed out. The model may be busy — try again.")

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from API: {exc}") from exc

    choices = data.get("choices") or []
    if not choices:
        # OpenRouter sometimes returns an error body with HTTP 200
        err = data.get("error", {})
        raise ValueError(err.get("message") or "Empty response from model.")

    text = (choices[0].get("message") or {}).get("content", "").strip()
    if not text:
        raise ValueError("Model returned an empty reply — please retry.")

    return text


def _handle_http_error(exc: urllib.error.HTTPError) -> None:
    """Parse HTTPError body and raise a user-friendly ValueError."""
    try:
        body = json.loads(exc.read().decode("utf-8"))
        msg = (body.get("error") or {}).get("message") or str(exc)
    except Exception:
        msg = str(exc)

    status = exc.code
    if status == 401:
        raise ValueError("Invalid API key — check your OpenRouter key.")
    if status == 429:
        raise ValueError("Rate limit reached. Wait a moment and retry.")
    if status == 402:
        raise ValueError("OpenRouter free quota exhausted. Add credits at openrouter.ai.")
    raise ValueError(f"API error {status}: {msg}")
