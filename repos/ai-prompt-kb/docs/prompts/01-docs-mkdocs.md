---
id: "01"
title: ドキュメント系（MkDocs / Markdown）構成・命名規則（詳細）
description: MkDocs(Material) + Markdown による技術ドキュメント基盤を、ディレクトリ構成・命名規則・Front Matter・品質チェック・ガバナンスまで詳細設計するプロンプト。
category: docs
tags: [mkdocs, markdown, naming, governance, lint]
status: published
version: 1.0.0
owner: "<your-team>"
updated: 2026-09-28
depends_on: ["00"]
---

# 01. ドキュメント系（MkDocs / Markdown）構成・命名規則（詳細）

> MkDocs(Material) + Markdown による技術ドキュメント基盤を、**ディレクトリ構成・命名規則・
> Front Matter・品質チェック・ガバナンス**まで一般ベストプラクティスで詳細設計するプロンプト。

````text
あなたはドキュメント基盤のアーキテクトです。MkDocs(Material) + Markdown による技術
ドキュメントリポジトリを、一般的なベストプラクティスで詳細に設計・構築してください。
特定企業の写しにはしないこと。

# 私が埋める前提
- ドキュメント種別: {{例: 設計ガイドライン / API仕様 / 運用手順 / 学習資料}}
- 想定読者: {{例: 社内開発者}}
- 公開範囲: {{組織内 / 限定公開}}（機密は載せない）
- 言語: {{日本語 / 多言語}}

# 1. リポジトリ構成（この形を基準に、各要素の根拠つきで）
docs-repo/
├── docs/                         # 公開対象の Markdown 一式（mkdocs の docs_dir）
│   ├── index.md                  # サイトのトップ（入口・全体地図）
│   ├── <section>/                # 章＝ディレクトリ。例: guides/ api/ operations/
│   │   ├── index.md              # 章のランディング（概要＋子ページ目次）
│   │   ├── <topic>.md            # 各トピック（1トピック=1ファイル）
│   │   └── assets/               # その章専用の画像・図（近接配置）
│   ├── assets/                   # 全体共通の画像・図・ダウンロード物
│   │   ├── images/
│   │   └── diagrams/             # 図のソース(.drawio/.svg)と書き出し(png/svg)をペア管理
│   ├── includes/                 # 再利用スニペット（用語・注意書き・略語表）
│   ├── templates/                # 新規ページ雛形（front matter 込み）
│   └── stylesheets/              # 追加CSS（必要時）
├── overrides/                    # Material テーマの部分上書き（任意）
├── mkdocs.yml                    # サイト設定・ナビゲーション
├── .markdownlint.jsonc           # Markdown Lint 設定
├── .textlintrc                   # 日本語文章校正（任意）
├── .github/workflows/            # ビルド検証・デプロイ（02 と連携）
├── CONTRIBUTING.md               # 執筆・レビューの手引き
├── RULES.md                      # 文章スタイル/表記ルール（一般項目で新規作成）
├── WORKFLOW.md                   # 起票→執筆→レビュー→公開 の流れ
├── requirements.txt              # mkdocs, mkdocs-material, プラグイン群
└── README.md                     # リポの目的・ローカルプレビュー手順

# 2. 命名規則（明文化して出力）
- ファイル/ディレクトリ: 半角小文字ケバブケース（例: api-design-guideline.md）。
  空白・全角・大文字・記号を避ける。URL がそのままファイル名になる前提で付ける。
- 並び順が重要な章のみ数値プレフィックス（例: 10-overview.md, 20-basics.md）。
  10刻みで採番し、後から間に挿入できる余地を残す。
- 各ディレクトリに index.md を必須化（URL 末尾スラッシュを安定させ、章の入口を用意）。
- 画像: <topic>-<連番>.png など内容がわかる名前。原則その章の assets/ に近接配置。
- 図: 編集可能ソース(.drawio/.svg)と書き出し画像をペアで管理し、Markdown からは
  書き出し画像（または svg）を参照する。ソースだけ / 画像だけの片方運用は禁止。
- 見出しアンカー: 変更に強いよう簡潔に。相互参照が多い見出しは明示アンカーを付与。
- ドキュメント ID を台帳管理する場合は front matter の id で持つ
  （例: DOMAIN-CATEGORY-001）。ファイル名に無理に ID を含めない。

# 3. Front Matter 規約（YAML・全ページ共通）
title / description / tags / status(draft|review|published) / owner / updated を標準化。
docs/templates/ に雛形を置き、新規ページはコピーして書き始める運用にする。

# 4. mkdocs.yml の推奨設定
- theme: material（palette 明暗、features: navigation.instant / navigation.sections /
  navigation.tabs / navigation.top / search.suggest / content.code.copy / toc.follow）
- nav: 明示定義（自動収集に頼らず、章立てを PR でレビュー可能にする）
- markdown_extensions: admonition, pymdownx.superfences(+ mermaid), pymdownx.snippets
  (includes/ 参照), pymdownx.tabbed, toc(permalink: true), tables, attr_list, footnotes
- plugins: search, （任意）awesome-pages, git-revision-date-localized, mermaid2
- extra: バージョン切替や社内リンク（機密は載せない）

# 5. 図の扱い（一般手法）
- 単純な関係図/フロー: Mermaid をコードフェンス（```mermaid）で記述しテキスト管理。
- 複雑な図: draw.io(.drawio) で作図 → svg/png へ書き出し → Markdown から参照。
  差分レビューしやすいよう .drawio ソースも同じ assets/ に置く。

# 6. 品質チェック（CI で回す）
- markdownlint（体裁・見出し階層・行長）
- textlint（日本語の表記ゆれ・敬体/常体の統一・二重否定など）
- 内部リンク・画像・外部 URL のリンク切れチェック
- mkdocs build --strict（未定義参照・欠落を警告ではなくエラーにする）

# 7. ガバナンス（RULES.md / WORKFLOW.md を一般項目で新規作成）
- RULES.md: 見出し階層ルール、用語統一、単位・数値表記、コードブロックは言語指定必須、
  画像 alt 必須、機密を書かない、一文一義、能動態推奨 等
- WORKFLOW.md: ブランチ作成 → 執筆 → PR → レビュー観点（正確性/網羅性/表記/リンク）→
  承認 → main マージで自動公開、というフロー（Mermaid 図つき）

# 出力
1. 上記ディレクトリ構成の実体（空の index.md と章テンプレ、templates/ を含む）
2. mkdocs.yml の完成形
3. RULES.md / WORKFLOW.md / CONTRIBUTING.md / README.md / requirements.txt
4. Lint 設定（.markdownlint.jsonc / .textlintrc）と CI（ビルド検証）
5. ページテンプレート（front matter 込み）と図の配置例
````

## 補足（命名規則クイックリファレンス）

| 対象 | 規則 | 例 |
|---|---|---|
| ページ | ケバブケース + `.md` | `error-handling.md` |
| 順序つき章 | `NN-` 数値プレフィックス（10刻み） | `20-basics.md` |
| 章の入口 | 各ディレクトリに `index.md` 必須 | `guides/index.md` |
| 画像 | `<topic>-<連番>` | `sequence-01.png` |
| 図ソース | 書き出しとペア管理 | `flow.drawio` + `flow.svg` |
