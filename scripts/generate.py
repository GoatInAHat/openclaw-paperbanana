#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["paperbanana[all-providers]>=0.1.2"]
# ///
"""
PaperBanana diagram generator for OpenClaw.
Wraps the paperbanana Python API to generate publication-quality academic diagrams.
Outputs MEDIA: lines for OpenClaw auto-attachment.
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path


def detect_provider(explicit: str | None = None) -> dict:
    """Auto-detect provider from env vars, or use explicit override."""
    if explicit == "openai" or (explicit is None and os.environ.get("OPENAI_API_KEY")):
        if not os.environ.get("OPENAI_API_KEY"):
            print("ERROR: --provider openai requires OPENAI_API_KEY", file=sys.stderr)
            sys.exit(1)
        return {
            "vlm_provider": "openai",
            "vlm_model": os.environ.get("OPENAI_VLM_MODEL", "gpt-5.2"),
            "image_provider": "openai_imagen",
            "image_model": os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1.5"),
        }
    elif explicit == "gemini" or (explicit is None and os.environ.get("GOOGLE_API_KEY")):
        if not os.environ.get("GOOGLE_API_KEY"):
            print("ERROR: --provider gemini requires GOOGLE_API_KEY", file=sys.stderr)
            sys.exit(1)
        return {
            "vlm_provider": "gemini",
            "vlm_model": os.environ.get("GEMINI_VLM_MODEL", "gemini-2.0-flash"),
            "image_provider": "google_imagen",
            "image_model": os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview"),
        }
    else:
        print("ERROR: No API key found.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Set one of these in ~/.openclaw/openclaw.json → skills.entries.paperbanana.env:", file=sys.stderr)
        print("  OPENAI_API_KEY=sk-...   (paid, best quality)", file=sys.stderr)
        print("  GOOGLE_API_KEY=AIza...  (free, good quality)", file=sys.stderr)
        sys.exit(1)


async def generate_diagram(args, provider_config: dict) -> str:
    """Run the PaperBanana pipeline and return the output image path."""
    from paperbanana import PaperBananaPipeline, GenerationInput, DiagramType
    from paperbanana.core.config import Settings

    # Build output directory
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"/tmp/paperbanana-{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        vlm_provider=provider_config["vlm_provider"],
        vlm_model=provider_config["vlm_model"],
        image_provider=provider_config["image_provider"],
        image_model=provider_config["image_model"],
        optimize_inputs=not args.no_optimize,
        auto_refine=args.auto_refine,
        refinement_iterations=args.iterations,
        output_dir=str(output_dir),
        output_format=args.format,
        save_iterations=True,
        save_metadata=True,
    )

    pipeline = PaperBananaPipeline(settings=settings)

    # Get source context
    if args.input:
        context = Path(args.input).read_text()
    elif args.context:
        context = args.context
    else:
        print("ERROR: Provide --input (file path) or --context (text string)", file=sys.stderr)
        sys.exit(1)

    gen_input = GenerationInput(
        source_context=context,
        communicative_intent=args.caption,
        diagram_type=DiagramType.METHODOLOGY,
    )

    # Add aspect ratio if specified
    if args.aspect:
        gen_input.aspect_ratio = args.aspect

    print(f"🍌 Generating diagram with {provider_config['vlm_provider']}...")
    print(f"   VLM: {provider_config['vlm_model']}")
    print(f"   Image: {provider_config['image_model']}")
    print(f"   Optimize: {not args.no_optimize}")
    print(f"   Iterations: {'auto' if args.auto_refine else args.iterations}")
    print()

    result = await pipeline.generate(gen_input)
    return result.image_path


async def continue_run(args, provider_config: dict) -> str:
    """Continue a previous PaperBanana run with feedback."""
    from paperbanana import PaperBananaPipeline
    from paperbanana.core.config import Settings
    from paperbanana.core.resume import load_resume_state

    settings = Settings(
        vlm_provider=provider_config["vlm_provider"],
        vlm_model=provider_config["vlm_model"],
        image_provider=provider_config["image_provider"],
        image_model=provider_config["image_model"],
        save_iterations=True,
        save_metadata=True,
    )

    pipeline = PaperBananaPipeline(settings=settings)

    # Find the run to continue
    if args.continue_run:
        run_id = args.continue_run
    else:
        # Find latest run in /tmp/paperbanana-*
        import glob
        runs = sorted(glob.glob("/tmp/paperbanana-*/run_*"))
        if not runs:
            print("ERROR: No previous runs found to continue.", file=sys.stderr)
            print("Generate a diagram first, then use --continue.", file=sys.stderr)
            sys.exit(1)
        run_dir = runs[-1]
        run_id = Path(run_dir).name

    # Find the outputs directory containing this run
    parent_dir = None
    import glob
    for d in sorted(glob.glob("/tmp/paperbanana-*"), reverse=True):
        if (Path(d) / run_id).exists() or any(Path(d).iterdir()):
            parent_dir = d
            break

    if not parent_dir:
        print(f"ERROR: Could not find run '{run_id}'", file=sys.stderr)
        sys.exit(1)

    print(f"🍌 Continuing run: {run_id}")
    print(f"   Feedback: {args.feedback}")
    print()

    state = load_resume_state(parent_dir, run_id)
    result = await pipeline.continue_run(
        resume_state=state,
        additional_iterations=args.iterations,
        user_feedback=args.feedback or "",
    )
    return result.image_path


def main():
    parser = argparse.ArgumentParser(description="PaperBanana diagram generator")

    # Input options
    parser.add_argument("--input", "-i", help="Path to methodology text file")
    parser.add_argument("--context", "-c", help="Methodology text (inline string)")
    parser.add_argument("--caption", help="Figure caption / communicative intent")

    # Generation options
    parser.add_argument("--iterations", "-n", type=int, default=3, help="Refinement rounds (default: 3)")
    parser.add_argument("--auto-refine", action="store_true", help="Loop until critic is satisfied")
    parser.add_argument("--aspect", help="Aspect ratio: 1:1, 2:3, 3:2, 3:4, 4:3, 9:16, 16:9, 21:9")
    parser.add_argument("--no-optimize", action="store_true", help="Disable input optimization")
    parser.add_argument("--format", "-f", default="png", choices=["png", "jpeg", "webp"], help="Output format")

    # Provider options
    parser.add_argument("--provider", choices=["openai", "gemini"], help="Override auto-detected provider")

    # Continuation options
    parser.add_argument("--continue", dest="do_continue", action="store_true", help="Continue latest run")
    parser.add_argument("--continue-run", help="Continue specific run by ID")
    parser.add_argument("--feedback", help="User feedback for refinement")

    args = parser.parse_args()

    # Detect provider
    provider_config = detect_provider(args.provider)

    # Route to generation or continuation
    if args.do_continue or args.continue_run:
        if not args.feedback:
            print("WARNING: No --feedback provided. Continuing with additional iterations only.", file=sys.stderr)
        image_path = asyncio.run(continue_run(args, provider_config))
    else:
        if not args.caption:
            print("ERROR: --caption is required for new diagram generation.", file=sys.stderr)
            sys.exit(1)
        if not args.input and not args.context:
            print("ERROR: Provide --input (file) or --context (text) for diagram generation.", file=sys.stderr)
            sys.exit(1)
        image_path = asyncio.run(generate_diagram(args, provider_config))

    # Deliver result
    resolved = str(Path(image_path).resolve())
    print()
    print(f"✅ Diagram saved: {resolved}")
    print(f"MEDIA:{resolved}")


if __name__ == "__main__":
    main()
