# STACK Research — OpenClaw PaperBanana Skill

*Researched: 2026-02-28*
*Sources: PyPI pyproject.toml, GitHub llmsresearch/paperbanana, /openclaw/skills/ audit*

---

## 1. Python Package Details

### Identification
- **Package name:** `paperbanana`
- **Current version:** `0.1.2`
- **Build system:** Hatchling
- **License:** MIT
- **Status:** Alpha (Development Status :: 3 - Alpha)

### Python Version Requirement
- **Minimum:** Python 3.10+
- **Tested on:** 3.10, 3.11, 3.12

### Core Dependencies (always installed)
```
pydantic>=2.0
pydantic-settings>=2.0
pyyaml>=6.0
google-genai>=1.65       ← Gemini SDK, bundled in core even without [google] extra
pillow>=10.0
typer>=0.12
rich>=13.0
httpx>=0.27
aiofiles>=23.0
matplotlib>=3.8
pandas>=2.0
tenacity>=8.0
structlog>=24.0
python-dotenv>=1.0
platformdirs>=4.0
```

### Optional Extras
| Extra | Packages | Purpose |
|-------|----------|---------|
| `[google]` | `google-genai>=1.65` | Gemini VLM + image gen (already in core deps, extra is a convenience alias) |
| `[openai]` | `openai>=1.0` | OpenAI GPT-5.2 VLM + GPT-Image-1.5 generation |
| `[all-providers]` | `google-genai>=1.65`, `openai>=1.0` | Both providers together |
| `[mcp]` | `fastmcp>=2.0` | MCP server for Claude Code / Cursor IDE integration |
| `[dev]` | `pytest>=8.0`, `pytest-asyncio>=0.23`, `pytest-cov>=4.0`, `ruff>=0.4` | Development and testing |
| `[pdf]` | `pymupdf>=1.24` | PDF reading for context extraction |

### CLI Entry Points (defined in pyproject.toml)
```
paperbanana       → paperbanana.cli:app          # main CLI
paperbanana-mcp   → mcp_server.server:main       # MCP server
```

### Wheel Bundled Data
The wheel ships with non-Python data included:
- `prompts/` — All agent prompt templates (retriever, planner, stylist, visualizer, critic, evaluation)
- `data/` — 13 curated reference methodology diagrams + NeurIPS-style guidelines
- `configs/config.yaml` — Default configuration

---

## 2. System Requirements

### No System-Level Dependencies
PaperBanana has **no native system dependencies** (no Cairo, Graphviz, Poppler, ImageMagick, etc.).

Everything runs in Python:
- Image processing via Pillow
- Statistical plots via Matplotlib
- Data handling via Pandas
- PDF reading (optional) via PyMuPDF

### Runtime Requirements
- Python 3.10+ binary (`python3` or via `uv`)
- Internet access for API calls (OpenAI or Gemini APIs)
- At least one valid API key: `OPENAI_API_KEY` or `GOOGLE_API_KEY`

### Disk Space Estimate
- Package + deps: ~150–300 MB (Pillow, Matplotlib, Pandas pull in numpy, etc.)
- Output files: PNG diagrams saved to `outputs/run_<timestamp>/`
- Reference data bundled in wheel: ~few MB

---

## 3. OpenClaw Skill Patterns

From auditing `/openclaw/skills/` (45+ skills), specifically `openai-image-gen`, `nano-banana-pro`, `coding-agent`, `skill-creator`, `himalaya`, `model-usage`:

### Directory Structure

```
skill-name/
├── SKILL.md          ← Required. YAML frontmatter + Markdown body
├── scripts/          ← Python/Bash executables
└── references/       ← Markdown docs loaded into context as needed
```
(No README.md, no CHANGELOG.md — skill-creator explicitly forbids extra docs)

### SKILL.md Frontmatter Schema
```yaml
---
name: skill-name
description: >
  What the skill does AND when to trigger it. Both audiences: 
  (1) the model deciding whether to load this skill, 
  (2) the model using the skill. Triggering uses this field.
metadata:
  openclaw:
    emoji: "🍌"
    requires:
      bins: ["python3"]         # or ["uv"] for uv-based scripts
      env: ["OPENAI_API_KEY"]   # list of required env vars
    primaryEnv: "OPENAI_API_KEY"   # single key shown in setup UI
    install:
      - id: python-brew
        kind: brew
        formula: python
        bins: ["python3"]
        label: "Install Python (brew)"
---
```

Key rules:
- `requires.env` → OpenClaw checks these exist before offering the skill
- `primaryEnv` → drives the API key setup UI in OpenClaw
- `install` → brew formulas shown in the "install missing deps" flow
- No other custom fields in frontmatter beyond `name`, `description`, `metadata`

### Script Pattern: uv with Inline PEP 723 Deps

The dominant pattern for Python scripts (seen in `nano-banana-pro`):
```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""Docstring..."""
import argparse, os, sys
from pathlib import Path

def get_api_key(provided_key=None):
    if provided_key:
        return provided_key
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
```

Run with: `uv run {baseDir}/scripts/script.py --args`

This makes the script **self-contained** — no pip install needed, uv handles isolation.

### The `{baseDir}` Template Variable
OpenClaw injects `{baseDir}` in SKILL.md as the absolute path to the skill directory.
Use this when referencing scripts: `python3 {baseDir}/scripts/generate.py`

### MEDIA: Output Signaling
Scripts that produce images print a special line for OpenClaw to auto-attach:
```python
print(f"MEDIA:{output_path}")
```
OpenClaw detects this and attaches the image in the chat response.

### References Pattern
For complex skills, separate domain docs into `references/`:
```
references/
├── api.md          ← Full API reference
├── providers.md    ← Provider config details  
└── examples.md     ← Usage examples
```
SKILL.md body stays lean (<500 lines), links to references files for details.
Agent reads reference files on-demand when needed.

### Env Var Injection
OpenClaw injects env vars from skill config into the subprocess. Scripts should:
1. Check env var first
2. Accept `--api-key` flag as override
3. Fail with clear message if neither provided

---

## 4. PaperBanana Python API Reference

### Import Surface
```python
from paperbanana import PaperBananaPipeline, GenerationInput, DiagramType
from paperbanana.core.config import Settings
from paperbanana.core.resume import load_resume_state
```

### Settings Object
```python
settings = Settings(
    # Provider selection
    vlm_provider="openai",         # "openai" | "gemini" | "openrouter"
    vlm_model="gpt-5.2",           # model name for VLM tasks
    image_provider="openai_imagen",# "openai_imagen" | "google_imagen" | "openrouter_imagen"
    image_model="gpt-image-1.5",   # model name for image generation
    
    # Pipeline behavior
    optimize_inputs=True,          # Phase 0: context enricher + caption sharpener
    auto_refine=True,              # loop until critic satisfied (up to max_iterations)
    max_iterations=30,             # safety cap for auto_refine
    refinement_iterations=3,       # default fixed rounds if not auto_refine
    
    # Output
    output_dir="outputs",          # base output directory
    output_format="png",           # "png" | "jpeg" | "webp"
    save_iterations=True,          # save intermediate renders
    save_metadata=True,            # save metadata JSON
)
```

### GenerationInput Object
```python
input = GenerationInput(
    source_context="Our framework consists of...",  # methodology text
    communicative_intent="Overview of the proposed method.",  # caption/goal
    diagram_type=DiagramType.METHODOLOGY,  # DiagramType.METHODOLOGY | DiagramType.PLOT
)
```

### DiagramType Enum
```python
DiagramType.METHODOLOGY   # Architecture/method diagrams (Gemini image gen)
DiagramType.PLOT          # Statistical plots (Matplotlib code)
```

### PaperBananaPipeline Methods
```python
pipeline = PaperBananaPipeline(settings=settings)

# Generate new diagram (async)
result = await pipeline.generate(generation_input)

# Or run synchronously
result = asyncio.run(pipeline.generate(generation_input))

# Continue a previous run
state = load_resume_state("outputs", "run_20260218_125448_e7b876")
result = await pipeline.continue_run(
    resume_state=state,
    additional_iterations=3,
    user_feedback="Make arrows thicker",
)
```

### Result Object
```python
result.image_path        # str: path to final_output.png
result.run_id            # str: "run_20260218_125448_e7b876"
result.output_dir        # str: "outputs/run_20260218_125448_e7b876"
result.iterations        # int: number of refinement rounds completed
```

### Output Directory Structure
```
outputs/
└── run_<YYYYMMDD_HHMMSS_<uuid6>/
    ├── final_output.png         ← the deliverable
    ├── iteration_1.png          ← if save_iterations=True
    ├── iteration_2.png
    ├── iteration_3.png
    └── metadata.json            ← if save_metadata=True (prompt, settings, timings)
```

### CLI Commands (for shell script path)
```bash
# Diagram generation
paperbanana generate \
    --input method.txt \
    --caption "Overview of framework" \
    --output diagram.png \
    --iterations 3 \
    --vlm-provider openai \
    --image-provider openai_imagen \
    --optimize --auto

# Statistical plots
paperbanana plot \
    --data results.csv \
    --intent "Bar chart comparing accuracy"

# Quality evaluation
paperbanana evaluate \
    --generated diagram.png \
    --reference human.png \
    --context method.txt \
    --caption "Overview"

# Continue run with feedback
paperbanana generate --continue \
    --feedback "Make colors more distinct"
```

### Multi-Agent Pipeline Summary
- **Phase 0 (optional):** Input Optimizer (Context Enricher + Caption Sharpener) in parallel
- **Phase 1:** Retriever → Planner → Stylist (linear)
- **Phase 2:** Visualizer → Critic (3 iterations by default, or `--auto` until satisfied)
- **Total agents:** Up to 7

---

## 5. Provider Configuration

### Supported Providers

| Component | Provider Key | Model Default | Env Var |
|-----------|-------------|---------------|---------|
| VLM | `openai` | `gpt-5.2` | `OPENAI_API_KEY` |
| Image Gen | `openai_imagen` | `gpt-image-1.5` | `OPENAI_API_KEY` |
| VLM | `gemini` | `gemini-2.0-flash` | `GOOGLE_API_KEY` |
| Image Gen | `google_imagen` | `gemini-3-pro-image-preview` | `GOOGLE_API_KEY` |
| VLM/Image | `openrouter` | any | `OPENROUTER_API_KEY` (inferred) |

### Environment Variables
```bash
# OpenAI (default)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1   # Azure: https://<resource>.openai.azure.com/openai/v1
OPENAI_VLM_MODEL=gpt-5.2        # optional model override
OPENAI_IMAGE_MODEL=gpt-image-1.5

# Google Gemini (free tier, good for testing)
GOOGLE_API_KEY=AIza...

# Azure OpenAI / Foundry (auto-detected via OPENAI_BASE_URL)
# No extra vars needed — just set OPENAI_BASE_URL to Azure endpoint
```

### Config YAML (configs/config.yaml pattern)
```yaml
vlm:
  provider: openai    # openai | gemini | openrouter
  model: gpt-5.2

image:
  provider: openai_imagen   # openai_imagen | google_imagen | openrouter_imagen
  model: gpt-image-1.5

pipeline:
  num_retrieval_examples: 10
  refinement_iterations: 3
  # auto_refine: true
  # max_iterations: 30
  # optimize_inputs: true
  output_resolution: "2k"

reference:
  path: data/reference_sets

output:
  dir: outputs
  save_iterations: true
  save_metadata: true
```

### API Key Recommendations for OpenClaw Skill
- **Primary:** `OPENAI_API_KEY` (best quality, gpt-5.2 + gpt-image-1.5)
- **Free alternative:** `GOOGLE_API_KEY` (gemini-2.0-flash + gemini-3-pro-image-preview)
- The skill should accept **either** and auto-detect which provider to use
- OpenClaw's `primaryEnv` should default to `OPENAI_API_KEY` with a note about Gemini fallback

---

## 6. Recommended Stack Decisions

### Installation Strategy
**Use `uv run` with inline PEP 723 deps** in scripts — this is the native OpenClaw pattern (see `nano-banana-pro`). Avoids global pip installs, fully isolated, self-documenting.

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["paperbanana[openai]>=0.1.2"]
# ///
```

For Google-only (free tier), use `paperbanana[google]>=0.1.2`.
For both: `paperbanana[all-providers]>=0.1.2`.

### Provider Strategy
- **Default to OpenAI** (higher quality, user likely already has key)
- **Env-detect fallback**: if `OPENAI_API_KEY` absent but `GOOGLE_API_KEY` present, use Gemini
- Expose `--provider` flag: `auto` (detect) | `openai` | `gemini`

### Skill Structure
```
paperbanana/
├── SKILL.md
├── scripts/
│   ├── generate.py      ← Main generation script (uv + inline deps)
│   ├── plot.py          ← Statistical plot generation
│   └── evaluate.py      ← Diagram quality evaluation
└── references/
    ├── api.md           ← Python API and CLI reference (this doc condensed)
    └── providers.md     ← Provider config guide
```

### API Keys (OpenClaw `requires.env`)
```yaml
requires:
  bins: ["uv"]
  env: ["OPENAI_API_KEY"]   # or GOOGLE_API_KEY — handle in script
primaryEnv: "OPENAI_API_KEY"
```

Actually, since the skill supports multiple keys, document both in SKILL.md but only require ONE:
```yaml
requires:
  bins: ["uv"]
  # Don't list env here — script will error helpfully if neither key is set
```

### Output Handling
- Print `MEDIA:{result.image_path}` for OpenClaw auto-attach
- Output to a workspace-relative path (e.g., `~/Projects/tmp/paperbanana-<timestamp>/`)
- Print human-readable summary of: diagram type, iterations, provider used, output path

### Trigger Description (SKILL.md `description`)
The description should match when the agent sees:
- "generate a diagram for my paper"
- "create a methodology figure"
- "illustrate this framework"
- "make a figure for my research"
- "plot these results"
- "visualize my method"

### Auto-Trigger Consideration
Since OpenClaw uses the `description` field to match user intent, write the description to cover:
- Academic paper illustration
- Methodology diagrams
- Architecture figures  
- Research visualization
- Statistical plots from data

### Async Handling
PaperBanana's Python API is **async** (`pipeline.generate()` is a coroutine). The wrapper script should use `asyncio.run()`. This works fine in a subprocess context.

### `[mcp]` Extra
Skip MCP integration in the OpenClaw skill — OpenClaw uses its own skill invocation system, not MCP. The MCP server is for Claude Code / Cursor IDE integration separately.

---

## Notes / Gotchas

1. **`google-genai>=1.65` is a CORE dep** — even if you only use `openai` provider, Gemini SDK gets installed. This is by design (it's in core, not just the `[google]` extra).

2. **`google-genai` version is high** — `>=1.65` is a very recent pinned version. Make sure `uv` resolves a compatible version. If conflicts occur, try `pip install paperbanana[openai]` first to check resolution.

3. **Data bundled in wheel** — The 13 reference diagrams and NeurIPS guidelines are shipped inside the wheel. No separate data download needed. `platformdirs` likely handles the cache location.

4. **Output dir default is `outputs/` relative to CWD** — override via `--output` flag or `Settings(output_dir=...)` to control where files land. For OpenClaw, use a predictable path like `/tmp/paperbanana-<timestamp>/`.

5. **No streaming/progress events** — the pipeline runs synchronously from the caller's perspective (no callbacks). Use `rich` console output for progress (already a dependency).

6. **`paperbanana setup` wizard** is interactive — not suitable for automated use. Skip it; configure via env vars directly.
