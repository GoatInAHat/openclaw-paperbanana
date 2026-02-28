#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["paperbanana[all-providers]>=0.1.2"]
# ///
"""
PaperBanana statistical plot generator for OpenClaw.
Generates publication-quality plots from CSV/JSON data.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path


def detect_provider(explicit: str | None = None) -> dict:
    """Auto-detect provider from env vars."""
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
        print("Set OPENAI_API_KEY or GOOGLE_API_KEY in skills.entries.paperbanana.env", file=sys.stderr)
        sys.exit(1)


async def generate_plot(args, provider_config: dict) -> str:
    """Generate a statistical plot from data."""
    from paperbanana import PaperBananaPipeline, GenerationInput, DiagramType
    from paperbanana.core.config import Settings

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"/tmp/paperbanana-plot-{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        vlm_provider=provider_config["vlm_provider"],
        vlm_model=provider_config["vlm_model"],
        image_provider=provider_config["image_provider"],
        image_model=provider_config["image_model"],
        optimize_inputs=not args.no_optimize,
        refinement_iterations=args.iterations,
        output_dir=str(output_dir),
        output_format=args.format,
        save_metadata=True,
    )

    pipeline = PaperBananaPipeline(settings=settings)

    # Load data
    if args.data_file:
        data_path = Path(args.data_file)
        if data_path.suffix == ".csv":
            import pandas as pd
            df = pd.read_csv(data_path)
            data_json = df.to_json()
        else:
            data_json = data_path.read_text()
    elif args.data:
        data_json = args.data
    else:
        print("ERROR: Provide --data (JSON string) or --data-file (CSV/JSON path)", file=sys.stderr)
        sys.exit(1)

    # Validate JSON
    try:
        json.loads(data_json)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON data: {e}", file=sys.stderr)
        sys.exit(1)

    gen_input = GenerationInput(
        source_context=data_json,
        communicative_intent=args.intent,
        diagram_type=DiagramType.PLOT,
        raw_data=data_json,
    )

    if args.aspect:
        gen_input.aspect_ratio = args.aspect

    print(f"🍌 Generating plot with {provider_config['vlm_provider']}...")
    print(f"   Intent: {args.intent}")
    print(f"   Iterations: {args.iterations}")
    print()

    result = await pipeline.generate(gen_input)
    return result.image_path


def main():
    parser = argparse.ArgumentParser(description="PaperBanana plot generator")

    parser.add_argument("--data", "-d", help="JSON data string")
    parser.add_argument("--data-file", help="Path to CSV or JSON data file")
    parser.add_argument("--intent", required=True, help="Description of desired plot")

    parser.add_argument("--iterations", "-n", type=int, default=3, help="Refinement rounds")
    parser.add_argument("--aspect", help="Aspect ratio")
    parser.add_argument("--no-optimize", action="store_true", help="Disable input optimization")
    parser.add_argument("--format", "-f", default="png", choices=["png", "jpeg", "webp"])
    parser.add_argument("--provider", choices=["openai", "gemini"])

    args = parser.parse_args()

    if not args.data and not args.data_file:
        print("ERROR: Provide --data or --data-file", file=sys.stderr)
        sys.exit(1)

    provider_config = detect_provider(args.provider)
    image_path = asyncio.run(generate_plot(args, provider_config))

    resolved = str(Path(image_path).resolve())
    print()
    print(f"✅ Plot saved: {resolved}")
    print(f"MEDIA:{resolved}")


if __name__ == "__main__":
    main()
