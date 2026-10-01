---
id: "07"
title: スライド生成 / 変換ツール
description: Markdown 等からスライドを生成・変換するツールを、一般ベストプラクティスで設計するプロンプト。
category: tools
tags: [slides, marp, reveal-js, markdown, export]
status: published
version: 1.0.0
owner: "<your-team>"
updated: 2026-09-28
depends_on: ["00"]
---

# 07. スライド生成 / 変換ツール

> Markdown 等からスライドを生成・変換するツールを、一般ベストプラクティスで設計するプロンプト。

````text
あなたはドキュメントツール開発者です。テキスト（Markdown 等）からスライドを生成・
変換するツールを、一般的なベストプラクティスで設計してください。特定企業の写しには
しないこと。

# 私が埋める前提
- 入力: {{Markdown / 構造化テキスト}}
- 出力: {{HTML スライド(reveal.js/Marp) / PPTX / PDF}}
- テーマ: {{コーポレートテンプレ（自作）}}

# 設計
- パーサ: Markdown をスライド単位（--- 区切り等）に分割
- レンダラ: Marp / reveal.js などの一般 OSS を利用、テーマは CSS で分離
- 図表: Mermaid、画像埋め込み、コードハイライト対応
- エクスポート: HTML/PDF/PPTX への書き出し
- 設定: テーマ・フッタ・ページ番号を設定ファイル化

# 出力
- ツール構成、変換パイプライン、サンプルテーマ、入出力サンプル、CLI、テスト
````
