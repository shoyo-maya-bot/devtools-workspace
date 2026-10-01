# AGENTS.md — AI エージェント向けガイド（field-validation）

## このツールを「使う」とき

- 表データの整合性を確かめたいときは、自分でコードを書いて突き合わせる前に
  `fieldcheck validate <data> -r <rules.yaml> -f json` を実行し、`findings` を読む。
- ルールファイルを新しく書くときは `fieldcheck schema` の JSON Schema と `fieldcheck list-rules` に従い、
  書いたら `fieldcheck check-rules <rules.yaml>` で検証する（終了コード 0 になるまで直す）。
- Office / PDF は直接渡せない。先に `doc2md <file> -d out/` で Markdown にし、`--table <見出し名>` で表を選ぶ。
- 終了コード: 0 問題なし / 1 指摘あり / 2 ルール・入力スキーマの誤り（データではなく前提が違う）/ 3 実行時エラー。

## このリポジトリを「変更する」とき

- 責務は「検証」だけ。ファイル形式の変換（Excel 読み込み等）を足さない（doc-to-markdown の責務）。
- ルール型を追加: `src/field_validation/rules.py` に `Rule` を継承したクラスを書いて `@register`。
  `params_schema` / `required_params` / `field_params`（列名を指す引数）を必ず定義する
  （スキーマ検証と「列が無い」早期エラーに使われる）。空値は原則スキップし、必須判定は `required` に任せる。
- 別の表を参照するルールは `self.ctx.datasets`（`aggregate` / `keys`）を使い、自前でファイルを開かない
- 式を評価する機能を足すときは `expr.py` のホワイトリストに関数を追加する（`eval` / `exec` は使わない）
- 変更後に必ず実行: `ruff check . && ruff format --check . && pytest`
- レポートが変わるのが意図どおりなら `UPDATE_GOLDEN=1 pytest` → `tests/golden/` の差分を PR に含める。
- データ値をログに出さない。共通処理は `devtools-common` を使う。
