---
id: "02"
title: プレビューサイト（GitHub Actions + GitHub Pages）
description: 01 で作った MkDocs ドキュメントを、PR プレビューと本番公開の両方で自動配信する CI/CD を構築するプロンプト。
category: docs
tags: [mkdocs, github-actions, github-pages, ci-cd]
status: published
version: 1.0.0
owner: "<your-team>"
updated: 2026-09-28
depends_on: ["01"]
---

# 02. プレビューサイト（GitHub Actions + GitHub Pages）

> 01 で作った MkDocs ドキュメントを、PR プレビューと本番公開の両方で自動配信する CI/CD を、
> 一般ベストプラクティスで構築するプロンプト。

````text
あなたは CI/CD エンジニアです。MkDocs(Material) のドキュメントを GitHub Actions で
ビルドし、GitHub Pages で公開するパイプラインを一般的なベストプラクティスで設計・
実装してください。特定企業の写しにはしないこと。

# 私が埋める前提
- ホスティング: {{GitHub Pages / 社内静的ホスティング}}
- 公開ブランチ: {{main}}
- 独自ドメイン: {{任意}}

# 実装してほしいこと
1. ビルド検証ワークフロー（PR 時）
   - Python セットアップ → pip install -r requirements.txt
   - markdownlint / textlint の実行
   - リンク切れチェック
   - mkdocs build --strict（警告をエラーにして未定義参照を検出）
   - 生成物を artifact として保存
2. プレビュー配信（PR 時・任意）
   - PR ごとにプレビュー URL を用意（GitHub Pages のサブパス、または
     PR プレビュー対応サービス）。PR にプレビュー URL をコメント。
3. 本番公開（main マージ時）
   - mkdocs gh-deploy 相当、または actions/deploy-pages を用いた Pages 公開
   - 権限は最小（permissions: pages: write, id-token: write）
   - concurrency 設定で多重デプロイを防止
4. 検索
   - MkDocs 標準の全文検索（lunr ベース）を有効化。日本語トークナイズに配慮。
5. 品質・運用
   - キャッシュ（pip / mkdocs）でビルド高速化
   - ビルド失敗時に main へマージできないよう必須チェック化
   - サイトマップ / 404 ページ

# 出力
- .github/workflows/docs-ci.yml（PR 検証）
- .github/workflows/docs-deploy.yml（main 公開）
- GitHub Pages 設定手順（README への追記）
- ローカルプレビュー手順（mkdocs serve）
- 独自ドメイン設定時の CNAME 手順（任意）
````

## 補足

- PR プレビューは、GitHub Pages のサブディレクトリ配信や、静的サイト向けプレビュー
  サービス（例: 各種ホスティングの Preview 機能）で実現できます。組織のポリシーに合う方式を選択してください。
- 全文検索は MkDocs 標準（lunr 相当）で完結します。日本語は分かち書きの精度に留意。
