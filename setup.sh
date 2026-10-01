#!/usr/bin/env bash
# ワークスペースのセットアップ（macOS / Linux）: 全リポジトリの取得と一括インストール
#   ./setup.sh --org my-org
set -euo pipefail
cd "$(dirname "$0")"
ORG=""
[ "${1:-}" = "--org" ] && ORG="${2:-}"
[ -n "$ORG" ] || read -r -p "GitHub の組織名（例: my-org）: " ORG
command -v git >/dev/null || { echo "Git をインストールしてください" >&2; exit 1; }
python3 scripts/bootstrap.py clone --org "$ORG"
python3 scripts/bootstrap.py install
../.venv/bin/doc2md --check-env
echo
echo "完了しました。VS Code で devtools.code-workspace を開き、Copilot Chat で / を入力してください。"
