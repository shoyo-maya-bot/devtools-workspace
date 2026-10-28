"""devtools 武具屋（armory/index.html）の品揃えが repos.yaml とずれていないかを確かめる。"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess  # nosec B404 - テストで node・bash・pwsh を呼ぶ
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import bootstrap  # noqa: E402

ARMORY = ROOT / "armory" / "index.html"


def armory_text() -> str:
    return ARMORY.read_text(encoding="utf-8")


def item_blocks() -> dict[str, str]:
    """ITEMS の 1 件ごとの JavaScript のテキスト（id → テキスト）."""
    blocks = re.split(r'^\{id:"', armory_text(), flags=re.M)[1:]
    return {b.split('"', 1)[0]: b for b in blocks}


class ArmoryTest(unittest.TestCase):
    def test_items_match_manifest(self):
        top, repos = bootstrap.load_manifest()
        items = re.findall(r'^\{id:"([^"]+)"', armory_text(), re.M)
        self.assertEqual(len(items), len(set(items)), "ITEMS に同じリポジトリが 2 回ある")
        self.assertEqual(
            sorted(items),
            sorted(r.name for r in repos),
            "repos.yaml と armory/index.html の ITEMS が合っていない",
        )

    def test_org_matches_manifest(self):
        top, _ = bootstrap.load_manifest()
        m = re.search(r'const ORG = "([^"]+)"', armory_text())
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), top["org"])

    def test_cli_names_match_manifest(self):
        """各道具の使い方に書いた CLI 名が repos.yaml の cli と同じか（手で写した使い方が古くなっていないか）."""
        _, repos = bootstrap.load_manifest()
        blocks = item_blocks()
        for r in repos:
            block = blocks[r.name]
            commands = re.findall(r'\["[^"]*","([^"]*)"\]', block)
            named = re.findall(r"CLI 名は ?([A-Za-z0-9_.-]+)", block)
            with self.subTest(repo=r.name):
                if r.cli:
                    self.assertTrue(
                        any(c == r.cli or c.startswith(r.cli + " ") for c in commands),
                        f"{r.name}: 装備スキルに CLI `{r.cli}` のコマンドがありません",
                    )
                    wrong = [n for n in named if n != r.cli]
                    self.assertEqual(wrong, [], f"{r.name}: CLI 名が repos.yaml の {r.cli} と違う")
                else:
                    self.assertEqual(named, [], f"{r.name}: repos.yaml に cli が無いのに CLI 名が書いてある")

    def test_sets_use_known_items(self):
        """おすすめセットの道具が ITEMS にあり、なり方を書いた称号が漏れなくあるか."""
        text = armory_text()
        items = set(re.findall(r'^\{id:"([^"]+)"', text, re.M))
        sets = re.search(r"^const SETS = \[\n(.*?)^\];", text, re.M | re.S)
        self.assertIsNotNone(sets)
        rows = re.findall(r'^ \["([^"]+)","[^"]+","[^"]+",\[([^\]]*)\]\]', sets.group(1), re.M)
        self.assertGreaterEqual(len(rows), 3)
        for name, ids in rows:
            with self.subTest(set=name):
                used = re.findall(r'"([^"]+)"', ids)
                self.assertTrue(used)
                self.assertEqual([u for u in used if u not in items], [], f"{name}: ITEMS に無い道具")
        jobs = re.search(r"^const JOBS = \[\n(.*?)^\];", text, re.M | re.S)
        self.assertIsNotNone(jobs)
        for line in jobs.group(1).splitlines():
            with self.subTest(job=line[:40]):
                self.assertRegex(line, r'"[^"]+","[^"]+"\],?$', "称号になり方（3 つ目）が無い")

    def test_every_item_has_skill(self):
        text = armory_text()
        blocks = re.split(r'^\{id:"', text, flags=re.M)[1:]
        for block in blocks:
            name = block.split('"', 1)[0]
            with self.subTest(item=name):
                self.assertIn("skill:{p:", block)
                self.assertRegex(block, r"steps:\[\s*\[")


def home_path_source() -> str:
    """armory/index.html の homePath 関数の JavaScript."""
    m = re.search(r"^function homePath\(raw,kind\)\{\n.*?^\}\n", armory_text(), re.M | re.S)
    if m is None:
        raise AssertionError("armory/index.html に homePath が見つかりません")
    return m.group(0)


def home_path_exprs(inputs: list[str], kind: str) -> list[str]:
    """homePath を node で実行し、入力ごとにマクロへ埋め込む式を返す."""
    call = f"{json.dumps(inputs)}.map(x=>homePath(x,{json.dumps(kind)}))"
    script = home_path_source() + f"process.stdout.write(JSON.stringify({call}))"
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", check=True)  # nosec B603 B607
    return json.loads(out.stdout)


HAVE_BASH = os.name != "nt" and shutil.which("bash") is not None

# シェルの記号を含む保存先（貼りつけた値がそのままフォルダ名になり、コマンドとして実行されないこと）
HOSTILE_DIRS = [
    "work/it's mine",
    "a'; touch PWNED; echo 'b",
    'x"; touch PWNED; echo "y',
    "$(touch PWNED)",
    "`touch PWNED`",
    "${HOME}/plain",
    "a\nb; touch PWNED",
    "line1\ntouch PWNED",
    "c:\\tmp\\x y",
]


@unittest.skipUnless(shutil.which("node"), "node が無い")
class HomePathQuotingTest(unittest.TestCase):
    """詠唱マクロの保存先（利用者が入力した文字列）を、シェルが解釈しない形で埋め込む."""

    def _run_bash(self, expr: str, cwd: str, home: str) -> str:
        script = f"base={expr}\nprintf '%s' \"$base\"\n"
        env = {**os.environ, "HOME": home}
        out = subprocess.run(["bash", "-c", script], cwd=cwd, env=env, capture_output=True, text=True, check=True)  # nosec B603 B607
        return out.stdout

    @unittest.skipUnless(HAVE_BASH, "bash が無い（Windows の bash は WSL のことがあるので使わない）")
    def test_bash_keeps_input_literal(self):
        exprs = home_path_exprs(HOSTILE_DIRS, "sh")
        for raw, expr in zip(HOSTILE_DIRS, exprs, strict=True):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as tmp:
                got = self._run_bash(expr, tmp, "/home/u")
                want = raw.replace("\n", "")  # 改行などの制御文字は取り除く
                self.assertEqual(got, want)
                self.assertFalse(Path(tmp, "PWNED").exists(), f"コマンドが実行された: {expr}")

    @unittest.skipUnless(HAVE_BASH, "bash が無い（Windows の bash は WSL のことがあるので使わない）")
    def test_bash_tilde_is_home(self):
        for raw, want in (
            ("", "/home/u/devtools"),
            ("~", "/home/u"),
            ("~/dev tools", "/home/u/dev tools"),
            ("~/it's", "/home/u/it's"),
            ("/opt/~x", "/opt/~x"),
        ):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as tmp:
                (expr,) = home_path_exprs([raw], "sh")
                self.assertEqual(self._run_bash(expr, tmp, "/home/u"), want)

    def test_powershell_expression_shape(self):
        """PowerShell 版は '…' の文字列（' と ‘ ’ ‚ ‛ は重ねる）で、$( や " がそのまま式にならない."""
        exprs = home_path_exprs([*HOSTILE_DIRS, "~/x", "it\u2019s"], "ps")
        for expr in exprs:
            with self.subTest(expr=expr):
                lit = expr.removeprefix("$HOME + ")
                self.assertRegex(lit, r"^'(?:[^'\u2018\u2019\u201a\u201b]|(['\u2018\u2019\u201a\u201b])\1)*'$")
        self.assertEqual(exprs[-2], "$HOME + '\\x'")
        self.assertEqual(exprs[-1], "'it\u2019\u2019s'")

    @unittest.skipUnless(shutil.which("pwsh"), "pwsh が無い")
    def test_powershell_keeps_input_literal(self):
        exprs = home_path_exprs(HOSTILE_DIRS, "ps")
        for raw, expr in zip(HOSTILE_DIRS, exprs, strict=True):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as tmp:
                script = f"$base = {expr}\n[Console]::Out.Write($base)\n"
                out = subprocess.run(  # nosec B603 B607
                    ["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=True,
                )
                self.assertEqual(out.stdout, raw.replace("\n", "").replace("/", "\\"))
                self.assertFalse(Path(tmp, "PWNED").exists(), f"コマンドが実行された: {expr}")

    def test_macro_uses_expression_without_extra_quotes(self):
        text = armory_text()
        self.assertIn('$base = ${homePath(dir,"ps")}\n', text)
        self.assertIn('base=${homePath(dir,"sh")}\n', text)


if __name__ == "__main__":
    unittest.main()
