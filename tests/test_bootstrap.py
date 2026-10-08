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

    def test_ci_manifest_pins_shas_and_matches_repos_yaml(self):
        """統合 CI が取り出す版（.github/ci-repos.yaml）は SHA で固定し、項目は repos.yaml と同じにする."""
        top, repos = bootstrap.load_manifest()
        ci_top, ci_repos = bootstrap.load_manifest(ROOT / ".github" / "ci-repos.yaml")
        self.assertEqual((ci_top["org"], ci_top["host"]), (top["org"], top["host"]))
        by_name = {r.name: r for r in repos}
        self.assertTrue(ci_repos)
        for r in ci_repos:
            with self.subTest(repo=r.name):
                self.assertIn(r.name, by_name)
                m = by_name[r.name]
                self.assertEqual((r.role, r.python, r.cli, r.packages), (m.role, m.python, m.cli, m.packages))
                self.assertRegex(r.ref, r"^[0-9a-f]{40}$", "ref はコミット SHA（40 桁）で固定する")

    def test_ci_manifest_has_every_python_repo(self):
        """全 Python ツールの一括インストールを CI で通すため、python: true のリポジトリはすべて入れる."""
        _, repos = bootstrap.load_manifest()
        _, ci_repos = bootstrap.load_manifest(ROOT / ".github" / "ci-repos.yaml")
        want = {r.name for r in repos if r.python}
        self.assertEqual({r.name for r in ci_repos if r.python}, want)
        for name in ("agent-lab", "review-platform", "ai-coding", "slack-agenda-bot"):
            self.assertIn(name, want)  # サブフォルダ・アプリ・基盤の Python 部分も入れる

    def test_ci_installs_all_tools_without_only(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("call setup.cmd -Manifest .github\\ci-repos.yaml\n", ci)
        self.assertIn("./setup.sh --manifest .github/ci-repos.yaml\n", ci)
        self.assertNotIn("--only devtools-common,doc-to-markdown", ci)
        self.assertNotIn("-Only devtools-common,doc-to-markdown", ci)
        self.assertEqual(ci.count("check-python"), 2)  # windows と setup-sh

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

    def _repos(self):
        return [
            bootstrap.Repo("devtools-common", python=True),
            bootstrap.Repo("tool-a", python=True),
            bootstrap.Repo("not-cloned", python=True),
        ]

    def test_default_keeps_pinned_common(self):
        """既定は各ツールの固定依存をそのまま pip に解決させ、ローカルの devtools-common で置き換えない."""
        plan = bootstrap.install_plan(self.tmp, self._repos())
        self.assertEqual(plan, [["install", "-e", str(self.tmp / "tool-a")]])
        flat = [a for p in plan for a in p]
        self.assertNotIn("--no-deps", flat)  # 依存（固定した devtools-common を含む）を解決する
        self.assertFalse(any(str(self.tmp / "devtools-common") in a for a in flat))  # ローカル版は入れない

    def test_default_without_tools_installs_common_alone(self):
        plan = bootstrap.install_plan(self.tmp, [bootstrap.Repo("devtools-common", python=True)])
        self.assertEqual(plan, [["install", "-e", str(self.tmp / "devtools-common")]])

    def test_dev_local_common_replaces_git_dependency(self):
        plan = bootstrap.install_plan(self.tmp, self._repos(), dev=True)
        self.assertEqual(plan[0], ["install", "-e", f"{self.tmp / 'devtools-common'}[dev]"])
        self.assertEqual(plan[1], ["install", "openpyxl>=3", "pytest>=8"])
        self.assertEqual(plan[2], ["install", "--no-deps", "-e", str(self.tmp / "tool-a")])
        self.assertFalse(any("git+" in " ".join(p) for p in plan))

    def test_is_common(self):
        self.assertTrue(bootstrap._is_common("devtools-common @ git+https://x@abc"))
        self.assertTrue(bootstrap._is_common("devtools_common>=0.1"))
        self.assertFalse(bootstrap._is_common("devtools-common-extra>=1"))

    def test_dry_run_modes(self):
        shutil.copytree(self.tmp / "tool-a", self.tmp / "doc-to-markdown")  # repos.yaml にあるツール名で置く
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(bootstrap.main(["--root", str(self.tmp), "install", "--no-venv", "--dry-run"]), 0)
        # main は --root を resolve する（Windows の一時フォルダは短い名前のことがある）
        self.assertIn(f"install -e {self.tmp.resolve() / 'doc-to-markdown'}", out.getvalue())
        self.assertNotIn("--no-deps", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(bootstrap.main(["--root", str(self.tmp), "install", "--no-venv", "--dry-run", "--dev"]), 0)
        self.assertIn("--no-deps", out.getvalue())

    def test_list_and_dry_run(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(bootstrap.main(["list"]), 0)
            self.assertEqual(bootstrap.main(["--root", str(self.tmp), "install", "--dry-run"]), 0)
        self.assertIn("| doc-to-markdown | tool | `doc2md` |", out.getvalue())
        self.assertIn("| office-review | tool | `harness` |", out.getvalue())

    def test_subfolder_packages_and_url_pinned_local_package(self):
        """サブフォルダのパッケージ（agent-lab の auto-review・mcp-server など）も入れる.

        ほかのツールが URL で固定しているもの（review-platform → auto-review）は手元の checkout を入れない
        （同じ名前を 2 か所から入れると pip が衝突で止まる）。--dev ではローカルで置き換える。
        """
        for rel, name, deps in (
            ("lab/auto-review", "auto-review", '["devtools-common @ git+https://x/devtools-common@abc"]'),
            ("lab/mcp-server", "devtools-mcp", '["mcp>=2,<3"]'),
            ("platform", "platform", '["auto-review @ git+https://x/lab@abc#subdirectory=auto-review", "httpx>=0.27"]'),
        ):
            d = self.tmp / rel
            d.mkdir(parents=True)
            (d / "pyproject.toml").write_text(f'[project]\nname = "{name}"\ndependencies = {deps}\n', encoding="utf-8")
        repos = [
            *self._repos(),
            bootstrap.Repo("lab", python=True, packages="auto-review, mcp-server"),
            bootstrap.Repo("platform", python=True),
        ]
        notes: list[str] = []
        plan = bootstrap.install_plan(self.tmp, repos, notes=notes)
        want = ["tool-a", "lab/mcp-server", "platform"]
        self.assertEqual(plan, [["install", *[a for w in want for a in ("-e", str(self.tmp / w))]]])
        self.assertTrue(any(n.startswith("auto-review: ほかのツールが固定した版を入れる") for n in notes), notes)

        dev = bootstrap.install_plan(self.tmp, repos, dev=True)
        flat = [" ".join(p) for p in dev]
        self.assertIn(f"install --no-deps -e {self.tmp / 'lab/auto-review'}", flat)
        self.assertFalse(any("git+" in f for f in flat))  # ローカルの checkout で置き換える
        self.assertIn("httpx>=0.27", dev[1])

    def test_package_dirs(self):
        self.assertEqual(bootstrap.Repo("tool-a").package_dirs(self.tmp), [self.tmp / "tool-a"])
        self.assertEqual(bootstrap.Repo("tool-a", packages="nope").package_dirs(self.tmp), [])
        self.assertEqual(bootstrap.Repo("not-cloned").package_dirs(self.tmp), [])

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


class RefTest(unittest.TestCase):
    """repos.yaml の ref（ブランチ・タグ・SHA）を clone / pull で取り出す."""

    def _git(self, *args, cwd):
        import subprocess

        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()

    def test_manifest_ref_and_pull_to_ref(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        manifest = tmp / "repos.yaml"
        manifest.write_text("org: o\nrepos:\n  - name: a\n    ref: v1\n", encoding="utf-8")
        self.assertEqual(bootstrap.load_manifest(manifest)[1][0].ref, "v1")

        ident = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
        src = tmp / "src"
        src.mkdir()
        self._git("init", "-q", "-b", "main", cwd=src)
        (src / "f.txt").write_text("1\n", encoding="utf-8")
        self._git("add", ".", cwd=src)
        self._git(*ident, "commit", "-q", "-m", "1", cwd=src)
        self._git("tag", "v1", cwd=src)
        self._git("clone", "-q", str(src), str(tmp / "ws" / "a"), cwd=tmp)
        (src / "f.txt").write_text("2\n", encoding="utf-8")
        self._git(*ident, "commit", "-q", "-am", "2", cwd=src)
        self._git("tag", "v2", cwd=src)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(bootstrap.cmd_pull(tmp / "ws", [bootstrap.Repo(name="a", ref="v2")]), 0)
        self.assertEqual((tmp / "ws" / "a" / "f.txt").read_text(encoding="utf-8"), "2\n")
        self.assertIn("pull   a: v2", out.getvalue())


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


class ManifestCommentTest(unittest.TestCase):
    """repos.yaml の行末コメントは引用符の外だけを除く。読めない形は黙って読み飛ばさず誤りにする."""

    def _load(self, text: str):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        p = tmp / "repos.yaml"
        p.write_text(text, encoding="utf-8")
        return bootstrap.load_manifest(p)

    def test_hash_inside_quotes_is_kept(self):
        top, repos = self._load(
            'org: "my # org"  # 組織\n'
            "repos:\n"
            "  - name: a   # 名前\n"
            '    description: "C# と F# の # ツール" # 説明\n'
            "    cli: 'x #1'\n"
            "    ref: v1 # タグ\n"
        )
        self.assertEqual(top["org"], "my # org")
        self.assertEqual(repos[0].name, "a")
        self.assertEqual(repos[0].description, "C# と F# の # ツール")
        self.assertEqual(repos[0].cli, "x #1")
        self.assertEqual(repos[0].ref, "v1")

    def test_hash_without_space_is_value(self):
        _, repos = self._load("repos:\n  - name: a\n    description: C#で書いた\n")
        self.assertEqual(repos[0].description, "C#で書いた")

    def test_unreadable_forms_are_errors(self):
        cases = {
            '  - name: a\n    description: "閉じていない # x\n': "閉じていません",
            '  - name: a\n    description: "a" b\n': "余計な文字",
            "  - name: a\n    descripton: typo\n": "知らない項目",
            "  - name: a\n    just text\n": "読めない行",
            "  - name: a\n  - name: a\n": "2 回",
            "  - role: tool\n": "name がありません",
            "  - name: a\n    python: yes\n": "true / false",
        }
        for body, msg in cases.items():
            with self.subTest(body=body), self.assertRaises(bootstrap.ManifestError) as cm:
                self._load("repos:\n" + body)
            self.assertIn(msg, str(cm.exception))
            self.assertRegex(str(cm.exception), r"repos\.yaml:\d+: ")

    def test_main_reports_manifest_error_as_usage_error(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        p = tmp / "m.yaml"
        p.write_text('repos:\n  - name: "a\n', encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(bootstrap.main(["--manifest", str(p), "list"]), 2)
        self.assertIn("マニフェストを読めません", err.getvalue())
        self.assertIn("m.yaml:2", err.getvalue())

    def test_real_manifests_still_parse(self):
        self.assertTrue(bootstrap.load_manifest()[1])
        self.assertTrue(bootstrap.load_manifest(ROOT / ".github" / "ci-repos.yaml")[1])


class CheckPinsTest(unittest.TestCase):
    """一括インストールの前に、各ツールの devtools-common などの固定 SHA の食い違いを見つける."""

    COMMON_URL = "git+https://github.com/o/devtools-common.git"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _pkg(self, rel: str, name: str, deps: list[str], optional: dict | None = None):
        d = self.tmp / rel
        d.mkdir(parents=True, exist_ok=True)
        text = f'[project]\nname = "{name}"\ndependencies = {deps!r}\n'.replace("'", '"')
        if optional:
            text += "[project.optional-dependencies]\n" + "".join(
                f"{k} = {v!r}\n".replace("'", '"') for k, v in optional.items()
            )
        (d / "pyproject.toml").write_text(text, encoding="utf-8")

    def test_url_pin(self):
        self.assertEqual(
            bootstrap.url_pin(f"devtools-common[excel] @ {self.COMMON_URL}@abc ; python_version>='3.12'"),
            ("devtools-common", "git+https://github.com/o/devtools-common", "abc"),
        )
        self.assertEqual(
            bootstrap.url_pin("auto-review @ git+https://h/o/lab.git@def#subdirectory=auto-review"),
            ("auto-review", "git+https://h/o/lab", "def"),
        )
        self.assertIsNone(bootstrap.url_pin("PyYAML>=6"))

    def test_same_pins_are_ok(self):
        self._pkg("tool-a", "tool-a", [f"devtools-common @ {self.COMMON_URL}@aaa", "PyYAML>=6"])
        self._pkg("tool-b", "tool-b", [f"devtools-common[excel] @ {self.COMMON_URL}@aaa"])
        repos = [bootstrap.Repo("tool-a", python=True), bootstrap.Repo("tool-b", python=True)]
        self.assertEqual(bootstrap.check_pins(self.tmp, repos), [])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(bootstrap.cmd_check_pins(self.tmp, repos), 0)
        self.assertIn("devtools-common は aaa", out.getvalue())

    def test_mismatch_names_tools_to_align(self):
        self._pkg("tool-a", "tool-a", [f"devtools-common @ {self.COMMON_URL}@aaa"])
        self._pkg("tool-b", "tool-b", [f"devtools-common @ {self.COMMON_URL}@aaa"])
        self._pkg("lab/sub", "sub", [f"devtools-common @ {self.COMMON_URL}@bbb"])
        repos = [
            bootstrap.Repo("tool-a", python=True),
            bootstrap.Repo("tool-b", python=True),
            bootstrap.Repo("lab", python=True, packages="sub"),
        ]
        problems = bootstrap.check_pins(self.tmp, repos)
        self.assertEqual(len(problems), 1)
        self.assertIn("devtools-common の固定がツールごとに違います", problems[0])
        self.assertIn("bbb", problems[0])
        self.assertIn("そろえる: lab/sub の pyproject.toml の devtools-common の固定を aaa にする", problems[0])
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(bootstrap.cmd_check_pins(self.tmp, repos), 1)
        self.assertIn("NG", err.getvalue())

    def test_main_check_pins_and_ignored_cases(self):
        """optional-dependencies と、ほかのツールが URL で固定するパッケージ（手元の checkout は入れない）は見ない."""
        self._pkg("doc-to-markdown", "doc-to-markdown", [f"devtools-common @ {self.COMMON_URL}@aaa"])
        self._pkg(
            "office-review",
            "office-review",
            [f"devtools-common @ {self.COMMON_URL}@aaa"],
            optional={"convert": ["doc-to-markdown @ git+https://h/o/doc-to-markdown.git@old"]},
        )
        self._pkg("agent-lab/auto-review", "auto-review", [f"devtools-common @ {self.COMMON_URL}@zzz"])
        self._pkg(
            "review-platform",
            "review-platform",
            [
                f"devtools-common @ {self.COMMON_URL}@aaa",
                "auto-review @ git+https://h/o/agent-lab.git@x#subdirectory=auto-review",
            ],
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = bootstrap.main(["--root", str(self.tmp), "check-pins"])
        self.assertEqual(code, 0, out.getvalue())

        # 固定が食い違えば main も 1
        self._pkg("design-diff", "design-diff", [f"devtools-common @ {self.COMMON_URL}@bbb"])
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bootstrap.main(["--root", str(self.tmp), "check-pins"]), 1)
        self.assertIn("design-diff", err.getvalue())

    def test_setup_and_ci_run_check_pins_before_install(self):
        sh = (ROOT / "setup.sh").read_text(encoding="utf-8")
        self.assertLess(sh.index("check-pins"), sh.index('"${BS[@]}" install'))
        ps1 = (ROOT / "scripts" / "setup.ps1").read_text(encoding="utf-8-sig")
        self.assertLess(ps1.index("check-pins"), ps1.index('$installArgs = $bs + @("install")'))
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertEqual(ci.count("check-pins"), 2)  # windows と setup-sh


class PipFailureTest(unittest.TestCase):
    """pip が失敗したら、トレースバックではなく案内を出して 1 で終わる."""

    def test_install_failure_prints_hint(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "tool-a").mkdir()
        (tmp / "tool-a" / "pyproject.toml").write_text('[project]\nname = "tool-a"\n', encoding="utf-8")
        import subprocess
        from unittest import mock

        err, out = io.StringIO(), io.StringIO()
        fail = subprocess.CalledProcessError(1, ["pip"])
        with (
            mock.patch.object(bootstrap.subprocess, "run", side_effect=fail),
            contextlib.redirect_stderr(err),
            contextlib.redirect_stdout(out),
        ):
            code = bootstrap.cmd_install(tmp, [bootstrap.Repo("tool-a", python=True)], None, dry_run=False)
        self.assertEqual(code, 1)
        self.assertIn("インストールに失敗しました（pip の終了コード: 1）", err.getvalue())
        self.assertIn("check-pins", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_missing_python_executable_is_reported(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "tool-a").mkdir()
        (tmp / "tool-a" / "pyproject.toml").write_text('[project]\nname = "tool-a"\n', encoding="utf-8")
        from unittest import mock

        err = io.StringIO()
        with (
            mock.patch.object(bootstrap.subprocess, "run", side_effect=FileNotFoundError("python")),
            contextlib.redirect_stderr(err),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            code = bootstrap.cmd_install(tmp, [bootstrap.Repo("tool-a", python=True)], None, dry_run=False)
        self.assertEqual(code, 1)
        self.assertIn("インストールに失敗しました", err.getvalue())


class ReadmeNeighborCommonTest(unittest.TestCase):
    """README の「隣の devtools-common」の説明が doc-to-markdown の install_deps.py（隣にあれば editable）と合う."""

    def test_readme_describes_install_deps_behavior(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("同じフォルダに clone した devtools-common は使いません", text)
        self.assertIn("scripts/install_deps.py", text)
        self.assertIn("隣のフォルダに devtools-common があればそれを editable で入れて", text)
