# PaperBanana Skill — Architecture Research

**Researched:** 2026-02-28
**Sources:** /openclaw/skills/ (nano-banana-pro, openai-image-gen, skill-creator, model-usage, sag), /openclaw/docs/tools/skills.md, /openclaw/docs/tools/skills-config.md, /openclaw/docs/tools/creating-skills.md, llmsresearch/paperbanana GitHub README

---

## Skill Directory Structure

OpenClaw uses the AgentSkills spec. Standard layout:

```
skills/paperbanana/
├── SKILL.md                   # Required — frontmatter + instructions
├── scripts/
│   ├── generate.py            # Main generation wrapper (diagram + plot)
│   ├── evaluate.py            # Diagram evaluation script
│   └── setup.py               # Install + configure paperbanana
└── references/
    ├── providers.md           # Provider table, env vars, model options
    └── cli-flags.md           # Full CLI flag reference (loaded on demand)
```

No `assets/` directory needed — PaperBanana generates outputs at runtime.

**Why this structure:**
- `generate.py` is the hot path; called for every generation request
- `evaluate.py` is optional/separate — different workflow, different flags
- `setup.py` is run once manually; no need to inline it in the main flow
- References are split so the agent only loads what it needs (progressive disclosure)

**SKILL.md frontmatter shape:**

```yaml
---
name: paperbanana
description: >
  Generate publication-quality academic diagrams, methodology figures, and
  statistical plots using the PaperBanana multi-agent pipeline. Supports
  OpenAI, Gemini, and Azure OpenAI providers. Use when: user asks to generate
  a research diagram, methodology figure, architecture figure, or statistical
  plot from a text description. Also use for evaluating diagram quality against
  a reference image.
metadata: {
  "openclaw": {
    "emoji": "🍌",
    "requires": { "bins": ["python3"], "env": ["OPENAI_API_KEY", "GOOGLE_API_KEY"] },
    "primaryEnv": "OPENAI_API_KEY"
  }
}
---
```

**Gating notes:**
- `requires.env` is OR-gated — skill loads if *any* listed var is present.
  Use `"anyEnv"` if that's supported, otherwise list primary. The skill
  should handle graceful fallback at runtime even if one key is absent.
- `requires.bins: ["python3"]` — always available on this Linux host.
- For `uv`-based execution (isolated deps, like nano-banana-pro), add `"uv"` to bins
  and use `uv run {baseDir}/scripts/generate.py`. This is the preferred pattern
  for Python scripts with heavy dependencies (avoids polluting system Python).

---

## Data Flow (Trigger → Execution → Delivery)

```
User message
    │
    ▼
Agent reads SKILL.md (already in context when session starts)
    │
    ▼
Agent matches request → selects paperbanana skill
    │
    ▼
Agent calls exec tool:
    uv run {baseDir}/scripts/generate.py --context "..." --caption "..."
    │
    ▼
Script runs → calls paperbanana CLI or Python API
    │
    ├── stdout: progress + "MEDIA: /path/to/output.png"
    └── stderr: errors
    │
    ▼
OpenClaw runtime parses stdout for MEDIA: tokens
    │
    ▼
OpenClaw attaches file to chat delivery
    │
    ▼
User receives image in Discord / WhatsApp / etc.
```

**Key points:**
- Scripts are **synchronous** from OpenClaw's perspective — exec blocks until
  the script exits. PaperBanana is async internally but scripts expose a sync
  entry point using `asyncio.run()`.
- The `MEDIA:` token is the **standard OpenClaw mechanism** for file delivery.
  nano-banana-pro, sag, and others all use this pattern. OpenClaw parses it from
  stdout and attaches the file on supported chat providers (Discord, WhatsApp, etc.).
- Session env vars from `skills.entries.paperbanana.env` or `.apiKey` are injected
  **before** the agent turn starts and available in the exec subprocess via process.env.
- Output from exec (stdout+stderr) is returned to the agent as tool output — the
  agent reads it, reports the image was saved, and OpenClaw handles attachment.

---

## Script Architecture

### `scripts/generate.py`

Thin wrapper around the `paperbanana` CLI. Handles:
1. Argument parsing (mirroring CLI flags the agent will pass)
2. Provider/key detection (env → default selection)
3. Calling `paperbanana generate` or `paperbanana plot` as subprocess
4. Capturing output path from paperbanana's stdout
5. Printing `MEDIA: <path>` for OpenClaw delivery

**Async handling:** PaperBanana is async at the Python API level, but its CLI
is a sync entry point. Two valid patterns:

**Pattern A — Shell out to CLI (recommended for simplicity):**
```python
import subprocess, sys, os, re

result = subprocess.run(
    ["paperbanana", "generate", "--input", input_file, "--caption", caption, ...],
    capture_output=True, text=True
)
print(result.stdout)
# Parse output path from paperbanana's stdout or use --output flag
# Then print MEDIA: line
```

**Pattern B — asyncio.run() wrapping Python API:**
```python
import asyncio
from paperbanana import PaperBananaPipeline, GenerationInput
from paperbanana.core.config import Settings

async def main():
    pipeline = PaperBananaPipeline(settings=settings)
    result = await pipeline.generate(GenerationInput(...))
    return result.image_path

path = asyncio.run(main())
print(f"MEDIA: {path}")
```

Pattern A is preferred because:
- Simpler — no need to mirror the Python API surface
- CLI is already the documented interface
- paperbanana CLI handles all error cases with proper exit codes
- Pattern B requires knowing the full Python API surface

**With uv (dependency isolation, like nano-banana-pro):**
```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["paperbanana[openai,google]>=0.1.0"]
# ///
```
This PEP 723 inline metadata lets `uv run generate.py` auto-install deps into an
isolated venv. No manual pip install needed at runtime. Requires `uv` on PATH.

### `scripts/setup.py`

Standalone setup/install script. Idempotent.

```
setup.py flow:
1. Check if paperbanana is importable → if not, pip install it
2. Detect env vars: OPENAI_API_KEY, GOOGLE_API_KEY
3. If neither found, prompt user for keys or show instructions
4. Optionally write .env to outputs/ dir or skill dir
5. Run `paperbanana setup` wizard if keys need interactive config
6. Print status summary
```

### `scripts/evaluate.py`

Thin wrapper for `paperbanana evaluate`. Accepts:
- `--generated` path
- `--reference` path  
- `--context` text file path
- `--caption` string

Prints scores to stdout for agent to relay to user.

---

## Output Management (Images, Metadata, Delivery)

### Storage Strategy

PaperBanana writes to `outputs/run_<timestamp>/` by default. For the skill:

- Pass `--output /tmp/paperbanana-<timestamp>/final_output.png` to control output path
- `/tmp/` is always writable, survives the exec call, cleaned by OS on reboot
- Alternatively accept paperbanana's default `outputs/` dir (relative to CWD)

**Recommended:** Use `--output /tmp/pb-$(date +%s)/diagram.png` so paths are
predictable and ephemeral. The MEDIA: line gives OpenClaw the absolute path.

### The MEDIA: Protocol

```python
# At the end of generate.py, after confirming file exists:
full_path = Path(output_path).resolve()
print(f"Image saved: {full_path}")
print(f"MEDIA: {full_path}")  # OpenClaw attaches this file
```

**Rules (from nano-banana-pro SKILL.md):**
- Print `MEDIA: <absolute_path>` to stdout
- **Do not read the image back** — don't pass it to the agent as base64
- Report the saved path to the user only
- OpenClaw handles platform-specific delivery (Discord attachment, WhatsApp media, etc.)

### Intermediate Artifacts

PaperBanana saves intermediate iterations by default (`save_iterations: true`).
The skill should either:
- Disable with `--no-save-iterations` flag (if available) to reduce clutter
- Or only emit `MEDIA:` for the final output

### Multi-Output Runs

If the user asks for multiple diagrams:
- Run in sequence, emit multiple `MEDIA:` lines
- OpenClaw will attach all files in a single message on Discord

---

## Setup/Install Flow

### First-Time Setup (user runs once)

```bash
python3 {baseDir}/scripts/setup.py
```

Script behavior:
1. **Detect Python** — check `python3 --version` (>=3.10 required)
2. **Detect uv** — if available, prefer uv for isolated installs
3. **Check existing install** — `python3 -c "import paperbanana"` 
4. **Install if needed** — `pip install "paperbanana[openai,google]"` or `uv pip install ...`
5. **Key detection** — check `OPENAI_API_KEY`, `GOOGLE_API_KEY` in env
6. **Config guidance** — print instructions for `~/.openclaw/openclaw.json` if keys missing:
   ```
   Add to ~/.openclaw/openclaw.json:
     skills.entries.paperbanana.env.OPENAI_API_KEY = "sk-..."
   ```
7. **Verification** — run `paperbanana --version` to confirm

### Runtime Dependency Loading (uv inline metadata preferred)

If using uv + PEP 723 inline deps in generate.py, no explicit setup needed —
`uv run generate.py` installs deps on first run into a cached isolated venv.
This is the nano-banana-pro pattern and is strongly preferred.

### Key Injection via OpenClaw Config

Users configure keys in `~/.openclaw/openclaw.json`:
```json5
{
  skills: {
    entries: {
      "paperbanana": {
        enabled: true,
        apiKey: "sk-...",  // → OPENAI_API_KEY (primaryEnv)
        env: {
          OPENAI_API_KEY: "sk-...",
          GOOGLE_API_KEY: "AI...",  // optional fallback
        }
      }
    }
  }
}
```
Keys are injected into the agent run's process.env before exec calls. Scripts
access them via `os.environ`.

---

## Provider Selection Architecture

### Priority Chain

```
1. OPENAI_API_KEY present → openai VLM (gpt-5.2) + openai_imagen (gpt-image-1.5)
2. GOOGLE_API_KEY present → gemini VLM (gemini-2.0-flash) + gemini image (gemini-3-pro-image-preview)
3. OPENAI_BASE_URL set    → Azure OpenAI / Foundry mode (auto-detected by paperbanana)
4. Neither → error with instructions
```

### Implementation in generate.py

```python
def detect_provider():
    if os.environ.get("OPENAI_API_KEY"):
        return {
            "vlm_provider": "openai",
            "vlm_model": "gpt-5.2",
            "image_provider": "openai_imagen",
            "image_model": "gpt-image-1.5",
        }
    elif os.environ.get("GOOGLE_API_KEY"):
        return {
            "vlm_provider": "gemini",
            "vlm_model": "gemini-2.0-flash",
            "image_provider": "google_imagen",
            "image_model": "gemini-3-pro-image-preview",
        }
    else:
        print("ERROR: No API key found.", file=sys.stderr)
        print("Set OPENAI_API_KEY or GOOGLE_API_KEY", file=sys.stderr)
        sys.exit(1)
```

### User Override

Agent should accept `--provider openai|gemini` flag and pass to script,
which overrides auto-detection. Document in SKILL.md.

### SKILL.md Gating Consideration

The `requires.env` field in OpenClaw gating is AND-gated by default.
To allow the skill to load with *either* key:
- List only `OPENAI_API_KEY` as `primaryEnv` (the most common case)
- Gate with a single env var, handle missing provider gracefully at runtime
- Or don't use `requires.env` at all — load always, fail gracefully at execution

---

## Component Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│  SKILL.md                                                   │
│  • Trigger recognition (description + body)                 │
│  • User-facing command examples                             │
│  • Routes agent to correct script + flags                   │
│  • References: providers.md, cli-flags.md (on demand)       │
└──────────────────────┬──────────────────────────────────────┘
                       │ exec tool call
         ┌─────────────┼────────────┐
         ▼             ▼            ▼
   generate.py    evaluate.py   setup.py
   • detect       • call         • pip install
     provider       paperbanana  • key detect
   • build CLI      evaluate     • config help
     invocation   • print        • verify
   • run CLI        scores
   • print
     MEDIA:
         │
         ▼
   paperbanana CLI  ←── OPENAI_API_KEY / GOOGLE_API_KEY
   (external pkg)
         │
         ▼
   outputs/run_*/final_output.png
         │
         ▼
   MEDIA: /tmp/pb-*/diagram.png
         │
         ▼ (OpenClaw parses stdout)
   Discord / WhatsApp attachment
```

**Responsibilities:**

| Component | Owns | Does NOT own |
|-----------|------|-------------|
| SKILL.md | Trigger logic, instruction prose, flag docs | Business logic |
| generate.py | Provider detection, CLI invocation, MEDIA output | UI/UX |
| setup.py | Install, key detection, config writing | Generation |
| references/providers.md | Provider + model reference table | Runtime selection |
| paperbanana (pip pkg) | All AI pipeline logic | OpenClaw delivery |

**Key architectural invariants:**
1. Scripts must be runnable standalone (no OpenClaw-specific imports)
2. All output paths must be absolute before printing MEDIA:
3. API keys come from env vars only (never hardcoded, never as CLI args)
4. Scripts exit non-zero on failure — exec tool surfaces this to the agent
5. Heavy deps (paperbanana itself) managed by uv inline metadata or explicit setup.py
