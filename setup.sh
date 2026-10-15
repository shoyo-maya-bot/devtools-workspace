#!/usr/bin/env bash
# ワークスペースのセットアップ（macOS / Linux）: 全リポジトリの取得と一括インストール
#   ./setup.sh               （組織名は repos.yaml の org。別の組織なら --org <組織名>）
#   ./setup.sh --only devtools-common,doc-to-markdown   一部のリポジトリだけ取得・インストールする
#   ./setup.sh --dev         開発者向け: devtools-common をローカルの checkout で置き換えて入れる（既定は各ツールが固定した版）
#   ./setup.sh --manifest <ファイル>   repos.yaml の代わりに使うマニフェスト（CI では ref を SHA で固定したものを使う）
# Python は 3.12 以上が要る（版の判定は scripts/python_version.py の 1 か所。python3.14 → … → python3 の順に探す）
set -euo pipefail
cd "$(dirname "$0")"
ORG=""
ONLY=""
DEV=""
MANIFEST=""
while [ $# -gt 0 ]; do
  case "$1" in
    --org) ORG="${2:-}"; shift 2 ;;
    --only) ONLY="${2:-}"; shift 2 ;;
    --dev) DEV="--dev"; shift ;;
    --manifest) MANIFEST="${2:-}"; shift 2 ;;
    *) echo "使い方: ./setup.sh [--org <組織名>] [--only <名前,名前>] [--dev] [--manifest <ファイル>]" >&2; exit 2 ;;
  esac
done
command -v git >/dev/null || { echo "Git をインストールしてください" >&2; exit 1; }
PY=""
for c in python3.14 python3.13 python3.12 python3 python; do
  command -v "$c" >/dev/null || continue
  if "$c" scripts/python_version.py --quiet; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  # 見つからなかった理由（今の版）を表示する
  if command -v python3 >/dev/null; then python3 scripts/python_version.py || true; fi
  echo "Python 3.12 以上が見つかりません。https://www.python.org/downloads/ から 3.12 を入れてください" >&2
  exit 1
fi
"$PY" scripts/python_version.py
BS=("$PY" scripts/bootstrap.py ${MANIFEST:+--manifest "$MANIFEST"} ${ONLY:+--only "$ONLY"})
"${BS[@]}" clone ${ORG:+--org "$ORG"}
"${BS[@]}" pull || echo "最新にできなかったリポジトリがあります（上の表示を確かめてください）。ref を指定したリポジトリが ref にそろっていなければ、インストールの前に止めます。" >&2
# 一括インストールの前に、各ツールが固定した devtools-common などの版がそろっているかを確かめる
# （食い違うと pip が衝突で止まる。どのツールの固定をそろえるかを表示して止める）。--dev はローカルの checkout で置き換えるので見ない
if [ -z "$DEV" ]; then
  "${BS[@]}" check-pins || { echo "固定がそろっていないため、インストールを止めました（上の表示を確かめてください）" >&2; exit 1; }
fi
"${BS[@]}" install ${DEV:+"$DEV"}
if [ -x ../.venv/bin/doc2md ]; then ../.venv/bin/doc2md --check-env; fi
echo
echo "完了しました。VS Code で devtools.code-workspace を開き、Copilot Chat で / を入力してください。"
