---
title: 活用ナレッジ
description: プロンプトを使った事例と教訓を蓄積する場所
---

# 活用ナレッジ

プロンプトは使って初めて改善点が見えます。使った結果をここに残し、プロンプト本文の改善につなげます。

| 種類 | 置き場所 | 雛形 | 書くこと |
|---|---|---|---|
| [事例](cases/index.md) | `docs/knowledge/cases/` | `docs/templates/case-template.md` | どのプロンプトを、どんな前提で使い、何ができたか |
| [教訓](lessons/index.md) | `docs/knowledge/lessons/` | `docs/templates/lesson-template.md` | 失敗・つまずきと、その対策 |

## 書き方のルール

- ファイル名は `YYYY-MM-<topic>.md`（例: `2026-10-docs-portal-setup.md`）。
- front matter の `prompts` に関連プロンプトの id を入れる。
- **機密・固有名は書かない**。社名・案件名・内部 URL・実データは一般化する（CI の禁止パターン検査対象）。
- 追加したら各 `index.md` の一覧と `mkdocs.yml` の `nav` に 1 行追加する。
