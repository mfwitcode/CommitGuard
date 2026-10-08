"""Unit tests for CommitGuard core modules (src/entropy.py and src/validators.py)."""

from __future__ import annotations

import unittest

from src.entropy import calculate_shannon_entropy, is_high_entropy
from src.validators import (
    is_valid_thai_id,
    scan_all_pii_and_secrets,
    scan_api_keys,
    scan_private_keys,
    scan_thai_ids,
    scan_thai_phone_numbers,
)


class TestEntropy(unittest.TestCase):
    """Test suite for Shannon entropy calculations and high-entropy detection."""

    def test_calculate_shannon_entropy_empty(self) -> None:
        self.assertEqual(calculate_shannon_entropy(""), 0.0)

    def test_calculate_shannon_entropy_single_character(self) -> None:
        self.assertEqual(calculate_shannon_entropy("aaaaaaa"), 0.0)

    def test_calculate_shannon_entropy_two_uniform_chars(self) -> None:
        # 'abababab' has 2 symbols with equal probability (0.5 each)
        # H(X) = - (0.5 * log2(0.5) + 0.5 * log2(0.5)) = 1.0 bit
        self.assertAlmostEqual(calculate_shannon_entropy("abababab"), 1.0, places=4)

    def test_is_high_entropy_short_token(self) -> None:
        # Length < 16 should always return False regardless of entropy
        self.assertFalse(is_high_entropy("aB3#xY9!"))
        self.assertFalse(is_high_entropy("123456789012345"))  # length 15

    def test_is_high_entropy_low_entropy_long_token(self) -> None:
        # Length >= 16 but repeated or low-diversity characters
        self.assertFalse(is_high_entropy("aaaaaaaaaaaaaaaa"))
        self.assertFalse(is_high_entropy("passwordpassword123"))

    def test_is_high_entropy_secret_keys(self) -> None:
        # Random secret with length >= 16 and high character variety
        secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        self.assertTrue(is_high_entropy(secret, threshold=4.3))

    def test_is_high_entropy_custom_threshold(self) -> None:
        token = "abcdefghijklmnop"  # 16 distinct chars -> entropy = 4.0
        self.assertFalse(is_high_entropy(token, threshold=4.3))
        self.assertTrue(is_high_entropy(token, threshold=3.9))


class TestThaiIDValidator(unittest.TestCase):
    """Test suite for Thai National ID Modulo 11 validation."""

    def test_valid_thai_id(self) -> None:
        # 1234567890121 is mathematically valid under Modulo 11
        self.assertTrue(is_valid_thai_id("1234567890121"))
        self.assertTrue(is_valid_thai_id("1-2345-67890-12-1"))

        # 1100100123454 is also valid
        self.assertTrue(is_valid_thai_id("1100100123454"))
        self.assertTrue(is_valid_thai_id("1-1001-00123-45-4"))

    def test_invalid_checksum(self) -> None:
        # Changing the last check digit makes it invalid
        self.assertFalse(is_valid_thai_id("1234567890120"))
        self.assertFalse(is_valid_thai_id("1-2345-67890-12-5"))

    def test_all_identical_digits(self) -> None:
        # All repeated digits must be rejected
        self.assertFalse(is_valid_thai_id("1111111111111"))
        self.assertFalse(is_valid_thai_id("9-9999-99999-99-9"))

    def test_invalid_length_and_characters(self) -> None:
        self.assertFalse(is_valid_thai_id(""))
        self.assertFalse(is_valid_thai_id("123456"))
        self.assertFalse(is_valid_thai_id("12345678901234"))  # 14 digits
        self.assertFalse(is_valid_thai_id("123456789012A"))  # Letter

    def test_scan_thai_ids(self) -> None:
        diff_text = """
        + user_id = "1234567890121" # valid
        + fake_id = "1234567890120" # invalid checksum
        + citizen_card = "1-1001-00123-45-4" # formatted valid
        """
        matched = scan_thai_ids(diff_text)
        self.assertEqual(len(matched), 2)
        self.assertIn("1234567890121", matched)
        self.assertIn("1-1001-00123-45-4", matched)


class TestValidatorsRegexScanners(unittest.TestCase):
    """Test suite for Thai phone numbers, private keys, and API key scanners."""

    def test_scan_thai_phone_numbers(self) -> None:
        text = """
        contact: 0812345678
        mobile: 081-234-5678
        new_mobile: 099-123-4567
        alt_prefix: 062-890-1234
        landline: 021234567
        invalid: 1234567890
        """
        phones = scan_thai_phone_numbers(text)
        self.assertEqual(len(phones), 4)
        self.assertIn("0812345678", phones)
        self.assertIn("081-234-5678", phones)
        self.assertIn("099-123-4567", phones)
        self.assertIn("062-890-1234", phones)
        self.assertNotIn("021234567", phones)
        self.assertNotIn("1234567890", phones)

    def test_scan_private_keys(self) -> None:
        text = """
        -----BEGIN RSA PRIVATE KEY-----
        MIIEowIBAAKCAQEA0Y...
        -----END RSA PRIVATE KEY-----
        -----BEGIN EC PRIVATE KEY-----
        -----BEGIN OPENSSH PRIVATE KEY-----
        -----BEGIN PRIVATE KEY-----
        -----BEGIN PUBLIC KEY-----
        """
        keys = scan_private_keys(text)
        self.assertEqual(len(keys), 4)
        self.assertIn("-----BEGIN RSA PRIVATE KEY-----", keys)
        self.assertIn("-----BEGIN EC PRIVATE KEY-----", keys)
        self.assertIn("-----BEGIN OPENSSH PRIVATE KEY-----", keys)
        self.assertIn("-----BEGIN PRIVATE KEY-----", keys)
        self.assertNotIn("-----BEGIN PUBLIC KEY-----", keys)

    def test_scan_api_keys(self) -> None:
        text = """
        AWS_KEY=AKIAIOSFODNN7EXAMPLE
        OPENAI_KEY=sk-proj-abc123456789012345678901234567890
        GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz
        NORMAL_VAR=hello_world
        """
        api_keys = scan_api_keys(text)
        self.assertEqual(len(api_keys), 3)

        types = [item["type"] for item in api_keys]
        values = [item["matched_value"] for item in api_keys]

        self.assertIn("AWS Access Key", types)
        self.assertIn("AKIAIOSFODNN7EXAMPLE", values)

        self.assertIn("OpenAI API Key", types)
        self.assertIn("sk-proj-abc123456789012345678901234567890", values)

        self.assertIn("GitHub Personal Access Token", types)
        self.assertIn("ghp_1234567890abcdefghijklmnopqrstuvwxyz", values)

    def test_scan_all_pii_and_secrets(self) -> None:
        git_diff_sample = """
        diff --git a/config.py b/config.py
        --- a/config.py
        +++ b/config.py
        @@ -1,3 +1,6 @@
        +THAI_ID = "1234567890121"
        +CALL_CENTER = "081-234-5678"
        +AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
        +RSA_HEADER = "-----BEGIN RSA PRIVATE KEY-----"
        """
        findings = scan_all_pii_and_secrets(git_diff_sample)
        self.assertEqual(len(findings), 4)

        categories = {f["category"] for f in findings}
        self.assertEqual(categories, {"PII", "SECRET"})


if __name__ == "__main__":
    unittest.main()
