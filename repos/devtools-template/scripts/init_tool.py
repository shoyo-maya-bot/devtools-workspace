#!/usr/bin/env python3
"""テンプレートから作ったリポジトリを、新しいツール名に初期化する（最初に 1 回だけ実行）.

    python scripts/init_tool.py api-spec-diff "OpenAPI 仕様の差分を抽出する"

- tool-name / tool_name / TOOL_DESCRIPTION を置き換え、src/tool_name を src/<package> に改名
- TOOL_README.md を README.md にする
- 初期化用のファイル（このスクリプトとそのテスト）を削除する
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".py", ".toml", ".md", ".yaml", ".yml", ".json", ".txt", ".cfg", ".example", ".ps1", ".sh", ".cmd"}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".ruff_cache", ".pytest_cache", "build", "dist"}
INIT_ONLY = ["scripts/init_tool.py", "tests/test_init_tool.py"]
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def init(root: Path, name: str, description: str) -> None:
    if not NAME_RE.match(name):
        raise SystemExit("ツール名は半角小文字のケバブケースにしてください（例: api-spec-diff）")
    if not (root / "src" / "tool_name").is_dir():
        raise SystemExit("初期化済みか、テンプレートの構成ではありません（src/tool_name が無い）")
    package = name.replace("-", "_")
    replacements = [("tool-name", name), ("tool_name", package), ("TOOL_DESCRIPTION", description)]

    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or set(rel.parts) & SKIP_DIRS or rel.as_posix() in INIT_ONLY:
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in {".env.example"}:
            continue
        raw = path.read_bytes()
        encoding = "cp932" if path.suffix == ".cmd" else "utf-8"  # .cmd は Windows のコマンドプロンプト用
        text = raw.decode(encoding)  # 改行コード・BOM はそのまま保つ（.ps1 は BOM + CRLF）
        new = text
        for old, rep in replacements:
            new = new.replace(old, rep)
        if new != text:
            path.write_bytes(new.encode(encoding))

    (root / "src" / "tool_name").rename(root / "src" / package)
    shutil.move(root / "TOOL_README.md", root / "README.md")
    for rel in INIT_ONLY:
        (root / rel).unlink(missing_ok=True)
    scripts = root / "scripts"
    if scripts.is_dir() and not any(scripts.iterdir()):
        scripts.rmdir()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="ツール名 = リポジトリ名（ケバブケース）")
    ap.add_argument("description", help="1 文の説明（責務）")
    args = ap.parse_args(argv)
    init(ROOT, args.name, args.description)
    print(f"initialized: {args.name}")
    print("次の手順: pip install -e '.[dev]' → pytest → src/ の core.py を自分の処理に置き換える")
    return 0


if __name__ == "__main__":
    sys.exit(main())
