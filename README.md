# OpenClaw Setup

Personal AI assistant running locally. Telegram is the primary interface.

```
You (Telegram) → OpenClaw (port 18789) → Smart Proxy (port 4000) → [Ollama | Anthropic | Codex]
```

## Agents

| Agent | Role | Model |
|-------|------|-------|
| `main` | Primary assistant, all Telegram DMs | smart-proxy/auto |
| `youtuber` | YouTube-related tasks | smart-proxy/auto |
| `mechanic` | Tool-heavy / maintenance tasks | smart-proxy/auto |
| `dumptruck` | Raw log dumping | ollama/qwen3.5:9b (local) |
| `distiller` | Distills rawlogs → mem files | ollama/qwen3.5:14b (local) |
| `memjudge` | Curates long-term memory | ollama/qwen3.5:27b (local) |

---

## Model Routing (Smart Proxy)

The proxy at `proxy/` classifies each request and routes to the cheapest capable model.

| Tier | Model | Triggers |
|------|-------|----------|
| cheap | `ollama/qwen3.5:9b` | Short/casual messages, summaries |
| balanced | `anthropic/claude-haiku-4-5` | General Q&A, analysis, tool use |
| premium | `anthropic/claude-sonnet-4-5` | Code, debugging, long context, architecture |

**Fallback chain** (if proxy is down): `openai-codex/gpt-5.3-codex` → `anthropic/claude-sonnet-4-5`

**Escalation** (if a tier fails): cheap → balanced → premium → proxy returns 502 → OpenClaw uses fallback chain above.

To change tiers or routing keywords: edit `proxy/config.yaml`.
Full proxy docs: `proxy/README.md`.

---

## Memory System

3-layer memory, all file-based in `workspace/`:

| Layer | Location | What it holds |
|-------|----------|---------------|
| Identity | `SOUL.md`, `USER.md` | Who the agent is, who Frank is |
| Short-term | `mem/YYYY-MM-DD.md` | Daily distilled notes (200-line cap) |
| Long-term | `MEMORY.md` | Curated keeper memories |

Raw session logs live in `rawlogs/`. Cron jobs distill rawlogs → mem files → MEMORY.md automatically.

**Semantic search** is enabled using local Ollama embeddings (`nomic-embed-text`). Hybrid BM25 + vector search with 14-day temporal decay (recent memories rank higher). If you haven't pulled the model yet: `ollama pull nomic-embed-text`.

---

## Key Config (`openclaw.json`)

| Setting | Value | Why |
|---------|-------|-----|
| `contextPruning.ttl` | 20m | Prune stale tool results aggressively |
| `contextPruning.keepLastAssistants` | 6 | Preserve enough turns for agentic continuity |
| `compaction.mode` | safeguard | Chunked summarization with guardrails |
| `compaction.keepRecentTokens` | 30k | Mid-task state survives compaction |
| `compaction.identifierPolicy` | strict | Preserves file paths, task IDs across compaction |
| `compaction.postCompactionSections` | On Startup, Red Lines | Re-injected from AGENTS.md after every compaction |
| `compaction.memoryFlush` | enabled | Writes state to disk before compaction fires |
| `session.maintenance` | enforce, 30d | Auto-cleans old session transcripts |
| `memorySearch.provider` | ollama | Local embeddings (free) |
| `memorySearch.cache` | enabled, 50k | Avoid re-embedding unchanged files |

---

## Starting Everything

**Smart proxy** auto-starts on login via launchd. To manage it manually:

```bash
# Start
launchctl load ~/Library/LaunchAgents/com.openclaw.smart-proxy.plist

# Stop
launchctl unload ~/Library/LaunchAgents/com.openclaw.smart-proxy.plist

# Health check
curl http://127.0.0.1:4000/health

# Logs
tail -f /Users/snappo/.openclaw/proxy/logs/stdout.log
```

**OpenClaw** start/restart as normal. Order doesn't matter — if the proxy isn't up yet, OpenClaw falls back to codex until it is.

---

## Directory Structure

```
.openclaw/
├── openclaw.json          # Main config — edit this to change agents, models, settings
├── .env                   # Secrets (never commit)
├── proxy/                 # Smart model routing proxy
│   ├── README.md          # Proxy-specific docs
│   ├── config.yaml        # Model tiers + routing keywords (edit to tune routing)
│   ├── server.py          # FastAPI proxy server
│   ├── router.py          # Classification logic
│   └── logs/              # Proxy request logs
├── workspace/             # Agent's persistent workspace (git repo)
│   ├── AGENTS.md          # Agent behavior rules
│   ├── SOUL.md            # Agent identity
│   ├── USER.md            # Frank's profile
│   ├── MEMORY.md          # Long-term memory
│   ├── mem/               # Short-term daily memory files
│   └── rawlogs/           # Raw session transcripts
├── agents/                # Per-agent state (sessions, auth profiles)
├── memory/                # SQLite semantic memory index
├── cron/jobs.json         # Scheduled jobs (distillation, log dumps)
└── logs/                  # Gateway server logs
```

---

## Common Tasks

**Change which model handles a tier:**
Edit `proxy/config.yaml` → `models.cheap/balanced/premium`

**Add a routing keyword:**
Edit `proxy/config.yaml` → `premium_keywords` or `balanced_keywords`

**Change compaction behavior:**
Edit `openclaw.json` → `agents.defaults.compaction`

**View what the agent remembers:**
```bash
cat workspace/MEMORY.md
cat workspace/mem/$(date +%Y-%m-%d).md
```

**Reload config without full restart:**
Send `SIGUSR1` to the OpenClaw process (hot-reloads channels, plugins, bindings).
Full structural changes (models, agents) require a restart.
