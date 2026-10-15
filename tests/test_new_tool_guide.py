"""docs/NEW_TOOL.md の登録手順に、テストが repos.yaml と突き合わせるファイルがすべて書いてあるか.

手順どおりに登録しても、書いていないファイルの追記が漏れると CI のテストが落ちる。
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "docs" / "NEW_TOOL.md"


def registration_step() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index("**登録**")
    return text[start:]


class RegistrationStepTest(unittest.TestCase):
    # repos.yaml と一致するかをテストが確かめているファイル（tests/test_bootstrap.py・tests/test_armory.py）
    CHECKED_FILES = ("repos.yaml", "devtools.code-workspace", "armory/index.html", ".github/ci-repos.yaml")

    def test_every_checked_file_is_in_registration_step(self):
        step = registration_step()
        for name in self.CHECKED_FILES:
            with self.subTest(file=name):
                self.assertIn(f"`{name}`", step, f"NEW_TOOL.md の登録手順に {name} がありません")

    def test_armory_items_and_ci_ref_are_explained(self):
        step = registration_step()
        self.assertIn("ITEMS", step)
        self.assertIn("ref:", step)
        self.assertIn("python: true", step)

    def test_checked_files_exist(self):
        for name in self.CHECKED_FILES:
            with self.subTest(file=name):
                self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
