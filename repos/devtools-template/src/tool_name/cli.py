"""tool-name — TOOL_DESCRIPTION

例:
  tool-name check docs/ --config config.yaml
  tool-name check README.md -f json -o report.json

終了コード: 0 指摘なし / 1 error の指摘あり / 2 引数・設定の誤り / 3 実行時エラー
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

import jsonschema
from devtools_common import cli as common_cli
from devtools_common import report
from devtools_common.config import load_dotenv, load_structured

from . import __version__

DEFAULT_CONFIG: dict[str, Any] = {"max_line_length": 120, "forbidden": []}


def load_config(path: Path | None) -> dict[str, Any]:
    """設定ファイルを読み、同梱の JSON Schema で検証する（誤りは実行前に終了コード 2）."""
    if path is None:
        return dict(DEFAULT_CONFIG)
    data = load_structured(path) or {}
    schema = json.loads(files("tool_name").joinpath("schemas/config.schema.json").read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        detail = "; ".join(f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in errors)
        raise common_cli.UsageError(f"設定ファイル {path} が不正です: {detail}")
    return {**DEFAULT_CONFIG, **data}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tool-name", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="ファイルを検査する")
    c.add_argument("paths", nargs="+", type=Path)
    c.add_argument("-c", "--config", type=Path, help="設定ファイル（YAML / JSON）")
    common_cli.add_common_args(c)
    return p


def _expand(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out += sorted(f for f in p.rglob("*") if f.is_file() and f.suffix in {".md", ".txt"})
        elif p.is_file():
            out.append(p)
        else:
            raise common_cli.UsageError(f"入力が見つかりません: {p}")
    return out


def main(argv: list[str] | None = None) -> int:
    load_dotenv()  # 外部 API のトークン等は .env（コミットしない）から。例は .env.example
    args = build_parser().parse_args(argv)
    common_cli.configure_from_args(args)

    from .core import run

    config = load_config(args.config)
    files_ = _expand(args.paths)
    findings = run(files_, config)
    text = report.render(findings, args.format, title="tool-name レポート", meta={"files": len(files_)})
    if args.output == "-":
        sys.stdout.write(text)
    else:
        Path(args.output).write_text(text, encoding="utf-8", newline="\n")
    return common_cli.ExitCode.FINDINGS if report.has_errors(findings) else common_cli.ExitCode.OK


def entrypoint() -> None:
    sys.exit(common_cli.run_main(main))


if __name__ == "__main__":
    entrypoint()
