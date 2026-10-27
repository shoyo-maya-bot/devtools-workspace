"""learning-materials の章の数: README・repos.yaml・武具屋（armory）に書いた数がそろい、実際の章ファイルの数と合う.

後退: learning-materials が 73 章になったのに、README は「全 60 章」、
repos.yaml・armory はクラウド・案件担当の編が無い説明のままだった.
実物との照合は兄弟の learning-materials があるときだけ（週 1 回の latest-mains で main を取り出して流す。
そこでは LEARNING_MATERIALS_REQUIRE_CHECKOUT=1 で、無ければ失敗にする）.
"""

from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATED = re.compile(r"全 (\d+) 章と付録 (\d+)")
CHAPTER = re.compile(r"^\d{2}-\d{2}-.*\.md$")  # learning-materials の tests/test_chapter_counts.py と同じ数え方


def stated_counts() -> dict[str, tuple[int, int]]:
    texts = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "repos.yaml": (ROOT / "repos.yaml").read_text(encoding="utf-8"),
        "armory/index.html": (ROOT / "armory" / "index.html").read_text(encoding="utf-8"),
    }
    out = {}
    for name, text in texts.items():
        found = {(int(a), int(b)) for a, b in STATED.findall(text)}
        if len(found) != 1:
            raise AssertionError(f"{name} に「全 N 章と付録 M」が 1 通りだけ書かれていません: {found}")
        out[name] = found.pop()
    return out


def actual_counts(docs: Path) -> tuple[int, int]:
    parts = [d for d in docs.iterdir() if d.is_dir() and re.match(r"^\d{2}-", d.name)]
    chapters = sum(1 for d in parts for f in d.iterdir() if CHAPTER.match(f.name))
    appendix = sum(1 for f in (docs / "appendix").glob("*.md") if f.name != "index.md")
    return chapters, appendix


class LearningMaterialsChaptersTest(unittest.TestCase):
    def test_stated_counts_agree(self):
        counts = stated_counts()
        self.assertEqual(len(set(counts.values())), 1, counts)

    def test_stated_counts_match_checkout(self):
        docs = Path(os.environ.get("LEARNING_MATERIALS_DIR", ROOT.parent / "learning-materials")) / "docs"
        if not docs.is_dir():
            if os.environ.get("LEARNING_MATERIALS_REQUIRE_CHECKOUT") == "1":
                self.fail(f"learning-materials が見つかりません: {docs}")
            self.skipTest("兄弟の learning-materials が未取得（latest-mains で確かめる）")
        want = actual_counts(docs)
        for name, got in stated_counts().items():
            with self.subTest(file=name):
                self.assertEqual(got, want, f"{name} の章の数（章, 付録）が learning-materials の実物と違います")


if __name__ == "__main__":
    unittest.main()
