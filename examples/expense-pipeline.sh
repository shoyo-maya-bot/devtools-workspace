#!/usr/bin/env bash
# doc2md → fieldcheck パイプライン例: Excel の申請一覧を Markdown 化し、項目間の整合性を検証する
# 2 つのツールは別プロセスで繋ぐ（それぞれ単体でも使える）。
#
#   ./examples/expense-pipeline.sh [入力.xlsx] [ルール.yaml]
#
# 前提: ワークスペースの setup（./setup.sh）で、兄弟フォルダの ../.venv に doc-to-markdown と office-review が入っていること。
# doc2md・fieldcheck は ../.venv/bin（VENV で変えられる）にあればそれを、無ければ PATH のものを使う（仮想環境の有効化は要らない）。
# 別の仮想環境を使うときは VENV=<仮想環境のフォルダ> を付けて実行する。
#
# 終了コード（どの段で何が起きたかを区別する）:
#   0 変換の警告なし・指摘なし
#   1 fieldcheck の指摘あり（変換の警告なし）
#   2 前提の誤り（ツール・入力が無い、doc2md・fieldcheck の引数・入力・ルールの誤り）
#   3 実行時エラー（doc2md・fieldcheck の想定外のエラー、変換結果の Markdown ができなかった）
#   4 doc2md --strict の変換の警告あり（変換ロスなど。fieldcheck は流した）・指摘なし
#   5 doc2md --strict の変換の警告あり・指摘あり
#   変換の警告があるときは、fieldcheck の結果を信じる前に $OUT/<名前>.convert.json の警告を確かめて元ファイルと突き合わせる
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

MD="$OUT/$STEM.md"
# 前回の出力が残っていると、変換できなかったのに古い Markdown を検証してしまうので消しておく
rm -f "$MD"

echo "== 1/2 doc2md: $INPUT → $MD"
set +e
"$DOC2MD" "$INPUT" -d "$OUT" --strict -f json -o "$OUT/$STEM.convert.json"
conv=$?
set -e
case "$conv" in
  0) ;;
  1)
    # --strict の警告（変換ロスなど）でも Markdown はできている. 項目間の検証は続け、最後に 4・5 で知らせる
    if [ ! -f "$MD" ]; then
      echo "doc2md: 変換できませんでした（$OUT/$STEM.convert.json を確かめてください）" >&2
      exit 3
    fi
    echo "doc2md: 変換の警告があります（$OUT/$STEM.convert.json）。fieldcheck は続けますが、元ファイルと突き合わせてください" >&2
    ;;
  2) echo "doc2md: 引数・入力の誤りで止まりました（終了コード 2）" >&2; exit 2 ;;
  *) echo "doc2md: 実行時エラーで止まりました（終了コード $conv）" >&2; exit 3 ;;
esac

echo "== 2/2 fieldcheck: $MD"
set +e
"$FIELDCHECK" validate "$MD" -r "$RULES" --table "${TABLE:-申請一覧}" -f html -o "$OUT/$STEM.validation.html"
rc=$?
"$FIELDCHECK" validate "$MD" -r "$RULES" --table "${TABLE:-申請一覧}"
set -e
case "$rc" in
  0 | 1) ;;
  2) echo "fieldcheck: ルール・列名・入力の誤りで止まりました（終了コード 2）" >&2; exit 2 ;;
  *) echo "fieldcheck: 実行時エラーで止まりました（終了コード $rc）" >&2; exit 3 ;;
esac

echo "レポート: $OUT/$STEM.convert.json, $OUT/$STEM.validation.html"
if [ "$conv" -eq 1 ]; then exit $((4 + rc)); fi
exit "$rc"
