---
title: ホーム
description: AI 活用プロンプト集（クリーンルーム / 一般ベストプラクティス版）のトップページ
---

# AI 活用プロンプト集

!!! note "クリーンルーム版"
    これは特定の勤務先・客先の資産を写したものではありません。
    公開情報・OSS・公式ドキュメントで裏取りできる範囲の**一般的なベストプラクティス**から、
    同種のリポジトリ／ツール／ドキュメント基盤を**新規に**構築するためのプロンプト集です。

## はじめに

<div class="grid cards" markdown>

- :material-rocket-launch: **[使い方](guides/how-to-use.md)**

    プロンプトを AI エージェントに投入し、工程境界でレビューしながら進める手順

- :material-format-list-numbered: **[プロンプト一覧](prompts/index.md)**

    収録 10 本と推奨順序（依存関係図）

- :material-shield-check: **[原則](guides/principles.md)**

    固有名・機密を入れない、複製を目的にしない

- :material-lightbulb-on: **[活用ナレッジ](knowledge/index.md)**

    使ってみた事例と教訓を蓄積する場所

</div>

## 全体像

```mermaid
flowchart LR
  subgraph 土台
    P00[00 リポジトリ運用]
  end
  subgraph ドキュメント
    P01[01 MkDocs 構成] --> P02[02 プレビューサイト]
    P04[04 学習資料]
  end
  subgraph AI駆動開発
    P03[03 コード生成FW]
  end
  subgraph 開発支援ツール
    P05[05 ツール集マルチレポ]
    P06[06 Office レビュー]
    P07[07 スライド生成]
    P08[08 Markdown 化] --> P09[09 項目間検証]
  end
  P00 --> P01 & P03 & P04 & P05 & P06 & P07 & P08
```

## 貢献する

プロンプトの改善・追加や活用事例の共有は、[執筆ガイド](guides/writing-prompts.md) と
[ライフサイクル](guides/lifecycle.md) を参照してください。
