from __future__ import annotations

import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import bootstrap  # noqa: E402


class ManifestTest(unittest.TestCase):
    def test_manifest_parses(self):
        top, repos = bootstrap.load_manifest()
        names = [r.name for r in repos]
        self.assertEqual(top["host"], "https://github.com")
        for required in [
            "devtools-workspace",
            "devtools-common",
            "dev-environment",
            "ai-coding",
            "learning-materials",
        ]:
            self.assertIn(required, names)
        self.assertEqual(len(names), len(set(names)))
        for retired in ("devtools-template", "field-validation", "spec-trace", "ai-prompt-kb"):
            self.assertNotIn(retired, names)  # 統合・廃止したリポジトリ
        tools = [r for r in repos if r.role == "tool"]
        self.assertTrue(tools)
        self.assertTrue(all(r.cli and r.python for r in tools))

    def test_code_workspace_lists_all_repos(self):
        text = (ROOT / "devtools.code-workspace").read_text(encoding="utf-8")
        for r in bootstrap.load_manifest()[1]:
            if r.name != "devtools-workspace":
                self.assertIn(
                    f'"../{r.name}"',
                    text,
                    f"{r.name} missing in devtools.code-workspace",
                )


class InstallPlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "devtools-common").mkdir()
        (self.tmp / "devtools-common" / "pyproject.toml").write_text(
            '[project]\nname = "devtools-common"\ndependencies = ["PyYAML>=6"]\n',
            encoding="utf-8",
        )
        (self.tmp / "tool-a").mkdir()
        (self.tmp / "tool-a" / "pyproject.toml").write_text(
            '[project]\nname = "tool-a"\ndependencies = ["devtools-common @ git+https://x/devtools-common@v0.1.0",'
            ' "openpyxl>=3"]\n[project.optional-dependencies]\ndev = ["pytest>=8"]\n',
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_local_common_replaces_git_dependency(self):
        repos = [
            bootstrap.Repo("devtools-common", python=True),
            bootstrap.Repo("tool-a", python=True),
            bootstrap.Repo("not-cloned", python=True),
        ]
        plan = bootstrap.install_plan(self.tmp, repos)
        self.assertEqual(plan[0], ["install", "-e", f"{self.tmp / 'devtools-common'}[dev]"])
        self.assertEqual(plan[1], ["install", "openpyxl>=3", "pytest>=8"])
        self.assertEqual(plan[2], ["install", "--no-deps", "-e", str(self.tmp / "tool-a")])
        self.assertFalse(any("git+" in " ".join(p) for p in plan))

    def test_list_and_dry_run(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(bootstrap.main(["list"]), 0)
            self.assertEqual(bootstrap.main(["--root", str(self.tmp), "install", "--dry-run"]), 0)
        self.assertIn("| doc-to-markdown | tool | `doc2md` |", out.getvalue())
        self.assertIn("| office-review | tool | `harness` |", out.getvalue())

    def test_clone_requires_org(self):
        with self.assertRaises(SystemExit):
            bootstrap.cmd_clone(self.tmp, {"org": "<your-org>"}, [], None)


if __name__ == "__main__":
    unittest.main()
