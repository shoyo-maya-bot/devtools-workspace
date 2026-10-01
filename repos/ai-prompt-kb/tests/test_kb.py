"""scripts/kb.py のテスト（標準ライブラリ unittest。pytest でも実行可）."""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import kb  # noqa: E402


def quiet(fn, *args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = fn(*args, **kwargs)
    return rc, out.getvalue(), err.getvalue()


class RepoFixture(unittest.TestCase):
    """実リポジトリの必要部分を一時ディレクトリへコピーして検証する。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "repo"
        self.root.mkdir()
        for name in ["kb.config.yaml", "README.md", "VERSION"]:
            shutil.copy(REPO / name, self.root / name)
        shutil.copytree(REPO / "docs", self.root / "docs")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def prompt_path(self, pid="03"):
        return next((self.root / "docs" / "prompts").glob(f"{pid}-*.md"))

    def edit(self, path: Path, old: str, new: str):
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def errors(self) -> str:
        rc, _, err = quiet(kb.cmd_validate, self.root)
        return err if rc else ""


class ValidateTest(RepoFixture):
    def test_repository_is_valid(self):
        rc, out, err = quiet(kb.cmd_validate, self.root)
        self.assertEqual(rc, 0, err)
        self.assertIn("10 件", out)

    def test_missing_clean_room_phrase(self):
        self.edit(self.prompt_path(), "特定企業の写しにはしないこと。", "")
        self.assertIn("クリーンルーム文言", self.errors())

    def test_missing_required_section(self):
        self.edit(self.prompt_path(), "# 私が埋める前提", "# 前提")
        self.assertIn("必須見出し '# 私が埋める前提'", self.errors())

    def test_id_must_match_filename(self):
        self.edit(self.prompt_path(), 'id: "03"', 'id: "13"')
        self.assertIn("一致しません", self.errors())

    def test_invalid_status_and_version(self):
        p = self.prompt_path()
        self.edit(p, "status: published", "status: done")
        self.edit(p, "version: 1.0.0", "version: v1")
        errs = self.errors()
        self.assertIn("status 'done'", errs)
        self.assertIn("SemVer", errs)

    def test_unknown_dependency(self):
        self.edit(self.prompt_path(), 'depends_on: ["00"]', 'depends_on: ["42"]')
        self.assertIn("'42'", self.errors())

    def test_forbidden_pattern_detected(self):
        fake_key = "AKIA" + "ABCDEFGHIJKLMNOP"  # 文字列を分割してリポジトリ自身の検査に掛からないようにする
        guide = self.root / "docs" / "guides" / "how-to-use.md"
        guide.write_text(guide.read_text(encoding="utf-8") + f"\nkey {fake_key}\n", encoding="utf-8")
        self.assertIn("AWS アクセスキー", self.errors())

    def test_dotenv_file_rejected(self):
        (self.root / ".env").write_text("X=1\n", encoding="utf-8")
        (self.root / ".env.example").write_text("X=<your-value>\n", encoding="utf-8")
        errs = self.errors()
        self.assertIn("ERROR .env:", errs)
        self.assertNotIn("ERROR .env.example:", errs)

    def test_stale_catalog_detected(self):
        self.edit(self.prompt_path(), "title: AI 駆動コード生成フレームワーク", "title: 改題したフレームワーク")
        self.assertIn("収録表が古い", self.errors())
        rc, _, _ = quiet(kb.cmd_catalog, self.root, False)
        self.assertEqual(rc, 0)
        rc, _, err = quiet(kb.cmd_validate, self.root)
        self.assertEqual(rc, 0, err)


class ParseTest(unittest.TestCase):
    def test_four_backtick_fence_keeps_inner_fence(self):
        p = kb.parse_prompt(REPO / "docs" / "prompts" / "01-docs-mkdocs.md")
        self.assertEqual(p.fence_count, 1)
        self.assertIn("```mermaid", p.body)
        self.assertTrue(p.body.startswith("あなたはドキュメント基盤のアーキテクトです。"))
        self.assertTrue(p.body.rstrip().endswith("図の配置例"))


class NewExtractTest(RepoFixture):
    def test_new_creates_valid_draft(self):
        rc, _, err = quiet(kb.cmd_new, self.root, "10", "api-diff-tool", "API 差分抽出ツール", "tools")
        self.assertEqual(rc, 0, err)
        created = self.root / "docs" / "prompts" / "10-api-diff-tool.md"
        p = kb.parse_prompt(created)
        self.assertEqual(p.id, "10")
        self.assertEqual(p.meta["status"], "draft")
        quiet(kb.cmd_catalog, self.root, False)
        rc, _, err = quiet(kb.cmd_validate, self.root)
        self.assertEqual(rc, 0, err)

    def test_new_rejects_duplicate_and_bad_slug(self):
        self.assertEqual(quiet(kb.cmd_new, self.root, "03", "dup", "x", "tools")[0], 2)
        self.assertEqual(quiet(kb.cmd_new, self.root, "11", "Bad_Slug", "x", "tools")[0], 2)

    def test_extract_outputs_body_only(self):
        rc, out, _ = quiet(kb.cmd_extract, self.root, "7")
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith("あなたはドキュメントツール開発者です。"))
        self.assertNotIn("---\nid:", out)


class DistTest(RepoFixture):
    def test_dist_contents(self):
        zip_path = kb.build_dist(self.root, self.tmp / "out")
        version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(zip_path.name, f"ai-prompt-kb-{version}.zip")
        with zipfile.ZipFile(zip_path) as z:
            names = set(z.namelist())
            base = f"ai-prompt-kb-{version}/"
            for f in ["README.md", "catalog.json", "PRINCIPLES.md",
                      "prompts/00-repo-operations.md", "plain/00-repo-operations.txt",
                      "copilot/.github/prompts/00-repo-operations.prompt.md"]:
                self.assertIn(base + f, names)
            catalog = json.loads(z.read(base + "catalog.json"))
            self.assertEqual(len(catalog["prompts"]), 10)
            self.assertEqual(catalog["prompts"][0]["updated"], "2026-09-28")
            copilot = z.read(base + "copilot/.github/prompts/03-ai-codegen-framework.prompt.md").decode()
            self.assertTrue(copilot.startswith('---\ndescription: "'))

    def test_dist_excludes_drafts(self):
        self.edit(self.prompt_path("07"), "status: published", "status: draft")
        with zipfile.ZipFile(kb.build_dist(self.root, self.tmp / "out")) as z:
            self.assertFalse(any("07-slide-tool" in n for n in z.namelist()))


if __name__ == "__main__":
    unittest.main()
