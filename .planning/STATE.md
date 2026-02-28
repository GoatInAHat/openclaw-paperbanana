# STATE.md — Project Memory

## Current Phase: 1 (Skill Foundation)
## Status: IN PROGRESS

## Decisions
- Use `uv run` + PEP 723 inline deps (nano-banana-pro pattern)
- Gate on `uv` binary only, handle API keys at runtime
- Default to Gemini free tier when no OpenAI key present
- Enable `--optimize` by default for better quality
- Auto-trigger requires explicit generation verbs
- Files stay local — no Discord file transfer concerns
- Output to /tmp/paperbanana-<timestamp>/
