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

# 呼ばれた引数を記録する偽の doc2md / fieldcheck（fieldcheck は指摘ありの 1 を返す）
STUB = """#!/usr/bin/env bash
echo "$(basename "$0") $*" >> "$STUB_LOG"
if [ "$(basename "$0")" = fieldcheck ]; then exit 1; fi
exit 0
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
        for tool in ("bash", "dirname", "basename", "cat", "mkdir"):
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


class PowerShellPipelineTest(unittest.TestCase):
    def test_ps1_looks_in_sibling_venv(self):
        text = PS1.read_text(encoding="utf-8-sig")
        self.assertIn('Join-Path $Root ".venv"', text)
        self.assertIn('"Scripts\\$Name.exe"', text)
        self.assertIn("exit 2", text)
        self.assertIn("& $Doc2md", text)
        self.assertIn("& $Fieldcheck validate", text)


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
