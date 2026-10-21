"""再利用ワークフロー（python-ci.yml・python-release.yml）の振る舞い.

- DEPS_TOKEN は git 依存の取得（git clone）だけに使い、pip（第三者の sdist のビルドを含む）の環境には残さない
- リリースは python-ci.yml と同じ lint・test が通ったときだけ公開する
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404 - テストで bash を呼ぶ
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
CI = WORKFLOWS / "python-ci.yml"
RELEASE = WORKFLOWS / "python-release.yml"
HAVE_BASH = os.name != "nt" and shutil.which("bash") is not None


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def jobs(text: str) -> dict[str, str]:
    """`jobs:` の下のジョブ（名前 → そのジョブのテキスト）."""
    body = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"(?m)^  ([\w-]+):\n", body)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def install_scripts(text: str) -> list[str]:
    """名前が Install で始まる手順の run: | のスクリプト（インデントを外したもの）."""
    out = []
    step = re.compile(
        r"(?m)^      - name: Install(?!.*system).*\n"  # 手順の名前（Install system packages は除く）
        r"(?:        .*\n)*?        run: \|\n"  # env: など → run: |
        r"((?:          .*\n|\n)+)"  # スクリプト本体
    )
    for m in step.finditer(text):
        out.append(textwrap.dedent(m.group(1)))
    return out


# 呼ばれたときの引数と環境変数を記録する偽の git / pip
GIT_STUB = """#!/usr/bin/env bash
{ echo "git $*"; env | grep -E '^(GIT_CONFIG|DEPS_TOKEN)' | sort; echo ---; } >> "$CALL_LOG"
if [ "$1" = clone ]; then mkdir -p "${@: -1}"; fi
exit 0
"""
PIP_STUB = """#!/usr/bin/env bash
{ echo "pip $*"; env | sort; echo ---; } >> "$CALL_LOG"
exit 0
"""


@unittest.skipUnless(HAVE_BASH, "bash が無い（Windows の bash は WSL のことがあるので使わない）")
class DepsTokenIsolationTest(unittest.TestCase):
    TOKEN = "ghs_secretTOKEN123"  # nosec B105 - テスト用の偽の値

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for name, body in (("git", GIT_STUB), ("pip", PIP_STUB)):
            (self.bin / name).write_text(body, encoding="utf-8")
            (self.bin / name).chmod(0o755)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        (self.repo / "pyproject.toml").write_text(
            '[project]\nname = "x"\ndependencies = [\n'
            '  "devtools-common @ git+https://github.com/example-org/devtools-common@0123abc",\n'
            '  "requests>=2",\n]\n',
            encoding="utf-8",
        )
        (self.repo / "constraints.txt").write_text(
            "other-lib @ git+https://github.com/example-org/other-lib.git@4567def\nrequests==2.32.0\n",
            encoding="utf-8",
        )
        self.log = self.tmp / "calls.log"
        self.runner_temp = self.tmp / "runner-temp"
        self.runner_temp.mkdir()

    def _run(self, script: str, token: str) -> tuple[subprocess.CompletedProcess[str], str]:
        env = {
            "PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "CALL_LOG": str(self.log),
            "RUNNER_TEMP": str(self.runner_temp),
            "DEPS_TOKEN": token,
            "HOME": str(self.tmp),
        }
        # GitHub Actions の bash と同じ（-e -o pipefail）
        p = subprocess.run(  # nosec B603 B607
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
        )
        return p, self.log.read_text(encoding="utf-8") if self.log.exists() else ""

    def _pip_calls(self, log: str) -> list[str]:
        return [c for c in log.split("---\n") if c.startswith("pip ")]

    def test_every_install_step_keeps_token_out_of_pip(self):
        for wf in (CI, RELEASE):
            scripts = install_scripts(read(wf))
            self.assertGreaterEqual(len(scripts), 2, wf.name)
            for i, script in enumerate(scripts):
                with self.subTest(workflow=wf.name, step=i):
                    self.log.unlink(missing_ok=True)
                    shutil.rmtree(self.runner_temp / "git-deps", ignore_errors=True)
                    p, log = self._run(script, self.TOKEN)
                    self.assertEqual(p.returncode, 0, p.stderr)
                    pips = self._pip_calls(log)
                    self.assertEqual(len(pips), 1, log)
                    self.assertNotIn(self.TOKEN, pips[0], "pip の環境にトークンが残っています")
                    self.assertNotIn("DEPS_TOKEN=", pips[0])
                    # git 依存はトークン付きで写し、pip にはトークンなしの insteadOf で写しを読ませる
                    clones = [c for c in log.split("---\n") if c.startswith("git clone")]
                    self.assertEqual(len(clones), 2, log)
                    for c in clones:
                        self.assertIn(self.TOKEN, c)
                        self.assertIn("--mirror", c)
                    mirror = self.runner_temp / "git-deps"
                    self.assertIn(f"url.{mirror}/example-org/devtools-common.git.insteadOf", pips[0])
                    self.assertIn("=https://github.com/example-org/devtools-common.git\n", pips[0])
                    self.assertIn("=https://github.com/example-org/other-lib\n", pips[0])
                    self.assertIn("GIT_CONFIG_COUNT=4\n", pips[0])

    def test_without_token_installs_without_git_rewrites(self):
        script = install_scripts(read(CI))[0]
        p, log = self._run(script, "")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("git clone", log)
        (pip,) = self._pip_calls(log)
        self.assertNotIn("GIT_CONFIG_", pip)
        self.assertIn("-c constraints.txt", pip)

    def test_insteadof_maps_to_local_mirror_with_real_git(self):
        """実際の git で、書き換え後の URL がトークンを含まない手元の写しになることを確かめる."""
        git = shutil.which("git")
        if git is None:
            self.skipTest("git が無い")
        script = install_scripts(read(CI))[0]
        (self.bin / "git").unlink()
        stub = self.bin / "git"
        # clone だけは偽物（ネットワークに出ない）、それ以外は本物の git に任せる
        stub.write_text(
            "#!/usr/bin/env bash\n"
            'if [ "$1" = clone ]; then dest="${@: -1}"; mkdir -p "$dest"; '
            f'"{git}" init -q --bare "$dest"; exit 0; fi\n'
            f'exec "{git}" "$@"\n',
            encoding="utf-8",
        )
        stub.chmod(0o755)
        (self.bin / "pip").write_text(
            "#!/usr/bin/env bash\n"
            'git ls-remote --get-url https://github.com/example-org/devtools-common.git > "$CALL_LOG.url"\n'
            'env > "$CALL_LOG.env"\n',
            encoding="utf-8",
        )
        p, _ = self._run(script, self.TOKEN)
        self.assertEqual(p.returncode, 0, p.stderr)
        url = Path(f"{self.log}.url").read_text(encoding="utf-8").strip()
        self.assertEqual(url, str(self.runner_temp / "git-deps" / "example-org" / "devtools-common.git"))
        self.assertNotIn(self.TOKEN, Path(f"{self.log}.env").read_text(encoding="utf-8"))


class InstallScriptsAgreeTest(unittest.TestCase):
    def test_token_handling_is_same_in_every_install_step(self):
        blocks = []
        for wf in (CI, RELEASE):
            for s in install_scripts(read(wf)):
                blocks.append(s.split("c=(); if [ -f constraints.txt ]")[0])
        self.assertGreaterEqual(len(blocks), 5)
        self.assertEqual(len(set(blocks)), 1, "Install の手順のトークンの扱いがワークフローごとに違います")
        self.assertIn("unset DEPS_TOKEN", blocks[0])


class ReleaseRunsTestsFirstTest(unittest.TestCase):
    def setUp(self):
        self.release = jobs(read(RELEASE))
        self.ci = jobs(read(CI))

    def test_release_job_needs_tests(self):
        job = self.release["release"]
        self.assertIn("needs: [lint, test, test-windows]", job)
        self.assertIn("needs.lint.result == 'success'", job)
        self.assertIn("needs.test.result == 'success'", job)
        self.assertIn("needs.test-windows.result == 'success'", job)

    def test_test_jobs_are_same_as_python_ci(self):
        for name in ("lint", "test", "test-windows"):
            with self.subTest(job=name):
                self.assertIn(name, self.release)
                self.assertEqual(self.release[name].strip(), self.ci[name].strip())

    def test_inputs_have_same_defaults_as_python_ci(self):
        ci, rel = read(CI), read(RELEASE)
        for name in ("python-versions", "extra-apt-packages", "run-windows", "windows-python-version"):
            pattern = rf"\n      {re.escape(name)}:\n((?:        .*\n)+)"
            with self.subTest(input=name):
                a, b = re.search(pattern, ci), re.search(pattern, rel)
                self.assertIsNotNone(b, f"python-release.yml に inputs.{name} がありません")
                self.assertEqual(a.group(1), b.group(1))

    def test_only_release_job_can_write(self):
        text = read(RELEASE)
        self.assertRegex(text, r"(?m)^permissions:\n  contents: read$")
        self.assertIn("    permissions:\n      contents: write\n", self.release["release"])
        for name in ("lint", "test", "test-windows"):
            self.assertNotIn("contents: write", self.release[name])


class LatestMainsWorkflowTest(unittest.TestCase):
    """latest-mains.yml: 週 1 回、各 main の最新どうし（repos.yaml）で setup を試し、落ちたら Issue を起こす."""

    def setUp(self):
        self.text = read(WORKFLOWS / "latest-mains.yml")
        self.jobs = jobs(self.text)

    def test_runs_weekly_and_by_hand(self):
        self.assertRegex(self.text, r'(?m)^  schedule:\n    - cron: "\d+ \d+ \* \* [0-6]"')
        self.assertIn("\n  workflow_dispatch:\n", self.text)

    def test_uses_latest_mains_not_pinned_manifest(self):
        code = "\n".join(ln for ln in self.text.splitlines() if not ln.lstrip().startswith("#"))
        # SHA に固定したマニフェスト（ci-repos.yaml）を使わない（repos.yaml の既定）
        self.assertNotRegex(code, r"--manifest|-Manifest")
        self.assertIn("./setup.sh --only", self.jobs["setup-sh"])
        self.assertIn("call setup.cmd -Only", self.jobs["windows"])
        for job in ("setup-sh", "windows"):
            with self.subTest(job=job):
                self.assertIn("check-pins", self.jobs[job])
                self.assertIn("check-python", self.jobs[job])
                self.assertIn("expense-pipeline", self.jobs[job])
                self.assertIn("README_FACTS_REQUIRE_CHECKOUTS", self.jobs[job])
                self.assertIn("unittest tests.test_bootstrap.ReadmeFactsTest", self.jobs[job])

    def test_ci_integration_jobs_check_readme_facts_after_setup(self):
        """第 7 回: README のツールごとの requires-python の一覧は、兄弟のリポジトリがある統合ジョブで確かめる
        （単体テストの段では未取得で飛ぶため、setup のあとに飛ばさない設定で流す）."""
        ci = jobs(read(WORKFLOWS / "ci.yml"))
        for job in ("setup-sh", "windows"):
            with self.subTest(job=job):
                body = ci[job]
                self.assertIn("README_FACTS_REQUIRE_CHECKOUTS", body)
                self.assertLess(body.index("setup."), body.index("unittest tests.test_bootstrap.ReadmeFactsTest"))

    def test_smoke_lists_match_ci(self):
        ci = read(WORKFLOWS / "ci.yml")
        for key in ("SMOKE_CLIS", "SMOKE_IMPORTS"):
            with self.subTest(key=key):
                want = re.search(rf"(?m)^  {key}: (.+)$", ci).group(1)
                self.assertIn(f"  {key}: {want}\n", self.text)

    def test_python_repo_list_matches_manifest(self):
        import sys

        sys.path.insert(0, str(ROOT / "scripts"))
        import bootstrap

        code = re.search(r'(?m)^  LIST_PYTHON_REPOS: "(.+)"$', self.text).group(1)
        p = subprocess.run(  # nosec B603
            [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True
        )
        _, repos = bootstrap.load_manifest()
        self.assertEqual(p.stdout.strip().split(","), [r.name for r in repos if r.python])

    def test_failure_opens_issue_with_least_privilege(self):
        self.assertRegex(self.text, r"(?m)^permissions:\n  contents: read\n")
        report = self.jobs["report"]
        self.assertIn("if: failure()", report)
        self.assertIn("needs: [setup-sh, windows]", report)
        self.assertIn("issues: write", report)
        self.assertEqual(self.text.count("issues: write"), 1)
        self.assertIn('gh api "repos/$GH_REPO/issues"', report)
        self.assertIn("/comments", report)  # 開いている同じ題の Issue があればコメントを足す


if __name__ == "__main__":
    unittest.main()
