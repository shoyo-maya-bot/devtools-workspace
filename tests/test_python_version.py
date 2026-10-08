"""必要な Python の版の確認が 1 か所（scripts/python_version.py）にまとまっていて、入口がすべてそれを使うことを確かめる.

採点で見つかった問題: install-prereqs.ps1 は py があるだけで「OK」にし、setup.sh は版を確かめずに python3 を呼んでいた。
bootstrap.py は先頭で tomllib（3.11+）を import するため、3.10 以下（macOS 標準の 3.9）では
トレースバックで止まっていた。
"""

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

import python_version  # noqa: E402


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig")


class PythonVersionTest(unittest.TestCase):
    def test_min_version(self):
        self.assertEqual(python_version.MIN_VERSION, (3, 11))

    def test_problem(self):
        self.assertIsNone(python_version.problem((3, 11, 0)))
        self.assertIsNone(python_version.problem((3, 12, 3)))
        msg = python_version.problem((3, 9, 6))
        self.assertIn("3.11 以上が必要", msg)
        self.assertIn("3.9.6", msg)
        self.assertIsNotNone(python_version.problem((3, 10, 14)))

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
        self.assertIn("3.11 以上が必要", p.stderr)
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
        """3.11 以上の Python が無いときは、理由を出して 1 で終わる（PATH から Python を外して確かめる）."""
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
                "#!/bin/sh\necho 'Python 3.11 以上が必要です（今の Python は 3.9.6: fake）。' >&2\nexit 1\n",
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
        self.assertIn("Python 3.11 以上が見つかりません", p.stderr)
        self.assertIn("3.9.6", p.stderr)


if __name__ == "__main__":
    unittest.main()
