#!/usr/bin/env bash
# ワークスペースのセットアップ（macOS / Linux）: 全リポジトリの取得と一括インストール
#   ./setup.sh               （組織名は repos.yaml の org。別の組織なら --org <組織名>）
#   ./setup.sh --only devtools-common,doc-to-markdown   一部のリポジトリだけ取得・インストールする
set -euo pipefail
cd "$(dirname "$0")"
ORG=""
ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --org) ORG="${2:-}"; shift 2 ;;
    --only) ONLY="${2:-}"; shift 2 ;;
    *) echo "使い方: ./setup.sh [--org <組織名>] [--only <名前,名前>]" >&2; exit 2 ;;
  esac
done
command -v git >/dev/null || { echo "Git をインストールしてください" >&2; exit 1; }
BS=(python3 scripts/bootstrap.py ${ONLY:+--only "$ONLY"})
"${BS[@]}" clone ${ORG:+--org "$ORG"}
"${BS[@]}" pull || echo "最新にできなかったリポジトリがあります（上の表示を確かめてください）。セットアップは続けます。" >&2
"${BS[@]}" install
if [ -x ../.venv/bin/doc2md ]; then ../.venv/bin/doc2md --check-env; fi
echo
echo "完了しました。VS Code で devtools.code-workspace を開き、Copilot Chat で / を入力してください。"
