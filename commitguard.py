#!/usr/bin/env python3
"""CommitGuard - Git Pre-commit Hook CLI Entrypoint.

Prevents leakage of PII, Thai National IDs, and high-entropy secrets
before developer commits code into git.
"""

from __future__ import annotations

import argparse
import sys

# Ensure UTF-8 output encoding across all operating systems and codepages
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.cli import install_hook, run, uninstall_hook


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="commitguard",
        description="CommitGuard - DevSecOps Git Pre-commit Secret & PII Shield",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python commitguard.py --install    Install pre-commit hook into .git/hooks/
  python commitguard.py --scan       Scan currently staged changes immediately
  python commitguard.py --uninstall  Remove CommitGuard hook from .git/hooks/
  python commitguard.py              Run standard hook check (invoked by git)
""",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--install",
        action="store_true",
        help="Install CommitGuard as a Git pre-commit hook in .git/hooks/pre-commit",
    )
    group.add_argument(
        "--scan",
        action="store_true",
        help="Perform an immediate scan of staged changes without committing",
    )
    group.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove CommitGuard pre-commit hook from .git/hooks/pre-commit",
    )

    return parser


def main() -> None:
    """CLI dispatcher."""
    parser = create_parser()
    args = parser.parse_args()

    if args.install:
        sys.exit(install_hook())
    elif args.uninstall:
        sys.exit(uninstall_hook())
    elif args.scan:
        sys.exit(run())
    else:
        # Default behavior: standard pre-commit hook execution
        sys.exit(run())


if __name__ == "__main__":
    main()
