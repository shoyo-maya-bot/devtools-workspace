# field-validation（fieldcheck）

構造化済みデータ（表 / YAML / JSON / 抽出済み項目）を入力に、**項目間の相関ルール** を評価する検証専用ツールです。
変換は行いません。Office / PDF は [doc-to-markdown](https://github.com/<your-org>/doc-to-markdown) で Markdown 化してから渡します（疎結合）。

## すぐ使う（3 ステップ）

1. このリポジトリを clone する（`devtools-common` も同じフォルダに clone しておくと GitHub の認証が不要）
2. **Windows**: `setup.cmd` をダブルクリック ／ **macOS・Linux**: `./setup.sh`
3. VS Code でこのフォルダを開き、Copilot Chat で次のプロンプトを使う

| Copilot のプロンプト | 何をするか |
|---|---|
| `/fieldcheck-write-rules` | 文章で書いた業務ルール（「合計は税抜と税額の和」など）から rules.yaml を作り、実データで試す |
| `/fieldcheck-run` | 検証を実行し、指摘を「どの行の何をどう直すか」の表で報告 |

## できること

| ルール型 | 例 |
|---|---|
| `required`（+ `when`） | 「区分 が 接待費 なら 承認者 は必須」 |
| `sum_equals` | 「合計 = 金額 + 税額」（許容誤差 `tolerance`） |
| `reference` | 「部門コード は部門マスタに存在」（マスタは CSV / YAML / JSON / 値リスト） |
| `range` | 数値・日付の値域 |
| `compare` | 「開始日 <= 終了日」「金額 <= 20000」 |
| `unique` | 一意性（複数項目の組み合わせも可） |
| `pattern` / `enum` / `length` | 書式・許可値・文字数 |
| `expression` | 任意の条件式: `0 <= days(終了日, 開始日) <= 30`、`value("金額/税込") == value("金額/税抜") + value("金額/税額")` |
| `aggregate_equals` | **表をまたぐ集計**: 「ヘッダの合計 = 明細（別の表・別ファイル）の金額の合計」を申請ID ごとに比較（sum / count / min / max） |
| `reference`（dataset） | **別ファイルとの参照整合性**: マスタを別の表の列から作る（例: 明細の申請ID はヘッダに存在） |
| プラグイン | Python で独自のルール型を追加（`--plugin` または entry point） |

- すべてのルールに `when`（適用条件: `equals` / `in` / `not_in` / `present` / `gt`〜`lte` / `all` / `any`）を付けられる
- `fields` に入力スキーマ（列と型）を宣言すると、**列が無ければ評価前に終了コード 2**（前提が崩れている）、
  型が合わない値は `schema.type` として指摘（その項目への二次的な指摘は抑止）
- レポートは Markdown / HTML / CSV / JSON。各指摘に **該当箇所・項目・期待値・実測値・修正提案** を含む

## インストール

```bash
pipx install "git+https://github.com/<your-org>/field-validation.git@v0.1.0"
```

## 使い方

```bash
fieldcheck validate data.csv -r rules.yaml                       # Markdown レポートを標準出力へ
fieldcheck validate data.csv -r rules.yaml -f html -o report.html
fieldcheck validate out/expense-list.md -r rules.yaml --table 申請一覧 -f json   # doc2md の出力を検証
fieldcheck validate data.csv -r rules.yaml --encoding cp932 --fail-on warning
fieldcheck check-rules rules.yaml                                # ルールファイルだけ検証（CI 用）
fieldcheck list-rules                                            # 使えるルール型と引数
fieldcheck schema > rules.schema.json                            # エディタ補完・AI 生成用の JSON Schema
fieldcheck --plugin my_rules.py validate data.csv -r rules.yaml  # カスタムルール
fieldcheck validate claims.csv -r rules.yaml --dataset 明細=lines.csv   # 参照する別の表を差し替え
```

入力形式: `.csv` `.tsv` `.json`（配列 or `{"records": [...]}`）`.jsonl` `.yaml` `.md`（GFM の表。`--table` で番号か直前の見出し名を指定）

### 終了コード

`0` 指摘なし（`--fail-on` 未満のみ） ／ `1` `--fail-on`（既定 error）以上の指摘あり ／ `2` 引数・ルールファイル・入力スキーマの誤り ／ `3` 実行時エラー

## ルールファイル

```yaml
# yaml-language-server: $schema=./rules.schema.json   ← VS Code の YAML 拡張で補完・検証が効く
version: 1
name: 経費申請の整合性
fields:                      # 入力スキーマ（前提）
  区分: {type: string}
  金額: {type: number}
  税額: {type: number}
  合計: {type: number}
  承認者: {type: string}
masters:
  部門: {file: masters/departments.csv, key: 部門コード}   # パスはルールファイルからの相対
rules:
  - id: EXP-002
    type: required
    when: {field: 区分, equals: 接待費}
    fields: [承認者]
    message: 接待費は承認者が必須です
    suggestion: 事前承認者を入力してください
  - id: EXP-003
    type: sum_equals
    total: 合計
    parts: [金額, 税額]
    severity: error           # error / warning / info（既定 error）
```

完全な例は [samples/rules.yaml](samples/rules.yaml)。ルールファイル自体も JSON Schema で検証され、
未知のルール型・引数の綴り間違いは実行前にエラーになります。

## 表をまたぐ検証（ヘッダと明細・別シート・別ファイル）

```yaml
datasets:                       # 参照する別の表（パスはルールファイルからの相対。--dataset で差し替え可）
  明細:
    file: claim-lines.csv       # Markdown なら table: で表（番号か直前の見出し名）を指定
masters:
  申請ID一覧: {dataset: 明細, key: 申請ID}   # 別の表の列をマスタにする
rules:
  - id: CR-001
    type: aggregate_equals      # ヘッダの 合計 = 明細の 金額 の合計（申請ID ごと）
    field: 合計
    group_by: 申請ID
    dataset: 明細
    dataset_field: 金額
    func: sum                   # sum / count / min / max。明細に無いキーは missing: error（既定）/ zero / ignore
  - id: CR-002
    type: expression            # 式は Python の安全なサブセット（eval は使わない）
    assert: "0 <= days(終了日, 開始日) <= 30"
```

サンプル: [samples/cross/](samples/cross/)（ヘッダと明細）、[samples/ledger/](samples/ledger/)（doc2md で変換した実務の Excel。
2 段見出し・合計行・同じシートの別表を使う）。式で使える関数は `fieldcheck list-rules` と
[src/field_validation/expr.py](src/field_validation/expr.py) の先頭を参照。

## doc-to-markdown との連携（パイプライン）

```bash
doc2md 申請一覧.xlsx -d out/
fieldcheck validate out/申請一覧.md -r rules.yaml --table 申請一覧
```

2 つのツールは別プロセスで繋ぎ、それぞれ単体で利用・テストできるように保ちます（責務を混ぜない）。

## カスタムルール（プラグイン）

[samples/plugins/weekday_rule.py](samples/plugins/weekday_rule.py) を参照。`Rule` を継承し `@register` するだけで、
ルールファイルの JSON Schema にも自動で反映されます。社内で共有する場合はパッケージにして entry point
`field_validation.rules` で配布します。

## 設計メモ

- **ストリーム評価**: CSV / JSONL は 1 行ずつ読み、レコードを保持しない。`unique` はキーのみ保持。
- **ゴールデンテスト**: `samples/` の入力に対する期待レポートを `tests/golden/` に置き回帰を検出。
- 値の解釈: 数値は `1,000` `¥1,000` `(1,000)` `▲1,000`（負数）`10%`（= 0.1）を許容。日付は `2026-04-01` `2026/04/01` `2026年4月1日`。
- 出力形式の約束: [docs/OUTPUT_SPEC.md](docs/OUTPUT_SPEC.md)（全ツール共通の schema_version 1.x）

## 開発

```bash
./setup.sh --dev          # Windows: .\scripts\setup.ps1 -Dev
ruff check . && ruff format --check . && pytest
UPDATE_GOLDEN=1 pytest    # 期待レポートの更新（差分を PR でレビュー）
```
