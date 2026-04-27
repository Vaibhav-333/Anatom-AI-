"""
serve.py — Launch the Anatom AI FastAPI server.

Usage
-----
    python scripts/serve.py [--host 0.0.0.0] [--port 8000] [--reload]

Interactive API docs available at:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Load .env from project root if present (never required — env vars also work)
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch Anatom AI REST API server.")
    parser.add_argument("--host",   default="0.0.0.0",   help="Bind host (default 0.0.0.0).")
    parser.add_argument("--port",   type=int, default=8000, help="Port (default 8000).")
    parser.add_argument("--reload", action="store_true",  help="Enable hot-reload (dev mode).")
    args = parser.parse_args()

    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.serving.api:app",
        "--host", args.host,
        "--port", str(args.port),
    ]
    if args.reload:
        cmd.append("--reload")

    print(f"Anatom AI API starting at http://{args.host}:{args.port}")
    print(f"Swagger UI: http://localhost:{args.port}/docs")
    subprocess.run(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    main()
