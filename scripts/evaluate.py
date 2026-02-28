#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["paperbanana[all-providers]>=0.1.2"]
# ///
"""
PaperBanana diagram evaluator for OpenClaw.
Compares a generated diagram against a human reference using VLM-as-Judge.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path


def detect_provider(explicit: str | None = None) -> dict:
    """Auto-detect provider from env vars."""
    if explicit == "gemini" or (explicit is None and os.environ.get("GOOGLE_API_KEY")):
        return {
            "vlm_provider": "gemini",
            "vlm_model": os.environ.get("GEMINI_VLM_MODEL", "gemini-2.0-flash"),
        }
    elif explicit == "openrouter" or (explicit is None and os.environ.get("OPENROUTER_API_KEY")):
        return {
            "vlm_provider": "openrouter",
            "vlm_model": os.environ.get("OPENROUTER_VLM_MODEL", "google/gemini-2.0-flash-001"),
        }
    else:
        print("ERROR: No API key found for evaluation.", file=sys.stderr)
        print("Set GOOGLE_API_KEY or OPENROUTER_API_KEY", file=sys.stderr)
        sys.exit(1)


async def evaluate_diagram(args, provider_config: dict) -> str:
    """Evaluate a generated diagram against a reference."""
    from paperbanana.evaluation.judge import VLMJudge

    # Validate paths
    gen_path = Path(args.generated)
    ref_path = Path(args.reference)

    if not gen_path.exists():
        print(f"ERROR: Generated image not found: {gen_path}", file=sys.stderr)
        sys.exit(1)
    if not ref_path.exists():
        print(f"ERROR: Reference image not found: {ref_path}", file=sys.stderr)
        sys.exit(1)

    # Get context
    if args.context_file:
        context = Path(args.context_file).read_text()
    elif args.context:
        context = args.context
    else:
        print("ERROR: Provide --context (text) or --context-file (path)", file=sys.stderr)
        sys.exit(1)

    print(f"🍌 Evaluating diagram with {provider_config['vlm_provider']}...")
    print(f"   Generated: {gen_path}")
    print(f"   Reference: {ref_path}")
    print()

    judge = VLMJudge(
        provider=provider_config["vlm_provider"],
        model=provider_config["vlm_model"],
    )

    scores = await judge.evaluate(
        generated_path=str(gen_path),
        reference_path=str(ref_path),
        context=context,
        caption=args.caption,
    )

    return scores


def main():
    parser = argparse.ArgumentParser(description="PaperBanana diagram evaluator")

    parser.add_argument("--generated", "-g", required=True, help="Path to generated image")
    parser.add_argument("--reference", "-r", required=True, help="Path to human reference image")
    parser.add_argument("--context", help="Source methodology text (inline)")
    parser.add_argument("--context-file", help="Path to source context text file")
    parser.add_argument("--caption", "-c", required=True, help="Figure caption")
    parser.add_argument("--provider", choices=["gemini", "openrouter"])

    args = parser.parse_args()

    provider_config = detect_provider(args.provider)
    scores = asyncio.run(evaluate_diagram(args, provider_config))

    print()
    print("📊 Evaluation Results:")
    print(scores)


if __name__ == "__main__":
    main()
