---
id: "00"
title: リポジトリ運用・親構成・設計思想（土台）
description: 複数リポ/ツールを束ねる「親ワークスペース」と、共通の運用ルールを一般ベストプラクティスで組み立てるプロンプト。
category: foundation
tags: [repository, workspace, governance, ci]
status: published
version: 1.0.0
owner: "<your-team>"
updated: 2026-09-28
depends_on: []
---

# 00. リポジトリ運用・親構成・設計思想（土台）

> 複数リポ/ツールを束ねる「親ワークスペース」と、共通の運用ルールを一般ベストプラクティスで組み立てるプロンプト。

````text
あなたはリポジトリ設計のアーキテクトです。複数の関連リポジトリ（アプリ、バッチ、
ドキュメント、開発支援ツール）を束ねる開発ワークスペースの土台を、一般的な
ベストプラクティスで設計してください。特定企業の写しにはしないこと。

# 私が埋める前提
- ドメイン: {{例: 業務システム / 社内基盤}}
- 主要言語: {{例: Java(Spring Boot), Python, TypeScript}}
- 構成方針: {{マルチリポ / モノレポ / ハイブリッド}}
- CI/CD: {{GitHub Actions など}}

# 設計してほしいこと
1. 親ワークスペースの考え方
   - 各リポの責務境界（アプリ / バッチ / 共通ライブラリ / ドキュメント / ツール）を明確化
   - VS Code マルチルートワークスペース（*.code-workspace）の例
2. 各リポ共通の運用ルール（root に置くファイル）
   - README.md（目的・セットアップ・主要コマンド）
   - CONTRIBUTING.md（ブランチ戦略・PR・レビュー観点・コミット規約 例: Conventional Commits）
   - CODEOWNERS / PR テンプレート / Issue テンプレート
   - .editorconfig / .gitignore / .gitattributes
   - ライセンス表記と第三者 OSS の扱い（NOTICE / THIRD-PARTY）
3. 品質ゲートの共通化
   - lint / format / test / セキュリティスキャン（SAST, 依存脆弱性）を CI 必須化
   - ブランチ保護（必須チェック、レビュー必須、直 push 禁止）
4. 設計思想の明文化（docs か root の DESIGN.md）
   - 単一責任・疎結合・SSOT（正の情報源を1箇所に）
   - 自動検証を優先し、人は境界で承認する運用
5. セキュリティ既定
   - .env はコミットしない。秘密は Secrets/Vault。テンプレは .env.example に <your-value>

# 出力
- 上記 root ファイル群の実体（テンプレート）
- ブランチ戦略と PR/レビューのフロー図（Mermaid）
- CI の共通ワークフロー雛形
````
