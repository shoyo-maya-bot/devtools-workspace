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


class PullTest(unittest.TestCase):
    """setup が取得済みのリポジトリを最新にする（bootstrap.py pull）."""

    def _git(self, *args, cwd):
        import subprocess

        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

    def test_pull_updates_and_reports_blocked(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        ident = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
        for name in ("a", "b"):
            src = tmp / "src" / name
            src.mkdir(parents=True)
            self._git("init", "-q", "-b", "main", cwd=src)
            (src / "f.txt").write_text("1\n", encoding="utf-8")
            self._git("add", ".", cwd=src)
            self._git(*ident, "commit", "-q", "-m", "1", cwd=src)
            self._git("clone", "-q", str(src), str(tmp / "ws" / name), cwd=tmp)
            (src / "f.txt").write_text("2\n", encoding="utf-8")
            self._git(*ident, "commit", "-q", "-am", "2", cwd=src)
        (tmp / "ws" / "b" / "f.txt").write_text("local\n", encoding="utf-8")  # b は手元で変更 → 進められない

        repos = [bootstrap.Repo(name="a"), bootstrap.Repo(name="b"), bootstrap.Repo(name="missing")]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = bootstrap.cmd_pull(tmp / "ws", repos)
        self.assertEqual(code, 1)
        self.assertEqual((tmp / "ws" / "a" / "f.txt").read_text(encoding="utf-8"), "2\n")
        self.assertEqual((tmp / "ws" / "b" / "f.txt").read_text(encoding="utf-8"), "local\n")
        self.assertIn("pull   b: 最新にできませんでした", out.getvalue())
        self.assertNotIn("missing", out.getvalue())


class SelectReposTest(unittest.TestCase):
    """--only で一部のリポジトリだけを扱う（CI や、必要なものだけ取りたいとき）."""

    def test_only_filters_in_manifest_order(self):
        repos = [bootstrap.Repo("a"), bootstrap.Repo("b"), bootstrap.Repo("c")]
        self.assertEqual([r.name for r in bootstrap.select_repos(repos, "c, a")], ["a", "c"])
        self.assertEqual(bootstrap.select_repos(repos, None), repos)

    def test_unknown_name_is_usage_error(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            bootstrap.main(["--only", "devtools-common,no-such-repo", "list"])
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("no-such-repo", err.getvalue())

    def test_only_list(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(bootstrap.main(["--only", "doc-to-markdown", "list"]), 0)
        self.assertIn("doc-to-markdown", out.getvalue())
        self.assertNotIn("office-review", out.getvalue())
