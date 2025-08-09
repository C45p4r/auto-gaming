# auto-gaming

Status: Planning. This repository currently contains only the README and Git metadata while we define the MVP scope.

## Vision

- Build an agent that learns to play 2D mobile games autonomously, starting with Epic7.
- Learn by observing screenshots continuously, reading on-screen text via OCR, and augmenting knowledge via web search for guides, events, rules, and mechanics.
- Accumulate game-specific memories over time to improve decisions.
- Guide behavior using a transparent metrics system (e.g., completing daily missions yields +1 points) for reinforcement and prioritization.
- Provide a modern UI to surface the agent's current status, decision logic, and memories, with optional light-touch manual guidance.
- Enforce strict safety: no real-world payments or monetization actions, ever.

## Scope and target game

- Focus: 2D mobile titles, with Epic7 as the initial target for MVP validation.
- Platform: mobile emulator on desktop (e.g., macOS) with programmatic screen capture and input control.
- Out of scope: any interaction that spends real money or violates game Terms of Service.

## Initial milestones

- Define the target game (Epic7), emulator, and confirm compliance boundaries with Terms of Service.
- Implement baseline data loop: continuous screenshots, OCR text extraction, simple UI overlay.
- Integrate web search for game knowledge ingestion and establish a durable memory store.
- Define the metrics schema (e.g., daily missions, resource caps, energy usage) and a scoring function.
- Draft the baseline architecture (emulator I/O, state encoder, policy/training/decision loop).
- Add safety guards to block IAP/payment flows and risky navigation.
- Decide on tooling (Python 3.11+, packaging, testing, linting, CI) and UI stack.

## Versioned roadmap and TODOs

Version numbers mark grouped milestones. Minor features that compose a major capability are listed as checkboxes to track progress.

### v0.1.0 — Foundations (repo, configs, capture + OCR)

- [x] Git + CI skeleton (lint, format, type-check)
- [x] Config system with `.env` and typed settings
- [x] Emulator connector (ADB) with device discovery
- [x] Screen capture loop (configurable FPS)
- [x] Baseline OCR adapter (Tesseract) with language packs
- [x] Structured logging to JSON; log rotation
- [x] CLI: capture one frame, run OCR, dump JSON

Quickstart (v0.1.0):

- `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- `cp env.example .env` then adjust values (e.g., `OCR_LANGUAGE`)
- Ensure an emulator/device is connected: `adb devices`
- Capture one frame with OCR: `python -m app.cli capture --output-dir captures`
- Capture loop at 1 FPS with OCR: `python -m app.cli capture-loop --fps 1 --ocr --count 5`

### v0.2.0 — State encoder and metrics

- [x] Parse common UI elements (buttons, counters, mission text)
- [x] State encoder: normalized features and timestamps
- [x] Metrics registry: define `daily_progress`, `resource_safety`, `farm_efficiency`, `arena_focus`
- [x] Scoring function with weights; config surface in `.env`
- [x] Unit tests for metrics and state encoding

Usage:
- Encode a state from a captured image via code:
  - `from app.state.encoder import encode_state, to_features`
  - `state = encode_state(Image.open('captures/frame_x.png'))`
  - `features = to_features(state)`
- Compute and score metrics:
  - `from app.metrics.registry import compute_metrics, score_metrics`
  - `metrics = compute_metrics(state)`
  - `score = score_metrics(metrics)`

### v0.3.0 — Memory and web knowledge

- [ ] Web search ingestion (guides/events) with rate limits
- [ ] Summarization into structured facts (title, source, claims)
- [ ] Embeddings index (FAISS/Chroma); cosine search
- [ ] SQLite store for structured memories and observations
- [ ] Retrieval API: given state, return top‑k relevant memories

### v0.4.0 — Planner v1 and action executor

- [ ] Heuristic policy using metrics + memory signals
- [ ] Action schema (tap, swipe, wait, back)
- [ ] Input executor (ADB) with retries and backoff
- [ ] Safety checks before/after action (screen diff, guard rails)
- [ ] Rollback/escape sequence (close dialogs, return home)

### v0.5.0 — UI Alpha

- [ ] WebSocket telemetry stream
- [ ] Status panel (current task, confidence, next step)
- [ ] Decision log with reasons and metric deltas
- [ ] Memory browser (search, view provenance)
- [ ] Manual guidance (simple nudges/priorities)

### v0.6.0 — Safety and non‑monetization hardening

- [ ] Purchase UI detection templates and OCR keywords
- [ ] Hard block on IAP flows; auto‑dismiss dialogs
- [ ] Risk scoring and quarantine mode
- [ ] Safety test suite (golden screenshots)

### v0.7.0 — Parallelism and multi‑agent

- [ ] Orchestrator (async/Ray) with time‑boxed tasks
- [ ] Specialist agents (policy‑lite, guide‑reader, mechanics‑expert)
- [ ] Judge/critic with consensus selection
- [ ] Result caching keyed by state hash
- [ ] Concurrency controls (max agents, CPU/GPU budget)

### v0.8.0 — Epic7 presets and loops

- [ ] Resolution/DPI presets and UI anchors for Epic7
- [ ] Daily mission flow (end‑to‑end)
- [ ] Stage farming loop with stamina checks
- [ ] Event detection and routing preferences

### v0.9.0 — Telemetry and analytics

- [ ] Metrics dashboard (graphs, trends)
- [ ] Session replay: step through screenshots, actions, decisions
- [ ] Export/import profiles (config, weights, presets)

### v1.0.0 — Beta release

- [ ] End‑to‑end stability pass and error budgets
- [ ] Documentation (setup, safety, UI, configs)
- [ ] Installer scripts (backend + UI)
- [ ] Release notes and versioned config templates

### Stretch goals (post‑1.0)

- [ ] RL policy (PPO) trained on offline logs and safe online finetuning
- [ ] Object detection for UI components beyond OCR
- [ ] Multi‑device support; Windows/Linux hosts
- [ ] Scenario editor for custom task graphs

Definition of Done per version:

- Major features and all listed checkboxes are completed and tested
- Safety guards verified; no IAP actions possible
- Docs updated (README, config samples, UI screenshots)

## Planned structure

- `src/` — core package (environment wrappers, decision loop, models, training).
- `src/agents/` — high-level task planners and policy implementations.
- `src/services/ocr/` — OCR adapters and text normalization.
- `src/services/search/` — web search ingestion and parsing.
- `src/memory/` — long-term memory store (facts, events, strategies) and retrieval.
- `src/metrics/` — metrics registry, scoring, and reinforcement signals.
- `ui/` — modern UI (status, decision logs, memory view, manual guidance controls).
- `notebooks/` — exploration and prototyping.
- `data/` — local data (excluded from version control).
- `models/` — checkpoints and artifacts.
- `scripts/` — utilities for data collection and evaluation.

## Architecture overview

```mermaid
graph LR
  subgraph Runtime
    EMU[Mobile Emulator\n(Android Emulator/LDPlayer/BlueStacks)]
    CAP[Screen Capture\n(ADB/native)]
    ACT[Input Control\n(ADB tap/keys)]
    CV[Perception Pipeline\n(OpenCV + OCR)]
    OCR[Tesseract/PaddleOCR]
    STATE[State Encoder]
    PLAN[Planner/Policy\n(metrics-weighted, RL-ready)]
    METRICS[Metrics Registry]
    SAFE[Safety Guards\n(no IAP/payments)]
  end

  subgraph Knowledge
    SEARCH[Web Search Ingestion\n(SerpAPI/Tavily/Playwright)]
    SUM[Summarizer]
    VEC[Vector Store\n(FAISS/Chroma)]
    DB[(Structured Store\n(SQLite))]
  end

  subgraph UI
    UI[React/TypeScript UI]
  end

  subgraph Backend
    API[FastAPI Service\n(WebSocket/REST)]
    BUS[Event/Scheduler]
    LOG[Structured Logging]
  end

  EMU <--> CAP --> CV --> OCR --> STATE --> PLAN --> ACT --> EMU
  PLAN --> METRICS --> PLAN
  PLAN --> SAFE
  SEARCH --> SUM --> VEC
  VEC --> PLAN
  DB --> PLAN
  STATE --> DB
  API <--> UI
  API <--> {CAP, PLAN, METRICS, VEC, DB, LOG}
  BUS --> {CAP, PLAN}
```

At a glance:

- Capture frames from the emulator, extract text with OCR, and encode state features.
- Combine current state with retrieved memories and metrics to choose actions.
- Continuously ingest game knowledge from the web into a memory store.
- Surface status, decision logs, and memories in a modern UI with live updates.
- Enforce guard rails to avoid any in-app purchases or real-money flows.

## Parallelism and multi‑agent strategy

- Perception, OCR, retrieval, and planning are designed to run in parallel where possible to reduce latency.
- Multiple specialized agents (small models and/or LLMs) propose actions concurrently and critique each other to reach a better decision.
- Each proposal includes predicted metric deltas (e.g., +1 `daily_progress`, −risk score), enabling a quantitative selection.
- A judge/consensus step selects the final action via weighted voting, historical accuracy, or a cost‑aware heuristic.
- Small/local models handle routine tasks; larger LLMs are used selectively on ambiguous or high‑impact decisions.

```mermaid
graph TB
  ORCH[Orchestrator\n(async/Ray)]
  subgraph Specialists
    P1[Policy-Lite\n(local small model]
    P2[Guide-Reader\n(LLM + retrieval)]
    P3[Mechanics-Expert\n(LLM)]
    SAFE[Safety-Rule Checker\n(local rules/model)]
  end
  CRITIC[Critic/Judge\n(consensus/vote)]
  SELECT[Consensus Selector\n(weighted by metrics & past accuracy)]
  ACT[Action Executor]

  ORCH --> P1
  ORCH --> P2
  ORCH --> P3
  ORCH --> SAFE
  P1 --> CRITIC
  P2 --> CRITIC
  P3 --> CRITIC
  SAFE --> CRITIC
  CRITIC --> SELECT --> ACT
```

Design notes:

- Time‑boxed debate: 1–2 short critique rounds before selection to maintain responsiveness.
- Memory‑aware decisions: agents retrieve relevant memories and cite evidence.
- Result caching: identical states reuse prior decisions when safe.

## Technologies

- Backend: Python 3.11, FastAPI, Pydantic v2, Uvicorn, APScheduler
- Computer vision: OpenCV, NumPy; template matching; optional object detection later
- OCR: Tesseract + `pytesseract` (or PaddleOCR as an alternative)
- Knowledge & memory: sentence-transformers embeddings, FAISS/Chroma vector store, SQLite for structured data
- Planning/learning: metrics-weighted heuristic policy initially; optional RL with Stable-Baselines3 (PPO) later
- Parallelism/orchestration: Python asyncio, Ray (optional), task queue via Redis/Celery (optional)
- Multi‑LLM/small models: OpenAI/Anthropic/Gemini APIs; local models via Ollama/llama.cpp; simple router to pick cheapest model that meets quality SLA
- Emulator & I/O: Android Platform Tools (ADB) for capture and input; macOS screen APIs as fallback
- UI: TypeScript + React (Vite or Next.js), Tailwind CSS, WebSocket for live telemetry; state via Zustand/Redux
- Tooling: Poetry or uv/pip-tools for Python deps; pnpm/npm/yarn for UI; pre-commit, ruff/black, mypy
- Caching/coordination: Redis for cache/pubsub; structured logs to JSON files or OpenTelemetry

## Hugging Face as AI agents

Hugging Face can power one or more agents in the parallel strategy: a fast local policy, a retrieval‑augmented guide reader, and/or a stronger remote judge.

- Modes of use

  - Local models (offline‑capable): `transformers` pipelines or `AutoModel*` + `bitsandbytes`/`accelerate`.
  - Hosted inference: `huggingface_hub.InferenceClient` (Serverless Inference API) or managed Inference Endpoints (TGI).
  - Embeddings: `sentence-transformers` from the Hub for vector search memory.

- Recommended roles

  - Policy‑Lite (local small instruct model): e.g., `mistralai/Mistral-7B-Instruct-v0.3`, `google/gemma-2-2b-it` (quantized for Mac).
  - Guide‑Reader (RA(R)G): the same or slightly larger instruct model, with memory retrieval context.
  - Judge/Critic (remote): larger endpoint model for consensus when decisions are ambiguous.

- Configuration (env)

  - `HUGGINGFACE_HUB_TOKEN` — personal access token for the Hub (read access is enough for most public models)
  - `HF_MODEL_ID_POLICY` — default local policy model id
  - `HF_MODEL_ID_JUDGE` — remote judge model id (if using Inference API/Endpoint)
  - `HF_INFERENCE_ENDPOINT_URL` — optional TGI endpoint URL for hosted inference

- Local generation (policy agent)

```python
from transformers import pipeline

policy = pipeline(
    "text-generation",
    model="mistralai/Mistral-7B-Instruct-v0.3",
    device_map="auto",
    torch_dtype="auto"
)

prompt = "You are the game policy. Given state and metrics, propose the next action and estimate metric deltas."
out = policy(prompt, max_new_tokens=256, do_sample=False)[0]["generated_text"]
```

- Hosted inference (judge/critic)

```python
import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    model=os.getenv("HF_MODEL_ID_JUDGE", "meta-llama/Llama-3.1-8B-Instruct"),
    token=os.getenv("HUGGINGFACE_HUB_TOKEN"),
)

judgment = client.text_generation(
    prompt="Critique and pick the best action among candidates with reasons",
    max_new_tokens=256,
    temperature=0.2,
)
```

- Embeddings for memory

```python
from sentence_transformers import SentenceTransformer

embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
vectors = embedder.encode(["arena guide text"], normalize_embeddings=True)
```

Notes:

- Prefer smaller local models for high‑frequency decisions; escalate to a stronger endpoint only when needed.
- Cache Hub downloads (`HF_HOME`) and pin model revisions for reproducibility.
- Respect each model’s license and usage restrictions.

## Setup outline

Prerequisites:

- Python 3.11+
- Node.js 20+
- Tesseract OCR installed and available on PATH
- Android Platform Tools (ADB) and a configured emulator

Backend (FastAPI):

1. Create environment and install deps: `poetry install` (or `uv pip install -r requirements.txt`).
2. Configure `.env` (OCR language, search provider keys, paths).
3. Run API: `uvicorn app.main:app --reload`.
4. Optional: start Ray for parallelism: `ray start --head` and set `PARALLEL_MODE=ray`.
5. Set LLM provider keys (as needed): `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or configure local `ollama`.

UI (React/TypeScript):

1. `cd ui && pnpm install` (or npm/yarn).
2. `pnpm dev` to start the UI; it connects to the backend via WebSocket/REST.

Emulator:

1. Install and launch your emulator; enable ADB.
2. Calibrate capture and input (resolution, DPI, window title); store settings in config.
3. Set concurrency knobs: frames per second, OCR batch size, and max parallel agents.

Safety:

- Enable purchase-UI detection; set hard-block mode to prevent any navigation into IAP screens.
- Configure judge to reject actions with any purchase‑related UI elements or ambiguous confirmations.

## Learning and knowledge system

- Continuous perception: capture screenshots at a configurable interval.
- OCR: extract on-screen text (menus, missions, resource counters) for state understanding.
- Web knowledge: periodically query public guides and event info; summarize into durable memories.
- Memory: store structured facts (e.g., drop rates, best stage for mats), recent context, and learned strategies.
- Feedback loop: decisions reference memory; successful outcomes strengthen related memories.

## Metrics-driven guidance

- Define explicit metrics aligned to game goals (e.g., clear daily missions, farm efficiency, stamina usage).
- Example: completing a daily mission → +1 to `daily_progress`; capping resources → +1 to `resource_safety`.
- Use a weighted score to prioritize tasks; expose weights in UI for transparency.
- Record per-action scores to enable reinforcement signals and post-hoc analysis.

## UI and operator controls

- Live status: show current task, confidence, and next steps.
- Decision log: chronological actions with reasons and contributing signals.
- Memory browser: searchable learned facts, strategies, and recent observations.
- Manual guidance: lightweight nudges (e.g., “prioritize arena” or “avoid event stages”).
- Safety panel: real-time indicators and hard stops for risky flows.

## Safety and non‑monetization

- No real-world money involvement: never trigger IAP screens or payment flows.
- Guard rails: detect and block UI elements related to purchases; exit gracefully if encountered.
- Respect ToS: operate within allowed automation boundaries for personal/research use.

## Links

- [Hugging Face](https://huggingface.co/)

## Legal and ethics

- Respect game Terms of Service and platform policies.
- Use for research and personal projects unless you have explicit permission.
- No monetization and no real-money transactions, directly or indirectly.

## License

MIT
