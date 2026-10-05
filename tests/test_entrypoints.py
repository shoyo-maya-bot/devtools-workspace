"""Windows の入口（.cmd / .ps1）の形を確かめる.

.cmd は CRLF でないと、cmd.exe が行の区切りを読み違えてラベルや if が壊れることがある。
.gitattributes で CRLF にしているが、設定が消えたり別の手段で LF に変わったりしても気づけるようにする。
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def tracked(*patterns: str) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", *patterns],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    return [ROOT / p for p in out.decode("utf-8").split("\0") if p]


class LineEndingTest(unittest.TestCase):
    def test_windows_scripts_are_crlf(self):
        files = tracked("*.cmd", "*.bat", "*.ps1")
        self.assertTrue(any(f.name == "setup.cmd" for f in files))
        for f in files:
            data = f.read_bytes()
            self.assertIn(b"\r\n", data, f"{f.name}: CRLF がありません")
            self.assertIsNone(re.search(rb"(?<!\r)\n", data), f"{f.name}: LF だけの行があります")

    def test_gitattributes_keeps_crlf(self):
        attrs = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        for pattern in ("*.cmd", "*.bat", "*.ps1"):
            self.assertRegex(attrs, rf"(?m)^{re.escape(pattern)}\s.*eol=crlf", pattern)

    def test_cmd_is_cp932_without_bom(self):
        # cmd.exe は BOM を読めず、日本語の Windows は cp932 で解釈する（.gitattributes の working-tree-encoding）
        for f in tracked("*.cmd"):
            data = f.read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"), f"{f.name}: BOM 付きです")
            data.decode("cp932")

    def test_ps1_has_bom(self):
        # Windows PowerShell 5.1 は BOM のない UTF-8 を ANSI として読み、日本語が化ける
        for f in tracked("*.ps1"):
            self.assertTrue(f.read_bytes().startswith(b"\xef\xbb\xbf"), f"{f.name}: BOM がありません")


class NonInteractiveTest(unittest.TestCase):
    """CI でも止まらずに終わり、終了コードを返すこと（ダブルクリックのときは従来どおり pause する）."""

    def test_cmd_skips_pause_in_ci_and_returns_exit_code(self):
        for name in ("setup.cmd", "install-prereqs.cmd"):
            text = (ROOT / name).read_bytes().decode("cp932")
            self.assertIn("if not defined CI if not defined DEVTOOLS_NO_PAUSE pause", text, name)
            self.assertIn("exit /b %RC%", text, name)
            self.assertNotRegex(text, r"(?mi)^pause\s*$", name)

    def test_prereqs_has_dry_run(self):
        text = (ROOT / "scripts" / "install-prereqs.ps1").read_text(encoding="utf-8-sig")
        self.assertRegex(text, r"param\(.*\[switch\]\$DryRun")
        # winget・wsl・code の実行の前に DryRun で抜けていること
        self.assertIn('if ($DryRun) { Write-Host ("[dry-run] winget "', text)


class WorkflowHardeningTest(unittest.TestCase):
    """Actions はコミット SHA で固定し、checkout は認証情報を残さない."""

    def test_actions_are_pinned_to_sha(self):
        for f in tracked(".github/workflows/*.yml"):
            for m in re.finditer(r"(?m)^\s*-?\s*uses:\s*(\S+)(.*)$", f.read_text(encoding="utf-8")):
                ref, rest = m.group(1), m.group(2)
                if ref.startswith("./") or ref.startswith("shoyo-maya-bot/"):
                    continue
                self.assertRegex(ref, r"@[0-9a-f]{40}$", f"{f.name}: {ref}")
                self.assertRegex(rest, r"#\s*v\d", f"{f.name}: {ref} に版のコメントがありません")

    def test_checkout_does_not_persist_credentials(self):
        for f in tracked(".github/workflows/*.yml"):
            text = f.read_text(encoding="utf-8")
            n = len(re.findall(r"uses:\s*actions/checkout@", text))
            self.assertEqual(n, len(re.findall(r"persist-credentials:\s*false", text)), f.name)


if __name__ == "__main__":
    unittest.main()
