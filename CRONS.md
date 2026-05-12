```zsh
curl -s -X POST "http://127.0.0.1:11434/api/generate" \
-H "Content-Type: application/json" \
-d '{
"model": "qwen3:32b-q4_K_M",
"prompt": "Test connection: say hello and report model name.",
"max_tokens": 60
}'

# # CRON AGENTS (CHANGE MODEL WHEN READY)
openclaw agents add dumptruck \
--agent-dir ~/.openclaw/agents/dumptruck/agent \
--workspace ~/.openclaw/workspace \
--model ollama/qwen3.5:9b

openclaw agents add distiller  \
--agent-dir ~/.openclaw/agents/distiller/agent \
--workspace ~/.openclaw/workspace \
--model ollama/qwen3.5:14b

openclaw agents add memjudge  \
--agent-dir ~/.openclaw/agents/memjudge/agent \
--workspace ~/.openclaw/workspace \
--model ollama/qwen3.5:27b

# # LOCAL MODEL CONTEXT WINDOWS 

# # 27b
# "contextWindow": 16000,
# "maxTokens": 2048

# # 14b
# "contextWindow": 24000,
# "maxTokens": 4096

# # 9b
# "contextWindow": 32000,
# "maxTokens": 8192

# # CRON JOBS
openclaw cron add \
--name rawlog-dump \
--cron "0 */6 * * *" \
--agent dumptruck \
--session isolated \
--announce \
--message 'Dump recent main session traces → workspace/rawlogs/YYYY-MM-DD-<agent-id>.md. Include tool calls, errors, chats > 1h. Max 50k chars.'

openclaw cron add \
--name distill-rawlogs \
--cron "0 23 * * *" \
--agent distiller \
--session isolated \
--announce \
--message 'Distill workspace/rawlogs/*.md (today) → workspace/mem/YYYY-MM-DD.md. Sections: problems, opportunities, observations/patterns, insights/epiphanies, decisions/rationale, todos, abnormalities/questions. 200 lines max. Git commit/push.'

openclaw cron add \
--name distill-mem \
--cron "30 23 * * 1,4" \
--agent memjudge \
--session isolated \
--announce \
--message 'Scan workspace/mem/*.md for the last unread markdown files (last 4 if monday, last 3 if thursday). Extract persistent facts, priorities, knowledge and append the top 20 bullets, dated, to MEMORY.md. Prune duplicates or outdated information. Cross-ref with mem/ and rawlogs/ if there are gaps. Commit and push to git.'

openclaw cron add \
--name crypto-morning \
--cron "0 16 * * *" \
--agent crypto \
--session isolated \
--announce \
--message 'Run scan_watchlist for BTC, ETH, STX, ALEO. For each coin output: trend direction + strength, setup type + quality, confidence score, entry zone, stop level with reason, R:R. Flag any coin with confidence >= 50 as actionable. End with "Not financial advice."'

openclaw cron add \
--name crypto-evening \
--cron "0 4 * * *" \
--agent crypto \
--session isolated \
--announce \
--message 'Run scan_watchlist for BTC, ETH, STX, ALEO. For each coin output: trend direction + strength, setup type + quality, confidence score, entry zone, stop level with reason, R:R. Flag any coin with confidence >= 50 as actionable. End with "Not financial advice."'
```
 

