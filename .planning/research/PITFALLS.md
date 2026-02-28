# PITFALLS Research — OpenClaw PaperBanana Skill

*Researched: 2026-02-28*
*Sources: OpenClaw docs (/openclaw/docs/), PaperBanana README (llmsresearch/paperbanana), OpenClaw sandboxing/skills/exec docs, first-principles reasoning*

---

## 1. Installation Pitfalls

### 1.1 Sandbox Network Disabled by Default (CRITICAL)

**Problem:** OpenClaw sandbox containers default to `docker.network: "none"` — no network egress. `pip install paperbanana` will silently hang or fail with network unreachable errors. This is one of the most common sandbox "it doesn't work" issues.

**Exact config key to fix:**
```json5
agents: {
  defaults: {
    sandbox: {
      docker: {
        network: "bridge",         // or "host" if inside a VM
        setupCommand: "pip install paperbanana"
      }
    }
  }
}
```

**Prevention:** The skill's SKILL.md must document this config requirement explicitly and check for it in the setup script. The setup script should test connectivity before attempting install.

---

### 1.2 Read-Only Root Filesystem

**Problem:** `readOnlyRoot: true` (the sandbox default in some configurations) prevents pip from writing to `/usr/local/lib/python*/site-packages`. You'll get `Read-only file system` errors.

**Prevention:** Setup script should test write access to site-packages. The skill SKILL.md should document setting `readOnlyRoot: false` or using a user-level install (`pip install --user`). User installs write to `~/.local/lib/...` which is NOT read-only even with `readOnlyRoot: true`.

**Mitigation:** `pip install --user paperbanana` + ensure `~/.local/bin` is on PATH.

---

### 1.3 Non-Root User Can't Install to System Python

**Problem:** Sandbox containers may run as a non-root user (configured via `agents.defaults.sandbox.docker.user`). Global pip installs require root. Silent failure or permission errors.

**OpenClaw docs say:** "user must be root for package installs (omit `user` or set `user: '0:0'`)"

**Prevention:** Always use `pip install --user` (works without root) OR use virtual environments scoped to the sandbox workspace.

---

### 1.4 setupCommand Only Runs Once — Not Guaranteed Per-Session

**Problem:** `setupCommand` runs once after container creation. With `scope: "session"`, a NEW container is created each session — so `setupCommand` reruns every session, which is slow (~30-60s for pip install). With `scope: "shared"`, it runs once ever, but the shared container may be recycled or rebuilt.

**Impact:** Users face 30-60 second cold starts every time in `scope: "session"` mode.

**Prevention:**
- Use `scope: "shared"` or `scope: "agent"` for the paperbanana skill
- Or bake a custom sandbox image with paperbanana pre-installed
- Or cache pip wheels in a bind-mounted volume

---

### 1.5 Dependency Conflicts with pydantic v2

**Problem:** PaperBanana requires `pydantic v2` (advertised via its badges). If the sandbox or host already has other packages installed that pin `pydantic < 2` (LangChain pre-0.1, FastAPI old versions, etc.), pip will either fail to resolve or silently downgrade PaperBanana's requirements.

**Known conflict pattern:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages 
that are installed. langchain X.X requires pydantic<2...
```

**Prevention:** Use a dedicated virtual environment (`python -m venv .pb-env`) inside the sandbox workspace. Never pollute the system site-packages with PaperBanana if other skills also use Python.

---

### 1.6 Python Version Mismatch

**Problem:** PaperBanana requires Python 3.10+. The default OpenClaw sandbox image (`openclaw-sandbox:bookworm-slim`) uses Debian Bookworm which ships Python 3.11 — fine. But if:
- The sandbox base image is older (Buster/Bullseye with Python 3.9)
- The host Python used is 3.8 or 3.9 in non-sandboxed mode
- `python` vs `python3` shebang issues on some systems

**Prevention:** Setup script should explicitly check `python3 --version` and fail fast with a clear error if < 3.10. Always invoke as `python3` not `python`.

---

### 1.7 pydantic-core Compilation Failure

**Problem:** On unusual CPU architectures (ARM, RISC-V) or older glibc, pydantic-core has no pre-built wheel and must compile from source — requiring a Rust toolchain. Docker containers frequently lack Rust.

**Error pattern:**
```
ERROR: Failed building wheel for pydantic-core
note: cargo not found; install with rustup
```

**Prevention:** Pin to a pydantic-core version with known good wheels. Consider `--only-binary :all:` flag if Rust isn't available, or pre-install `rustup` in the setupCommand.

---

### 1.8 No Persistence of Outputs Across Sessions (scope: "session")

**Problem:** With `scope: "session"` (default), the sandbox container is created fresh each session. Any outputs in `/data/workspace` inside the container are lost unless `workspaceAccess: "rw"` mounts the actual workspace.

**Impact:** User asks for a diagram, gets it, but can't access it in a later session.

**Prevention:** Always use `workspaceAccess: "rw"` for PaperBanana so outputs are written to the real workspace, not the ephemeral container filesystem.

---

### 1.9 `paperbanana` Binary Not on PATH After Install

**Problem:** When pip installs into `--user`, the binary goes to `~/.local/bin`. If `~/.local/bin` is not on the sandbox container's PATH, `paperbanana` command fails with `command not found` even though it's installed.

**Prevention:** Use `python3 -m paperbanana` as the invocation pattern (bypasses PATH issues). Always test this in setup script.

---

## 2. API/Provider Pitfalls

### 2.1 Cutting-Edge Model Availability (gpt-5.2, gpt-image-1.5)

**Problem:** PaperBanana defaults to `gpt-5.2` and `gpt-image-1.5` — models that as of early 2026 are new/preview. Not all OpenAI API tiers have access to these. A user with a basic OpenAI account will get:
```
Error: model not found: gpt-5.2
```
Or: pricing/access tier errors for gpt-image-1.5.

**Prevention:** Default to Gemini free tier (gemini-2.0-flash + gemini-3-pro-image-preview) in the skill config. Only fall back to OpenAI if explicitly requested. Document OpenAI model tier requirements.

---

### 2.2 Gemini Free Tier Rate Limits

**Problem:** Gemini free tier has strict rate limits:
- gemini-2.0-flash: ~15 RPM (requests per minute)
- gemini-3-pro-image-preview (Imagen 3): very low quotas on free tier

PaperBanana's pipeline makes **up to 7 LLM calls** per generation (2 optimize + 1 retrieve + 1 plan + 1 style + N×2 visualize/critique). With `--auto` and `--iterations 10+`, you can easily hit rate limits mid-pipeline, causing the whole generation to fail with a partially-complete result.

**Prevention:**
- Default `--iterations 3` (not more) for the skill
- Don't expose `--auto` by default (max 30 iterations is extremely risky on free tier)
- Add retry-with-backoff in wrapper scripts for rate limit errors (HTTP 429)
- Warn users when Gemini free tier is detected

---

### 2.3 Long Generation Time (Timeouts)

**Problem:** A full PaperBanana generation with `--optimize --iterations 3` can take 3-8 minutes:
- Input optimization: ~30s (2 parallel VLM calls)
- Planning phase: ~60-90s (3 sequential VLM calls)
- Refinement (3×): ~90-180s per iteration (generate + critique)
- Total: up to 5-10 minutes

OpenClaw's exec tool has a 1800s (30 min) timeout, which is fine. But the user experience requires the agent to inform them of expected wait time and ideally send progress updates.

**Prevention:**
- Use `background: true` with exec and send progress messages
- Emit intermediate status updates (Phase 1 done, generating iteration 1/3...)
- Set `--verbose` flag and parse progress output

---

### 2.4 gemini-3-pro-image-preview Is a Preview Model

**Problem:** Preview models get deprecated without much notice. If `gemini-3-pro-image-preview` is renamed/removed, all Gemini image generation breaks silently.

**Prevention:** Abstract provider/model selection in a config file. Make it easy to swap models without changing skill scripts.

---

### 2.5 OpenAI Image API Returns URL That Expires

**Problem:** When using OpenAI image generation, the API may return a temporary URL (expires in 1 hour) rather than base64 data. If the script doesn't immediately save the image to disk, it becomes unavailable.

**Prevention:** Always save the image bytes to disk immediately in the wrapper script, not just store the URL.

---

### 2.6 Azure OpenAI Auto-Detection via OPENAI_BASE_URL

**Problem:** PaperBanana auto-detects Azure if `OPENAI_BASE_URL` is set. If the user's OpenClaw environment already has `OPENAI_BASE_URL` set for a different purpose (custom proxy, LiteLLM, etc.), PaperBanana will silently route requests to the wrong endpoint.

**Prevention:** Document that the skill checks for `OPENAI_BASE_URL`. Let users explicitly configure the PaperBanana provider rather than relying on env var auto-detection if there's any ambiguity.

---

### 2.7 API Key Environment Not Available Inside Sandbox (CRITICAL)

**Problem:** This is a **critical OpenClaw-specific pitfall.** OpenClaw's `skills.entries.<key>.env` and `skills.entries.<key>.apiKey` inject environment variables into the **host process**, NOT into sandbox containers. If sandboxing is enabled, the Python scripts running inside the container will NOT see `OPENAI_API_KEY` or `GEMINI_API_KEY` unless explicitly passed via `agents.defaults.sandbox.docker.env`.

**From OpenClaw docs:** *"Sandbox exec does not inherit host process.env. Use agents.defaults.sandbox.docker.env (or a custom image) for skill API keys."*

**Prevention:**
- The skill's setup documentation MUST explain this
- The setup script should detect sandboxed execution and warn
- Alternative: write API keys to a config file in the workspace that scripts read (works in both sandboxed and non-sandboxed environments)

---

## 3. OpenClaw Integration Pitfalls

### 3.1 Gating Chicken-and-Egg: `requires.bins: ["paperbanana"]`

**Problem:** If the skill uses `requires.bins: ["paperbanana"]` to gate loading, OpenClaw won't load the skill until `paperbanana` is on PATH. But the skill IS the thing that's supposed to install it. The skill can never load to trigger its own install.

**Prevention:**
- Gate on `python3` (which should already exist) NOT on `paperbanana`
- Use a lazy install check in scripts: if `paperbanana` not found, install it
- Or: don't gate on the binary, gate on the API key env var (`requires.env: ["GEMINI_API_KEY"]`)

---

### 3.2 Session Snapshot — Skill Changes Don't Apply Mid-Session

**Problem:** OpenClaw snapshots eligible skills when a session starts. If a user configures the API key during the session (e.g., in response to the setup script asking for it), the skill state doesn't refresh until the next session. The `env` injection also doesn't update mid-session.

**Prevention:** Document that users need to start a new session after initial setup. The setup script should end with "Setup complete! Start a new chat session to use PaperBanana."

---

### 3.3 `env` Injection Only Injects When Not Already Set

**Problem:** From OpenClaw docs: *"env: injected only if the variable isn't already set in the process."* If `OPENAI_API_KEY` is already set in the host environment (e.g., from `.bashrc` or another skill), the skill's injected value is ignored. This means an old/different key could be used.

**Prevention:** Document this behavior. The setup script should check if the variable is already set and warn the user if the configured skill key won't be used.

---

### 3.4 Non-Main Sessions Are Sandboxed (Discord/Group Channels)

**Problem:** With OpenClaw's default `mode: "non-main"` sandbox setting, Discord channel sessions are sandboxed (they're "non-main"). The API key injection issue from §2.7 will hit EVERY Discord user by default.

**Impact:** User in #research channel asks for a diagram. Skill runs. Python script in sandbox has no API keys. Silent failure or cryptic error.

**Prevention:** Either:
1. Configure the API keys in `sandbox.docker.env` explicitly
2. Write keys to a config file in the workspace (accessible via `workspaceAccess: "rw"`)
3. Document the requirement clearly in SKILL.md

---

### 3.5 `workspaceAccess: "none"` — Output Files Inaccessible

**Problem:** With `workspaceAccess: "none"` (the default), the sandbox container writes files to `~/.openclaw/sandboxes/<session-id>/...`. The host's workspace does NOT contain the generated image. When the agent tries to deliver the file to the chat, it looks for a path that doesn't exist outside the container.

**Prevention:** Require `workspaceAccess: "rw"` and have all scripts write to `/workspace/...` inside the container. This maps to the real workspace directory on the host.

---

### 3.6 Skill Description Token Cost in System Prompt

**Problem:** Each eligible skill costs ~24 tokens per skill in the system prompt. PaperBanana's description + instructions may be verbose. If combined with many other skills, this can bloat context.

**Prevention:** Keep the skill `description` field short (one sentence). Move detailed instructions to a referenced file (`{baseDir}/USAGE.md`) that the agent reads lazily.

---

## 4. Auto-Trigger Pitfalls

### 4.1 Keyword False Positives (HIGH RISK)

**Problem:** The proposed trigger keywords — "diagram", "figure", "plot", "chart", "graph", "visualize" — are extremely common in everyday conversation:
- "Here's a chart that explains it" → looking at an existing chart, not requesting generation
- "That's off the charts!" → idiom
- "Can you plot this route?" → navigation context
- "My progress graph looks good" → describing existing content
- "Figure out what's wrong" → the word "figure" meaning "determine"
- "In Figure 3 of this paper..." → referencing, not requesting

Each false positive trigger fires a **multi-minute, multi-API-call pipeline** that costs real money (or rate limit quota).

**Prevention:**
- Require **explicit intent**: "generate a diagram", "make a figure", "create a plot" — not just keywords
- Use compositional triggers: keyword + academic context (working on paper, LaTeX file present) OR keyword + explicit generation verb
- Add a confirmation step: "I can generate a diagram for this. Should I proceed?" rather than auto-executing

---

### 4.2 Over-Triggering in Heartbeats

**Problem:** The PROJECT.md mentions proactive heartbeat triggering: "During heartbeats, if academic work is in progress, suggest figure generation." A heartbeat fires multiple times per day. If Bennett is writing a paper, EVERY heartbeat could suggest/trigger diagram generation. This would:
- Spam the user with suggestions
- Potentially auto-generate diagrams without consent
- Burn API quota/rate limits

**Prevention:** 
- Never auto-generate during heartbeats — only suggest (with a cooldown of at least 24h between suggestions)
- Track last-suggested timestamp in workspace state file
- Heartbeat role should be **suggestion only**, never execution

---

### 4.3 Group Chat Collateral Triggering

**Problem:** In Discord group chats, OTHER users might mention keywords like "diagram" or "figure" in unrelated contexts. The skill shouldn't trigger for other users' conversations unless PaperBanana is explicitly requested.

**Prevention:**
- In group/channel contexts, only trigger on direct mentions or explicit requests directed at the assistant
- Check if the requesting user is the authorized user (Bennett) before auto-executing expensive operations

---

### 4.4 Context Mismatches — Analyzing vs. Generating

**Problem:** User shares an image of a diagram and says "analyze this diagram" — the word "diagram" is present, but the intent is analysis, not generation. Auto-trigger fires the generation pipeline inappropriately.

**Prevention:** Auto-trigger should check for presence of images (inbound media) and treat those as analysis context, not generation triggers.

---

### 4.5 Re-Trigger on Refine Requests

**Problem:** User says "make the arrows thicker on that diagram" — this is a refine/continue request for an EXISTING diagram. If the trigger keywords fire the generation pipeline instead of the refine pipeline, a completely new diagram is generated from scratch, losing the previous work.

**Prevention:** Check for continuation keywords ("that diagram", "the figure you made", "the last one") and route to `paperbanana generate --continue` instead of a fresh generation.

---

### 4.6 Trigger Firing During Skill Self-Description

**Problem:** When a user asks "what can you do?" or the agent describes its capabilities, it might say "I can generate diagrams and figures..." — these description words could cause a recursive trigger.

**Prevention:** This is mitigated by context — the agent won't trigger itself. But be careful in documentation and system prompts about keyword placement.

---

## 5. Output Delivery Pitfalls

### 5.1 Platform File Size Limits

| Platform | File Size Limit | Notes |
|----------|-----------------|-------|
| Discord | 8 MB (free), 25 MB (Nitro) | Bot uploads same as free: 8 MB |
| Telegram | 20 MB via Bot API | Files >20 MB need workaround |
| WhatsApp | ~16 MB (media), varies | Images may be downscaled |
| Slack | 1 GB | Rarely a problem |
| iMessage/BlueBubbles | Varies by carrier | MMS limits can be low (1-5 MB) |

**PaperBanana output:** A PNG of a publication-quality diagram can easily be 2-15 MB. Discord's 8 MB limit is the binding constraint for most users.

**Prevention:**
- After generation, check file size and auto-convert to JPEG if >6 MB
- Add `--format jpeg` option in the wrapper scripts
- For Discord: hard limit at 7.5 MB with auto-compression to JPEG if exceeded

---

### 5.2 WhatsApp Image Compression Destroys Diagram Quality

**Problem:** WhatsApp re-encodes all images as JPEG with aggressive compression. A carefully rendered academic diagram with fine text, arrows, and color coding will become unreadable after WhatsApp's compression pipeline.

**Prevention:**
- For WhatsApp delivery, offer to send as a document/file instead of an image (bypasses compression)
- Or generate at higher resolution so compressed version is still legible
- Warn user when delivering to WhatsApp channels

---

### 5.3 Output Path Not Accessible Outside Sandbox

**Problem:** PaperBanana saves outputs to `outputs/run_<timestamp>/final_output.png` — relative to the working directory of the process. In a sandbox, this is inside the container, at a path like `/home/user/outputs/...`. If the agent tries to deliver this file using the `message` tool with `filePath:`, it points to a path that doesn't exist on the host.

**Prevention:**
- Always use `workspaceAccess: "rw"` (maps `/workspace` to real workspace on host)
- Have all scripts write to `/workspace/skills/paperbanana/outputs/...` inside the container
- The `message` tool's `media` parameter accepts local file paths that must exist on the gateway host, not inside the container

---

### 5.4 PaperBanana Generates Multiple Intermediate Files

**Problem:** Each generation run creates:
- A timestamped directory `outputs/run_<timestamp>/`
- Multiple PNG files (one per iteration)
- Metadata JSON files
- With `--optimize`, additional text files

Over time, with multiple generation runs, this creates significant disk usage. In a shared sandbox, multiple users could fill up disk space.

**Prevention:**
- Clean up intermediate files after delivery
- Only deliver the final output file
- Add disk space check before generation
- Implement a cleanup routine in the skill

---

### 5.5 `message` Tool Media Delivery — data: URLs Not Supported

**Problem:** OpenClaw's `message` tool does NOT accept `data:` URLs for the `media` parameter. From the tool schema: *"data: URLs are not supported here, use buffer"*. If scripts try to deliver images as `data:image/png;base64,...`, it will fail.

**Prevention:**
- Always save the image to a file first, then use `filePath` OR `media` (local path)
- For base64 delivery, use the `buffer` parameter (base64 without `data:` prefix)
- Test delivery method for each target channel in the skill test suite

---

### 5.6 Sandboxed File Path Not Reachable by Gateway

**Problem:** Even if `workspaceAccess: "rw"` maps `/workspace` inside the container to the real workspace directory, the agent calling the `message` tool is on the HOST — it needs to reference the HOST path, not the container's `/workspace/...` path.

**Prevention:** Scripts should output the HOST path of the generated file. The wrapper script should know the workspace root (via environment variable or config) and translate the container path to the host path before reporting back to the agent.

---

### 5.7 Slow Delivery Blocking Chat Response

**Problem:** Large images (5-15 MB) uploaded via Discord API or other channels can take significant time. During this upload, the user sees no activity indicator. If the upload fails (network issue, rate limit), the user gets no result after waiting 5+ minutes.

**Prevention:**
- Send a "Generating your diagram..." message immediately when starting
- Send progress updates at key pipeline stages
- On upload failure, save the file to workspace and report the path to the user
- Implement retry logic for file upload

---

## 6. Prevention Strategies Summary

### Installation
| Pitfall | Prevention |
|---------|-----------|
| No network in sandbox | Document `docker.network: "bridge"` as required. Test before install. |
| Read-only root | Use `pip install --user` + ensure `~/.local/bin` on PATH. Or use venv. |
| Non-root user | Always use `pip install --user` in scripts. |
| Slow cold-start | Use `scope: "agent"` or pre-bake custom image. |
| Pydantic conflicts | Use dedicated venv. |
| Python version | Check `python3 --version` ≥ 3.10 at setup time. Fail fast. |
| Rust missing | Test on ARM; document pydantic-core compilation requirement. |
| Lost outputs | Always use `workspaceAccess: "rw"`. |
| Binary not on PATH | Use `python3 -m paperbanana` invocation. |

### API/Provider
| Pitfall | Prevention |
|---------|-----------|
| gpt-5.2 unavailable | Default to Gemini free tier. |
| Rate limits | Retry-with-backoff. Cap iterations at 3 by default. No `--auto` by default. |
| Long generation time | Background exec + progress updates. |
| Deprecated preview models | Config-driven model selection. Easy to update. |
| URL expiry | Save bytes immediately, not URLs. |
| OPENAI_BASE_URL collision | Explicit provider config, don't rely on env auto-detection. |
| Keys not in sandbox | Use `sandbox.docker.env` OR config file in workspace. |

### OpenClaw Integration
| Pitfall | Prevention |
|---------|-----------|
| Gating chicken-and-egg | Gate on `python3`, not `paperbanana`. Lazy install in scripts. |
| Session snapshot | Tell user to start new session after setup. |
| Env injection precedence | Document and check for pre-existing env vars. |
| Non-main session sandboxing | Use workspace config file approach for API keys. |
| WorkspaceAccess default | Require `workspaceAccess: "rw"` — document as prerequisite. |
| Token bloat | Short description, lazy-load detailed instructions. |

### Auto-Trigger
| Pitfall | Prevention |
|---------|-----------|
| Keyword false positives | Require explicit generation intent verb. Confirmation before execution. |
| Heartbeat over-triggering | Heartbeat = suggestions only with 24h cooldown. Never auto-execute. |
| Group chat collateral | Only trigger on direct requests in group contexts. |
| Context mismatches | Check for inbound images before triggering generation. |
| Re-trigger on refine | Detect continuation language → route to `--continue`. |

### Output Delivery
| Pitfall | Prevention |
|---------|-----------|
| Discord 8 MB limit | Auto-convert to JPEG if >6 MB. |
| WhatsApp compression | Offer document send instead of image. |
| Path not on host | Write to `/workspace/...` in container. Report host path to agent. |
| Intermediate file bloat | Clean up after delivery. Only keep final output. |
| `data:` URL in message | Use `filePath` or `buffer` parameter. |
| Container vs host path | Translate container path to host path in wrapper script. |
| Upload failure | Implement retry + fallback to path reporting. |

---

## Key Risk Matrix

| Risk | Severity | Likelihood | Priority |
|------|----------|------------|----------|
| API keys not injected into sandbox | HIGH | HIGH (Discord = non-main = sandboxed) | 🔴 P0 |
| No network in sandbox → pip fails | HIGH | MEDIUM (depends on config) | 🔴 P0 |
| Auto-trigger false positives | MEDIUM | HIGH (common vocabulary) | 🟠 P1 |
| Rate limit mid-pipeline | MEDIUM | MEDIUM (free tier) | 🟠 P1 |
| Output files inaccessible | HIGH | MEDIUM (depends on workspaceAccess) | 🟠 P1 |
| Discord 8 MB file limit | MEDIUM | MEDIUM (diagrams can be large) | 🟡 P2 |
| WhatsApp compression | MEDIUM | LOW (less common usage) | 🟡 P2 |
| Cold-start installation time | LOW | HIGH (session scope default) | 🟡 P2 |
| pydantic dependency conflict | LOW | LOW (dedicated venv mitigates) | 🟢 P3 |

---

*End of PITFALLS research.*
