---
name: paperbanana
description: >
  Generate publication-quality academic diagrams, methodology figures, architecture
  illustrations, and statistical plots from text descriptions using the PaperBanana
  multi-agent AI pipeline. Also evaluate diagram quality against reference images.
  Use when: (1) user asks to generate, create, or make a research diagram, methodology
  figure, system architecture illustration, pipeline diagram, or framework figure,
  (2) user asks to create a statistical plot, bar chart, or data visualization from
  CSV/JSON data, (3) user asks to evaluate or score a generated diagram against a
  reference, (4) user asks to refine or improve a previously generated diagram.
  NOT for: analyzing existing images, general image generation (non-academic),
  or chart/graph discussions without explicit generation intent.
metadata: {"openclaw":{"emoji":"🍌","requires":{"bins":["uv"]}}}
---

# PaperBanana — Academic Illustration Generator

Generate publication-quality academic diagrams and statistical plots from text
descriptions. Uses a multi-agent pipeline (Retriever → Planner → Stylist →
Visualizer → Critic) with iterative refinement.

## Quick Reference

### Generate a Diagram

```bash
uv run {baseDir}/scripts/generate.py \
  --context "Our framework consists of an encoder module that processes..." \
  --caption "Overview of the proposed encoder-decoder architecture"
```

Or from a file:
```bash
uv run {baseDir}/scripts/generate.py \
  --input /path/to/method_section.txt \
  --caption "Overview of the proposed method"
```

Options:
- `--iterations N` — refinement rounds (default: 3)
- `--auto-refine` — loop until critic is satisfied (use for final quality)
- `--aspect RATIO` — aspect ratio: `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `9:16`, `16:9`, `21:9`
- `--provider gemini|openrouter` — override auto-detected provider
- `--format png|jpeg|webp` — output format (default: png)
- `--no-optimize` — disable input optimization (on by default)

### Generate a Plot

```bash
uv run {baseDir}/scripts/plot.py \
  --data '{"model":["GPT-4","Claude","Gemini"],"accuracy":[92.1,94.3,91.8]}' \
  --intent "Bar chart comparing model accuracy across benchmarks"
```

Or from a CSV file:
```bash
uv run {baseDir}/scripts/plot.py \
  --data-file /path/to/results.csv \
  --intent "Line plot showing training loss over epochs"
```

### Evaluate a Diagram

```bash
uv run {baseDir}/scripts/evaluate.py \
  --generated /path/to/generated.png \
  --reference /path/to/human_drawn.png \
  --context "The methodology section text..." \
  --caption "Overview of the framework"
```

Returns scores on: Faithfulness, Readability, Conciseness, Aesthetics.

### Refine a Previous Diagram

```bash
uv run {baseDir}/scripts/generate.py \
  --continue \
  --feedback "Make the arrows thicker and use more distinct colors"
```

Or continue a specific run:
```bash
uv run {baseDir}/scripts/generate.py \
  --continue-run run_20260228_143022_a1b2c3 \
  --feedback "Add labels to each component box"
```

## Setup

The skill auto-installs `paperbanana` on first use via `uv` (isolated, no global install).

**API keys:** Configure at least one in `~/.openclaw/openclaw.json`:

```json5
{
  skills: {
    entries: {
      "paperbanana": {
        env: {
          // Option A: Google Gemini (free tier — recommended)
          GOOGLE_API_KEY: "AIza...",

          // Option B: OpenRouter (paid, access to any model)
          // OPENROUTER_API_KEY: "sk-or-...",
        }
      }
    }
  }
}
```

If both keys are set, Gemini is preferred (free). OpenRouter gives access to any model.

## Provider Details

For provider comparison, model options, and advanced configuration:
see `{baseDir}/references/providers.md`

## Behavior Notes

- **Input optimization is ON by default** — enriches context and sharpens captions before generation. Disable with `--no-optimize` for speed.
- **Generation takes 1-5 minutes** depending on iterations and provider. The script prints progress.
- **Output is delivered automatically** via the MEDIA: protocol — no manual file handling needed.
- **Run continuation** is the natural way to iterate: "make it better" → `--continue --feedback "..."`.
- **Gemini free tier** has rate limits (~15 RPM). Keep iterations ≤ 3 on free tier.
