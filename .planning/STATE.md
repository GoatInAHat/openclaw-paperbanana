# STATE.md — Project Memory

## Current Phase: COMPLETE (all 4 phases)
## Status: ✅ SHIPPED

## What Was Built

### Files
```
skills/paperbanana/
├── SKILL.md                    # Frontmatter + triggers + instructions
├── scripts/
│   ├── generate.py             # Diagram generation (+ continuation)
│   ├── plot.py                 # Statistical plot generation
│   └── evaluate.py             # Diagram quality evaluation
└── references/
    └── providers.md            # Provider comparison + config examples
```

### Config Added
- `skills.entries.paperbanana.enabled = true`
- `skills.entries.paperbanana.env.GOOGLE_API_KEY` = Gemini key (fallback)
- `OPENAI_API_KEY` already global in env.vars (auto-detected as primary)

## Decisions Made
- Use `uv run` + PEP 723 inline deps (nano-banana-pro pattern)
- Gate on `uv` binary only, handle API keys at runtime
- Auto-detect: OpenAI first, Gemini fallback
- Enable `--optimize` by default for better quality
- Auto-trigger requires explicit generation verbs (not bare keywords)
- Files stay local — no Discord file transfer concerns
- Output to /tmp/paperbanana-<timestamp>/
- MEDIA: protocol for output delivery
