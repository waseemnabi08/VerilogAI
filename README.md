# VerilogAI 🤖⚡

> **An open-source, AI-powered assistant for Verilog and SystemVerilog development.**  
> Generate RTL, debug code, explain designs, and build testbenches — all from a chat interface.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Stars](https://img.shields.io/github/stars/waseemnabi08/VerilogAI?style=social)](https://github.com/waseemnabi08/VerilogAI/stargazers)
[![Forks](https://img.shields.io/github/forks/waseemnabi08/VerilogAI?style=social)](https://github.com/waseemnabi08/VerilogAI/network/members)

---

## What is VerilogAI?

VerilogAI is a web-based chatbot purpose-built for hardware designers and students. Unlike general-purpose AI tools, every prompt is engineered specifically for RTL development — with structured output formats, chain-of-thought debugging, few-shot examples, and mode-specific tuning.

It currently supports six specialised modes:

| Mode | What it does |
|---|---|
| **Chat** | General Verilog/SystemVerilog Q&A with conversation memory |
| **Generate** | RTL module generation from a natural-language spec |
| **Debug** | Severity-classified bug analysis + corrected code |
| **Explain** | Structured port-by-port, signal-flow explanation |
| **Testbench** | Self-checking SV testbench with directed + random stimulus |
| **Optimize** | Area / timing / power optimisation with trade-off analysis |

---

## Features

- **Structured AI responses** — every mode uses a fixed output template (Design Notes → Code → Instantiation Template) so responses are always scannable and consistent
- **Chain-of-thought debugging** — the model reasons through issue categories before producing a severity table (`🔴 Critical / 🟡 Warning / 🔵 Info`)
- **Multi-turn conversation** — history is threaded through all endpoints, not just chat, enabling iterative debugging sessions
- **Static pre-analysis** — module extraction, clock-domain detection, and style checking run client-side before the AI call to give the model better context
- **Per-mode temperature tuning** — debug uses `0.05` for maximum precision; explain uses `0.20` for more natural prose
- **File upload** — drop a `.v` or `.sv` file directly into the interface
- **Responsive design** — works on desktop and mobile

---

## Tech Stack

**Backend**
- Python 3.10+ · FastAPI · Uvicorn
- Google Gemini API (`gemini-2.0-flash`)
- httpx (async HTTP) · python-dotenv

**Frontend**
- Vanilla HTML / CSS / JavaScript
- Vite (build tooling)
- Marked.js (Markdown rendering) · Font Awesome (icons)

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- A [Google Gemini API key](https://aistudio.google.com/app/apikey) (free tier available)

### 1. Clone the repo

```bash
git clone https://github.com/waseemnabi08/VerilogAI.git
cd VerilogAI
```

### 2. Backend setup

```bash
# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set your API key
echo "GEMINI_API_KEY=your_key_here" > .env
```

### 3. Frontend setup

```bash
cd frontend
npm install
```

### 4. Run

Open two terminals:

```bash
# Terminal 1 — backend (from repo root)
uvicorn main:app --reload
# → http://127.0.0.1:8000

# Terminal 2 — frontend (from /frontend)
npm run dev
# → http://localhost:5173
```

---

## Project Structure

```
VerilogAI/
├── main.py             # FastAPI backend — all routes and prompt engineering
├── requirements.txt    # Python dependencies
├── .env                # Your API key (not committed)
├── README.md
└── frontend/
    ├── index.html      # App shell
    ├── script.js       # Frontend logic and API calls
    ├── style.css       # Styles
    ├── package.json
    └── vite.config.js
```

---

## API Reference

The backend exposes a REST API at `http://localhost:8000`. All endpoints accept JSON and return `{ "reply": "..." }`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Health check |
| `POST` | `/chat` | General Verilog chat |
| `POST` | `/generate` | RTL code generation |
| `POST` | `/debug` | Code review and debugging |
| `POST` | `/explain` | Code explanation |
| `POST` | `/testbench` | Testbench generation |
| `POST` | `/optimize` | RTL optimisation |
| `POST` | `/analyze` | Static + AI analysis |
| `POST` | `/upload` | Upload a `.v` / `.sv` file |

Interactive docs (Swagger UI) are available at `http://localhost:8000/docs`.

---

## Roadmap

Here's what's planned. These are great starting points for contributors:

- [ ] **RAG pipeline** — index Verilog LRM, FPGA primitive docs, and RTL design patterns into a vector DB (ChromaDB) for grounded responses
- [ ] **Streaming responses** — pipe Gemini tokens as they arrive for a faster-feeling UX
- [ ] **Syntax highlighting** — Prism.js or Highlight.js with a Verilog grammar
- [ ] **Copy button** on every code block
- [ ] **Model selector** — toggle between Gemini Flash (fast) and Pro (powerful)
- [ ] **Export chat** as Markdown or PDF
- [ ] **VS Code extension** — bring VerilogAI into the editor
- [ ] **CI/CD** — GitHub Actions for lint + test on PRs

---

## Contributing

Contributions are very welcome — whether it's a bug fix, a new feature, better prompts, or just improving the docs.

### How to contribute

1. **Fork** the repository and create a branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes.** Keep commits focused — one logical change per commit.

3. **Test your changes** locally before opening a PR.

4. **Open a Pull Request** against `main`. Include:
   - What you changed and why
   - Screenshots or example outputs if it's a UI/prompt change
   - Any follow-up work you'd suggest

### Good first issues

Not sure where to start? Look for issues tagged [`good first issue`](https://github.com/waseemnabi08/VerilogAI/issues?q=label%3A%22good+first+issue%22) or pick anything from the Roadmap above.

### Prompt engineering contributions

If you work in RTL design or EDA and have ideas for better system prompts, that's one of the highest-leverage contributions you can make. Open an issue describing the improvement and we can discuss before implementation.

### Code style

- Python: follow PEP 8, use type hints
- JavaScript: vanilla ES6+, no frameworks unless discussed first
- Commit messages: use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `refactor:`, etc.)

---

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.  
You are free to use, modify, and distribute this project. Attribution appreciated but not required.

---

## Acknowledgements

Built by [@waseemnabi08](https://github.com/waseemnabi08) as an open tool for the hardware design community.  
Powered by [Google Gemini](https://deepmind.google/technologies/gemini/) · Built with [FastAPI](https://fastapi.tiangolo.com/) · Served with [Vite](https://vitejs.dev/)

---

*If VerilogAI saved you time, consider giving it a ⭐ — it helps others find the project.*
