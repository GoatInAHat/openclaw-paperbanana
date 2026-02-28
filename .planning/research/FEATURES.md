# PaperBanana Features Research
> Researched: 2026-02-28 UTC
> Sources: GitHub README, mcp_server/README.md, mcp_server/server.py (exact), PyPI page

---

## 1. PaperBanana Feature Inventory

### CLI Commands

#### `paperbanana generate` — Methodology Diagrams
| Flag | Short | Description |
|------|-------|-------------|
| `--input` | `-i` | Path to methodology text file (required for new runs) |
| `--caption` | `-c` | Figure caption / communicative intent (required for new runs) |
| `--output` | `-o` | Output image path (default: auto-generated in `outputs/`) |
| `--iterations` | `-n` | Number of Visualizer-Critic refinement rounds (default: 3) |
| `--auto` | | Loop until critic is satisfied (with `--max-iterations` safety cap) |
| `--max-iterations` | | Safety cap for `--auto` mode (default: 30) |
| `--optimize` | | Preprocess inputs with parallel context enrichment and caption sharpening |
| `--continue` | | Continue from the latest run in `outputs/` |
| `--continue-run` | | Continue from a specific run ID (e.g. `run_20260218_125448_e7b876`) |
| `--feedback` | | User feedback for the critic when continuing a run |
| `--vlm-provider` | | VLM provider name (default: `openai`) |
| `--vlm-model` | | VLM model name (default: `gpt-5.2`) |
| `--image-provider` | | Image gen provider (default: `openai_imagen`) |
| `--image-model` | | Image gen model (default: `gpt-image-1.5`) |
| `--format` | `-f` | Output format: `png`, `jpeg`, or `webp` (default: `png`) |
| `--config` | | Path to YAML config file |
| `--verbose` | `-v` | Show detailed agent progress and timing |

#### `paperbanana plot` — Statistical Plots
| Flag | Short | Description |
|------|-------|-------------|
| `--data` | `-d` | Path to data file, CSV or JSON (required) |
| `--intent` | | Communicative intent for the plot (required) |
| `--output` | `-o` | Output image path |
| `--iterations` | `-n` | Refinement iterations (default: 3) |

#### `paperbanana evaluate` — Quality Assessment
| Flag | Short | Description |
|------|-------|-------------|
| `--generated` | `-g` | Path to generated image (required) |
| `--reference` | `-r` | Path to human reference image (required) |
| `--context` | | Path to source context text file (required) |
| `--caption` | `-c` | Figure caption (required) |

Scores on 4 dimensions (hierarchical aggregation per the paper):
- **Primary**: Faithfulness, Readability
- **Secondary**: Conciseness, Aesthetics

#### `paperbanana setup` — First-Time Configuration
Interactive wizard to obtain and save API keys (Google Gemini or OpenAI).

---

### Python API

**Core classes:**
- `PaperBananaPipeline(settings: Settings)` — main pipeline orchestrator
- `GenerationInput(source_context, communicative_intent, diagram_type, aspect_ratio?, raw_data?)` — input model
- `DiagramType` enum — `METHODOLOGY`, `STATISTICAL_PLOT`
- `Settings(vlm_provider, vlm_model, image_provider, image_model, optimize_inputs, auto_refine, refinement_iterations, max_iterations)`
- `load_resume_state(outputs_dir, run_id)` — load previous run state for continuation

**Core methods:**
- `await pipeline.generate(gen_input: GenerationInput) -> GenerationResult` — run full pipeline
- `await pipeline.continue_run(resume_state, additional_iterations, user_feedback)` — continue a run

**Supporting modules:**
- `paperbanana.core.config.Settings` — configuration management
- `paperbanana.core.resume.load_resume_state` — run continuation
- `paperbanana.evaluation.judge.VLMJudge` — standalone evaluation
- `paperbanana.providers.registry.ProviderRegistry` — provider instantiation

---

### MCP Tools (4 tools — exact schemas from `mcp_server/server.py`)

#### `generate_diagram`
```python
async def generate_diagram(
    source_context: str,    # Methodology section text or paper excerpt
    caption: str,           # Figure caption describing what to communicate
    iterations: int = 3,    # Refinement rounds (used when auto_refine=False)
    aspect_ratio: str | None = None,  # "1:1"|"2:3"|"3:2"|"3:4"|"4:3"|"9:16"|"16:9"|"21:9"
    optimize: bool = False, # Enrich context and sharpen caption before generation
    auto_refine: bool = False, # Critic loops until satisfied (max 30 iterations)
) -> Image  # Returns PNG image
```

#### `generate_plot`
```python
async def generate_plot(
    data_json: str,         # JSON string of data: '{"x":[1,2,3],"y":[4,5,6]}'
    intent: str,            # Description of desired plot
    iterations: int = 3,
    aspect_ratio: str | None = None,
    optimize: bool = False,
    auto_refine: bool = False,
) -> Image  # Returns PNG image
```

#### `evaluate_diagram`
```python
async def evaluate_diagram(
    generated_path: str,    # File path to model-generated image
    reference_path: str,    # File path to human-drawn reference image
    context: str,           # Original methodology text
    caption: str,           # Figure caption
) -> str  # Returns formatted score report: Faithfulness, Conciseness, Readability, Aesthetics + overall winner
```

#### `download_references` *(hidden 4th tool — not in README summary)*
```python
async def download_references(
    force: bool = False,    # Re-download even if cached
) -> str  # Downloads ~294 examples (~257MB) from HuggingFace PaperBananaBench
```
> **Note**: The README says "3 MCP tools" but the actual server exposes 4. `download_references` is real and useful.

---

### Claude Code Skills (ships in `.claude/skills/`)

| Skill | Invocation |
|-------|-----------|
| Generate diagram | `/generate-diagram <file> [caption]` |
| Generate plot | `/generate-plot <data-file> [intent]` |
| Evaluate diagram | `/evaluate-diagram <generated> <reference>` |

These are project-local skills (require repo clone). They are thin wrappers that call the MCP tools.

---

### Multi-Agent Pipeline Architecture

**Phase 0 — Input Optimization (optional, `--optimize` / `optimize=True`):**
- **Context Enricher** — Structures raw methodology text into diagram-ready format (components, flows, groupings, I/O)
- **Caption Sharpener** — Transforms vague captions into precise visual specifications
- Both run in parallel via two VLM calls

**Phase 1 — Linear Planning:**
1. **Retriever** — Selects most relevant examples from 13 curated (or 294 expanded) reference diagrams
2. **Planner** — Generates detailed textual diagram description via in-context learning
3. **Stylist** — Refines description for visual aesthetics (NeurIPS-style: color palette, layout, typography)

**Phase 2 — Iterative Refinement:**
4. **Visualizer** — Renders description to image
5. **Critic** — Evaluates image vs. source context, provides revised description
6. Steps 4-5 repeat: fixed `iterations` rounds, or until satisfied (`auto_refine`)

---

### Provider Support

| Component | Provider | Models |
|-----------|----------|--------|
| VLM (planning + critique) | OpenAI | `gpt-5.2` (default) |
| Image Generation | OpenAI | `gpt-image-1.5` (default) |
| VLM | Google Gemini | `gemini-2.0-flash` (free tier) |
| Image Generation | Google Gemini | `gemini-3-pro-image-preview` (free tier) |
| VLM + Image | OpenRouter | Any supported model (flexible routing) |
| VLM + Image | Azure OpenAI / Foundry | Auto-detected via `OPENAI_BASE_URL` |

---

### Configuration System

- YAML config file (`configs/config.yaml`) — override any setting
- Environment variables (`.env`): `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `GOOGLE_API_KEY`
- CLI flags override config file
- Key config fields: `vlm.provider`, `vlm.model`, `image.provider`, `image.model`, `pipeline.refinement_iterations`, `pipeline.auto_refine`, `pipeline.max_iterations`, `pipeline.optimize_inputs`, `pipeline.output_resolution`, `output.dir`, `output.save_iterations`, `output.save_metadata`

---

### Output Management

- Runs saved to `outputs/run_<timestamp>_<hash>/`
- `final_output.png` — the best result
- All intermediate iterations saved (`save_iterations: true`)
- Metadata JSON saved alongside each run
- Run IDs allow continuation (`--continue-run <run_id>`)
- Auto-detected "latest run" for `--continue`

---

### Reference Data

- **Bundled**: 13 curated methodology diagrams spanning 4 domains (agent/reasoning, vision/perception, generative/learning, science/applications)
- **Expanded** (optional download): ~294 examples (~257MB) from HuggingFace PaperBananaBench dataset
- `download_references` MCP tool to fetch expanded set

---

## 2. Table Stakes (Must-Have in OpenClaw Skill)

These features form the minimum viable skill — without them, the skill adds no value:

| Feature | Rationale |
|---------|-----------|
| **Install & dependency check** | Verify `paperbanana` is installed; auto-install if not; check API keys are configured |
| **`generate` diagram** — wrapper | Core workflow: text file + caption → PNG |
| **`plot` generation** — wrapper | Core workflow: CSV/JSON data + intent → PNG |
| **API key configuration** | Wrap `paperbanana setup`; store keys in OpenClaw secrets store |
| **Multi-provider selection** | Expose OpenAI vs. Gemini choice; Gemini is free so important for low-cost usage |
| **Output path management** | Map PaperBanana's `outputs/` directory into a consistent OpenClaw-managed location |
| **Basic error surfacing** | If generation fails (API key missing, rate limit), surface actionable message to user in chat |
| **Verbose/progress reporting** | Long-running pipeline (30s–2min); user needs feedback that it's working |

---

## 3. Differentiators

What makes the OpenClaw skill more valuable than just running `paperbanana generate` directly:

| Feature | Why It Differentiates |
|---------|----------------------|
| **Run continuation from chat** | User says "make the arrows thicker" → skill loads last run, passes feedback, continues — no CLI needed |
| **Auto-refine mode with progress updates** | Enable `--auto` by default; stream critic iteration count back to chat ("Iteration 2/∞ — critic not satisfied yet…") |
| **Input optimization by default** | `--optimize` is off by default in CLI; skill turns it on by default for better quality |
| **Evaluation workflow** | Generate → auto-evaluate against a reference → post score card to chat; closes the quality loop |
| **Proactive illustration suggestions** | When user pastes paper methodology text into chat, skill detects and proactively offers "Want me to generate a diagram for this?" |
| **Aspect ratio selection** | MCP tool exposes 8 aspect ratios; skill can prompt user for target venue (NeurIPS poster = 16:9, paper figure = 4:3) |
| **Iteration count tuning guidance** | Skill can suggest: "For a quick draft use 2 iterations; for final paper quality use auto-refine" |
| **Reference expansion** | Skill can trigger `download_references` to upgrade from 13 → 294 examples on first use |
| **Run history browsing** | List previous `outputs/run_*` runs in chat with thumbnails and metadata |

---

## 4. OpenClaw-Specific Additions

Features that require OpenClaw integration and don't exist in raw PaperBanana:

| Feature | Implementation Notes |
|---------|---------------------|
| **Chat image delivery** | After generation, send image directly to Discord/Slack channel via `message` tool — not just a file path |
| **File management in workspace** | Save outputs to `/data/workspace/paperbanana/outputs/` instead of a relative `outputs/` dir |
| **Context-aware triggering** | Parse chat messages for methodology text patterns ("our framework consists of…", "we propose…") and offer to generate diagram |
| **Secrets integration** | Store `OPENAI_API_KEY` / `GOOGLE_API_KEY` in `/data/workspace/.secrets/` rather than `.env` files |
| **Structured run log** | Append each run to a session log: timestamp, run_id, input summary, output path, iteration count — supports "last run" lookups |
| **Canvas preview** | If canvas is available, show generated diagram inline before delivering to chat |
| **Subagent isolation** | Long-running generations (auto-refine, optimize) should run in background subagents so they don't block main session |
| **Multi-figure batch** | Accept a list of method sections → spawn subagents per figure → collect and deliver all outputs |
| **Provider auto-selection** | Check which API keys are present; prefer Gemini if no OpenAI key (it's free); surface config gap if neither present |
| **Skill installer wizard** | `paperbanana setup` equivalent that writes secrets to OpenClaw's secrets store and validates with a test generation |

---

## 5. Anti-Features (What NOT to Build)

Features we explicitly should NOT add to the OpenClaw skill:

| Anti-Feature | Reason to Avoid |
|-------------|----------------|
| **Streamlit / web UI** | PaperBanana's HuggingFace demo is already this; OpenClaw delivers via chat — no web UI needed |
| **Dataset management / curation scripts** | `scripts/` in the repo are for the paper authors; not relevant to skill users |
| **Custom agent prompt editing** | The `prompts/` directory ships tuned prompts; don't expose editing as a skill feature (complexity without payoff) |
| **Reference set curation tools** | Building your own reference set is a research activity, not a skill use case |
| **Matplotlib code output mode** | Plots use Matplotlib internally; exposing raw Python code adds no value for OpenClaw users |
| **Direct VLM provider SDK wrapping** | Don't re-expose OpenAI/Gemini APIs — use PaperBanana as the abstraction layer |
| **Training / fine-tuning hooks** | Not in scope for a generation skill |
| **Batch benchmark evaluation** | `evaluate` is for single-pair QA; running PaperBananaBench at scale is a research workflow |
| **Version pinning / dependency management** | Let `pip install paperbanana` handle this; skill should not try to manage venv isolation |
| **Exposing raw `--config` YAML editing** | OpenClaw's config patterns (env vars, secrets) supersede YAML file management for skill users |

---

## 6. Feature Dependencies

```
REQUIRED TO INSTALL:
  paperbanana           # pip install paperbanana
  paperbanana[mcp]      # pip install paperbanana[mcp]   (for MCP server mode)
  fastmcp               # pulled in by [mcp] extra
  Pillow                # pulled in by paperbanana (image compress/resize)
  structlog             # pulled in by paperbanana
  pydantic v2           # pulled in by paperbanana
  typer                 # CLI framework (pulled in)

REQUIRED AT RUNTIME:
  One of:
    OPENAI_API_KEY      → OpenAI VLM + image generation (default, paid)
    GOOGLE_API_KEY      → Gemini VLM + image generation (free tier)
    OPENROUTER_API_KEY  → OpenRouter routing (flexible, paid)

  For Azure/Foundry:
    OPENAI_BASE_URL     → Custom endpoint, auto-detected by paperbanana

OPTIONAL RUNTIME:
  download_references   → Network access to HuggingFace (~257MB, one-time)
  PAPERBANANA_MAX_IMAGE_BYTES → Override 3.75MB MCP image size limit

OPENCLAW SKILL DEPENDENCIES:
  exec tool             → Run paperbanana CLI commands
  message tool          → Deliver generated images to chat channels
  canvas tool           → Optional inline preview
  /data/workspace/.secrets/ → API key storage
  subagents tool        → Background generation for long-running jobs

PYTHON COMPATIBILITY:
  Python 3.10+          (hard requirement from paperbanana)

OPENCLAW COMPATIBILITY:
  OpenClaw any version  (uses only standard exec/message/canvas tools)
```

---

## Summary Notes

- **4 MCP tools** (not 3 as README claims): `generate_diagram`, `generate_plot`, `evaluate_diagram`, `download_references`
- **`download_references` is significant**: upgrades retriever from 13 → 294 examples, meaningfully improves quality
- **`optimize` defaults to False** in both CLI and MCP — OpenClaw skill should flip this default to `True`
- **`auto_refine` defaults to False** — skill should offer it prominently; it's the highest-quality path
- **Run continuation is first-class**: the `--continue`/`--continue-run` + `--feedback` pattern maps naturally to chat iteration ("make it better")
- **Aspect ratio is under-documented**: 8 supported ratios are only in MCP docstring, not CLI help — worth surfacing in skill
- **Gemini is free tier**: Strongest differentiator for users without OpenAI credits; skill should default-prefer Gemini if available
- **Image size compression**: MCP server auto-compresses >3.75MB images for Claude API compatibility — this is transparent but good to know for quality expectations
