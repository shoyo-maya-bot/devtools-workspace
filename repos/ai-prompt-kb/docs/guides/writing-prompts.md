---
title: 執筆ガイド
description: プロンプトファイルの構成・front matter・本文の書き方
tags: [guide, contributing]
---

# 執筆ガイド

## ファイルの作り方

```bash
python scripts/kb.py new 09 api-diff-tool "API 差分抽出ツール" --category tools
```

`docs/templates/prompt-template.md` から `docs/prompts/09-api-diff-tool.md` が作られます。

## ファイル構成（1 プロンプト = 1 ファイル）

`````text
---                      ← front matter（メタデータ。カタログ・配布に使う）
id / title / description / category / tags / status / version / owner / updated / depends_on
---
# NN. タイトル
> 要約（1〜2 文）
````text               ← プロンプト本文（ここだけが AI に投入される）
役割宣言 + 「特定企業の写しにはしないこと。」
# 私が埋める前提        ← {{ }} プレースホルダ
# 設計してほしいこと / 設計 / 構成 など
# 出力                  ← 生成物のリスト
````
## 補足                 ← 任意。一般手法メモ・参考リンク
`````

## front matter

| キー | 必須 | 規則 |
|---|---|---|
| `id` | ✓ | 2 桁の文字列。ファイル名の番号と一致（`"09"`） |
| `title` | ✓ | H1 と同じ表記 |
| `description` | ✓ | 1 文。カタログ・Copilot プロンプトの説明に使われる |
| `category` | ✓ | `kb.config.yaml` の `categories` のいずれか |
| `tags` | ✓ | 1 つ以上。半角小文字ケバブケース |
| `status` | ✓ | `draft` / `review` / `published` / `deprecated` |
| `version` | ✓ | SemVer。[ライフサイクル](lifecycle.md) 参照 |
| `owner` | ✓ | チーム名などの担当（個人の連絡先は書かない） |
| `updated` | ✓ | `YYYY-MM-DD` |
| `depends_on` | ✓ | 先に実施すべきプロンプトの id のリスト（無ければ `[]`） |

## 本文の書き方

- **役割を宣言する**: 「あなたは○○です」で始め、期待する専門性を固定する。
- **前提は利用者に埋めさせる**: 変わりうる値はすべて `{{ }}` に出す。既定値や選択肢は `{{例: A / B}}` で示す。
- **出力を列挙する**: 何が生成されれば完了かを `# 出力` に具体的に書く（ファイル名・図・テスト）。
- **検証可能にする**: 品質ゲート・チェックリストなど、生成物の合否を判断できる基準を含める。
- **本文にコードフェンスを含める場合**は、外側を 4 連バッククォート（` ```` `）で囲む。
- **一般手法で書く**: 特定製品名は OSS・公開サービスのみ。社内ツール名は書かない。

## 提出前チェック

```bash
python scripts/kb.py catalog    # 収録表を更新
python scripts/kb.py validate   # 検証
mkdocs build --strict           # サイトのビルド
```

`mkdocs.yml` の `nav` への追加も忘れずに行ってください。
