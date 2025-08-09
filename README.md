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
