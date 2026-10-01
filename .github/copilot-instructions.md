# Copilot への指示（devtools-workspace）

このフォルダは、開発支援ツール群（1 ツール = 1 リポジトリ）の親ワークスペースです。
利用者は初心者の場合があります。日本語で、手順は番号付きで説明してください。

## 使えるツール

| やりたいこと | コマンド |
|---|---|
| Word / Excel / PowerPoint / PDF / draw.io の中身を読む | `doc2md <file> -d out -f json` → `out/<名前>.md` を読む |
| 表の整合性をルールでチェック | `fieldcheck validate <data> -r rules.yaml -f json`（Markdown の表は `--table <見出し>`） |
| 外部ツール（LibreOffice・OCR）の有無 | `doc2md --check-env` |
| 新しいツールを作る | [docs/NEW_TOOL.md](../docs/NEW_TOOL.md)（既存ツールに機能を足さない） |

- コマンドが見つからないときは `../.venv/Scripts/doc2md`（Windows）/ `../.venv/bin/doc2md` のように、setup が作った
  共有の仮想環境（1 つ上の `.venv`）の中のコマンドを使う。それも無ければ `setup.cmd` / `./setup.sh --org <組織名>` を案内する
- 文書・データの **ファイルを直接開かない**。必ずツールで変換・検証した結果を読む
- 実行結果の JSON の `warning` は利用者にそのまま伝える。終了コード 2 は前提（引数・列名・ルール）の誤り
- 機密の可能性がある内容をチャットに長く引用しない。社外のサービスにデータを送るコード・コマンドを提案しない
- AI 利用の注意は [docs/AI_USAGE.md](../docs/AI_USAGE.md) を参照
