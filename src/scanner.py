"""CommitGuard - Git Diff Scanner module for staged changes."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

from src.entropy import calculate_shannon_entropy, is_high_entropy
from src.validators import (
    scan_api_keys,
    scan_private_keys,
    scan_thai_ids,
    scan_thai_phone_numbers,
)

HUNK_HEADER_REGEX = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
DIFF_FILE_REGEX = re.compile(r"^\+\+\+ b/(.+)$")
TOKEN_CANDIDATE_REGEX = re.compile(r"[A-Za-z0-9+/=_\-\.]{16,}")


@dataclass
class Finding:
    """Represents a security or PII finding detected in staged git diff."""

    file: str
    line: int
    type: str
    snippet: str
    entropy_score: Optional[float] = None
    category: str = "SECRET"


def get_git_diff_cached() -> str:
    """Execute 'git diff --cached --no-color' to obtain staged additions.

    Returns:
        String containing raw unified git diff output.

    Raises:
        RuntimeError: If git command fails or current directory is not a git repository.
    """
    try:
        # Check if current directory is inside a git repository
        repo_check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
        if repo_check.returncode != 0:
            raise RuntimeError("Not a git repository. CommitGuard must be run within a Git repository.")

        result = subprocess.run(
            ["git", "diff", "--cached", "--no-color"],
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Failed to run git diff"
            raise RuntimeError(f"Git command failed (exit code {result.returncode}): {error_msg}")
        return result.stdout
    except FileNotFoundError:
        raise RuntimeError("Git executable not found in system PATH.")


def parse_diff(diff_text: str) -> List[Tuple[str, int, str]]:
    """Parse git unified diff into structured list of added lines.

    Extracts:
        (filename, line_number_in_new_file, line_content)

    Args:
        diff_text: Raw diff output string.

    Returns:
        List of tuples (file, line_no, content).
    """
    results: List[Tuple[str, int, str]] = []
    current_file = ""
    current_line_no = 0

    for line in diff_text.splitlines():
        # Handle file target line: +++ b/path/to/file.ext
        if line.startswith("+++ "):
            match = DIFF_FILE_REGEX.match(line)
            if match:
                current_file = match.group(1).strip()
            elif line.startswith("+++ /dev/null"):
                current_file = ""
            continue

        # Handle hunk header line: @@ -old,len +new,len @@
        if line.startswith("@@ "):
            match = HUNK_HEADER_REGEX.match(line)
            if match:
                current_line_no = int(match.group(1))
            continue

        # Skip headers or when no valid file target
        if not current_file or current_line_no == 0:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            # Addition line
            added_content = line[1:]
            results.append((current_file, current_line_no, added_content))
            current_line_no += 1
        elif line.startswith("-") and not line.startswith("---"):
            # Deletion line in old file does not increment new file line counter
            continue
        elif line.startswith(" "):
            # Context line in both old and new file
            current_line_no += 1

    return results


def extract_potential_secret_tokens(text: str) -> List[str]:
    """Extract individual alphanumeric/symbol candidate tokens of length >= 16.

    Args:
        text: Line content.

    Returns:
        List of candidate secret tokens.
    """
    return TOKEN_CANDIDATE_REGEX.findall(text)


def scan_diff_content(diff_text: str, entropy_threshold: float = 4.3) -> List[Finding]:
    """Analyze all staged additions in the diff content for PII and secrets.

    Args:
        diff_text: Unified diff output.
        entropy_threshold: Cutoff Shannon entropy for secret detection (default 4.3).

    Returns:
        List of Finding objects.
    """
    parsed_lines = parse_diff(diff_text)
    findings: List[Finding] = []

    for file_path, line_no, content in parsed_lines:
        line_matched_snippets: set[str] = set()

        # 1. Check Thai National IDs
        for thai_id in scan_thai_ids(content):
            findings.append(
                Finding(
                    file=file_path,
                    line=line_no,
                    type="Thai National ID",
                    snippet=thai_id,
                    entropy_score=round(calculate_shannon_entropy(thai_id), 2),
                    category="PII",
                )
            )
            line_matched_snippets.add(thai_id)

        # 2. Check Thai Phone Numbers
        for phone in scan_thai_phone_numbers(content):
            findings.append(
                Finding(
                    file=file_path,
                    line=line_no,
                    type="Thai Phone Number",
                    snippet=phone,
                    entropy_score=round(calculate_shannon_entropy(phone), 2),
                    category="PII",
                )
            )
            line_matched_snippets.add(phone)

        # 3. Check Private Key Headers
        for key_header in scan_private_keys(content):
            findings.append(
                Finding(
                    file=file_path,
                    line=line_no,
                    type="Private Key Header",
                    snippet=key_header,
                    entropy_score=None,
                    category="SECRET",
                )
            )
            line_matched_snippets.add(key_header)

        # 4. Check Known Hardcoded API Keys
        for api_item in scan_api_keys(content):
            val = api_item["matched_value"]
            findings.append(
                Finding(
                    file=file_path,
                    line=line_no,
                    type=api_item["type"],
                    snippet=val,
                    entropy_score=round(calculate_shannon_entropy(val), 2),
                    category="SECRET",
                )
            )
            line_matched_snippets.add(val)

        # 5. Check High-Entropy Secrets (Entropy analysis)
        candidates = extract_potential_secret_tokens(content)
        for token in candidates:
            # Skip if this token is already identified by dedicated regexes
            if any(token in matched or matched in token for matched in line_matched_snippets):
                continue

            if is_high_entropy(token, threshold=entropy_threshold):
                score = round(calculate_shannon_entropy(token), 2)
                findings.append(
                    Finding(
                        file=file_path,
                        line=line_no,
                        type="High-Entropy Secret",
                        snippet=token,
                        entropy_score=score,
                        category="SECRET",
                    )
                )
                line_matched_snippets.add(token)

    return findings


def scan_staged_changes(entropy_threshold: float = 4.3) -> List[Finding]:
    """Execute git diff and scan all staged additions.

    Args:
        entropy_threshold: Cutoff Shannon entropy for secret detection.

    Returns:
        List of Finding objects.
    """
    diff_text = get_git_diff_cached()
    return scan_diff_content(diff_text, entropy_threshold=entropy_threshold)
