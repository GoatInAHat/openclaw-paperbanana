# PROJECT.md — OpenClaw PaperBanana Skill

## What This Is

An OpenClaw skill that integrates PaperBanana — an AI framework for generating publication-quality academic diagrams and statistical plots from text descriptions. The skill wraps the community `llmsresearch/paperbanana` Python package, exposing all features through OpenClaw's native skill system with smart auto-triggering.

## Core Value

Enable any OpenClaw instance to generate professional academic illustrations (methodology diagrams, statistical plots, architecture figures) from natural language — automatically detecting when diagrams are needed and using the instance's existing API keys or user-provided ones.

## Who It's For

- OpenClaw users who work with academic papers, research, or technical documentation
- Anyone who needs publication-quality diagrams without manual design tools
- Specifically: Bennett (CS student, RAF patent, research papers)

## How It Works

### Integration Architecture

1. **SKILL.md** — Core skill file with frontmatter triggers, usage instructions, and progressive disclosure references
2. **Scripts** — Python wrappers around PaperBanana's Python API (generate_diagram, generate_plot, evaluate_diagram, refine)
3. **Setup script** — First-run installer that `pip install paperbanana`, detects existing API keys from OpenClaw config, and optionally accepts custom keys
4. **MCP config generator** — Bonus: outputs MCP server config JSON for users who also run Claude Code/Cursor alongside OpenClaw

### API Key Strategy

On installation, the skill:
1. Checks for existing API keys in the OpenClaw environment (`GOOGLE_API_KEY`, `OPENAI_API_KEY`, etc.)
2. If found: auto-configures PaperBanana to use them (Gemini free tier preferred, OpenAI as fallback)
3. If not found: prompts user for keys via interactive setup
4. Stores config in `skills.entries.paperbanana.env` via OpenClaw's native mechanism
5. Users can also provide keys in `~/.openclaw/openclaw.json` config overrides

### Auto-Triggering (When to Use)

The skill should be automatically invoked when:

**Keyword triggers:**
- "diagram", "figure", "plot", "chart", "graph", "visualize", "illustration", "flowchart", "architecture diagram", "pipeline diagram", "method figure"

**Context triggers:**
- Working on academic papers, research documents, LaTeX files
- Discussing methodology or system architecture that would benefit from visual representation
- When CSV/JSON data is present and user discusses results/comparisons
- During paper writing workflows

**Proactive:**
- During heartbeats, if academic work is in progress, suggest figure generation
- When method sections or system descriptions are written, offer to generate accompanying diagrams

### PaperBanana Features to Expose

All features from the `llmsresearch/paperbanana` package:

1. **Generate Diagram** — From method text + caption → publication-quality methodology diagram
   - Input optimization (context enrichment + caption sharpening)
   - Auto-refine mode (iterate until critic satisfied)
   - Configurable iterations, providers, models
   - Output format selection (PNG, JPEG, WebP)

2. **Generate Plot** — From CSV/JSON data + intent → statistical plot
   - Bar charts, line plots, scatter plots, etc.
   - Refinement iterations

3. **Evaluate Diagram** — Compare generated vs human reference
   - Faithfulness, Readability, Conciseness, Aesthetics scores
   - VLM-as-Judge assessment

4. **Refine/Continue** — Resume a previous generation with feedback
   - Continue from latest or specific run
   - User feedback for targeted improvements

### Provider Support

| Component | Provider | Model | Notes |
|-----------|----------|-------|-------|
| VLM (planning, critique) | OpenAI | gpt-5.2 | Default |
| Image Generation | OpenAI | gpt-image-1.5 | Default |
| VLM | Google Gemini | gemini-2.0-flash | Free tier |
| Image Generation | Google Gemini | gemini-3-pro-image-preview | Free tier |
| VLM / Image | OpenRouter | Any supported model | Flexible |

## Constraints

- Must work in sandboxed (Docker) and non-sandboxed environments
- Must not require manual pip install — setup script handles it
- Must respect OpenClaw's env injection system (`skills.entries`)
- Must work with just a Gemini API key (free tier) — no hard dependency on OpenAI
- Output images must be saved to accessible paths and delivered to chat surfaces
- Should be publishable to ClawHub as a community skill

## Tech Stack

- Python 3.10+ (PaperBanana requirement)
- `paperbanana` pip package (community, `llmsresearch/paperbanana`)
- OpenClaw skill format (SKILL.md + scripts/ + references/)
- YAML/JSON config for PaperBanana settings
- Shell scripts for setup/installation

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Community package over official | `llmsresearch/paperbanana` has pip install, MCP, multi-provider support | ✅ Decided |
| Python scripts over MCP for OpenClaw | OpenClaw has no native MCP client; exec + scripts is the native pattern | ✅ Decided |
| Gemini as default provider | Free tier, Bennett has key, lowest friction for new users | ✅ Decided |
| Auto-trigger via description keywords | OpenClaw loads skill description into system prompt for matching | ✅ Decided |
| Setup script for first-run | Handles pip install + key detection without manual steps | ✅ Decided |

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] SKILL.md with proper frontmatter, triggers, and instructions
- [ ] Setup/install script (pip install + key detection)
- [ ] Generate diagram script (wraps Python API)
- [ ] Generate plot script (wraps Python API)  
- [ ] Evaluate diagram script (wraps Python API)
- [ ] Refine/continue script (resume with feedback)
- [ ] Provider auto-detection from OpenClaw env
- [ ] Output delivery to chat surfaces (file paths → message tool)
- [ ] Reference docs for configuration and advanced usage
- [ ] MCP config generator for Claude Code/Cursor users

### Out of Scope

- Building a custom UI/Streamlit interface — PaperBanana has one
- Training custom models — we use existing providers
- Hosting a persistent PaperBanana server — stateless script invocations
- Direct integration with specific paper-writing tools (Overleaf, etc.)

---
*Last updated: 2026-02-28 after initialization*
