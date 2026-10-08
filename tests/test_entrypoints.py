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


def code_lines(text: str) -> list[str]:
    """YAML のコメント行を除いた行."""
    return [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]


class WorkflowReproducibilityTest(unittest.TestCase):
    """CI の結果が他のリポジトリやツールの新しい版で変わらないこと、シークレットを広く渡さないこと."""

    TOOLS = ("ruff", "bandit", "pip-audit", "build", "pip-tools", "uv")

    def test_tool_versions_are_pinned(self):
        for f in tracked(".github/workflows/*.yml"):
            for line in code_lines(f.read_text(encoding="utf-8")):
                m = re.search(r"pip install (.*)$", line)
                if not m:
                    continue
                for tok in re.findall(r'"([^"]+)"|(\S+)', m.group(1)):
                    spec = (tok[0] or tok[1]).split("#")[0]
                    name = re.split(r"[=<>!~\[]", spec, maxsplit=1)[0].lower()
                    if name in self.TOOLS:
                        with self.subTest(file=f.name, spec=spec):
                            self.assertRegex(spec, r"==(\d|\$\{)", f"{f.name}: {spec} の版を固定してください")

    def test_integration_jobs_use_pinned_manifest(self):
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        runs = [ln for ln in code_lines(text) if re.search(r"setup\.(cmd|sh)\b", ln) and "run:" in ln]
        self.assertGreaterEqual(len(runs), 4)
        for ln in runs:
            self.assertRegex(ln, r"(-Manifest|--manifest) \.github[\\/]ci-repos\.yaml", ln)

    def test_setup_sh_runs_in_ci(self):
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("./setup.sh --manifest", text)
        self.assertIn("macos-latest", text)

    def test_no_secrets_inherit(self):
        # ワークフロー本体と、使い方の例（コメント・Markdown のコードブロック）の両方で、行として書いていないこと
        for f in tracked(".github/workflows/*.yml", "docs/*.md", "README.md"):
            for ln in f.read_text(encoding="utf-8").splitlines():
                if ln.strip().lstrip("#").strip() == "secrets: inherit":
                    self.fail(f"{f.name}: secrets: inherit を使わず、必要なシークレットだけを名前で渡す")
        ci = (ROOT / ".github" / "workflows" / "python-ci.yml").read_text(encoding="utf-8")
        self.assertIn("DEPS_TOKEN: ${{ secrets.DEPS_TOKEN }}", ci)

    def test_token_is_not_written_to_git_config(self):
        for f in tracked(".github/workflows/*.yml"):
            text = "\n".join(code_lines(f.read_text(encoding="utf-8")))
            self.assertNotRegex(text, r"git config --global[^\n]*(TOKEN|token)", f.name)
            # DEPS_TOKEN はジョブ全体の env に置かず、使う手順の env にだけ置く
            self.assertNotRegex(text, r"(?m)^    env:\n(      \w+: .*\n)*      DEPS_TOKEN:", f.name)

    def test_python_ci_runs_windows_and_constraints(self):
        ci = (ROOT / ".github" / "workflows" / "python-ci.yml").read_text(encoding="utf-8")
        self.assertRegex(ci, r"run-windows:\n(\s+\w+: .*\n)*?\s+default: true")
        self.assertRegex(ci, r"if: inputs\.run-windows\n\s+runs-on: windows-latest")
        self.assertEqual(ci.count("c=(-c constraints.txt)"), 3)  # test・test-windows・security


if __name__ == "__main__":
    unittest.main()
