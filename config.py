"""
config.py
Central configuration for Nexus Enterprise Bot.
All settings live here — edit this file to change model, port, etc.
"""

# ── Server ────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 8000

# ── OpenRouter / NVIDIA Nemotron ──────────────────────────────────────
API_BASE_URL   = "https://openrouter.ai/api/v1/chat/completions"
MODEL          = "nvidia/nemotron-nano-12b-v2-vl:free"
MAX_TOKENS     = 2048
TEMPERATURE    = 0.3
SITE_URL       = "http://localhost:8000"
SITE_NAME      = "Nexus Enterprise Bot"

# ── Document ingestion ────────────────────────────────────────────────
MAX_DOC_CHARS  = 40_000   # Characters per document sent to LLM
HISTORY_LIMIT  = 10       # Message pairs kept in context

# ── Supported file extensions ─────────────────────────────────────────
SUPPORTED_EXTS = {".pdf", ".txt", ".md", ".csv", ".json"}

# ── Analysis modes ────────────────────────────────────────────────────
MODES = {
    "general": {
        "label": "🏢 General",
        "instruction": """MODE: General Knowledge Assistant.
Answer questions about company policies, HR procedures, onboarding, benefits,
IT guidelines, and any internal knowledge thoroughly and clearly.""",
        "chips": [
            "What is the leave policy?",
            "Explain the reimbursement rules",
            "What are the IT security guidelines?",
            "Summarize the HR compliance requirements",
            "What is the remote work policy?",
            "Give me a 5-point document summary",
        ],
    },
    "legal": {
        "label": "⚖️ Legal",
        "instruction": """MODE: Legal Contract Analyzer.
Focus on legal provisions, clauses, obligations, rights, and contractual risks.
Use precise legal terminology. Always add: 'This is not legal advice.'""",
        "chips": [
            "What are the termination conditions?",
            "List all indemnification clauses",
            "What are the governing law provisions?",
            "Extract all IP ownership terms",
            "What are the dispute resolution mechanisms?",
            "Summarize NDA obligations",
        ],
    },
    "finance": {
        "label": "💰 Finance",
        "instruction": """MODE: Financial Document Reviewer.
Focus on monetary figures, payment terms, penalties, financial obligations,
and fiscal risk. Format all figures clearly with currency symbols.""",
        "chips": [
            "What financial penalties apply?",
            "List all payment milestones",
            "What are the late payment consequences?",
            "Summarize all financial obligations",
            "What revenue sharing terms exist?",
            "Identify any hidden costs or fees",
        ],
    },
    "risk": {
        "label": "🛡️ Risk",
        "instruction": """MODE: Risk Intelligence Scanner.
Identify, categorize, and score risks as:
  🔴 HIGH   — immediate legal, financial, or operational exposure
  🟡 MEDIUM — significant risk requiring attention
  🟢 LOW    — minor or standard boilerplate risk

Provide a structured risk register: Risk | Category | Severity | Clause | Action.""",
        "chips": [
            "Highlight the key liability risks",
            "What compliance violations are mentioned?",
            "Score the overall contract risk level",
            "What limitations of liability exist?",
            "Identify all force majeure provisions",
            "What indemnity obligations do we hold?",
        ],
    },
}
