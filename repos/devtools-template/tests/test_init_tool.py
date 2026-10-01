"""scripts/init_tool.py のテスト（テンプレートを一時ディレクトリに複製して初期化し、新ツールのテストが通ること）."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import init_tool  # noqa: E402


class InitToolTest(unittest.TestCase):
    def test_init_and_run_tests_of_new_tool(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "api-spec-diff"
            shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.egg-info"))
            init_tool.init(repo, "api-spec-diff", "OpenAPI 仕様の差分を抽出する")

            self.assertTrue((repo / "src" / "api_spec_diff" / "cli.py").is_file())
            self.assertFalse((repo / "src" / "tool_name").exists())
            self.assertFalse((repo / "scripts" / "init_tool.py").exists())
            self.assertFalse((repo / "TOOL_README.md").exists())
            pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
            self.assertIn('name = "api-spec-diff"', pyproject)
            self.assertIn('api-spec-diff = "api_spec_diff.cli:entrypoint"', pyproject)
            self.assertIn("OpenAPI 仕様の差分を抽出する", (repo / "README.md").read_text(encoding="utf-8"))
            leftovers = [
                p
                for p in repo.rglob("*")
                if p.is_file()
                and p.suffix in {".py", ".toml", ".md", ".ps1", ".sh"}
                and ("tool_name" in p.read_text(encoding="utf-8") or "tool-name" in p.read_text(encoding="utf-8"))
            ]
            self.assertEqual(leftovers, [])
            ps1 = (repo / "scripts" / "setup.ps1").read_bytes()
            self.assertTrue(ps1.startswith(b"\xef\xbb\xbf") and b"\r\n" in ps1, "setup.ps1 は BOM + CRLF を保つ")
            self.assertIn(b"api-spec-diff.exe", ps1)

            env = {**os.environ, "PYTHONPATH": str(repo / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")}
            r = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_rejects_bad_name(self):
        with self.assertRaises(SystemExit):
            init_tool.init(ROOT, "Bad_Name", "x")


if __name__ == "__main__":
    unittest.main()
