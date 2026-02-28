# Research Summary — OpenClaw PaperBanana Skill

## Stack
- **Package:** `paperbanana` v0.1.2 via pip, Python 3.10+, no system deps
- **Pattern:** `uv run` with PEP 723 inline deps (`# /// script` block) — the nano-banana-pro pattern. Zero manual pip installs needed.
- **Deps inline:** `paperbanana[all-providers]>=0.1.2` gives both OpenAI + Gemini
- **API:** `PaperBananaPipeline(settings)` → `pipeline.generate(GenerationInput)` → `result.image_path`
- **CLI:** `paperbanana generate --input X --caption Y [--optimize] [--auto]`
- **Output:** `MEDIA:{path}` stdout protocol for OpenClaw auto-attach

## Features
- 4 MCP tools (not 3): generate_diagram, generate_plot, evaluate_diagram, download_references
- `optimize` and `auto_refine` default to False — skill should flip optimize to True
- 8 aspect ratios: 1:1, 2:3, 3:2, 3:4, 4:3, 9:16, 16:9, 21:9
- Run continuation is first-class: `--continue --feedback "..."` maps to chat iteration
- Gemini free tier viable as default (gemini-2.0-flash + gemini-3-pro-image-preview)

## Architecture
- Directory: SKILL.md + scripts/generate.py + scripts/evaluate.py + references/
- Data flow: user msg → agent matches skill → exec `uv run generate.py` → MEDIA: output → chat delivery
- Provider auto-detect: check OPENAI_API_KEY first, fall back to GOOGLE_API_KEY
- Don't gate on env vars in metadata — handle at runtime for graceful degradation
- Gate only on `uv` binary (required for isolated dep management)

## Key Pitfalls & Fixes
- **Sandbox env injection:** Use workspace config file approach, not just env vars
- **Gating chicken-and-egg:** Gate on `uv`, not `paperbanana`
- **Auto-trigger false positives:** Require explicit generation verbs, not bare keywords
- **Rate limits:** Default 3 iterations, not auto-refine. Gemini free tier is 15 RPM.
- **File delivery:** Files stay local (Bennett confirmed no Discord transfer needed), MEDIA: protocol handles it
