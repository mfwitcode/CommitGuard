"""CommitGuard - Validators and regex scanner module for PII and Secrets."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Pattern, Tuple

# Thai Phone Number Regex (Supports formats like 0812345678, 081-234-5678, 08-1234-5678)
THAI_PHONE_REGEX: Pattern[str] = re.compile(
    r"\b0[689](?:[-]?\d{4}[-]?\d{4}|\d[-]?\d{3}[-]?\d{4})\b"
)

# Private Key Header Regex (Supports RSA, EC, OPENSSH, DSA or generic PRIVATE KEY)
PRIVATE_KEY_REGEX: Pattern[str] = re.compile(
    r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"
)

# API Key Patterns with friendly descriptive names
API_KEY_PATTERNS: List[Tuple[str, Pattern[str]]] = [
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("OpenAI API Key", re.compile(r'\bsk-[a-zA-Z0-9_-]{20,}\b')),
    ("GitHub Personal Access Token", re.compile(r"\bghp_[a-zA-Z0-9]{36}\b")),
]

# Thai National ID candidate pattern (raw digits or formatted like X-XXXX-XXXXX-XX-X)
THAI_ID_CANDIDATE_REGEX: Pattern[str] = re.compile(
    r"\b\d(?:-\d{4}-\d{5}-\d{2}-\d|\d{12})\b"
)


def is_valid_thai_id(id_str: str) -> bool:
    """Validate Thai National ID using Modulo 11 checksum algorithm.

    Formula:
        Sum = sum(d_i * (13 - i)) for i in 0..11
        Check_digit = (11 - (Sum % 11)) % 10
        Valid if Check_digit == d_12

    Args:
        id_str: National ID string, can include hyphens or whitespace.

    Returns:
        True if valid 13-digit Thai ID with correct checksum, False otherwise.
    """
    cleaned = re.sub(r"[-\s]", "", id_str)
    if not re.match(r"^\d{13}$", cleaned):
        return False

    # All identical digits (e.g. 1111111111111) are invalid
    if len(set(cleaned)) == 1:
        return False

    digits = [int(c) for c in cleaned]
    weighted_sum = sum(digits[i] * (13 - i) for i in range(12))
    check_digit = (11 - (weighted_sum % 11)) % 10

    return check_digit == digits[12]


def scan_thai_ids(text: str) -> List[str]:
    """Scan text for candidate Thai National IDs and filter by Modulo 11 checksum.

    Args:
        text: Text to scan.

    Returns:
        List of valid Thai National ID strings found.
    """
    candidates = THAI_ID_CANDIDATE_REGEX.findall(text)
    return [candidate for candidate in candidates if is_valid_thai_id(candidate)]


def scan_thai_phone_numbers(text: str) -> List[str]:
    """Scan text for Thai mobile phone numbers (06x, 08x, 09x).

    Args:
        text: Text to scan.

    Returns:
        List of matched Thai phone number strings.
    """
    return THAI_PHONE_REGEX.findall(text)


def scan_private_keys(text: str) -> List[str]:
    """Scan text for Private Key headers.

    Args:
        text: Text to scan.

    Returns:
        List of matched Private Key header strings.
    """
    return PRIVATE_KEY_REGEX.findall(text)


def scan_api_keys(text: str) -> List[Dict[str, str]]:
    """Scan text for known hardcoded API key patterns.

    Args:
        text: Text to scan.

    Returns:
        List of dicts containing 'type' and 'matched_value'.
    """
    matches: List[Dict[str, str]] = []
    for key_type, pattern in API_KEY_PATTERNS:
        for match in pattern.findall(text):
            matches.append({
                "type": key_type,
                "matched_value": match,
            })
    return matches


def scan_all_pii_and_secrets(text: str) -> List[Dict[str, Any]]:
    """Comprehensive scan for PII, Thai National IDs, Private Keys, and API Keys.

    Args:
        text: Diff content or source code text to scan.

    Returns:
        Unified list of findings with category, type, and matched value.
    """
    findings: List[Dict[str, Any]] = []

    for thai_id in scan_thai_ids(text):
        findings.append({
            "category": "PII",
            "type": "Thai National ID",
            "matched_value": thai_id,
        })

    for phone in scan_thai_phone_numbers(text):
        findings.append({
            "category": "PII",
            "type": "Thai Phone Number",
            "matched_value": phone,
        })

    for key_header in scan_private_keys(text):
        findings.append({
            "category": "SECRET",
            "type": "Private Key Header",
            "matched_value": key_header,
        })

    for api_match in scan_api_keys(text):
        findings.append({
            "category": "SECRET",
            "type": api_match["type"],
            "matched_value": api_match["matched_value"],
        })

    return findings
