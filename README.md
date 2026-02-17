# Nexus — Enterprise Intelligence Bot (Pure Python)

> Powered by **NVIDIA Nemotron Nano 12B V2 VL** (free) via OpenRouter  
> Built entirely in **Python** — zero npm, zero pip required to run

---

## 📁 Project Structure

```
nexus-python/
├── main.py                    # Entry point — starts the HTTP server
├── config.py                  # All settings: model, port, modes
├── requirements.txt           # Optional pip packages
│
├── modules/
│   ├── __init__.py
│   ├── pdf_parser.py          # Browser-side PDF text extraction (pure Python)
│   ├── document_store.py      # In-memory document store & knowledge base
│   ├── llm_client.py          # OpenRouter API client (urllib only)
│   └── router.py              # HTTP request router & all API endpoints
│
├── templates/
│   └── index.html             # Main HTML page served by Python
│
└── static/
    ├── css/
    │   └── style.css          # Complete design system
    └── js/
        ├── renderer.js        # Markdown → HTML renderer (frontend)
        └── app.js             # All frontend logic (talks to Python backend)
```

---

## 🚀 Quick Start

### 1. Get a Free OpenRouter API Key

1. Go to [openrouter.ai](https://openrouter.ai) and sign up (free)
2. Click **Keys → Create Key**
3. Copy your key — it starts with `sk-or-v1-...`

### 2. Run

```bash
# Navigate to the project folder
cd nexus-python

# Start the server (no pip install needed)
python main.py
```

The browser opens automatically at **http://127.0.0.1:8000**

### 3. Use It

1. Paste your OpenRouter API key in the sidebar
2. Upload documents (PDF, TXT, MD, CSV, JSON) via drag-drop or click
3. Click **⚡ Ingest Documents** to index your knowledge base
4. Pick an analysis mode and start chatting

---

## 🧠 The Model

**NVIDIA Nemotron Nano 12B V2 VL**

| Property | Value |
|---|---|
| Parameters | 12B |
| Architecture | Hybrid Transformer-Mamba |
| Context | 128K tokens |
| Strengths | Document intelligence, OCR, chart reasoning |
| Cost | **Free** on OpenRouter |
| Model string | `nvidia/nemotron-nano-12b-v2-vl:free` |

---

## 🔧 Module Responsibilities

| File | What it does |
|---|---|
| `main.py` | Starts Python's built-in HTTPServer, auto-opens browser |
| `config.py` | Single source of truth: model, port, mode definitions |
| `modules/pdf_parser.py` | Heuristic PDF binary text extraction (no deps); optionally uses PyPDF2 |
| `modules/document_store.py` | Stores uploaded docs in memory, compiles knowledge base |
| `modules/llm_client.py` | Posts to OpenRouter using only `urllib` (stdlib) |
| `modules/router.py` | Routes GET/POST requests to handler functions |
| `templates/index.html` | Full single-page UI shell |
| `static/css/style.css` | Design system: dark industrial theme with lime accent |
| `static/js/renderer.js` | Converts markdown + risk tags to styled HTML |
| `static/js/app.js` | All frontend logic: upload, ingest, chat, mode switching |

---

## 🌐 API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Serve the HTML app |
| GET | `/static/*` | Serve CSS/JS assets |
| GET | `/api/documents` | List uploaded documents |
| GET | `/api/modes` | Get analysis modes + chips |
| GET | `/api/health` | Health check |
| POST | `/api/upload` | Upload documents (multipart) |
| POST | `/api/remove` | Remove a document `{"name": "..."}` |
| POST | `/api/ingest` | Compile knowledge base |
| POST | `/api/chat` | Send a query, get a reply |
| POST | `/api/clear` | Clear conversation history |

---

## 🔐 Security Notes

- API key stored in browser `sessionStorage` only (cleared on tab close)
- Documents stored **in-memory** only — nothing written to disk
- All processing happens locally; only the compiled text is sent to OpenRouter

---

## ⚙️ Configuration (`config.py`)

```python
HOST        = "127.0.0.1"   # Change to "0.0.0.0" to expose on LAN
PORT        = 8000
MODEL       = "nvidia/nemotron-nano-12b-v2-vl:free"
MAX_TOKENS  = 2048
TEMPERATURE = 0.3
MAX_DOC_CHARS = 40_000      # Characters per document to send to LLM
HISTORY_LIMIT = 10          # Message pairs kept in context
```

---

## 🛠 Optional Enhancements

### Better PDF extraction

```bash
pip install PyPDF2
```

`pdf_parser.py` detects PyPDF2 automatically and uses it when available.

### Change the model

Edit `config.py`:
```python
MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"
# Other free models on OpenRouter:
# "meta-llama/llama-3.1-8b-instruct:free"
# "google/gemma-3-12b-it:free"
```
