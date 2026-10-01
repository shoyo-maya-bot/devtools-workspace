# tool-name

TOOL_DESCRIPTION

<!-- 責務は 1 文で。やらないこと（他ツールの責務）も書く -->

## すぐ使う（3 ステップ）

1. このリポジトリを clone する（`devtools-common` も同じフォルダに clone しておくと GitHub の認証が不要）
2. **Windows**: `setup.cmd` をダブルクリック ／ **macOS・Linux**: `./setup.sh`
3. `.venv` を有効にして `tool-name --help`（または VS Code の Copilot Chat から使う）

CLI だけ入れる場合: `pipx install "git+https://github.com/<your-org>/tool-name.git@v0.1.0"`

## 使い方

```bash
tool-name check docs/ --config config.yaml
tool-name check README.md -f json -o report.json    # CI・AI エージェント向け
```

### 入力と出力

| 項目 | 内容 |
|---|---|
| 入力 | <!-- 例: Markdown / テキストファイル、またはそれを含むディレクトリ --> |
| 設定 | YAML / JSON（スキーマ: `src/tool_name/schemas/config.schema.json`、例: `config.example.yaml`） |
| 出力 | レポート（Markdown / HTML / CSV / JSON）を標準出力または `-o` のファイルへ |

### 終了コード

`0` 指摘なし ／ `1` error の指摘あり ／ `2` 引数・設定の誤り ／ `3` 実行時エラー

## 秘密情報

外部 API のトークン等は `.env.example` をコピーした `.env` に書く（`.env` はコミットしない）。

## 開発

```bash
./setup.sh --dev          # Windows: .\scripts\setup.ps1 -Dev
ruff check . && ruff format --check . && pytest
```

リリース: `pyproject.toml` の version と CHANGELOG を更新 → マージ → `git tag v0.1.0 && git push origin v0.1.0`
