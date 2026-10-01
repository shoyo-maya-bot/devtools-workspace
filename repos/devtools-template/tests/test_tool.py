from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from devtools_common.cli import run_main

from tool_name import cli

ROOT = Path(__file__).resolve().parent.parent


def run_cli(*args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = run_main(cli.main, list(args))
    return rc, out.getvalue(), err.getvalue()


class ToolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_sample_with_example_config(self):
        rc, out, _ = run_cli("check", str(ROOT / "samples"), "-c", str(ROOT / "config.example.yaml"), "-f", "json")
        self.assertEqual(rc, 0)  # warning のみ
        data = json.loads(out)
        self.assertEqual([f["rule_id"] for f in data["findings"]], ["no-todo"])

    def test_error_finding_sets_exit_code(self):
        f = self.tmp / "a.md"
        f.write_text("see https://wiki.corp/x\n", encoding="utf-8")
        rc, _, _ = run_cli("check", str(f), "-c", str(ROOT / "config.example.yaml"))
        self.assertEqual(rc, 1)

    def test_invalid_config_is_usage_error(self):
        cfg = self.tmp / "c.yaml"
        cfg.write_text("max_line_length: -1\nunknown: 1\n", encoding="utf-8")
        rc, _, err = run_cli("check", str(ROOT / "samples"), "-c", str(cfg))
        self.assertEqual(rc, 2)
        self.assertIn("unknown", err)

    def test_missing_input(self):
        rc, _, _ = run_cli("check", str(self.tmp / "nope.md"))
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
