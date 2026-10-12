"""CommitGuard - Command-line Interface and Direct Terminal I/O module."""

from __future__ import annotations

import os
import sys
from typing import List

from src.scanner import Finding, scan_staged_changes

# Enable ANSI colors on Windows consoles
if os.name == "nt":
    os.system("")

# ANSI Color Codes
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_DIM = "\033[2m"
COLOR_RED = "\033[1;31m"
COLOR_GREEN = "\033[1;32m"
COLOR_YELLOW = "\033[1;33m"
COLOR_BLUE = "\033[1;34m"
COLOR_CYAN = "\033[1;36m"
COLOR_BG_RED = "\033[41;1m"


def print_banner() -> None:
    """Print CommitGuard visual header banner."""
    sys.stdout.write(
        f"{COLOR_CYAN}{COLOR_BOLD}CommitGuard{COLOR_RESET} "
        f"{COLOR_DIM}- DevSecOps Pre-commit Secret & PII Shield{COLOR_RESET}\n"
    )
    sys.stdout.flush()


def mask_snippet(snippet: str) -> str:
    visible = len(snippet) // 5
    side = visible // 2
    """Mask sensitive tokens partially to prevent credential exposure in logs.
    
    Shows about 20% of the characters, split between start and end.
    Very short values are fully hidden
    """
    if side == 0:
        return "****"
    return f"{snippet[:side]}...{snippet[-side:]}"


def display_findings(findings: List[Finding]) -> None:
    """Render findings list on Terminal with colored layout."""
    sys.stdout.write(
        f"\n{COLOR_BG_RED} [SECURITY ALERT] {COLOR_RESET} "
        f"{COLOR_RED}{COLOR_BOLD}Detected {len(findings)} potential secret(s) / PII in staged changes!{COLOR_RESET}\n\n"
    )

    separator = f"{COLOR_DIM}{'-' * 84}{COLOR_RESET}"
    sys.stdout.write(f"{separator}\n")
    sys.stdout.write(
        f"{COLOR_BOLD}{'FILE':<24} {'LINE':<6} {'CATEGORY':<10} {'TYPE':<26} {'SCORE':<8} {'SNIPPET'}{COLOR_RESET}\n"
    )
    sys.stdout.write(f"{separator}\n")

    for finding in findings:
        entropy_display = f"{finding.entropy_score:.2f}" if finding.entropy_score is not None else "N/A"
        category_color = COLOR_YELLOW if finding.category == "PII" else COLOR_RED
        masked = mask_snippet(finding.snippet)

        file_truncated = (finding.file[:21] + "...") if len(finding.file) > 24 else finding.file
        sys.stdout.write(
            f"{file_truncated:<24} "
            f"{COLOR_CYAN}{finding.line:<6}{COLOR_RESET} "
            f"{category_color}{finding.category:<10}{COLOR_RESET} "
            f"{COLOR_BOLD}{finding.type:<26}{COLOR_RESET} "
            f"{COLOR_DIM}{entropy_display:<8}{COLOR_RESET} "
            f"{COLOR_RED}{masked}{COLOR_RESET}\n"
        )

    sys.stdout.write(f"{separator}\n")


def prompt_user_tty() -> str:
    """Read interactive choice directly from Terminal Device (/dev/tty or CONIN$),
    bypassing Git's stdin redirection."""
    tty_path = "CONIN$" if os.name == "nt" else "/dev/tty"

    try:
        with open(tty_path, "r", encoding="utf-8") as tty:
            while True:
                sys.stdout.write(f"\n{COLOR_YELLOW}{COLOR_BOLD}[CommitGuard Action Required]{COLOR_RESET}\n")
                sys.stdout.write(f"  {COLOR_RED}[A]{COLOR_RESET} Abort commit (Fix your secrets)\n")
                sys.stdout.write(f"  {COLOR_GREEN}[B]{COLOR_RESET} Bypass and proceed anyway\n")
                sys.stdout.write(f"{COLOR_BOLD}Select action [A/B]: {COLOR_RESET}")
                sys.stdout.flush()

                line = tty.readline()
                if line == "":
                    sys.stdout.write(f"\n{COLOR_YELLOW}[CommitGuard Warning]{COLOR_RESET} EOF detected. Defaulting to Abort.\n")
                    return "A"
                choice = line.strip().upper()
                if choice in ("A", "B"):
                    return choice
                sys.stdout.write(f"{COLOR_YELLOW}Invalid option '{choice}'. Please type A or B.\n")
    except Exception as e:
        # If TTY cannot be opened (e.g. non-interactive CI/CD), fail-safe by aborting
        sys.stderr.write(
            f"\n{COLOR_RED}Could not access TTY: {e}. Aborting commit for safety.{COLOR_RESET}\n"
        )
        return "A" 


def run() -> int:
    """Execute pre-commit scan workflow and return exit code.

    Returns:
        0: Safe to commit or user bypassed.
        1: Block commit due to detected secrets or errors.
    """
    print_banner()

    try:
        findings = scan_staged_changes()
    except RuntimeError as e:
        sys.stderr.write(f"{COLOR_RED}[CommitGuard Error]{COLOR_RESET} {e}\n")
        return 1

    if not findings:
        sys.stdout.write(
            f"\n{COLOR_GREEN}{COLOR_BOLD}[CLEAN]{COLOR_RESET} "
            f"{COLOR_GREEN}No secrets or PII detected in staged changes. Commit authorized!{COLOR_RESET}\n\n"
        )
        return 0

    display_findings(findings)
    user_choice = prompt_user_tty()

    if user_choice == "B":
        sys.stdout.write(
            f"\n{COLOR_YELLOW}[CommitGuard Warning]{COLOR_RESET} "
            f"Commit bypassed by developer. Proceeding with commit...\n\n"
        )
        return 0

    sys.stdout.write(
        f"\n{COLOR_RED}[CommitGuard Blocked]{COLOR_RESET} "
        f"Commit aborted. Please remove sensitive data before committing.\n\n"
    )
    return 1


def install_hook() -> int:
    """Install CommitGuard as a Git pre-commit hook in .git/hooks/pre-commit.

    Returns:
        0 on success, 1 on error.
    """
    import stat
    import subprocess

    print_banner()

    try:
        res = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            sys.stderr.write(
                f"\n{COLOR_RED}[Error]{COLOR_RESET} Not a git repository. Cannot install pre-commit hook.\n"
                f"Please initialize a Git repository first (`git init`).\n\n"
            )
            return 1
        git_dir = res.stdout.strip()
    except Exception as e:
        sys.stderr.write(f"\n{COLOR_RED}[Error]{COLOR_RESET} Git check failed: {e}\n\n")
        return 1

    hooks_dir = os.path.join(git_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    hook_path = os.path.join(hooks_dir, "pre-commit")

    hook_script_content = """#!/bin/sh
# CommitGuard - Pre-commit Hook for DevSecOps Secret & PII Scanning
# Automatically installed by `python commitguard.py --install`

REPO_ROOT="$(git rev-parse --show-toplevel)"

# Detect python executable
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "[CommitGuard] Error: Python executable not found in PATH." >&2
    exit 1
fi

exec "$PYTHON_BIN" "$REPO_ROOT/commitguard.py" "$@"
"""

    try:
        with open(hook_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(hook_script_content)

        # Set executable permissions (chmod +x / 0o755)
        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        sys.stdout.write(
            f"\n{COLOR_GREEN}{COLOR_BOLD}[SUCCESS]{COLOR_RESET} "
            f"CommitGuard hook installed successfully!\n"
            f"Hook location: {COLOR_CYAN}{hook_path}{COLOR_RESET}\n"
            f"Every future '{COLOR_BOLD}git commit{COLOR_RESET}' will now automatically scan for secrets and PII.\n\n"
        )
        return 0
    except Exception as e:
        sys.stderr.write(f"\n{COLOR_RED}[Error]{COLOR_RESET} Failed to write hook file: {e}\n\n")
        return 1


def uninstall_hook() -> int:
    """Remove CommitGuard hook from .git/hooks/pre-commit.

    Returns:
        0 on success, 1 on error.
    """
    import subprocess

    print_banner()

    try:
        res = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            sys.stderr.write(
                f"\n{COLOR_RED}[Error]{COLOR_RESET} Not a git repository.\n\n"
            )
            return 1
        git_dir = res.stdout.strip()
    except Exception as e:
        sys.stderr.write(f"\n{COLOR_RED}[Error]{COLOR_RESET} Git check failed: {e}\n\n")
        return 1

    hook_path = os.path.join(git_dir, "hooks", "pre-commit")
    if os.path.exists(hook_path):
        try:
            os.remove(hook_path)
            sys.stdout.write(
                f"\n{COLOR_GREEN}[SUCCESS]{COLOR_RESET} Pre-commit hook removed from {COLOR_CYAN}{hook_path}{COLOR_RESET}\n\n"
            )
            return 0
        except Exception as e:
            sys.stderr.write(f"\n{COLOR_RED}[Error]{COLOR_RESET} Could not delete hook file: {e}\n\n")
            return 1
    else:
        sys.stdout.write(f"\n{COLOR_YELLOW}[Notice]{COLOR_RESET} No pre-commit hook found at {hook_path}\n\n")
        return 0


def main() -> None:
    """Main CLI entrypoint."""
    sys.exit(run())


if __name__ == "__main__":
    main()
