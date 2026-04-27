"""
launch_app.py — Launch the Anatom AI Streamlit dashboard.

Usage
-----
    python scripts/launch_app.py [--port 8501] [--browser]
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch Anatom AI dashboard.")
    parser.add_argument("--port", type=int, default=8501, help="Streamlit port (default 8501).")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically.")
    args = parser.parse_args()

    app_path = ROOT / "src" / "ui" / "app.py"
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(app_path),
        "--server.port", str(args.port),
        "--server.headless", "true" if args.no_browser else "false",
        "--theme.base", "dark",
        "--theme.primaryColor", "#4FC3F7",
        "--theme.backgroundColor", "#0f0f19",
        "--theme.secondaryBackgroundColor", "#1a1a2e",
        "--theme.textColor", "#e0e0e0",
    ]
    print(f"Launching Anatom AI at http://localhost:{args.port}")
    subprocess.run(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    main()
