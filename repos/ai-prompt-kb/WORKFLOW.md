# WORKFLOW — 起票から公開・配布まで

```mermaid
flowchart TD
  A[Issue 起票<br/>新規プロンプト / 改善提案 / 事例共有] --> B[ブランチ作成<br/>feat/NN-slug, fix/NN-slug, docs/...]
  B --> C[執筆<br/>kb.py new / 本文編集 / version・updated 更新]
  C --> D[ローカル検証<br/>kb.py catalog → validate → mkdocs build --strict]
  D --> E[PR 作成<br/>テンプレートのチェックリストを埋める]
  E --> F{CI<br/>validate / lint / docs-build}
  F -- 失敗 --> C
  F -- 成功 --> G{レビュー<br/>CODEOWNERS 1 名以上}
  G -- 差し戻し --> C
  G -- 承認 --> H[main へ squash マージ]
  H --> I[GitHub Pages へ自動公開]
  H --> J{リリース?}
  J -- Yes --> K[VERSION / CHANGELOG 更新 → v* タグ push]
  K --> L[Release に配布 zip を添付]
```

## ブランチとコミット

- `main` は保護ブランチ（直 push 禁止・必須チェック・レビュー必須）。
- ブランチ名: `feat/<NN>-<slug>`（追加）、`fix/<NN>-<slug>`（修正）、`docs/<topic>`（ガイド・ナレッジ）、`chore/<topic>`（基盤）。
- コミットは [Conventional Commits](https://www.conventionalcommits.org/ja/v1.0.0/) に従う。
  例: `feat(prompts): add 09 api-diff-tool` / `fix(03): clarify quality gates`

## レビュー観点

| 観点 | 確認内容 |
|---|---|
| 原則 | 固有名・機密がない。一般手法で書かれている。実在資産の逐語コピーでない |
| 正確性 | 手法・ツール名・設定値が公開情報で裏取りできる |
| 網羅性 | `# 出力` を見れば完了条件がわかる。品質基準が含まれる |
| 再利用性 | 変わりうる値が `{{ }}` に出ている。前提を埋めれば他チームでも使える |
| 表記 | [RULES.md](RULES.md) に準拠 |
| 版 | `version` の上げ方が [ライフサイクル](docs/guides/lifecycle.md) に沿っている。`updated` 更新済み |
| リンク | 収録表・nav が更新され、`mkdocs build --strict` が通る |
