---
id: "08"
title: ドキュメント Markdown 化（変換）ツール
description: 各種ドキュメント（Office/PDF/図）を Markdown + 抽出図に変換することだけに責務を絞ったツールを設計するプロンプト。検証は 09 に分離する。
category: tools
tags: [conversion, markdown, drawio, pdf, office]
status: published
version: 2.0.0
owner: "<your-team>"
updated: 2026-09-28
depends_on: ["00"]
---

# 08. ドキュメント Markdown 化（変換）ツール

> 各種ドキュメント（Office/PDF/図）を Markdown ＋ 抽出図に変換することだけに責務を絞ったツール。
> 検証は別ツール（[09-field-validation.md](09-field-validation.md)）に分離する。

````text
あなたはドキュメント処理エンジニアです。各種ドキュメント（Office/PDF/図）を Markdown に
変換する単機能ツールを、一般的なベストプラクティスで設計してください。検証機能は含めず、
変換に責務を絞ること。特定企業の写しにはしないこと。

# 私が埋める前提
- 入力: {{.docx / .xlsx / .pptx / .pdf / .drawio}}
- 出力: {{Markdown + 抽出図(svg/png)}}

# 変換パイプライン（一般手法）
1. 前処理: Office→PDF 変換を中間表現に使うと、レイアウト崩れの少ない抽出がしやすい
   （LibreOffice headless などの一般ツールで PDF 化 → テキスト/表を抽出）
2. 図: draw.io(.drawio) は svg/png へ書き出し、Markdown から参照。
   ソース(.drawio)と書き出しをペアで保管し差分レビュー可能に
3. 本文/表: python-docx / openpyxl / pdfplumber 等で抽出し Markdown へ整形
4. 正規化: 見出し階層・表・箇条書きを一定ルールで整える

# 品質・運用
- 中間ファイル（PDF 等）の安全な一時管理と削除、ログに機密本文を残さない
- 変換ロスの検知（元と変換後の項目数・見出し数チェック）
- 出力は決定的（同入力→同出力）にしてゴールデンテスト可能に
- CLI + バッチ + CI

# 出力
- ツール構成、変換アダプタ群（形式ごと）、正規化処理、変換ロス検知、サンプル、テスト
````

## 補足（一般手法メモ）

- **Office → PDF 中間変換**は、表・本文を安定抽出するためのよく知られた前処理（LibreOffice headless 等）。
- **draw.io の svg/png 書き出し＋ソース併存**は、図をテキスト管理下に置き差分レビュー可能にする一般運用。
