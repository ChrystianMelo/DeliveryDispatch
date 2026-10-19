"""Development commands shared by local scripts and CI."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = {
    "setup": [["pip", "install", "-e", ".[dev]"]],
    "check": [["ruff", "check", "."], ["ruff", "format", "--check", "."]],
    "test": [["pytest", "-v", "tests"]],
    "build": [["build"]],
    "run": [["delivery_dispatch.main"]],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=COMMANDS)
    parser.add_argument("task_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.task != "run" and args.task_args:
        parser.error("argumentos adicionais são aceitos somente pela tarefa run")

    for command in COMMANDS[args.task]:
        result = subprocess.run(
            [sys.executable, "-m", *command, *args.task_args],
            cwd=ROOT,
            check=False,
        )
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
