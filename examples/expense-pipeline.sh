#!/usr/bin/env bash
# doc2md → fieldcheck パイプライン例: Excel の申請一覧を Markdown 化し、項目間の整合性を検証する
# 2 つのツールは別プロセスで繋ぐ（それぞれ単体でも使える）。
#
#   ./examples/expense-pipeline.sh [入力.xlsx] [ルール.yaml]
#
# 前提: ワークスペースの setup（./setup.sh）で、兄弟フォルダの ../.venv に doc-to-markdown と office-review が入っていること。
# doc2md・fieldcheck は PATH にあればそれを、無ければ ../.venv/bin のものを使う（仮想環境の有効化は要らない）。
# 別の仮想環境を使うときは VENV=<仮想環境のフォルダ> を付けて実行する。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
INPUT="${1:-$ROOT/doc-to-markdown/samples/expense-list.xlsx}"
RULES="${2:-$ROOT/office-review/fieldcheck/samples/rules.yaml}"
OUT="${OUT:-out}"
STEM="$(basename "${INPUT%.*}")"
VENV="${VENV:-$ROOT/.venv}"

# ツールの場所: 指定した仮想環境（既定 ../.venv）の bin → PATH の順に探す
find_tool() {
  if [ -x "$VENV/bin/$1" ]; then
    printf '%s\n' "$VENV/bin/$1"
  elif command -v "$1" >/dev/null 2>&1; then
    command -v "$1"
  else
    return 1
  fi
}
missing=()
DOC2MD="$(find_tool doc2md)" || missing+=(doc2md)
FIELDCHECK="$(find_tool fieldcheck)" || missing+=(fieldcheck)
if [ ${#missing[@]} -gt 0 ]; then
  {
    echo "${missing[*]} が見つかりません（探した場所: $VENV/bin と PATH）。"
    echo "先にワークスペースの ./setup.sh を流して ../.venv に入れるか、"
    echo "入れた仮想環境を有効化する（source ../.venv/bin/activate）か、VENV=<仮想環境> を付けて実行してください。"
  } >&2
  exit 2
fi
for f in "$INPUT" "$RULES"; do
  [ -f "$f" ] || { echo "ファイルがありません: $f（doc-to-markdown・office-review を兄弟フォルダに取得してください）" >&2; exit 2; }
done

echo "== 1/2 doc2md: $INPUT → $OUT/$STEM.md"
"$DOC2MD" "$INPUT" -d "$OUT" --strict -f json -o "$OUT/$STEM.convert.json"

echo "== 2/2 fieldcheck: $OUT/$STEM.md"
set +e
"$FIELDCHECK" validate "$OUT/$STEM.md" -r "$RULES" --table "${TABLE:-申請一覧}" -f html -o "$OUT/$STEM.validation.html"
rc=$?
"$FIELDCHECK" validate "$OUT/$STEM.md" -r "$RULES" --table "${TABLE:-申請一覧}"
set -e

echo "レポート: $OUT/$STEM.convert.json, $OUT/$STEM.validation.html"
exit $rc
