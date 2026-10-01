# Changelog

形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)、版は [SemVer](https://semver.org/lang/ja/) に従います。

## [Unreleased]

## [0.2.0] - 2026-09-30

### Added

- setup.cmd / setup.sh / scripts/install_deps.py（隣の devtools-common を優先して使う）
- Copilot: `.github/copilot-instructions.md`、`/implement-tool`（設計 → 実装 → テストを工程ごとに確認）

### Fixed

- init_tool.py がセットアップスクリプト（.ps1 / .sh / .cmd）の名前を置換していなかった。改行コード・BOM を保つよう修正

## [0.1.0] - 2026-09-28

### Added

- 初版
