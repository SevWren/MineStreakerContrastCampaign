"""Argument parsing for the standalone visual solver demo."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the Iter9 visual solver demo.")
    parser.add_argument("--grid", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--event-trace", default=None)
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)

