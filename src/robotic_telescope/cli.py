"""Offline planning and scripted simulation; never opens an instrument."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .pointing import load_request
from .workflow import export_demo, export_plan, export_simulation


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline telescope planning and ideal mount simulation; no device control."
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["demo", "plan", "simulate"]:
        command = sub.add_parser(name)
        command.add_argument("--output", type=Path, required=True)
        if name == "plan":
            command.add_argument("--request", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            export_demo(args.output)
        elif args.command == "simulate":
            export_simulation(args.output)
        else:
            request, payload = load_request(args.request)
            export_plan(args.output, request, payload)
        print(f"Offline report: {args.output / 'index.html'}")
        print("No hardware command or physical telescope observation performed.")
        return 0
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
