# Changelog

このファイルは [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) の形式に従い、
配布パッケージの版は [SemVer](https://semver.org/lang/ja/) で管理します。

## [Unreleased]

## [1.1.0] - 2026-09-28

### Changed

- 05 をマルチレポ前提に改訂（2.0.0）：1 ツール = 1 リポ、テンプレートリポ、共有ライブラリ、org の再利用ワークフロー、選定メモ
- 08 を「ドキュメント Markdown 化（変換）ツール」に改訂（2.0.0、ファイル名 `08-doc-to-markdown.md`）。検証を分離

### Added

- 09 項目間検証（クロスフィールド検証）ツール

### Removed

- `08-doc-convert-validate.md`（08 / 09 に分割）

## [1.0.0] - 2026-09-28

### Added

- プロンプト 00〜08 を収録（リポジトリ運用 / MkDocs 構成 / プレビューサイト / AI 駆動コード生成 /
  学習資料 / 開発支援ツール集 / Office レビュー / スライド生成 / ドキュメント変換・検証）
- `scripts/kb.py`（validate / catalog / new / extract / dist）
- MkDocs サイト、CI 検証、GitHub Pages 公開、Release 配布のワークフロー
- 活用ナレッジ（事例・教訓）の置き場と雛形
