"""Unit tests for src/scanner.py and src/cli.py."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
from unittest.mock import mock_open

from src.cli import mask_snippet, run
from src.scanner import (
    Finding,
    extract_potential_secret_tokens,
    parse_diff,
    scan_diff_content,
)

SAMPLE_GIT_DIFF = """diff --git a/app/config.py b/app/config.py
index e69de29..49b61d1 100644
--- a/app/config.py
+++ b/app/config.py
@@ -10,3 +10,6 @@ import os
 def get_settings():
-    pass
+    # Sensitive config additions
+    thai_id = "1234567890121"
+    phone = "081-234-5678"
+    aws_key = "AKIAIOSFODNN7EXAMPLE"
+    high_entropy_token = "aB3dEf9hI1kLmNoPqRsTuVwXyZ0123"
diff --git a/certs/key.pem b/certs/key.pem
new file mode 100644
--- /dev/null
+++ b/certs/key.pem
@@ -0,0 +1,2 @@
+-----BEGIN RSA PRIVATE KEY-----
+MIIEowIBAAKCAQEA0Y...
"""


class TestScanner(unittest.TestCase):
    """Test suite for git diff parsing and secret detection."""

    def test_parse_diff_extracts_additions_and_lines(self) -> None:
        parsed = parse_diff(SAMPLE_GIT_DIFF)
        self.assertGreater(len(parsed), 0)

        # First addition in app/config.py starts at line 11 (after context line 10)
        self.assertEqual(parsed[0][0], "app/config.py")
        self.assertEqual(parsed[0][1], 11)
        self.assertIn("Sensitive config additions", parsed[0][2])

        # Second addition at line 12
        self.assertEqual(parsed[1][0], "app/config.py")
        self.assertEqual(parsed[1][1], 12)
        self.assertIn("1234567890121", parsed[1][2])

        # Check certs/key.pem additions
        cert_additions = [p for p in parsed if p[0] == "certs/key.pem"]
        self.assertEqual(len(cert_additions), 2)
        self.assertEqual(cert_additions[0][1], 1)
        self.assertIn("-----BEGIN RSA PRIVATE KEY-----", cert_additions[0][2])

    def test_extract_potential_secret_tokens(self) -> None:
        line = 'secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'
        tokens = extract_potential_secret_tokens(line)
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0], "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    def test_scan_diff_content_detects_all_issues(self) -> None:
        findings = scan_diff_content(SAMPLE_GIT_DIFF)
        self.assertGreaterEqual(len(findings), 5)

        types = [f.type for f in findings]
        self.assertIn("Thai National ID", types)
        self.assertIn("Thai Phone Number", types)
        self.assertIn("AWS Access Key", types)
        self.assertIn("Private Key Header", types)
        self.assertIn("High-Entropy Secret", types)

        # Check lines and files
        id_finding = next(f for f in findings if f.type == "Thai National ID")
        self.assertEqual(id_finding.file, "app/config.py")
        self.assertEqual(id_finding.line, 12)
        self.assertEqual(id_finding.snippet, "1234567890121")
        self.assertEqual(id_finding.category, "PII")

        key_finding = next(f for f in findings if f.type == "Private Key Header")
        self.assertEqual(key_finding.file, "certs/key.pem")
        self.assertEqual(key_finding.line, 1)

    def test_clean_diff_returns_no_findings(self) -> None:
        clean_diff = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,3 +1,3 @@
-print('hello')
+print('hello safe world')
"""
        findings = scan_diff_content(clean_diff)
        self.assertEqual(len(findings), 0)


class TestCli(unittest.TestCase):
    """Test suite for CLI display and prompt workflows."""

    @patch("builtins.open", mock_open(read_data=""))
    def test_prompt_user_tty_eof_returns_abort(self) -> None:
        from src.cli import prompt_user_tty
        result = prompt_user_tty()
        
        self.assertEqual(result, "A")

    def test_mask_snippet(self) -> None:
        self.assertEqual(mask_snippet("short"), "****")
        self.assertEqual(mask_snippet("AKIAIOSFODNN7EXAMPLE"), "AKIA...MPLE")

    @patch("src.cli.scan_staged_changes")
    def test_run_clean_diff_returns_zero(self, mock_scan: MagicMock) -> None:
        mock_scan.return_value = []
        exit_code = run()
        self.assertEqual(exit_code, 0)

    @patch("src.cli.scan_staged_changes")
    @patch("src.cli.prompt_user_tty")
    def test_run_with_findings_abort_returns_one(
        self, mock_prompt: MagicMock, mock_scan: MagicMock
    ) -> None:
        mock_scan.return_value = [
            Finding(
                file="sec.py",
                line=5,
                type="AWS Access Key",
                snippet="AKIAIOSFODNN7EXAMPLE",
                entropy_score=3.8,
                category="SECRET",
            )
        ]
        mock_prompt.return_value = "A"
        exit_code = run()
        self.assertEqual(exit_code, 1)

    @patch("src.cli.scan_staged_changes")
    @patch("src.cli.prompt_user_tty")
    def test_run_with_findings_bypass_returns_zero(
        self, mock_prompt: MagicMock, mock_scan: MagicMock
    ) -> None:
        mock_scan.return_value = [
            Finding(
                file="sec.py",
                line=5,
                type="AWS Access Key",
                snippet="AKIAIOSFODNN7EXAMPLE",
                entropy_score=3.8,
                category="SECRET",
            )
        ]
        mock_prompt.return_value = "B"
        exit_code = run()
        self.assertEqual(exit_code, 0)

    @patch("subprocess.run")
    def test_install_hook_outside_git_fails(self, mock_subproc: MagicMock) -> None:
        from src.cli import install_hook

        mock_subproc.return_value = MagicMock(returncode=1, stderr="fatal: not a git repo")
        exit_code = install_hook()
        self.assertEqual(exit_code, 1)

    @patch("subprocess.run")
    def test_uninstall_hook_outside_git_fails(self, mock_subproc: MagicMock) -> None:
        from src.cli import uninstall_hook

        mock_subproc.return_value = MagicMock(returncode=1, stderr="fatal: not a git repo")
        exit_code = uninstall_hook()
        self.assertEqual(exit_code, 1)

    def test_argument_parser(self) -> None:
        from commitguard import create_parser

        parser = create_parser()

        args_install = parser.parse_args(["--install"])
        self.assertTrue(args_install.install)
        self.assertFalse(args_install.scan)

        args_scan = parser.parse_args(["--scan"])
        self.assertTrue(args_scan.scan)
        self.assertFalse(args_scan.install)

        args_default = parser.parse_args([])
        self.assertFalse(args_default.install)
        self.assertFalse(args_default.scan)



if __name__ == "__main__":
    unittest.main()
