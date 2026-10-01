---
description: 業務ルール（文章・仕様書）から検証ルールの YAML を作り、実データで試す
agent: agent
argument-hint: 検証したいデータのパスと、守るべきルール（文章でよい）
---

次のデータに対する検証ルール（YAML）を作ってください。

- 検証するデータ: ${input:data:CSV / Markdown / JSON のパス（Excel なら先に doc2md で変換）}
- 守るべきルール: ${input:rules:例「合計は税抜と税額の和」「接待費は承認者が必須」「部門コードは部門マスタにある」}

## 手順

1. データの列名を確認する
   - CSV: 1 行目を読む / Markdown: 表の見出し行を読む（複数の表があれば、どの表か利用者に確認する）
   - Excel・Word・PDF の場合: `doc2md "<ファイル>" -d out -f json` で変換してから、`out/<名前>.md` の表を見る
2. `fieldcheck list-rules` を実行し、使えるルールの種類を確認する
3. `rules.yaml` を新しく作る（既存があれば上書きせず `rules.new.yaml`）
   - 先頭に `# yaml-language-server: $schema=<field-validation のフォルダ>/rules.schema.json` を書く
   - `fields:` に列と型（string / number / date）を書く
   - ルールごとに `id`（例: R-001）、`description`（日本語で何を確かめるか）、分かりやすい `message` と `suggestion` を付ける
   - 文章のルールを 1 つずつ対応づける。対応するルール型が無いものは `type: expression` と `assert:` の式で書く
   - 合計行・小計行があるときは `when: {field: <列>, not_equals: 合計}` で除外する
4. `fieldcheck check-rules rules.yaml` を実行し、終了コード 0 になるまで直す
5. `fieldcheck validate "<データ>" -r rules.yaml -f json`（Markdown なら `--table <見出し名>` も）で試す
6. 報告:
   - 作ったルールの一覧（id と、文章のどのルールに対応するか）を表で
   - 検証結果の要約（何件の指摘があり、どの行が何に違反したか）
   - 文章のルールのうち、ルールにできなかったもの・解釈に迷ったもの（必ず書く）

ルールの意図が曖昧なとき（例:「上限」が税込か税抜か）は、推測で決めずに利用者に質問してください。
