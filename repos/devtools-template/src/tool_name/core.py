"""ツールの本体（CLI から独立させ、単体テストしやすくする）.

テンプレートのサンプル実装: テキストファイルを設定のルールで検査し、指摘（Finding）を返す。
新しいツールでは、この関数を自分の処理に置き換える。入出力の型（Finding / 設定の dict）はそのまま使える。
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from devtools_common.log import get_logger
from devtools_common.report import Finding, Severity

log = get_logger(__name__)


def check_file(path: Path, config: dict[str, Any]) -> Iterator[Finding]:
    max_len = config.get("max_line_length")
    forbidden = [(re.compile(f["pattern"]), f) for f in config.get("forbidden", [])]
    with path.open(encoding=config.get("encoding", "utf-8")) as f:
        for lineno, line in enumerate(f, 1):  # 1 行ずつ読む（大きなファイルもメモリに載せない）
            line = line.rstrip("\n")
            loc = f"{path.name}:{lineno}"
            if max_len and len(line) > max_len:
                yield Finding(
                    "line-length",
                    Severity.WARNING,
                    "行が長すぎます",
                    location=loc,
                    expected=f"<= {max_len}",
                    actual=str(len(line)),
                    suggestion="行を分割してください",
                )
            for rx, spec in forbidden:
                if rx.search(line):
                    yield Finding(
                        spec.get("id", "forbidden"),
                        Severity(spec.get("severity", "error")),
                        spec.get("message", "禁止された表現があります"),
                        location=loc,
                        actual=rx.pattern,
                        suggestion=spec.get("suggestion", ""),
                    )


def run(paths: Iterable[Path], config: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    count = 0
    for p in paths:
        count += 1
        findings.extend(check_file(p, config))
    log.info("checked %d files: %d findings", count, len(findings))  # 本文はログに出さない
    return findings
