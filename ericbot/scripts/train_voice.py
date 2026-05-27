#!/usr/bin/env python3
"""
EricBot Voice Trainer — feed samples to teach EricBot how you talk.

Usage:
  Interactive:  python scripts/train_voice.py --interactive
  Single text:  python scripts/train_voice.py --category email --text "Hey man, so here's the deal..."
  From file:    python scripts/train_voice.py --category email --file my_emails.txt
  From dir:     python scripts/train_voice.py --category text --dir ./texts/
  Profile:      python scripts/train_voice.py --profile
"""

import argparse
import sys
import os
import re
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

API_BASE = os.getenv("ERICBOT_API", "http://localhost:8000")
VALID_CATEGORIES = ["email", "phone", "text", "social", "sales"]


def ingest(category: str, content: str) -> dict:
    resp = httpx.post(
        f"{API_BASE}/api/voice/ingest",
        json={"category": category, "content": content},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_profile() -> dict:
    resp = httpx.get(f"{API_BASE}/api/voice/profile", timeout=10)
    resp.raise_for_status()
    return resp.json()


def print_profile(profile: dict):
    print("\n=== Voice Profile ===")
    print(f"Total samples: {profile['sample_count']}")
    print(f"Confidence:    {profile['confidence'] * 100:.0f}%")
    print(f"Categories:    {profile['categories']}")
    print("\nStyle Summary:")
    print(profile["style_summary"])
    print("=" * 40)


def interactive_mode():
    print("\n🎤 EricBot Voice Trainer — Interactive Mode")
    print("Train the bot by feeding it real samples of how you communicate.\n")

    while True:
        print(f"Category options: {', '.join(VALID_CATEGORIES)}")
        category = input("Category (or 'quit'): ").strip().lower()
        if category in ("quit", "q", "exit"):
            break
        if category not in VALID_CATEGORIES:
            print(f"  Invalid. Choose from: {', '.join(VALID_CATEGORIES)}")
            continue

        print("Paste your sample (end with a line containing only '---'):")
        lines = []
        while True:
            line = input()
            if line.strip() == "---":
                break
            lines.append(line)

        content = "\n".join(lines).strip()
        if not content:
            print("  Empty sample, skipping.")
            continue

        result = ingest(category, content)
        print(f"  ✓ Ingested. Total samples: {result['total_samples']}\n")

    profile = get_profile()
    print_profile(profile)


def from_file(category: str, filepath: str):
    text = Path(filepath).read_text(encoding="utf-8")
    # Split on --- delimiter for multi-sample files
    samples = [s.strip() for s in re.split(r"\n---\n", text) if s.strip()]
    print(f"Found {len(samples)} sample(s) in {filepath}")
    for i, sample in enumerate(samples, 1):
        result = ingest(category, sample)
        print(f"  [{i}/{len(samples)}] ingested — total: {result['total_samples']}")


def from_dir(category: str, dirpath: str):
    files = list(Path(dirpath).glob("*.txt"))
    print(f"Found {len(files)} .txt file(s) in {dirpath}")
    for f in files:
        print(f"  Processing {f.name}...")
        from_file(category, str(f))


def main():
    parser = argparse.ArgumentParser(description="EricBot Voice Trainer")
    parser.add_argument("--interactive", action="store_true", help="Interactive input mode")
    parser.add_argument("--profile", action="store_true", help="Show current voice profile")
    parser.add_argument("--category", choices=VALID_CATEGORIES, help="Sample category")
    parser.add_argument("--text", help="Single sample text")
    parser.add_argument("--file", help="File path (--- delimited for multiple samples)")
    parser.add_argument("--dir", help="Directory of .txt files")

    args = parser.parse_args()

    if args.profile:
        profile = get_profile()
        print_profile(profile)
        return

    if args.interactive:
        interactive_mode()
        return

    if not args.category:
        parser.error("--category is required unless using --interactive or --profile")

    if args.text:
        result = ingest(args.category, args.text)
        print(f"✓ Ingested. Total samples: {result['total_samples']}")
    elif args.file:
        from_file(args.category, args.file)
    elif args.dir:
        from_dir(args.category, args.dir)
    else:
        parser.error("Provide --text, --file, or --dir")


if __name__ == "__main__":
    main()
