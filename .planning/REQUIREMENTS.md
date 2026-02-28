# REQUIREMENTS.md — OpenClaw PaperBanana Skill

## v1 Requirements

### Setup & Configuration
- [ ] **SETUP-01**: Skill loads when `uv` is on PATH (no other binary requirements)
- [ ] **SETUP-02**: On first use, `uv run` auto-installs `paperbanana[all-providers]` into isolated venv via PEP 723 inline deps
- [ ] **SETUP-03**: Provider auto-detected from environment: OPENAI_API_KEY → OpenAI, GOOGLE_API_KEY → Gemini, neither → clear error with setup instructions
- [ ] **SETUP-04**: Users configure keys via `skills.entries.paperbanana.env` in `~/.openclaw/openclaw.json`

### Diagram Generation
- [ ] **GEN-01**: Generate methodology diagram from text description + caption via `uv run generate.py`
- [ ] **GEN-02**: Input optimization enabled by default (`--optimize`) for better quality
- [ ] **GEN-03**: Configurable iterations (default: 3), auto-refine available on request
- [ ] **GEN-04**: Output saved to `/tmp/paperbanana-<timestamp>/` and delivered via `MEDIA:` protocol
- [ ] **GEN-05**: Support aspect ratio selection (8 ratios: 1:1, 2:3, 3:2, 3:4, 4:3, 9:16, 16:9, 21:9)

### Plot Generation
- [ ] **PLOT-01**: Generate statistical plot from CSV/JSON data + intent description
- [ ] **PLOT-02**: Support inline JSON data and file path inputs

### Evaluation
- [ ] **EVAL-01**: Evaluate generated diagram against human reference image
- [ ] **EVAL-02**: Return structured scores (Faithfulness, Readability, Conciseness, Aesthetics)

### Run Continuation
- [ ] **CONT-01**: Continue/refine last generation with user feedback (`--continue --feedback "..."`)
- [ ] **CONT-02**: Continue specific run by ID

### Skill Integration
- [ ] **SKILL-01**: SKILL.md with proper frontmatter, emoji, gating on `uv` binary
- [ ] **SKILL-02**: Description triggers on explicit generation intent ("generate a diagram", "create a figure", "make a plot")
- [ ] **SKILL-03**: Progressive disclosure: lean SKILL.md body, detailed reference docs in references/
- [ ] **SKILL-04**: Provider reference doc (references/providers.md) with model table and config examples

## v2 Requirements (Deferred)
- [ ] Reference set expansion (download_references — 294 examples from HuggingFace)
- [ ] MCP config generator for Claude Code/Cursor users
- [ ] Batch multi-figure generation via subagent spawning
- [ ] Run history browser with metadata display
- [ ] Canvas preview before final delivery
- [ ] Venue-aware aspect ratio suggestions (NeurIPS poster vs paper figure)

## Out of Scope
- Streamlit/web UI — PaperBanana already has one
- Dataset curation tools — research workflow, not skill use case
- Custom agent prompt editing — internal PaperBanana concern
- Direct VLM provider wrapping — use PaperBanana as abstraction
- YAML config file management — OpenClaw env vars supersede this

## Traceability

| Phase | Requirements |
|-------|-------------|
| 1 | SKILL-01, SKILL-02, SKILL-03, SKILL-04, SETUP-01, SETUP-03, SETUP-04 |
| 2 | GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, SETUP-02 |
| 3 | PLOT-01, PLOT-02, EVAL-01, EVAL-02 |
| 4 | CONT-01, CONT-02 |
