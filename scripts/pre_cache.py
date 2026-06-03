"""
pre_cache.py — Pre-warm the Gemini response cache for offline/interview use.

Usage
-----
    # Cache every file in a folder (both modes):
    python scripts/pre_cache.py path/to/demo/reports/

    # Cache a single file:
    python scripts/pre_cache.py path/to/report.pdf

    # Cache with a specific mode only (simple | doctor):
    python scripts/pre_cache.py path/to/reports/ --mode simple

Run this at home with internet BEFORE the interview.
At the interview, start the backend normally — the same files will be
served instantly from disk without any Gemini API call.

Supported file types: PDF, JPG, JPEG, PNG, WEBP
"""

from __future__ import annotations

import argparse
import asyncio
import mimetypes
import sys
from pathlib import Path

# Allow running from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}

MIME_MAP = {
    ".pdf":  "application/pdf",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
}


async def cache_file(filepath: Path, mode: str) -> bool:
    """Analyse one file and persist the result. Returns True on success."""
    from src.serving.ai_interpreter import interpret_document, sha256_hex, _cache_get

    mime = MIME_MAP.get(filepath.suffix.lower(), "application/octet-stream")
    file_bytes = filepath.read_bytes()
    cache_key = f"{sha256_hex(file_bytes)}:{mode}"

    # Already cached — skip Gemini call
    if _cache_get(cache_key) is not None:
        print(f"  [SKIP]  {filepath.name}  ({mode}) - already in cache")
        return True

    print(f"  [CALL]  {filepath.name}  ({mode}) - calling Gemini...", end=" ", flush=True)
    try:
        await interpret_document(file_bytes, mime, filepath.name, mode)  # type: ignore[arg-type]
        print("OK cached")
        return True
    except Exception as exc:
        print(f"FAILED: {exc}")
        return False


async def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-warm Gemini response cache.")
    parser.add_argument("path", help="File or folder of medical reports to cache.")
    parser.add_argument(
        "--mode",
        choices=["simple", "doctor", "both"],
        default="both",
        help="Which explanation mode(s) to cache (default: both).",
    )
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"ERROR: path not found: {target}")
        sys.exit(1)

    # Collect files
    if target.is_file():
        files = [target]
    else:
        files = [f for f in sorted(target.rglob("*")) if f.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not files:
        print("No supported files found (PDF/JPG/PNG/WEBP).")
        sys.exit(0)

    modes = ["simple", "doctor"] if args.mode == "both" else [args.mode]

    print(f"\nPre-caching {len(files)} file(s) × {len(modes)} mode(s) = {len(files)*len(modes)} total calls\n")

    ok = fail = skip = 0
    for f in files:
        for m in modes:
            result = await cache_file(f, m)
            if result:
                ok += 1
            else:
                fail += 1

    from src.serving.ai_interpreter import _DISK_CACHE_PATH
    print(f"\n{'-'*50}")
    print(f"Done.  OK:{ok} cached   FAILED:{fail}")
    print(f"Cache saved to: {_DISK_CACHE_PATH.resolve()}")
    print("\nYou can now run the backend offline — these files will be served")
    print("instantly from disk without any internet connection.\n")


if __name__ == "__main__":
    asyncio.run(main())
