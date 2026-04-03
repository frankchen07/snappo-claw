# MEMORY.md - Long-Term Memory

## About Me
- I'm snappo, a fluffy crimson lobster with tortoise shell hues
- Frank's coworker and complementary peer
- Chaotic good energy, direct, curious, low BS tolerance

## About Frank
- Lives in Cupertino, CA (Pacific time)
- Partner Amy (13 years this June), dog Speck (7yo)
- Background: biochem → MPH Columbia → data science → PM → crypto → sabbatical → exploring food/hospitality/tech
- Jiujitsu brown belt, coached 3 years, writes longform on Substack
- Part-time barista at Boast Coffee Co
- Mornings = creation time, no meetings before 13:00

## Key Decisions & Lessons
- macOS TCC blocks OpenClaw from ~/Downloads and ~/Documents — files must be in workspace
- Video file transfers can corrupt silently — always run decode check (`ffmpeg -v error -i file -f null -`) before processing
- Mac mini has ancient bash 3.2 — no associative arrays (`declare -A`), indexed arrays work fine
- youtubeuploader needs "web" type OAuth credentials (not "installed"), redirect URI `http://localhost:8080/oauth2callback`
- Google restricts unverified API projects to ~6 uploads/24h

## Active Projects

### JJ Video Pipeline (jjvideos/)
- **Status:** Working end-to-end as of 2026-03-25
- **Script:** `jjvideos/process.sh` — fully automated compress + rename + upload + trash
- **Input:** Drop .MOV files into `10psj/` (San Jose) or `10psm/` (San Mateo) or root (10p fallback)
- **Naming:** `YYYYMMDD-dayofweektimeofday-LOC-rolling-footage-viewN.mov` from video metadata
- **Outputs:** `sstready/` (archive with audio), `ytready/` (YouTube no audio)
- **Teaching detection:** only for `10psm` Mon/Wed/Fri ~6am PST → auto-copies as `YYYYMMDD-teaching-class-fc.mov`, uploads public to Teaching Snippets playlist (`10psj` morning classes do not create teaching copy)
- **Rolling footage:** unlisted, routed to 10PSJ or 10PSM playlist
- **Post-upload cleanup:** after upload confirmation, move both original source file and uploaded `*-ytready.mov` artifact to `jjvideos/.trash`
- **YouTube account:** frankthetankjj (frankchen07@gmail.com)
- **Credentials:** `client_secrets.json` + `request.token` in jjvideos/ (gitignored)
- **Playlist IDs:** Teaching=PLqn-1QlUBKlCBo9J2Pc63uJL-YkgOMzf-, 10PSJ=PLqn-1QlUBKlDGWyP6FKdvPui8W74wLB3m, 10PSM=PLqn-1QlUBKlCyjUBDOYWXW1Wtw5SI4wNI
