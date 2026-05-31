from __future__ import annotations

import argparse
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local Meroq FastAPI backend.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind, default 127.0.0.1.")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind, default 8000.")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload for development.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.reload:
        cmd.append("--reload")
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
