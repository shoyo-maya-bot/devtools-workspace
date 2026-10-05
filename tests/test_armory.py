"""devtools 武具屋（armory/index.html）の品揃えが repos.yaml とずれていないかを確かめる。"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import bootstrap  # noqa: E402

ARMORY = ROOT / "armory" / "index.html"


def armory_text() -> str:
    return ARMORY.read_text(encoding="utf-8")


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

    def test_every_item_has_skill(self):
        text = armory_text()
        blocks = re.split(r'^\{id:"', text, flags=re.M)[1:]
        for block in blocks:
            name = block.split('"', 1)[0]
            with self.subTest(item=name):
                self.assertIn("skill:{p:", block)
                self.assertRegex(block, r"steps:\[\s*\[")


if __name__ == "__main__":
    unittest.main()
