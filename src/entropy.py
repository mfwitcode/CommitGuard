"""CommitGuard - Git Pre-commit Hook CLI for DevSecOps.

Core entropy calculation and secret detection module.
"""

from __future__ import annotations

import math
from collections import Counter


def calculate_shannon_entropy(text: str) -> float:
    """Calculate the Shannon Entropy of a string in bits per character.

    Formula: H(X) = -sum(P(x) * log2(P(x)))

    Args:
        text: Input string to calculate entropy for.

    Returns:
        Shannon entropy value (float) in bits per character.
    """
    if not text:
        return 0.0

    length = len(text)
    frequencies = Counter(text)
    entropy = 0.0

    for count in frequencies.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return entropy


def is_high_entropy(token: str, threshold: float = 4.0) -> bool:
    """Evaluate whether a string token has suspiciously high entropy,
    indicating it may be an API key, secret, or cryptographic token.

    Rules:
    - Filters out tokens shorter than 16 characters.
    - Evaluates Shannon entropy against the given threshold.

    Args:
        token: The token/string to evaluate.
        threshold: Entropy cutoff threshold (default 4.3 bits/char).

    Returns:
        True if token length >= 16 and entropy >= threshold, False otherwise.
    """
    if len(token) < 16:
        return False

    entropy = calculate_shannon_entropy(token)
    return entropy >= threshold
