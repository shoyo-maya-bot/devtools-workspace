# CONTRIBUTING

このリポジトリへの貢献方法です。まず [原則](docs/guides/principles.md) を読んでください。

## 貢献の種類

| やりたいこと | 手順 |
|---|---|
| 使ってみた結果を共有したい | `docs/knowledge/cases/` または `lessons/` に雛形から 1 ファイル追加して PR |
| プロンプトの改善を提案したい | Issue「プロンプト改善提案」を起票（PR まで出せるならそのまま PR で可） |
| 新しいプロンプトを追加したい | Issue「新規プロンプト」で目的を合意 → `kb.py new` で作成 → PR |
| 基盤（CI・スクリプト）を直したい | Issue で相談 → PR（`tests/` にテストを追加） |

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
npm install                        # markdownlint / textlint を使う場合
```

## 提出前チェック

```bash
python scripts/kb.py catalog       # 収録表を更新
python scripts/kb.py validate      # 原則・構成の検証
python -m unittest discover -s tests
mkdocs build --strict
npm run lint                       # 任意（CI では必須）
```

詳細な流れは [WORKFLOW.md](WORKFLOW.md)、書き方は [RULES.md](RULES.md) と
[執筆ガイド](docs/guides/writing-prompts.md) を参照してください。
