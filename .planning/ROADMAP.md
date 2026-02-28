# ROADMAP.md — OpenClaw PaperBanana Skill

## Phase 1: Skill Foundation
**Goal:** SKILL.md with proper frontmatter, triggers, instructions, and reference docs. Skill loads and is visible in OpenClaw.

**Requirements:** SKILL-01, SKILL-02, SKILL-03, SKILL-04, SETUP-01, SETUP-03, SETUP-04

**Success Criteria:**
1. SKILL.md exists with correct frontmatter (name, description, metadata.openclaw)
2. Skill appears in OpenClaw's available_skills when `uv` is on PATH
3. references/providers.md exists with provider table and config examples
4. Description triggers only on explicit generation intent, not bare keywords

## Phase 2: Diagram Generation
**Goal:** Core generation script that produces methodology diagrams from text + caption and delivers via MEDIA: protocol.

**Requirements:** GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, SETUP-02

**Success Criteria:**
1. `uv run scripts/generate.py --context "..." --caption "..."` produces a PNG
2. Provider auto-detected from env vars (OpenAI or Gemini)
3. Output optimization enabled by default
4. MEDIA: line printed to stdout with absolute path
5. Aspect ratio selectable via --aspect flag

## Phase 3: Plot & Evaluation
**Goal:** Statistical plot generation and diagram quality evaluation scripts.

**Requirements:** PLOT-01, PLOT-02, EVAL-01, EVAL-02

**Success Criteria:**
1. `uv run scripts/plot.py --data "..." --intent "..."` produces a plot PNG
2. `uv run scripts/evaluate.py --generated X --reference Y --context Z --caption W` returns scores
3. Both scripts use MEDIA: protocol for output delivery
4. Error handling with clear messages for missing keys/data

## Phase 4: Run Continuation
**Goal:** Refine previous generations with user feedback, supporting iterative improvement via chat.

**Requirements:** CONT-01, CONT-02

**Success Criteria:**
1. `uv run scripts/generate.py --continue --feedback "..."` continues last run
2. `uv run scripts/generate.py --continue-run <id> --feedback "..."` continues specific run
3. SKILL.md documents the continuation workflow for the agent
