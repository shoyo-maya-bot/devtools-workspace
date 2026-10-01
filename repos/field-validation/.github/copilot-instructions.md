# Copilot への指示（field-validation）

このリポジトリは、表データ（CSV / Excel を変換した Markdown / JSON / YAML）の項目どうしの整合性を
YAML のルールで検証する CLI `fieldcheck` です。利用者は初心者の場合があります。日本語で、手順は番号付きで説明してください。

## ツールを使うとき

- 整合性の確認は、自分でスクリプトを書かずに `fieldcheck validate <データ> -r <rules.yaml> -f json` を使う
  （仮想環境が有効でなければ `.venv/Scripts/fieldcheck`（Windows）/ `.venv/bin/fieldcheck`）
- Excel / Word / PDF は直接渡せない。先に `doc2md <ファイル> -d out` で Markdown にし、`--table <見出し名>` で表を選ぶ
- ルールを書くとき:
  1. `fieldcheck list-rules` で使えるルールを確認（`expression` で任意の式、`aggregate_equals` で別の表との集計比較）
  2. 列名は **データの見出しと 1 文字も違わず** 書く（Excel 由来は `金額/税抜` のような 2 段見出しがある。`/` を含む列を式で使うときは `value("金額/税抜")`）
  3. 書いたら `fieldcheck check-rules <rules.yaml>` が終了コード 0 になるまで直す
- 終了コード: 0 問題なし / 1 指摘あり / 2 **前提の誤り**（ルールの書き方・列名・ファイルパス）。2 のときはデータではなく前提を直す
- 指摘は `location`（行番号）・`field`・`expected`・`actual` を使って、どの行のどの値をどう直せばよいかを具体的に説明する
- データの値をチャットに大量に貼らない。指摘のあった行だけ扱う

## コードを変更するとき

- [AGENTS.md](../AGENTS.md) の規約に従う（責務は検証だけ・ルール型は `@register` で追加・`params_schema` 必須）
- 変更後: `ruff check . && ruff format --check . && pytest`。ルール型を足したら `fieldcheck schema > rules.schema.json`
- 出力形式を変えるときは [docs/OUTPUT_SPEC.md](../docs/OUTPUT_SPEC.md) も更新する
