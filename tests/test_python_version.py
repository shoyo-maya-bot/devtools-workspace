"""必要な Python の版の確認が 1 か所（scripts/python_version.py）にまとまっていて、入口がすべてそれを使うことを確かめる.

以前の問題: install-prereqs.ps1 は py があるだけで「OK」にし、setup.sh は版を確かめずに python3 を呼んでいた。
bootstrap.py は先頭で tomllib（3.11+）を import するため、3.10 以下（macOS 標準の 3.9）では
トレースバックで止まっていた。
第 2 回: 最低版は各ツールの requires-python の下限（最も高いもの = 3.12）と同じにする（RequiresPythonTest）。
"""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import python_version  # noqa: E402


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig")


class PythonVersionTest(unittest.TestCase):
    def test_min_version(self):
        self.assertEqual(python_version.MIN_VERSION, (3, 12))

    def test_problem(self):
        self.assertIsNone(python_version.problem((3, 12, 0)))
        self.assertIsNone(python_version.problem((3, 13, 3)))
        msg = python_version.problem((3, 9, 6))
        self.assertIn("3.12 以上が必要", msg)
        self.assertIn("3.9.6", msg)
        self.assertIsNotNone(python_version.problem((3, 10, 14)))
        self.assertIsNotNone(python_version.problem((3, 11, 9)))  # office-review などの requires-python は >=3.12

    def test_cli_exit_codes(self):
        script = str(ROOT / "scripts" / "python_version.py")
        ok = subprocess.run([sys.executable, script], capture_output=True, text=True, check=False)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        quiet = subprocess.run([sys.executable, script, "--quiet"], capture_output=True, text=True, check=False)
        self.assertEqual((quiet.returncode, quiet.stdout, quiet.stderr), (0, "", ""))

    def test_bootstrap_on_old_python_exits_with_message(self):
        """古い Python では tomllib を import する前に、理由を出して終了コード 1 で終わる（トレースバックにしない）."""
        code = (
            "import runpy, sys\n"
            f"sys.path.insert(0, {str(ROOT / 'scripts')!r})  # python scripts/bootstrap.py と同じ\n"
            "sys.version_info = (3, 9, 6, 'final', 0)\n"
            "sys.modules['tomllib'] = None  # import されたら ImportError になる\n"
            "sys.argv = ['bootstrap.py', 'list']\n"
            f"runpy.run_path({str(ROOT / 'scripts' / 'bootstrap.py')!r}, run_name='__main__')\n"
        )
        p = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            check=False,
        )
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertIn("3.12 以上が必要", p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def test_bootstrap_checks_before_tomllib(self):
        text = read("scripts/bootstrap.py")
        self.assertLess(text.index("require()"), text.index("import tomllib"))


class EntrypointsUseSharedCheckTest(unittest.TestCase):
    """入口ごとに版の判定を書かない（ずれると「全部 OK」の直後に失敗する）."""

    FILES = ("setup.sh", "scripts/setup.ps1", "scripts/install-prereqs.ps1")

    def test_entrypoints_call_python_version(self):
        for rel in self.FILES:
            with self.subTest(rel=rel):
                self.assertIn("python_version.py", read(rel))

    def test_no_inline_version_comparison(self):
        for rel in (*self.FILES, "scripts/bootstrap.py"):
            with self.subTest(rel=rel):
                self.assertNotRegex(read(rel), r"version_info\s*>=|\(3,\s*1\d\)")

    def test_prereqs_does_not_accept_py_launcher_alone(self):
        text = read("scripts/install-prereqs.ps1")
        self.assertNotRegex(text, r"Test = \{ \[bool\]\(Get-Command py\b")
        self.assertRegex(text, r"Test = \{ \(Get-PythonStatus\)\.Ok")

    def test_setup_sh_picks_checked_python(self):
        text = read("setup.sh")
        self.assertRegex(text, r'"\$c" scripts/python_version\.py --quiet')
        self.assertIn('BS=("$PY" scripts/bootstrap.py', text)
        self.assertNotRegex(text, r"(?m)^BS=\(python3 ")

    def test_setup_sh_fails_clearly_without_python(self):
        """3.12 以上の Python が無いときは、理由を出して 1 で終わる（PATH から Python を外して確かめる）."""
        if sys.platform == "win32":
            self.skipTest("setup.sh は macOS・Linux 用（Windows は setup.cmd を CI の windows ジョブで確かめる）")
        bash, git = shutil.which("bash"), shutil.which("git")
        if not bash or not git:
            self.skipTest("bash と git が要る")
        with tempfile.TemporaryDirectory() as d:
            # git だけがある PATH（python3 は 3.9 のふりをする偽物）
            Path(d, "git").symlink_to(git)
            fake = Path(d, "python3")
            fake.write_text(
                "#!/bin/sh\necho 'Python 3.12 以上が必要です（今の Python は 3.9.6: fake）。' >&2\nexit 1\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            p = subprocess.run(
                [bash, str(ROOT / "setup.sh"), "--only", "devtools-common"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env={**os.environ, "PATH": d},
                check=False,
            )
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("Python 3.12 以上が見つかりません", p.stderr)
        self.assertIn("3.9.6", p.stderr)


class RequiresPythonTest(unittest.TestCase):
    """setup が求める最低版（MIN_VERSION）と、各ツールの pyproject.toml の requires-python を一致させる.

    ずれると、setup が「Python OK」と言った直後に pip が「Requires-Python >=3.12」でツールを入れられない
    （以前は 3.11 で OK と表示していたが、office-review などは >=3.12）。
    """

    def setUp(self):
        import bootstrap

        self.bs = bootstrap
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _pkg(self, rel: str, spec: str | None) -> None:
        d = self.tmp / rel
        d.mkdir(parents=True)
        line = f'requires-python = "{spec}"\n' if spec is not None else ""
        (d / "pyproject.toml").write_text(f'[project]\nname = "{d.name}"\n{line}', encoding="utf-8")

    def test_spec_helpers(self):
        lb, ok = self.bs.requires_python_lower_bound, self.bs.accepts
        self.assertEqual(lb(">=3.12"), (3, 12))
        self.assertEqual(lb(">=3.10, <4"), (3, 10))
        self.assertEqual(lb("~=3.11"), (3, 11))
        self.assertEqual(lb("<4"), ())
        self.assertTrue(ok(">=3.12", (3, 12)))
        self.assertFalse(ok(">=3.13", (3, 12)))
        self.assertFalse(ok(">=3.10,<3.12", (3, 12)))
        self.assertTrue(ok(">=3.10,<4", (3, 12)))
        self.assertFalse(ok("!=3.12.*", (3, 12)))

    def test_accepts_follows_pep440(self):
        """packaging の SpecifierSet と同じ判定（(major, minor) だけなら、その系列のどれかを受け付けるか）."""
        ok = self.bs.accepts
        cases = [
            ("~=3.12.1", (3, 13), False),  # ~=3.12.1 は >=3.12.1, ==3.12.*
            ("~=3.12.1", (3, 12), True),
            ("~=3.12.1", (3, 12, 0), False),
            ("~=3.12.1", (3, 12, 5), True),
            (">3.12", (3, 12), True),  # 3.12.1 以降を受け付ける
            (">3.12", (3, 12, 0), False),
            (">3.12", (3, 12, 1), True),
            ("~=3.11", (3, 12), True),
            ("~=3.11", (4, 0), False),
            ("==3.12.*", (3, 12), True),
            ("==3.12.*", (3, 13), False),
            ("!=3.12.*", (3, 13), True),
            ("==3.12", (3, 12, 0), True),
            ("==3.12", (3, 12, 1), False),
            (">=3.12, <3.12.4", (3, 12), True),
            ("<3.12", (3, 12), False),
            ("<=3.12", (3, 12, 0), True),
            (">=3.10,!=3.11.*,<4", (3, 11), False),
            (">=3.10,!=3.11.*,<4", (3, 12), True),
            ("", (3, 12), True),
            ("~=3", (3, 12), False),  # ~= は 2 桁以上でないと誤り
            (">=3.12a", (3, 12), False),  # 読めない指定は受け付けない
        ]
        for spec, version, want in cases:
            with self.subTest(spec=spec, version=version):
                self.assertIs(ok(spec, version), want)

    def test_check_python_uses_pep440(self):
        self._pkg("a", "~=3.12.1")
        self.assertEqual(
            self.bs.check_python(self.tmp, [self.bs.Repo("a", python=True)], (3, 13))[:1],
            ["a: requires-python '~=3.12.1' が Python 3.13 を受け付けません"],
        )

    def test_consistent(self):
        self._pkg("a", ">=3.12")
        self._pkg("b", ">=3.10")
        self._pkg("c/sub", ">=3.11")
        repos = [
            self.bs.Repo("a", python=True),
            self.bs.Repo("b", python=True),
            self.bs.Repo("c", python=True, packages="sub"),
        ]
        self.assertEqual(self.bs.check_python(self.tmp, repos, (3, 12)), [])

    def test_minimum_lower_than_tools_is_error(self):
        self._pkg("a", ">=3.12")
        problems = self.bs.check_python(self.tmp, [self.bs.Repo("a", python=True)], (3, 11))
        self.assertEqual(len(problems), 2, problems)  # 3.11 を受け付けない + 最低版が下限と合わない
        self.assertIn("MIN_VERSION", problems[-1])

    def test_minimum_higher_than_needed_is_error(self):
        self._pkg("a", ">=3.10")
        problems = self.bs.check_python(self.tmp, [self.bs.Repo("a", python=True)], (3, 12))
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("3.10", problems[0])

    def test_missing_requires_python_and_upper_bound(self):
        self._pkg("a", None)
        self._pkg("b", ">=3.12,<3.12")
        problems = self.bs.check_python(
            self.tmp, [self.bs.Repo("a", python=True), self.bs.Repo("b", python=True)], (3, 12)
        )
        self.assertTrue(any("a: requires-python がありません" in p for p in problems), problems)
        self.assertTrue(any(p.startswith("b: ") and "受け付けません" in p for p in problems), problems)

    def test_cli_exit_code(self):
        self._pkg("devtools-common", ">=3.10")  # repos.yaml にある名前で置く
        self._pkg("office-review", ">=3.12")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.bs.main(["--root", str(self.tmp), "--only", "devtools-common,office-review", "check-python"])
        self.assertEqual(code, 0, out.getvalue())
        self._pkg("design-diff", ">=3.13")
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = self.bs.main(["--root", str(self.tmp), "--only", "design-diff,office-review", "check-python"])
        self.assertEqual(code, 1)
        self.assertIn("design-diff", err.getvalue())

    def test_real_checkouts_match(self):
        """兄弟に取得済みのリポジトリがあれば、実物の requires-python と一致するか（統合ジョブでも確かめる）."""
        root = ROOT.parent
        _, repos = self.bs.load_manifest()
        present = [r for r in repos if r.python and r.package_dirs(root)]
        if not present:
            self.skipTest("兄弟のリポジトリが未取得（統合ジョブの bootstrap.py check-python で確かめる）")
        self.assertEqual(self.bs.check_python(root, present, python_version.MIN_VERSION), [])

    def test_docs_state_the_same_minimum(self):
        want = "{}.{} 以上".format(*python_version.MIN_VERSION)
        for rel in ("setup.sh", "scripts/setup.ps1", "scripts/install-prereqs.ps1", "README.md"):
            with self.subTest(rel=rel):
                text = read(rel)
                self.assertIn(want, text)
                self.assertNotRegex(text, r"3\.(9|10|11) 以上")


if __name__ == "__main__":
    unittest.main()
