# auto-gaming

Status: Beta v1.0.2 (Windows Emulator). OCR ensemble enabled; RL exploration more aggressive and diversity-aware; still memory-first with locked-feature learning.

## Vision

- Build an agent that learns to play 2D mobile games autonomously, starting with Epic7.
- Learn by observing screenshots continuously, reading on-screen text via OCR, and augmenting knowledge via web search for guides, events, rules, and mechanics.
- Accumulate game-specific memories over time to improve decisions.
- Guide behavior using a transparent metrics system (e.g., completing daily missions yields +1 points) for reinforcement and prioritization.
- Provide a modern UI to surface the agent's current status, decision logic, and memories, with optional light-touch manual guidance.
- Enforce strict safety: no real-world payments or monetization actions, ever.

## Terminology and naming (for precise targeting)

- Program: "auto-gaming" (this backend service and agent runtime)
- UI: "auto-gaming UI" (React/Vite frontend in `ui/`)
- Game: "Epic Seven" (aka "Epic 7")
- Emulator: "Google Play Games Beta" on Windows (target environment for testing)
- Capture backend names: `adb` (device screencap), `window` (Windows client-area capture)
- Input backend names: `adb` (shell input), `window` (Windows SendInput scaled to client area)
- Window title hint (regex): `WINDOW_TITLE_HINT=Google Play Games|Epic Seven|Epic 7`
- Window management: "topmost" and fixed client size/position (see `WINDOW_ENFORCE_TOPMOST`, geometry vars)
- Agent runner: `AgentRunner` (lifecycle: running/paused/stopped)
- Policy (heuristic): `policy-lite`
- Policy (Hugging Face): `hf-policy` (enabled via `HF_MODEL_ID_POLICY`)
- Judge (Hugging Face): `hf-judge` (enabled via `HF_MODEL_ID_JUDGE`)
- Safety rules (names): `no-external-navigation`, `no-item-change` (sell/remove/unequip)
- Stuck recovery: OCR-driven web search + memory enrichment
  - Windows click safety: set `INPUT_EXCLUDE_BOTTOM_PX` to avoid taskbar/overlay clicks. All taps are clamped to the client area with small margins.
- Control endpoints: `/telemetry/control/{start|pause|stop}`; WebSocket: `/telemetry/ws`
- Key env variables: `CAPTURE_BACKEND`, `INPUT_BACKEND`, `WINDOW_TITLE_HINT`, `HF_MODEL_ID_POLICY`, `HF_MODEL_ID_JUDGE`, `HUGGINGFACE_HUB_TOKEN`

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

- [x] Web search ingestion (guides/events) with rate limits
- [x] Summarization into structured facts (title, source, claims)
- [x] Embeddings index (FAISS/Chroma); cosine search
- [x] SQLite store for structured memories and observations
- [x] Retrieval API: given state, return top‑k relevant memories

Usage:

- Ingest URLs and store summaries:
  - `from app.services.search.web_ingest import fetch_urls, summarize`
  - `from app.memory.store import MemoryStore, Fact`
  - `docs = fetch_urls(["https://example.com/guide"])`
  - `facts = [Fact(id=None, title=d.title, source_url=d.url, summary=summarize(d)) for d in docs]`
  - `store = MemoryStore()`; `store.add_facts(facts)`
- Retrieve relevant facts by query:
  - `store.search("best farming stage for mats")`

### v0.4.0 — Planner v1 and action executor

- [x] Heuristic policy using metrics + memory signals
- [x] Action schema (tap, swipe, wait, back)
- [x] Input executor (ADB) with retries and backoff
- [x] Safety checks before/after action (screen diff, guard rails)
- [x] Rollback/escape sequence (close dialogs, return home)

Usage:

- Propose an action: `from app.policy.heuristic import propose_action`
- Execute: `from app.actions.executor import execute, escape_sequence`
- Safety checks: `from app.safety.guards import detect_purchase_ui, screen_change`

### v0.5.0 — UI Alpha

- [x] WebSocket telemetry stream
- [x] Status panel (current task, confidence, next step)
- [x] Decision log with reasons and metric deltas
- [x] Memory browser (search, view provenance) — via REST `/telemetry/memory/search?q=...`
- [x] Manual guidance (simple nudges/priorities)

UI dev quickstart:

- `cd ui && pnpm install` (or npm/yarn)
- `pnpm dev` (proxies to `http://localhost:8000` for `/telemetry`)

Controls:

- A sticky control bar in the UI provides Start, Pause, Stop buttons to control the agent.
- Backend endpoints:
  - `POST /telemetry/control/start`
  - `POST /telemetry/control/pause`
  - `POST /telemetry/control/stop`

### v0.6.0 — Safety and non‑monetization hardening

- [x] Purchase UI detection templates and OCR keywords
- [x] Hard block on IAP flows; auto‑dismiss dialogs
- [x] Risk scoring and quarantine mode
- [x] Safety test suite (golden screenshots)

Config:

- `HARD_BLOCK_IAP=true` — abort actions when purchase UI is detected
- `RISK_QUARANTINE=true` and `RISK_SCORE_THRESHOLD=0.5` — quarantine high‑risk states
- Templates in `app/safety/templates/keywords.txt` (extendable)

### v0.7.0 — Parallelism and multi‑agent

- [x] Orchestrator (async/Ray) with time‑boxed tasks
- [x] Specialist agents (policy‑lite, guide‑reader, mechanics‑expert)
- [x] Judge/critic with consensus selection
- [ ] Result caching keyed by state hash
- [x] Concurrency controls (max agents, CPU/GPU budget)

Config:

- `MAX_AGENTS=3`, `AGENT_TIMEOUT_S=1.5`, `DEBATE_ROUNDS=1`, `PARALLEL_MODE=async|ray`

### v0.8.0 — Epic7 presets and loops

- [x] Resolution/DPI presets and UI anchors for Epic7
- [x] Daily mission flow (end‑to‑end)
- [x] Stage farming loop with stamina checks (basic attempt)
- [x] Event detection and routing preferences (anchor‑based)

Usage:

- `from app.games.epic7.loops import run_daily_missions` then call `run_daily_missions(max_steps=5)`

### v0.9.0 — Telemetry and analytics

- [x] Metrics dashboard (graphs, trends)
- [x] Session replay: step through screenshots, actions, decisions (basic via API)
- [x] Export/import profiles (config, weights, presets) — planned via `.env` + anchors; CLI to follow

Usage:

- Backend API: `/analytics/metrics` and `/analytics/session`
- UI: metrics panel in the dev UI (auto-refresh)

### v1.0.0 — Beta release (Windows emulator)

- [x] End‑to‑end stability pass and error backoff thresholds
- [x] Documentation (Windows setup, safety, UI controls, configs)
- [x] Windows setup script (`scripts/windows_setup.ps1`)
- [x] Release notes and Windows-focused quickstart

Notes:

- v1.0.0 is a beta. Expect to run primarily on Windows emulator (Google Play Games Beta) and report issues.
- New safety rules: block external links/programs; block selling/removing heroes or equipment.
- Stuck recovery: when the agent stalls, it re-evaluates OCR and performs lightweight web search to enrich memory and propose next steps.

### Stretch goals (post‑1.0)

- [ ] RL policy (PPO) trained on offline logs and safe online finetuning
- [ ] Object detection for UI components beyond OCR
- [ ] Multi‑device support; Windows/Linux hosts
- [ ] Scenario editor for custom task graphs

### Post‑1.0 plan to v2.0 — Tests, fixes, and full functionality

The goal is to move from v1.0.0 (beta on Windows emulator) to a fully functional v2.0.0. Each minor version focuses on stabilizing core subsystems with measurable tests.

#### v1.1.0 — Input, capture, and window stability

- [ ] Coordinate mapping correctness across DPI/scales
  - [ ] Unit: scale/clamp math for `INPUT_BASE_WIDTH/HEIGHT`, `INPUT_EXCLUDE_BOTTOM_PX`
  - [ ] Golden: click heatmaps align with client rect at 100%, 125%, 150% DPI
  - [ ] Integration: center/edge taps land within ±5 px on emulator
- [ ] Window management race hardening
  - [ ] Unit: client vs. window rect math; restore when minimized
  - [ ] Integration: debounce topmost/resize prevents focus flapping
  - [ ] Health: error when emulator not found; retries/backoff telemetry
- [ ] Capture robustness
  - [ ] Golden: window capture crops correctly (no black bars)
  - [ ] Perf: 1–3 FPS sustained without stutter on CPU‑only

#### v1.2.0 — OCR quality and state encoding

- [ ] OCR accuracy improvements
  - [ ] Configurable `TESSERACT_CMD`, language packs validation
  - [ ] Golden OCR corpus for Epic Seven lobby/menus; ≥95% key token recall
  - [ ] Noise handling: outlines, anti‑aliasing, shadowed text
- [ ] State encoder coverage
  - [ ] Parse more UI anchors (battle, event, summon, shop, arena, sanctuary)
  - [ ] Unit: feature extraction determinism; hashing for identical frames
  - [ ] Telemetry: OCR fingerprint uniqueness, distribution

#### v1.3.0 — Policy exploration and stuck recovery

- [ ] Heuristic exploration diversification
  - [ ] Avoid repetition: adaptive jitter, rotation, cooldowns per label
  - [ ] Backoff escalations: wait → back → alternate region sampling
  - [ ] Unit: repetition controller; Integration: no >3 identical taps on static OCR
- [ ] Stuck recovery playbook
  - [ ] Web search hints gated by cooldown and privacy settings
  - [ ] Memory enrichment: deduplicate by title/domain; size caps
  - [ ] Telemetry: stuck events, recovery success ratio

#### v1.4.0 — Safety guards and hard blocks

- [ ] External navigation and item change guards
  - [ ] Golden: block phrases (external links, YouTube, sell, remove equipment)
  - [ ] Unit: keyword matchers with locale variants
  - [ ] Integration: auto Back and recovery without crash
- [ ] Negative test suite
  - [ ] Ensure no action hits system taskbar/other apps
  - [ ] Dry‑run mode parity (no input emitted)

#### v1.5.0 — HF agents integration hardening

- [ ] Local/hosted model selection and fallback logic
  - [ ] Startup checks: gated models, token scope, CPU Torch availability
  - [ ] Timeouts, retries, and degradation to heuristic
- [ ] Evaluation harness
  - [ ] Prompt fixtures and expected JSON action parsing
  - [ ] Judge selection determinism under seeds
  - [ ] Latency and cost budget telemetry

#### v1.6.0 — Analytics, logging, and replay

- [ ] Structured logs enrichment
  - [ ] Action latencies, success/fail, post‑action screen diff magnitude
  - [ ] Session replay: compact trace (frame hash + action + OCR fp)
- [ ] UI analytics
  - [ ] Trends for FPS, actions, blocks, stuck, unique screens explored
  - [ ] Decision table filters (who, action type, errors)

#### v1.7.0 — End‑to‑end reliability and CI

- [ ] Flake dashboard: triage, quarantine, auto‑retry
- [ ] CI jobs for unit + golden tests (CPU only)
- [ ] Artifact uploads: sample frames, OCR JSON, coverage reports

#### v2.0.0 — Full Windows emulator functionality

- [ ] Stable capture/input across common DPIs and window states
- [ ] Robust exploration: avoids repeats; progresses through core menus
- [ ] Safety‑first: no external links, no hero/equipment sell/remove
- [ ] HF agents optional but seamless; falls back gracefully
- [ ] Comprehensive docs and troubleshooting; one‑click Windows setup
- [ ] Test suite green: unit, golden OCR, integration, telemetry assertions

### v1.0.1 — Learning‑aware policy and UX polish

- [x] Memory‑first decision consult: orchestrator queries `MemoryStore` each step and surfaces hits in UI (`memory:search` step)
- [x] Locked‑feature learning: heuristic infers lock popups (e.g., “You can enter after…/Tap to close”) and persists locked labels, skipping both text and icon taps
- [x] Icon‑based targeting: perception detects common buttons via normalized anchors; policy can click icons even when OCR font/color differs
- [x] Lightweight reinforcement learning: contextual bandit (epsilon‑greedy) biases exploration vs. exploitation and updates from reward shaped by metrics
- [x] Guidance/Goals persistence: edits saved to `data/guidance.json` and restored on startup
- [x] Logs panel improvements: fixed‑height scroll and display only 10 most recent entries

#### v2.0.1 — v2.1.0 UI/UX improvements (10 updates)

- v2.0.1

  - [ ] Collapsible panels and layout presets (compact, detailed)
  - [ ] Decision table filters (agent, type, latency range, errors only)
  - [ ] Sticky mini heads-up strip (FPS, actions/s, blocks, stuck, model)
  - [ ] One-click actions: Back, Wait(1s), Gentle Swipe (operator shortcuts)
  - [ ] Memory thumbnails with inline expand and copy-to-clipboard OCR

- v2.0.2

  - [ ] Session replay scrubber (time slider) with frame previews
  - [ ] Export session trace (JSONL) and frames; Import for replay
  - [ ] Metrics compare view (last 5 sessions) with deltas

- v2.0.3

  - [ ] Guidance editor (prioritize/avoid templates, presets)
  - [ ] Doctor panel enhancements (quick fixes, open config, re-run with logs)

- v2.1.0
  - [ ] Theming (dark/light/system) and accessibility (font size, high contrast)
  - [ ] Status toasts and inline error chips (e.g., OCR/decision errors)
  - [ ] Keyboard shortcuts (Start/Pause/Stop, Refresh, Focus panes)
  - [ ] Screenshot annotate mode (draw box and copy coords as base-space)
  - [ ] Model indicator with quick toggle (heuristic/hf-policy) and last error

### v2.1.1 → v3.0.0 — Learning speed and performance

Focus: reduce end‑to‑end decision latency, improve sample efficiency, and accelerate learning from logs while preserving safety.

#### v2.1.1 — Perception pipeline throughput

- [ ] Frame diff skip: bypass OCR/encode when screen unchanged beyond threshold
- [ ] Downscale+ROI OCR pass (fast path) with selective full‑res fallback
- [ ] Parallelize capture→OCR→encode with bounded queues (prefetch next frame)
- [ ] Cache normalized OCR (text + bbox) keyed by frame hash

#### v2.1.2 — OCR batching and normalization

- [ ] Batch OCR across tiles; merge results; unify quote/spacing normalization
- [ ] Language pack auto‑verify and fallback to English tokens
- [ ] Prompt compression for LLM policy (top‑k tokens, dedup lines)

#### v2.2.0 — Retrieval/memory performance

- [ ] Streaming embeddings; lazy re‑index; background compaction
- [ ] ANN index (FAISS HNSW/IVF) with sharding for >100k facts
- [ ] Deduplicate facts by semantic similarity; aging/TTL policies

#### v2.3.0 — Policy speedups and serving

- [ ] Distilled lightweight policy (1–3B) for default decisions
- [ ] Quantization (int8/int4) and ONNX/TensorRT/DirectML backends
- [ ] Response caching: (state_hash → action) with TTL + accuracy guard
- [ ] Multi‑worker model server with micro‑batching

#### v2.4.0 — Learn from logs (offline RL/BC)

- [ ] Session log export → dataset builder (state, action, reward proxy)
- [ ] Behavior Cloning baseline; evaluate vs. heuristic
- [ ] Safety‑aware reward shaping; guard against unsafe actions

#### v2.5.0 — Goal conditioning and curriculum

- [ ] Condition policy on user goals (Suggestions/Guidance) and progress metrics
- [ ] Curriculum scheduler: start with safe menus → battles → events
- [ ] Auto‑tuning exploration parameters based on stuck/blocks rate

#### v2.6.0 — Fast targeting cues

- [ ] Lightweight detector (tiny/NNAPI/DirectML) for common buttons/anchors
- [ ] Hybrid targeter: OCR+detector fusion with confidence gating

#### v2.7.0 — Stuck detection and recovery

- [ ] Visual similarity (SSIM/LPIPS) + OCR fingerprints for robust stuck signal
- [ ] Dynamic backoff scheduler (exponential wait/back/sweep patterns)
- [ ] Recovery outcome metrics and A/B of strategies

#### v2.8.0 — Concurrency tuning and prefetch

- [ ] Asynchronous multi‑agent with micro‑batches
- [ ] Prefetch next frame and retrieval while executing current action
- [ ] Adaptive FPS and policy timeout based on device load

#### v2.9.0 — Hardware acceleration

- [ ] Optional GPU/DirectML for OCR/NN; auto‑detect and enable when safe
- [ ] Mixed precision where applicable; fall back to CPU deterministically

#### v3.0.0 — Performance release

- [ ] Decision p50 ≤ 150 ms; p95 ≤ 400 ms on baseline CPU
- [ ] Sample efficiency: reach defined goals (e.g., clear X menus) in Y minutes
- [ ] Robust to DPI/scales (100/125/150%) and window states
- [ ] Safety and guardrail parity maintained; tests and docs updated

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
- Emulator & I/O: Android Platform Tools (ADB) for capture and input; Windows/macOS screen APIs as fallback
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

Runtime integration (enable HF agents):

- Policy agent: set `HF_MODEL_ID_POLICY` in `.env`. The system auto-loads a local `transformers` pipeline or uses `huggingface_hub.InferenceClient` when `HF_INFERENCE_ENDPOINT_URL` is set. Falls back to heuristic on errors.
- Judge agent: set `HF_MODEL_ID_JUDGE` to enable candidate selection via HF. Falls back to score-based vote on errors.
- Optionally set `HUGGINGFACE_HUB_TOKEN` for gated models/endpoints.

Setup (manual steps):

1. Choose mode:
   - Local policy on CPU: recommended to start with a small model (e.g., `TinyLlama/TinyLlama-1.1B-Chat-v1.0`). Large models (e.g., 7B) are slow on CPU.
   - Hosted policy/judge: use `HF_INFERENCE_ENDPOINT_URL` or Serverless Inference via `huggingface_hub.InferenceClient`.
2. Install PyTorch CPU if using local `transformers`:
   - Windows (CPU):
     - `pip install --index-url https://download.pytorch.org/whl/cpu torch`
   - Verify: `python -c "import torch; print(torch.__version__)"`
3. Create a Hugging Face account and token (if needed):
   - Generate a PAT at `https://huggingface.co/settings/tokens` and set `HUGGINGFACE_HUB_TOKEN` in `.env`.
   - If the model is gated, visit its model page and click “Agree/Accept” to enable downloads.
4. Configure `.env`:
   - `HF_MODEL_ID_POLICY=TinyLlama/TinyLlama-1.1B-Chat-v1.0` (example small CPU model)
   - Optional judge: `HF_MODEL_ID_JUDGE=TinyLlama/TinyLlama-1.1B-Chat-v1.0`
   - Optional hosted: `HF_INFERENCE_ENDPOINT_URL=https://...` (pointing to your TGI endpoint)
   - Optional cache: set `HF_HOME` to move the HF cache directory (e.g., to a larger drive)
5. Restart backend:
   - `uvicorn app.main:app --reload`
6. Verify it’s active:
   - Start the agent from the UI. In the Status panel, the Task will mention `hf-policy` when the HF policy is used; otherwise it shows `policy-lite` (heuristic).
   - Logs will also indicate model loading the first time.

Troubleshooting:

- Falls back to heuristic: missing/invalid `HF_MODEL_ID_POLICY`, model fetch errors, or runtime generation errors. Check logs and `.env`.
- Import errors for `torch`: ensure PyTorch CPU is installed (step 2) or switch to hosted mode.
- 403/401 on model download: accept the model’s license on its page and/or set a valid `HUGGINGFACE_HUB_TOKEN`.
- Slow generations on CPU: switch to a smaller model or hosted endpoint via `HF_INFERENCE_ENDPOINT_URL`.

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
  - On Windows, Google Play Games Beta is supported via window capture if ADB is not available

Windows quickstart:

- PowerShell: `./scripts/windows_setup.ps1`
- Configure `.env` as needed (see Capture/Input and Window sections)
- Run backend: `uvicorn app.main:app --reload`
- Run UI: `cd ui && pnpm install && pnpm dev`
- Use the UI Start/Pause/Stop buttons to control the agent

### Reinforcement Learning (bandit) configuration

The agent includes a lightweight contextual bandit to guide exploration.

- Environment variables:
  - `RL_ENABLED=true|false` — enable/disable bandit guidance (default true)
  - `RL_METHOD=bandit|off` — select algorithm (currently bandit)
- `RL_EPS_START=0.35` — initial epsilon for exploration (more aggressive)
- `RL_EPS_END=0.10` — floor for epsilon after decay
  - `RL_PERSIST_PATH=data/policy.json` — where learned arm statistics are stored
- Arms: high‑level targets such as `episode`, `side story`, `battle`, `hunt`, `arena`, `summon`, `shop`, `sanctuary`.
- Reward shaping: positive for `daily_progress` increases; negative for `blocks`, `stuck_events`, and `decision_latency_ms` increases.
- Safety: locked features (learned from popups/memory) are skipped by heuristic and down‑weighted by orchestrator.
 - Clickmap learning: the agent records whether taps change the screen and builds a persistent grid of likely-buttons vs static regions to guide future exploration.

Notes:

- The bandit now derives eligible arms from all visible UI button labels and avoids locked ones; it also boosts exploration when the screen is unchanged to break loops.

Clickmap learning (auto-discovery):

- Persists at `data/clickmap.json` as a coarse grid in base-space (40 px cells).
- Each tap updates success/fail counts based on OCR change after the action.
- Policy boosts score near high-success cells (likely buttons), slightly nudges unknown cells, and downweights consistently static areas.

OCR ensemble configuration:

```env
OCR_ENSEMBLE=true
OCR_ENGINES=tesseract,tesseract_batched,paddle
```

- Guidance/Goals edits are persisted to `data/guidance.json`.
- The policy consults memory before proposing actions; check the “Agent Steps” stream for `memory:search` and `memory:locked_labels`.

Backend (FastAPI):

1. Create environment and install deps: `poetry install` (or `uv pip install -r requirements.txt`).
2. Configure `.env` (OCR language, search provider keys, paths).
3. Run API: `uvicorn app.main:app --reload`.
4. Optional: start Ray for parallelism: `ray start --head` and set `PARALLEL_MODE=ray`.
5. Set LLM provider keys (as needed): `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or configure local `ollama`.

UI (React/TypeScript):

1. `cd ui && pnpm install` (or npm/yarn).
2. If Sass preprocessor error occurs, run `npm i -D sass-embedded` (or `pnpm add -D sass-embedded`).
3. `pnpm dev` to start the UI; it connects to the backend via WebSocket/REST.

Emulator:

1. Install and launch your emulator; enable ADB.
2. Calibrate capture and input (resolution, DPI, window title); store settings in config.
3. Set concurrency knobs: frames per second, OCR batch size, and max parallel agents.

### Windows window capture (Google Play Games Beta)

- Set environment variables in `.env` if needed:
  - `CAPTURE_BACKEND=auto` (default) will try ADB first, then window capture
  - `CAPTURE_BACKEND=window` forces window capture
  - `WINDOW_TITLE_HINT=Google Play Games|Epic Seven|Epic 7` can be a regex or simple text to match the emulator window title
  - `WINDOW_ENFORCE_TOPMOST=true` keeps the window on top during capture
  - `WINDOW_LEFT=100`, `WINDOW_TOP=100`, `WINDOW_CLIENT_WIDTH=1280`, `WINDOW_CLIENT_HEIGHT=720` set the fixed position and client-area size
  - `INPUT_EXCLUDE_BOTTOM_PX=40` (optional) keeps taps above the bottom 40px to avoid taskbar overlaps
- Ensure the emulator window is visible (not minimized) and on any monitor.
- Usage examples:
  - Capture one frame: `python -m app.cli capture --output-dir captures`
  - Capture loop: `python -m app.cli capture-loop --fps 1 --ocr --count 5`
  - To force window management before capture add `--ensure-window`

Safety:

- Enable purchase-UI detection; set hard-block mode to prevent any navigation into IAP screens.
- Configure judge to reject actions with any purchase‑related UI elements or ambiguous confirmations.

## Learning and knowledge system

- Continuous perception: capture screenshots at a configurable interval.
- OCR: extract on-screen text (menus, missions, resource counters) for state understanding.
- Web knowledge: periodically query public guides and event info; summarize into durable memories.
- Observational memory: the agent stores lightweight observations of on-screen OCR text as it explores to build a map of where menu labels lead.
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
