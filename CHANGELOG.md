# Changelog

形式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)、版は [SemVer](https://semver.org/lang/ja/) に従います。


## 2026-10-03 再構成

- リポジトリを用途別の 13 個に作り直した（repos.yaml）: dev-environment、ai-coding、office-review、design-diff、quality-analytics、
  office-replace、backlog-report、slack-agenda-bot、slide-tool、learning-materials を追加
- field-validation は office-review に、spec-trace は ai-coding に同梱。devtools-template・ai-prompt-kb は廃止（.github は今後のために残す）
- README・AGENTS.md・ARCHITECTURE・NEW_TOOL・VS Code ワークスペース・パイプライン例を新しい構成に合わせた
## [Unreleased]

### Added

- spec-trace を一覧（repos.yaml・README・VS Code ワークスペース）に追加
- Copilot への指示に AI エージェントの約束

## [0.2.0] - 2026-09-30

### Added

- setup.cmd / setup.sh（全リポの clone と一括インストール）
- Copilot: `.github/copilot-instructions.md`、`/check-excel`（doc2md → fieldcheck を通しで）
- docs/AI_USAGE.md（clone + Copilot で使う方針、MCP を見送った理由、情報の扱い）

## [0.1.0] - 2026-09-28

### Added

- 初版
