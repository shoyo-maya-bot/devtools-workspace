"""examples/ のパイプライン例: 有効化しなくても ../.venv のツールを見つけるか、無ければ分かりやすく止まるか."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - テストで bash を呼ぶ
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "examples" / "expense-pipeline.sh"
PS1 = ROOT / "examples" / "expense-pipeline.ps1"
HAVE_BASH = os.name != "nt" and shutil.which("bash") is not None

# 呼ばれた引数を記録する偽の doc2md / fieldcheck.
# 終了コードは D2M_RC（既定 0）・FC_RC（既定 1 = 指摘あり）、D2M_MD を付けると doc2md がその Markdown を書く
STUB = """#!/usr/bin/env bash
echo "$(basename "$0") $*" >> "$STUB_LOG"
if [ "$(basename "$0")" = fieldcheck ]; then exit "${FC_RC:-1}"; fi
if [ -n "${D2M_MD:-}" ]; then mkdir -p "$(dirname "$D2M_MD")"; echo "# x" > "$D2M_MD"; fi
exit "${D2M_RC:-0}"
"""


@unittest.skipUnless(HAVE_BASH, "bash が無い（Windows の bash は WSL のことがあるので使わない）")
class PipelineScriptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        # <tmp>/devtools-workspace/examples/expense-pipeline.sh と兄弟フォルダを並べる
        ws = self.tmp / "devtools-workspace" / "examples"
        ws.mkdir(parents=True)
        shutil.copy(SCRIPT, ws / SCRIPT.name)
        self.script = ws / SCRIPT.name
        for rel in ("doc-to-markdown/samples/expense-list.xlsx", "office-review/fieldcheck/samples/rules.yaml"):
            f = self.tmp / rel
            f.parent.mkdir(parents=True)
            f.write_text("x", encoding="utf-8")
        self.log = self.tmp / "calls.log"
        # PATH には bash の基本コマンドだけを置き、doc2md・fieldcheck は無い状態にする
        self.bin = self.tmp / "sysbin"
        self.bin.mkdir()
        for tool in ("bash", "dirname", "basename", "cat", "mkdir", "rm"):
            found = shutil.which(tool)
            if found:
                (self.bin / tool).symlink_to(found)

    def _stub(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        for name in ("doc2md", "fieldcheck"):
            p = folder / name
            p.write_text(STUB, encoding="utf-8")
            p.chmod(0o755)

    def _run(self, **env: str) -> subprocess.CompletedProcess[str]:
        base = {"PATH": str(self.bin), "STUB_LOG": str(self.log), "OUT": str(self.tmp / "out"), "LANG": "C.UTF-8"}
        return subprocess.run(  # nosec B603
            [str(self.bin / "bash"), str(self.script)],
            cwd=self.tmp,
            env={**base, **env},
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_uses_sibling_venv_without_activation(self):
        self._stub(self.tmp / ".venv" / "bin")
        p = self._run()
        self.assertEqual(p.returncode, 1, p.stderr)  # fieldcheck の指摘ありがそのまま返る
        calls = self.log.read_text(encoding="utf-8").splitlines()
        self.assertTrue(calls[0].startswith("doc2md "), calls)
        self.assertTrue(all(c.startswith(("doc2md ", "fieldcheck validate ")) for c in calls), calls)

    def test_venv_can_be_given(self):
        self._stub(self.tmp / "other-venv" / "bin")
        p = self._run(VENV=str(self.tmp / "other-venv"))
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertTrue(self.log.exists())

    def test_missing_tools_stop_with_guidance(self):
        p = self._run()
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn("doc2md fieldcheck が見つかりません", p.stderr)
        self.assertIn("setup.sh", p.stderr)
        self.assertFalse(self.log.exists())

    def test_tools_on_path_still_work(self):
        self._stub(self.bin)
        p = self._run()
        self.assertEqual(p.returncode, 1, p.stderr)

    # 終了コードで、どの段で何が起きたかを区別する（doc2md --strict の警告を fieldcheck の指摘と混ぜない）
    def _calls(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def _md(self) -> Path:
        return self.tmp / "out" / "expense-list.md"

    def test_conversion_warning_still_runs_fieldcheck_and_returns_5_with_findings(self):
        self._stub(self.tmp / ".venv" / "bin")
        p = self._run(D2M_RC="1", D2M_MD=str(self._md()))
        self.assertEqual(p.returncode, 5, p.stderr)
        self.assertIn("変換の警告があります", p.stderr)
        self.assertEqual(sum(c.startswith("fieldcheck validate ") for c in self._calls()), 2)

    def test_conversion_warning_without_findings_returns_4(self):
        self._stub(self.tmp / ".venv" / "bin")
        p = self._run(D2M_RC="1", D2M_MD=str(self._md()), FC_RC="0")
        self.assertEqual(p.returncode, 4, p.stderr)

    def test_no_warning_no_findings_returns_0(self):
        self._stub(self.tmp / ".venv" / "bin")
        p = self._run(FC_RC="0")
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_conversion_failure_without_markdown_returns_3_and_skips_fieldcheck(self):
        self._stub(self.tmp / ".venv" / "bin")
        p = self._run(D2M_RC="1")
        self.assertEqual(p.returncode, 3, p.stderr)
        self.assertIn("変換できませんでした", p.stderr)
        self.assertFalse(any(c.startswith("fieldcheck") for c in self._calls()))

    def test_stale_markdown_from_previous_run_is_not_validated(self):
        self._md().parent.mkdir(parents=True)
        self._md().write_text("# 前回の出力", encoding="utf-8")
        self._stub(self.tmp / ".venv" / "bin")
        p = self._run(D2M_RC="1")
        self.assertEqual(p.returncode, 3, p.stderr)
        self.assertFalse(self._md().exists())
        self.assertFalse(any(c.startswith("fieldcheck") for c in self._calls()))

    def test_doc2md_input_error_returns_2_and_runtime_error_returns_3(self):
        self._stub(self.tmp / ".venv" / "bin")
        for d2m, want in (("2", 2), ("3", 3), ("9", 3)):
            with self.subTest(doc2md=d2m):
                self.log.unlink(missing_ok=True)
                p = self._run(D2M_RC=d2m, D2M_MD=str(self._md()))
                self.assertEqual(p.returncode, want, p.stderr)
                self.assertFalse(any(c.startswith("fieldcheck") for c in self._calls()))

    def test_fieldcheck_errors_are_not_reported_as_findings(self):
        self._stub(self.tmp / ".venv" / "bin")
        for fc, want in (("2", 2), ("3", 3)):
            for d2m in ("0", "1"):
                with self.subTest(fieldcheck=fc, doc2md=d2m):
                    p = self._run(FC_RC=fc, D2M_RC=d2m, D2M_MD=str(self._md()))
                    self.assertEqual(p.returncode, want, p.stderr)


class PowerShellPipelineTest(unittest.TestCase):
    def test_ps1_looks_in_sibling_venv(self):
        text = PS1.read_text(encoding="utf-8-sig")
        self.assertIn('Join-Path $Root ".venv"', text)
        self.assertIn('"Scripts\\$Name.exe"', text)
        self.assertIn("exit 2", text)
        self.assertIn("& $Doc2md", text)
        self.assertIn("& $Fieldcheck validate", text)
        # 終了コードは .sh と同じ（変換の警告は 4・5、前回の Markdown は消してから変換）
        self.assertIn("exit (4 + $rc)", text)
        self.assertIn("Remove-Item -LiteralPath $Md", text)
        self.assertIn("exit 3", text)

    def test_exit_codes_are_documented_the_same_in_both_scripts_and_readme(self):
        sh = SCRIPT.read_text(encoding="utf-8")
        ps1 = PS1.read_text(encoding="utf-8-sig")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme = readme.split("### パイプライン例", 1)[1].split("\n### ", 1)[0]
        for code in ("4 doc2md --strict の変換の警告あり", "5 "):
            self.assertIn(code, sh)
        self.assertIn("4 doc2md --strict の変換の警告あり・指摘なし", ps1)
        for code in ("`4`", "`5`", "`3`", "`2`"):
            self.assertIn(code, readme)


class ReadmeAndCiTest(unittest.TestCase):
    def test_readme_states_setup_prerequisite(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        section = readme.split("### パイプライン例", 1)[1].split("\n### ", 1)[0]
        self.assertIn("../.venv", section)
        self.assertIn("setup", section)

    def test_ci_runs_examples_after_setup(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("./examples/expense-pipeline.sh", ci)
        self.assertIn(".\\examples\\expense-pipeline.ps1", ci)
        self.assertLess(ci.index("./setup.sh --manifest"), ci.index("./examples/expense-pipeline.sh"))


if __name__ == "__main__":
    unittest.main()
