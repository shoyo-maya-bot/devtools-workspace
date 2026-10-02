#!/usr/bin/env bash
# doc2md → fieldcheck パイプライン例: Excel の申請一覧を Markdown 化し、項目間の整合性を検証する
# 2 つのツールは別プロセスで繋ぐ（それぞれ単体でも使える）。
#
#   ./examples/expense-pipeline.sh [入力.xlsx] [ルール.yaml]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
INPUT="${1:-$ROOT/doc-to-markdown/samples/expense-list.xlsx}"
RULES="${2:-$ROOT/office-review/fieldcheck/samples/rules.yaml}"
OUT="${OUT:-out}"
STEM="$(basename "${INPUT%.*}")"

echo "== 1/2 doc2md: $INPUT → $OUT/$STEM.md"
doc2md "$INPUT" -d "$OUT" --strict -f json -o "$OUT/$STEM.convert.json"

echo "== 2/2 fieldcheck: $OUT/$STEM.md"
set +e
fieldcheck validate "$OUT/$STEM.md" -r "$RULES" --table "${TABLE:-申請一覧}" -f html -o "$OUT/$STEM.validation.html"
rc=$?
fieldcheck validate "$OUT/$STEM.md" -r "$RULES" --table "${TABLE:-申請一覧}"
set -e

echo "レポート: $OUT/$STEM.convert.json, $OUT/$STEM.validation.html"
exit $rc
