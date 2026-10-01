---
id: "06"
title: Office ドキュメントレビュー（Python）
description: Word/Excel/PowerPoint 等のレビューを自動支援する Python ツールを、一般ベストプラクティスで設計するプロンプト。
category: tools
tags: [python, office, review, rule-engine]
status: published
version: 1.0.0
owner: "<your-team>"
updated: 2026-09-28
depends_on: ["00"]
---

# 06. Office ドキュメントレビュー（Python）

> Word/Excel/PowerPoint 等のレビューを自動支援する Python ツールを、一般ベストプラクティスで設計するプロンプト。

````text
あなたは Python ツール開発者です。Office ドキュメント（Word/Excel/PowerPoint）の
レビューを自動支援するツールを、一般的なベストプラクティスで設計してください。
特定企業の写しにはしないこと。

# 私が埋める前提
- 対象形式: {{.docx / .xlsx / .pptx / .pdf}}
- レビュー観点: {{表記ゆれ / 必須項目の欠落 / 体裁 / 用語統一 など}}

# 設計
- 入力アダプタ: python-docx / openpyxl / python-pptx 等で本文・表・メタを抽出
- ルールエンジン: レビュー観点をルール化（正規表現・辞書・スキーマ）
- レポート: 指摘一覧（該当箇所・重要度・修正提案）を Markdown/HTML/CSV で出力
- 設定: ルールセットを設定ファイル化（プロジェクト差し替え可能）
- テスト: サンプル文書に対するゴールデンテスト

# 品質・運用
- 大きなファイルのストリーム処理、文字コード配慮
- 機密文書を扱うため一時ファイルの安全な削除、ログに本文を残さない
- CLI とバッチ実行、CI 連携

# 出力
- ツール構成、抽出アダプタ、ルールエンジン、レポート生成、サンプルルール、テスト
````
