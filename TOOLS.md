# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

### Model Routing Preferences

Default auth priority: anthropic:manual → openai-codex:default → api (anthropic credits)

| Task Type | Model | Why |
|---|---|---|
| Main session (chat, decisions, writing) | opus 4.6 | Needs nuance and quality |
| Complex reasoning, brainstorming | opus 4.6 | Heavy thinking |
| Coding subagents, PR work, implementation | codex 5.3 | Built for code |
| Research, summarization, bulk processing | sonnet 4.5 | Good enough, cheaper |
| Quick lookups, cron jobs, low-stakes automation | haiku 4.5 | Fast and light |
| Writing drafts, editing | opus 4.6 | Voice and craft matter |

When spawning subagents, pick the model that fits the job — don't default everything to opus.

**Active subscriptions/credits** (update as things change):
- anthropic:manual — active (subscription token)
- openai-codex:default — active (OAuth, check weekly limits via `openclaw models status`)
- api — active (anthropic API credits, check spend at console.anthropic.com)

**When a subscription expires or credits run low:** Update this section and adjust routing. The fallback chain in openclaw.json handles automatic failover, but we should proactively shift workloads to avoid burning expensive credits on tasks that don't need them.

---

Add whatever helps you do your job. This is your cheat sheet.
