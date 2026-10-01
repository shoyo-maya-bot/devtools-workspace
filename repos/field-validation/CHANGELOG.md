# Changelog

形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)、版は [SemVer](https://semver.org/lang/ja/) に従います。

## [Unreleased]

## [0.2.0] - 2026-09-30

### Added

- `expression` ルール（安全な式の評価。日付計算・文字列関数・`value("列名")`）
- `aggregate_equals` ルール（表をまたぐ集計の一致: sum / count / min / max）
- `datasets:` と `--dataset`（別シート・別ファイルの参照）。`masters` を dataset の列・Markdown の表から作成
- 数値の `10%` `▲1,000` の解釈
- setup.cmd / setup.sh、Copilot のプロンプト（`/fieldcheck-write-rules`・`/fieldcheck-run`）、docs/OUTPUT_SPEC.md
- サンプル: samples/cross（ヘッダと明細）、samples/ledger（doc2md で変換した実務の Excel）

### Changed

- レポートの JSON に `schema_version` / `tool` / `tool_version`（devtools-common 0.2.0）

## [0.1.0] - 2026-09-28

### Added

- 初版
